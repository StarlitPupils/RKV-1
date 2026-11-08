"""Resource-clean wrapper around unchanged official reader; never changes/retries its RPCs."""
import contextlib,importlib.util,io,json,subprocess,time
from pathlib import Path

class GuardReadError(RuntimeError):
    def __init__(self,message,record):super().__init__(message);self.record=record

def read_official(script,*,owned_fail_after_spawn=False):
    script=Path(script);module_spec=importlib.util.spec_from_file_location('official_quota_owned_scope',script);module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
    held=[];records=[];start,cpu=time.perf_counter(),time.process_time();buffer=io.StringIO();failure=None;parsed=None
    class LocalSubprocessView:
        def __getattr__(self,name):return getattr(subprocess,name)
        def Popen(self,*args,**kwargs):
            process=subprocess.Popen(*args,**kwargs);held.append(process)
            if owned_fail_after_spawn:raise OSError('Owned injected failure after app-server creation,before any RPC')
            return process
    # Only the fresh official module's subprocess binding changes. The stdlib/global subprocess object stays intact.
    module.subprocess=LocalSubprocessView()
    try:
        with contextlib.redirect_stdout(buffer):module.read()
        parsed=json.loads(buffer.getvalue())
    except BaseException as exc:failure={'type':type(exc).__name__,'message':str(exc)}
    finally:
        for process in held:
            row={'pid':process.pid,'actual_exit_code':None,'pipes_closed':False,'cleanup_error':None}
            try:
                if process.poll() is None:process.terminate()
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
                row['actual_exit_code']=process.returncode
                for stream in (process.stdin,process.stdout,process.stderr):
                    if stream is not None:stream.close()
                row['pipes_closed']=all(stream is None or stream.closed for stream in (process.stdin,process.stdout,process.stderr))
            except BaseException as exc:row['cleanup_error']={'type':type(exc).__name__,'message':str(exc)};failure=failure or row['cleanup_error']
            records.append(row)
    record={'summary':parsed,'failure':failure,'held_app_servers':records,'wall_s':time.perf_counter()-start,'parent_self_cpu_s':time.process_time()-cpu,'app_server_CPU_RSS':None,'official_RPC_source_unchanged':True,'RPC_retries':0,'owned_failure_before_RPC':owned_fail_after_spawn}
    if failure is not None:raise GuardReadError('Quota reader/cleanup unavailable',record)
    if len(records)!=1 or not all(r['pipes_closed'] and r['actual_exit_code'] is not None for r in records):raise GuardReadError('Quota cleanup evidence incomplete',record)
    return record
