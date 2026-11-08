"""New task observer with global budget callback; old seven-case monitor stays unchanged."""
import ctypes as c,json,os,subprocess,sys,time,hashlib
from pathlib import Path
from version_cost_process_monitor import api,checked,Extended,Startup,Process,Accounting,probe
from ctypes import wintypes as w

def run_task(root,worker,spec_path,*,wall_s,rss_B,global_snapshot,on_created):
    root=Path(root);root.mkdir(exist_ok=False);work=root/'work';work.mkdir();start,cpu=time.perf_counter(),time.process_time()
    k,p=api();job=None;pi=Process();assigned=False;resumed=False;reason=None;error=None;final=None;code=None;account=None;samples=[]
    def event(name,**fields):
        with (root/'events.jsonl').open('ab') as f:f.write(json.dumps({'event':name,'elapsed_s':time.perf_counter()-start,**fields},sort_keys=True).encode()+b'\n');f.flush();os.fsync(f.fileno())
    try:
        job=k.CreateJobObjectW(None,None);checked(job);ex=Extended();ex.Basic.Flags=0x2108;ex.Basic.Active=1;ex.ProcessMemory=512<<20;checked(k.SetInformationJobObject(job,9,c.byref(ex),c.sizeof(ex)))
        exe=Path(sys._base_executable).resolve().with_name('pythonw.exe');si=Startup();si.cb=c.sizeof(si)
        cmd=c.create_unicode_buffer(subprocess.list2cmdline([str(exe),'-I','-S',str(Path(worker).resolve()),str(work.resolve()),str(Path(spec_path).resolve())]))
        checked(k.CreateProcessW(str(exe),cmd,None,None,False,0x08000004,None,str(work.resolve()),c.byref(si),c.byref(pi)))
        created={'pid':int(pi.pid),'worker_sha256':hashlib.sha256(Path(worker).read_bytes()).hexdigest(),'spec_sha256':hashlib.sha256(Path(spec_path).read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()};event('created_suspended',**created)
        checked(k.AssignProcessToJobObject(job,pi.process));assigned=True
        initial=probe(k,p,pi.process);event('assigned_and_observed',created_FILETIME=initial['created_FILETIME']);on_created(created)
        budget=global_snapshot()
        if budget['reason']:reason=budget['reason'];checked(k.TerminateJobObject(job,0xE0000011))
        else:
            if k.ResumeThread(pi.thread)==0xffffffff:raise c.WinError(c.get_last_error())
            resumed=True;event('resumed')
        while True:
            wait=k.WaitForSingleObject(pi.process,0)
            if wait not in (0,258):raise OSError('Unrecognized process wait')
            state=probe(k,p,pi.process);budget=global_snapshot();elapsed=time.perf_counter()-start
            samples.append({'elapsed_s':elapsed,'phase':'exited' if wait==0 else 'running','process':state,'global':budget})
            if reason is None:
                if budget['reason']:reason=budget['reason']
                elif state['peak_rss_B']>rss_B:reason='task_rss_limit'
                elif elapsed>wall_s:reason='task_wall_limit'
            if wait==0:break
            if reason:
                checked(k.TerminateJobObject(job,0xE0000011));event('terminated_owned_job',reason=reason)
                if k.WaitForSingleObject(pi.process,5000)!=0:raise RuntimeError('Exit not observed after own Job termination')
                break
            time.sleep(.01)
    except BaseException as exc:
        reason='observation_unavailable';error={'type':type(exc).__name__,'message':str(exc)};event('fail_closed',error=error)
        if pi.process:
            checked(k.TerminateJobObject(job,0xE0000012) if assigned else k.TerminateProcess(pi.process,0xE0000012))
            if k.WaitForSingleObject(pi.process,5000)!=0:raise RuntimeError('Unobserved owned process exit')
    finally:
        try:
            if pi.process:
                actual=w.DWORD();checked(k.GetExitCodeProcess(pi.process,c.byref(actual)));code=int(actual.value)
                if code==259:raise RuntimeError('Live task cannot be complete')
                if reason!='observation_unavailable':
                    try:final=probe(k,p,pi.process)
                    except BaseException as exc:reason='observation_unavailable';error={'type':type(exc).__name__,'message':str(exc)}
                event('actual_exit_observed',pid=int(pi.pid),actual_exit_code=code,final_metrics=final)
            if job:
                a=Accounting();checked(k.QueryInformationJobObject(job,1,c.byref(a),c.sizeof(a),None));account={'total':int(a.Total),'active':int(a.Active)}
                if pi.process and account!={'total':1,'active':0}:reason='job_scope_violation'
        finally:
            for handle in (pi.thread,pi.process,job):
                if handle:checked(k.CloseHandle(handle))
    if reason is None and code!=0:reason='task_exit_nonzero'
    result={'status':'completed' if reason is None and code==0 else 'stopped','reason':reason,'pid':int(pi.pid) if pi.pid else None,'resumed':resumed,'actual_exit_code':code,'final_process_metrics':final,'job_accounting':account,'samples':samples,'error':error,'parent_wall_s':time.perf_counter()-start,'parent_self_cpu_s':time.process_time()-cpu,'physical_IO_and_full_system_resources':None,'limits_are_observed_not_instantaneous':True}
    with (root/'monitor.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.flush();os.fsync(f.fileno())
    return result
