"""Private Windows held-handle observer. Sampled RSS/disk refusal is not a hard RSS/disk quota."""
import ctypes as c
from ctypes import wintypes as w
import hashlib,json,os,subprocess,sys,time
from pathlib import Path

class Basic(c.Structure):
    _fields_=[('ProcessTime',c.c_longlong),('JobTime',c.c_longlong),('Flags',w.DWORD),('MinWS',c.c_size_t),('MaxWS',c.c_size_t),('Active',w.DWORD),('Affinity',c.c_size_t),('Priority',w.DWORD),('Scheduling',w.DWORD)]
class IO(c.Structure):_fields_=[(n,c.c_ulonglong) for n in ('ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes')]
class Extended(c.Structure):_fields_=[('Basic',Basic),('IO',IO),('ProcessMemory',c.c_size_t),('JobMemory',c.c_size_t),('PeakProcess',c.c_size_t),('PeakJob',c.c_size_t)]
class Accounting(c.Structure):_fields_=[(n,c.c_longlong) for n in ('User','Kernel','PeriodUser','PeriodKernel')]+[(n,w.DWORD) for n in ('Faults','Total','Active','Terminated')]
class Startup(c.Structure):
    _fields_=[('cb',w.DWORD),('reserved',w.LPWSTR),('desktop',w.LPWSTR),('title',w.LPWSTR)]+[(n,w.DWORD) for n in ('x','y','sx','sy','charsx','charsy','fill','flags')]+[('show',w.WORD),('reserved_B',w.WORD),('reserved_p',c.POINTER(c.c_byte)),('stdin',w.HANDLE),('stdout',w.HANDLE),('stderr',w.HANDLE)]
class Process(c.Structure):_fields_=[('process',w.HANDLE),('thread',w.HANDLE),('pid',w.DWORD),('tid',w.DWORD)]
class Memory(c.Structure):
    _fields_=[('cb',w.DWORD),('faults',w.DWORD)]+[(n,c.c_size_t) for n in ('PeakWS','WS','PeakPaged','Paged','PeakNonPaged','NonPaged','PrivateCommit','PeakPrivateCommit')]

def api():
    if os.name!='nt' or c.sizeof(c.c_void_p)!=8:raise RuntimeError('This private observer requires Windows64')
    assert c.sizeof(Basic)==64 and c.sizeof(Extended)==144 and c.sizeof(Startup)==104
    k=c.WinDLL('kernel32',use_last_error=True);p=c.WinDLL('psapi',use_last_error=True)
    specs={'CreateJobObjectW':([c.c_void_p,w.LPCWSTR],w.HANDLE),'SetInformationJobObject':([w.HANDLE,c.c_int,c.c_void_p,w.DWORD],w.BOOL),'QueryInformationJobObject':([w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.c_void_p],w.BOOL),'CreateProcessW':([w.LPCWSTR,w.LPWSTR,c.c_void_p,c.c_void_p,w.BOOL,w.DWORD,c.c_void_p,w.LPCWSTR,c.POINTER(Startup),c.POINTER(Process)],w.BOOL),'AssignProcessToJobObject':([w.HANDLE,w.HANDLE],w.BOOL),'ResumeThread':([w.HANDLE],w.DWORD),'WaitForSingleObject':([w.HANDLE,w.DWORD],w.DWORD),'GetExitCodeProcess':([w.HANDLE,c.POINTER(w.DWORD)],w.BOOL),'GetProcessTimes':([w.HANDLE,c.POINTER(w.FILETIME),c.POINTER(w.FILETIME),c.POINTER(w.FILETIME),c.POINTER(w.FILETIME)],w.BOOL),'TerminateJobObject':([w.HANDLE,w.UINT],w.BOOL),'TerminateProcess':([w.HANDLE,w.UINT],w.BOOL),'CloseHandle':([w.HANDLE],w.BOOL)}
    for name,(args,result) in specs.items():f=getattr(k,name);f.argtypes=args;f.restype=result
    p.GetProcessMemoryInfo.argtypes=[w.HANDLE,c.POINTER(Memory),w.DWORD];p.GetProcessMemoryInfo.restype=w.BOOL
    return k,p
def checked(result):
    if not result:raise c.WinError(c.get_last_error())
def probe(k,p,process):
    m=Memory();m.cb=c.sizeof(m);checked(p.GetProcessMemoryInfo(process,c.byref(m),m.cb))
    created,exited,kernel,user=(w.FILETIME() for _ in range(4));checked(k.GetProcessTimes(process,c.byref(created),c.byref(exited),c.byref(kernel),c.byref(user)))
    ticks=lambda t:(t.dwHighDateTime<<32)|t.dwLowDateTime
    return {'created_FILETIME':ticks(created),'kernel_cpu_s':ticks(kernel)/1e7,'user_cpu_s':ticks(user)/1e7,'peak_rss_B':int(m.PeakWS),'rss_B':int(m.WS),'private_commit_B':int(m.PrivateCommit),'peak_private_commit_B':int(m.PeakPrivateCommit)}
def disk_bytes(root):
    total=0
    for p in root.rglob('*'):
        if p.is_symlink():raise ValueError('Refuse links in owned worker outputs')
        if p.is_file():total+=p.stat().st_size
    return total
