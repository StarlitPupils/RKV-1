"""Independent held-Job deadline for quota preflight; not the single-process archive worker."""
import ctypes as c,hashlib,json,math,os,subprocess,sys,time
from ctypes import wintypes as w
from pathlib import Path
from version_cost_process_monitor import api,checked,Extended,Startup,Process,Accounting

def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1<<20),b''):h.update(part)
    return h.hexdigest()
def allowed(record):
    try:
        if record['mode']!='official' or record['reason'] is not None or record['root_exit_code']!=0 or not record['cleanup_confirmed'] or record['job_final']['active']!=0:return False
        result=record['worker_result'];footer=record['worker_footer'];read=result['read_record']
        if result['pid']!=record['root_pid'] or footer['pid']!=record['root_pid'] or result['spec_sha256']!=record['spec_sha256'] or footer['spec_sha256']!=record['spec_sha256'] or not footer['success']:return False
        if read['failure'] is not None or len(read['held_app_servers'])!=1 or not all(r['pipes_closed'] and r['actual_exit_code'] is not None for r in read['held_app_servers']):return False
        value=read['summary'];primary=value['primary'];used=primary['usedPercent'];reset=primary['resetsAt']
        return value['ordinaryUsageAllowed'] is True and type(used) in (int,float) and math.isfinite(used) and 0<=used<100 and type(reset) is int and abs(reset-record['authorized_reference'])<=60
    except (KeyError,TypeError,ValueError):return False