def run_owned(root,worker,mode,*,wall_s,rss_B,output_B,commit_B=256<<20,owned_probe_failure=False):
    if any(type(v) is not int or v<=0 for v in (rss_B,output_B,commit_B)) or type(wall_s) not in (float,int) or not 0<wall_s<=30:raise ValueError('Bounded positive limits required')
    root=Path(root).resolve();root.mkdir(exist_ok=False);work=root/'work';work.mkdir();worker=Path(worker).resolve()
    start,cpu=time.perf_counter(),time.process_time();k,p=api();job=None;pi=Process();resumed=False;assigned=False;cause=None;error=None;exit_code=None;final=None;samples=[];account=None
    limits={'wall_s':wall_s,'rss_B':rss_B,'worker_output_logical_B':output_B,'OS_private_commit_B':commit_B,'poll_s':0.01,'active_process_limit':1}
    def event(name,**fields):
        with (root/'events.jsonl').open('ab') as f:f.write(json.dumps({'event':name,'elapsed_s':time.perf_counter()-start,**fields},sort_keys=True).encode()+b'\n');f.flush();os.fsync(f.fileno())
    try:
        job=k.CreateJobObjectW(None,None);checked(job);ex=Extended();ex.Basic.Flags=0x2000|0x8|0x100;ex.Basic.Active=1;ex.ProcessMemory=commit_B;checked(k.SetInformationJobObject(job,9,c.byref(ex),c.sizeof(ex)))
        base=Path(getattr(sys,'_base_executable',sys.executable)).resolve();executable=base.with_name('pythonw.exe')
        image=executable.read_bytes();pe=int.from_bytes(image[0x3c:0x40],'little')
        if image[:2]!=b'MZ' or image[pe:pe+4]!=b'PE\x00\x00' or int.from_bytes(image[pe+24+68:pe+24+70],'little')!=2:raise ValueError('Frozen no-console Python image required')
        si=Startup();si.cb=c.sizeof(si);cmd=[str(executable),'-I','-S',str(worker),str(work),mode];command=c.create_unicode_buffer(subprocess.list2cmdline(cmd))
        checked(k.CreateProcessW(str(executable),command,None,None,False,0x4|0x08000000,None,str(work),c.byref(si),c.byref(pi)))
        event('created_suspended',pid=int(pi.pid),worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),avoids_venv_launcher=True,no_console_GUI_subsystem=True)
        checked(k.AssignProcessToJobObject(job,pi.process));assigned=True;event('assigned_single_process_job')
        if owned_probe_failure:raise OSError('Owned simulated first-observation failure')
        initial=probe(k,p,pi.process);samples.append({'elapsed_s':time.perf_counter()-start,'phase':'suspended',**initial,'output_B':0})
        if k.ResumeThread(pi.thread)==0xffffffff:raise c.WinError(c.get_last_error())
        resumed=True;event('resumed')
        while True:
            wait=k.WaitForSingleObject(pi.process,0)
            if wait not in (0,258):raise OSError('Unknown wait result')
            state=probe(k,p,pi.process);size=disk_bytes(work);elapsed=time.perf_counter()-start
            samples.append({'elapsed_s':elapsed,'phase':'exited' if wait==0 else 'running',**state,'output_B':size})
            if state['peak_rss_B']>rss_B:cause='rss_limit'
            elif size>output_B:cause='output_limit'
            elif elapsed>wall_s:cause='wall_limit'
            if wait==0:break
            if cause:
                checked(k.TerminateJobObject(job,0xE0000001));event('terminated_owned_job',reason=cause)
                if k.WaitForSingleObject(pi.process,5000)!=0:raise RuntimeError('Owned process exit not observed')
                break
            time.sleep(0.01)
    except BaseException as exc:
        cause='observation_unavailable';error={'type':type(exc).__name__,'message':str(exc)};event('fail_closed',error=error)
        if pi.process:
            checked(k.TerminateJobObject(job,0xE0000002) if assigned else k.TerminateProcess(pi.process,0xE0000002))
            if k.WaitForSingleObject(pi.process,5000)!=0:raise RuntimeError('Owned failed-observation process still unobserved')
    finally:
        try:
            if pi.process:
                code=w.DWORD();checked(k.GetExitCodeProcess(pi.process,c.byref(code)));exit_code=int(code.value)
                if exit_code==259:raise RuntimeError('Cannot report a live worker as exited')
                # An intentionally unavailable observation remains null, even if cleanup could read it.
                if cause!='observation_unavailable':
                    try:final=probe(k,p,pi.process)
                    except BaseException as exc:cause='observation_unavailable';error={'type':type(exc).__name__,'message':str(exc)};final=None
                if final and final['peak_rss_B']>rss_B and cause is None:cause='rss_limit'
                event('actual_exit_observed',exit_code=exit_code,final_metrics=final)
            if job:
                a=Accounting();checked(k.QueryInformationJobObject(job,1,c.byref(a),c.sizeof(a),None));account={'total_processes':int(a.Total),'active_processes':int(a.Active),'terminated_processes':int(a.Terminated)}
        finally:
            for handle in (pi.thread,pi.process,job):
                if handle:checked(k.CloseHandle(handle))
    result={'status':'completed' if cause is None and exit_code==0 else 'stopped','reason':cause or ('exit_nonzero' if exit_code!=0 else None),'pid':int(pi.pid) if pi.pid else None,'resumed':resumed,'actual_exit_code':exit_code,'final_process_metrics':final,'job_accounting':account,'limits':limits,'samples':samples,'maximum_observed_output_B':max((s['output_B'] for s in samples),default=None),'error':error,'parent_wall_s':time.perf_counter()-start,'parent_self_cpu_s':time.process_time()-cpu,'full_system_or_other_process_resources':None,'RSS_and_disk_limits_are_sampled_not_instantaneous':True,'worker_footer_used_as_process_exit_witness':False}
    with (root/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.flush();os.fsync(f.fileno())
    return result