def run_bounded(root,spec,*,deadline,cleanup_s=2.):
    start,cpu=time.perf_counter(),time.process_time();root=Path(root).resolve();root.mkdir(exist_ok=False);work=root/'work';work.mkdir();spec_path=root/'spec.json'
    raw=json.dumps(spec,sort_keys=True,separators=(',',':')).encode();spec_path.write_bytes(raw);spec_sha=sha(raw)
    k,p=api();job=None;pi=Process();assigned=False;reason=None;error=None;job_final=None;root_exit=None;members={};samples=[];cleanup_confirmed=False;result=footer=None
    class IDs(c.Structure):_fields_=[('assigned',w.DWORD),('listed',w.DWORD),('pids',c.c_size_t*32)]
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
    k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,c.POINTER(w.DWORD)];k.QueryFullProcessImageNameW.restype=w.BOOL
    def event(name,**fields):
        with (root/'events.jsonl').open('ab') as f:f.write(json.dumps({'event':name,'elapsed_s':time.perf_counter()-start,**fields},sort_keys=True).encode()+b'\n');f.flush();os.fsync(f.fileno())
    def capture(phase):
        a=Accounting();checked(k.QueryInformationJobObject(job,1,c.byref(a),c.sizeof(a),None));ids=IDs();checked(k.QueryInformationJobObject(job,3,c.byref(ids),c.sizeof(ids),None));assert ids.listed<=32
        row={'phase':phase,'elapsed_s':time.perf_counter()-start,'total':int(a.Total),'active':int(a.Active),'pids':list(ids.pids)[:ids.listed],'job_user_cpu_s':a.User/1e7,'job_kernel_cpu_s':a.Kernel/1e7}
        for pid in row['pids']:
            if pid in members:continue
            handle=pi.process if pid==int(pi.pid) else k.OpenProcess(0x1000|0x100000,False,pid)
            member={'pid':pid,'handle':handle,'image_path':None,'creation_FILETIME':None,'actual_exit_code':None,'observation_error':None}
            if handle:
                try:
                    buffer=c.create_unicode_buffer(32768);size=w.DWORD(len(buffer));checked(k.QueryFullProcessImageNameW(handle,0,buffer,c.byref(size)));member['image_path']=buffer.value
                    created,ended,kernel,user=(w.FILETIME() for _ in range(4));checked(k.GetProcessTimes(handle,c.byref(created),c.byref(ended),c.byref(kernel),c.byref(user)));member['creation_FILETIME']=(created.dwHighDateTime<<32)|created.dwLowDateTime
                except BaseException as exc:member['observation_error']=type(exc).__name__
            else:member['observation_error']='member_handle_unavailable'
            members[pid]=member
        samples.append(row);return row
    try:
        if time.perf_counter()>=deadline:reason='deadline_before_launch'
        else:
            frozen=Path(spec['freeze_path']).read_bytes();assert sha(frozen)==spec['freeze_sha256'];freeze=json.loads(frozen)
            for path,item in freeze['absolute_files'].items():assert file_sha(path)==item['sha256'],path
            if spec['mode']=='official':assert file_sha(freeze['quota_cli']['path'])==freeze['quota_cli']['sha256']
            if time.perf_counter()>=deadline:reason='deadline_before_launch'
            else:
                job=k.CreateJobObjectW(None,None);checked(job);ex=Extended();ex.Basic.Flags=0x2308;ex.Basic.Active=8;ex.ProcessMemory=256<<20;ex.JobMemory=512<<20;checked(k.SetInformationJobObject(job,9,c.byref(ex),c.sizeof(ex)))
                exe=Path(sys._base_executable).resolve().with_name('pythonw.exe');worker=Path(spec['worker']).resolve();si=Startup();si.cb=c.sizeof(si);cmd=c.create_unicode_buffer(subprocess.list2cmdline([str(exe),'-I','-S',str(worker),str(work),str(spec_path)]))
                checked(k.CreateProcessW(str(exe),cmd,None,None,False,0x08000004,None,str(work),c.byref(si),c.byref(pi)));event('root_created_suspended',pid=int(pi.pid),worker_sha256=sha(worker.read_bytes()),spec_sha256=spec_sha,executable_sha256=sha(exe.read_bytes()))
                checked(k.AssignProcessToJobObject(job,pi.process));assigned=True;capture('assigned_before_resume')
                if time.perf_counter()>=deadline:reason='deadline_before_resume'
                else:
                    if k.ResumeThread(pi.thread)==0xffffffff:raise c.WinError(c.get_last_error())
                    event('root_resumed')
                    while True:
                        state=capture('observing');now=time.perf_counter()
                        if now>=deadline:reason='deadline';break
                        wait=k.WaitForSingleObject(pi.process,min(20,max(1,math.ceil((deadline-now)*1000))))
                        if wait not in (0,258):raise RuntimeError('Unknown held-process wait')
                        if wait==0 and state['active']==0:break
                        if wait==0:time.sleep(.005)
    except BaseException as exc:reason='observation_unavailable';error={'type':type(exc).__name__,'message':str(exc)}
    finally:
        cleanup_deadline=time.perf_counter()+cleanup_s
        try:
            if pi.process:
                if reason is not None:
                    checked(k.TerminateJobObject(job,0xE0000021) if assigned else k.TerminateProcess(pi.process,0xE0000021));event('terminated_owned_scope',reason=reason)
                while True:
                    job_final=capture('cleanup') if assigned else None
                    if k.WaitForSingleObject(pi.process,0)==0 and (job_final is None or job_final['active']==0):break
                    if time.perf_counter()>=cleanup_deadline:raise RuntimeError('Owned Job cleanup not confirmed')
                    time.sleep(.005)
                code=w.DWORD();checked(k.GetExitCodeProcess(pi.process,c.byref(code)));root_exit=int(code.value);assert root_exit!=259
                for member in members.values():
                    if member['handle'] and k.WaitForSingleObject(member['handle'],0)==0:
                        code=w.DWORD();checked(k.GetExitCodeProcess(member['handle'],c.byref(code)));member['actual_exit_code']=int(code.value)
                cleanup_confirmed=True;event('root_exit_and_job_quiescent',pid=int(pi.pid),actual_exit_code=root_exit,active=job_final['active'] if job_final else None)
            else:cleanup_confirmed=True
        except BaseException as exc:reason='cleanup_unconfirmed';error={'type':type(exc).__name__,'message':str(exc)}
        finally:
            for member in members.values():
                if member['handle'] and member['handle']!=pi.process:checked(k.CloseHandle(member['handle']))
            for handle in (pi.thread,pi.process,job):
                if handle:checked(k.CloseHandle(handle))
    if reason is None:
        try:
            for name in ('result.json','finally.json'):assert (work/name).stat().st_size<=1<<20
            result=json.loads((work/'result.json').read_bytes());footer=json.loads((work/'finally.json').read_bytes())
            if time.perf_counter()>=deadline:reason='deadline_before_permission'
        except BaseException as exc:reason='output_or_exit_invalid';error={'type':type(exc).__name__,'message':str(exc)}
    record={'mode':spec['mode'],'authorized_reference':spec['authorized_reference'],'spec_sha256':spec_sha,'root_pid':int(pi.pid) if pi.pid else None,'root_exit_code':root_exit,'reason':reason,'error':error,'cleanup_confirmed':cleanup_confirmed,'job_final':job_final,'members':[{k:v for k,v in member.items() if k!='handle'} for member in members.values()],'samples':samples,'worker_result':result,'worker_footer':footer,'partial_result_exists':(work/'result.json').exists(),'wall_s':time.perf_counter()-start,'parent_self_cpu_s':time.process_time()-cpu,'deadline_from_start_s':deadline-start,'cleanup_reserve_s':cleanup_s,'full_system_RSS_and_IO':None,'hard_realtime_millisecond_guarantee':False}
    record['permission']=allowed(record)
    if not record['permission'] and record['reason'] is None:record['reason']='quota_or_evidence_denied'
    with (root/'observation.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.flush();os.fsync(f.fileno())
    return record
