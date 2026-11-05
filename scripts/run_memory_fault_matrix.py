"""Private bounded Memory/process integration; no original science, no replay."""
import os,sys,time,json,subprocess,hashlib
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from rkv1.memory import Memory
from rkv1.benchmark import peak_rss
from scripts.execution_receipts import create,inspect,exclusive,encoded,sha
from scripts.memory_fault_fixture import source,file_ledger,audit_result

class Producer:
 def __init__(self,pid,launcher):
  if type(pid) is not int or pid<=0 or pid==os.getpid():raise ValueError('Invalid owned producer PID')
  self.pid,self.launcher,self.handle=pid,launcher,None
  if os.name=='nt':
   import ctypes
   from ctypes import wintypes
   self.dll=ctypes.WinDLL('kernel32',use_last_error=True)
   self.dll.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];self.dll.OpenProcess.restype=wintypes.HANDLE
   self.dll.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];self.dll.WaitForSingleObject.restype=wintypes.DWORD
   self.dll.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT];self.dll.TerminateProcess.restype=wintypes.BOOL
   self.dll.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];self.dll.GetExitCodeProcess.restype=wintypes.BOOL
   self.dll.CloseHandle.argtypes=[wintypes.HANDLE]
   if pid!=launcher.pid:
    class ProcessEntry(ctypes.Structure):
     _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('pid',wintypes.DWORD),('heap',ctypes.c_size_t),('module',wintypes.DWORD),('threads',wintypes.DWORD),('parent',wintypes.DWORD),('priority',wintypes.LONG),('flags',wintypes.DWORD),('exe',wintypes.WCHAR*260)]
    self.dll.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];self.dll.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    self.dll.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(ProcessEntry)];self.dll.Process32FirstW.restype=wintypes.BOOL
    self.dll.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(ProcessEntry)];self.dll.Process32NextW.restype=wintypes.BOOL
    snapshot=self.dll.CreateToolhelp32Snapshot(2,0)
    if snapshot==ctypes.c_void_p(-1).value:raise OSError('Cannot bind producer to owned launcher')
    matched=False
    try:
     entry=ProcessEntry();entry.size=ctypes.sizeof(entry);valid=self.dll.Process32FirstW(snapshot,ctypes.byref(entry))
     while valid:
      if entry.pid==pid:matched=entry.parent==launcher.pid;break
      valid=self.dll.Process32NextW(snapshot,ctypes.byref(entry))
    finally:self.dll.CloseHandle(snapshot)
    if not matched:raise ValueError('Producer PID not direct owned launcher child')
   self.handle=self.dll.OpenProcess(0x100000|0x1000|1,False,pid)
   if not self.handle:raise OSError(ctypes.get_last_error(),'Cannot retain exact owned producer handle')
 def kill(self):
  if self.handle:
   if not self.dll.TerminateProcess(self.handle,77):raise OSError('Owned producer termination failed')
  else:
   import signal
   if self.pid!=self.launcher.pid:raise ValueError('POSIX fixture expected direct child')
   os.kill(self.pid,signal.SIGKILL)
 def exit(self):
  if self.handle:
   import ctypes
   from ctypes import wintypes
   if self.dll.WaitForSingleObject(self.handle,30000)!=0:raise TimeoutError('Producer not exited')
   value=wintypes.DWORD()
   if not self.dll.GetExitCodeProcess(self.handle,ctypes.byref(value)):raise OSError('Cannot observe exact producer exit')
   return value.value
  return self.launcher.wait(timeout=30)
 def close(self):
  if self.handle:self.dll.CloseHandle(self.handle);self.handle=None

def write(path,value):exclusive(path,(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
def wait_file(p,proc):
 end=time.monotonic()+30
 while not p.exists():
  if proc.poll() is not None or time.monotonic()>=end:raise RuntimeError('Owned barrier failed: '+p.name)
  time.sleep(.005)

def run(out,n=9,guard=None,preparation_only=True):
 if type(n) is not int or n not in (9,17,129,513):raise ValueError("Fixed owned sizes required")
 out=Path(out);out.mkdir(exist_ok=False);T,C=time.perf_counter(),time.process_time();rows=[];ok=False
 try:
  for point in ('after_first_object','after_snapshot','after_index','before_HEAD','after_HEAD','success'):
   if guard:guard()
   folder=out/point;folder.mkdir();(folder/'originals').mkdir()
   for epoch in (0,1):exclusive(folder/'originals'/f'{epoch}.jsonl',source(n,epoch))
   anchor=create(folder/'receipts','owned_memory_'+point,['update']);start,cpu=time.perf_counter(),time.process_time();producer=None
   with (out/(point+'.log')).open('xb') as stream:
    proc=subprocess.Popen([sys.executable,str(Path(__file__).with_name('run_memory_fault_worker.py')),str(folder.resolve()),str(n),point,anchor],stdout=stream,stderr=subprocess.STDOUT)
    try:
     wait_file(folder/'BASELINE_READY',proc);baseline=json.loads((folder/'BASELINE_READY').read_bytes());producer=Producer(baseline['producer_pid'],proc)
     original=file_ledger(folder/'memory');write(out/(point+'-baseline-identities.json'),original)
     exclusive(folder/'GO_UPDATE',b'parent-verified-baseline')
     ready=None
     if point!='success':
      wait_file(folder/'FAULT_READY',proc);ready=json.loads((folder/'FAULT_READY').read_bytes());assert ready['producer_pid']==producer.pid and ready['phase']==point;producer.kill()
     observed_exit=producer.exit();launcher_exit=proc.wait(timeout=30)
    finally:
     if proc.poll() is None:
      if producer is not None:producer.kill()
      else:proc.kill()
      proc.wait(timeout=30)
     if producer is not None:producer.close()
   assert observed_exit==0 if point=='success' else observed_exit!=0
   parent={'parent_wall_s':time.perf_counter()-start,'parent_self_CPU_s':time.process_time()-cpu,'actual_producer_pid':baseline['producer_pid'],'launcher_pid':proc.pid,'producer_observed_exit_code':observed_exit,'launcher_observed_exit_code':launcher_exit,'child_CPU_RSS_if_no_finally':None}
   events=(folder/'receipts'/'events.jsonl').read_bytes();witness=folder/'parent-witness.json'
   exclusive(witness,encoded({'schema':1,'run_id':'owned_memory_'+point,'plan_SHA':anchor,'events_SHA':sha(events),'child_pid':baseline['producer_pid'],'observed_exit_code':observed_exit}))
   inspection=inspect(folder/'receipts',anchor,witness_path=witness,expected_witness_SHA=sha(witness.read_bytes()));assert inspection['campaign_complete']==(point=='success')
   memory=Memory(folder/'memory');current=memory.current();epoch=1 if point in ('after_HEAD','success') else 0
   current_result=memory.search('RKV97PROBE',top_k=8);old_result=memory.search('RKV97PROBE',snapshot=baseline['old_sid'],top_k=8)
   audits=[audit_result(memory,current_result,source(n,epoch),current),audit_result(memory,old_result,source(n,0),baseline['old_sid'])]
   new_sid=ready.get('new_sid') if ready else json.loads((folder/'receipts'/'artifacts'/'update.bin').read_bytes())['new_sid']
   if point=='after_snapshot':
    with memory.store.snapshot(new_sid) as snap:new_raw=snap.read_range('corpus.jsonl')
    assert new_raw==source(n,1)
    audits.append({'verified_original_records':0,'source_SHA':sha(new_raw),'source_application_return_B':len(new_raw),'raw_snapshot_before_index':True})
   if point in ('after_index','before_HEAD','after_HEAD','success'):
    new_result=memory.search('RKV97PROBE',snapshot=new_sid,top_k=8);audits.append(audit_result(memory,new_result,source(n,1),new_sid))
    write(folder/'explicit-new-query.json',new_result)
   after=file_ledger(folder/'memory')
   for name,identity in original.items():
    if name!='HEAD.json':assert after[name]==identity
   if epoch==0:assert after['HEAD.json']==original['HEAD.json']
   else:assert current!=baseline['old_sid']
   write(folder/'current-query.json',current_result);write(folder/'old-query.json',old_result)
   write(out/(point+'-parent.json'),parent)
   rows.append({'phase':point,'visible_source_epoch':epoch,'operation_receipt_complete':inspection['campaign_complete'],'receipt_state':inspection['states']['update'],'old_sid':baseline['old_sid'],'visible_sid':current,'known_new_sid':new_sid,'parent':parent,'original_source_audits':audits,'old_files_unchanged_except_permitted_HEAD':True,'all_private_file_identities':file_ledger(folder)})
  write(out/'summary.json',{'private_owned_preparation_only':preparation_only,'size':n,'fresh_children':6,'actual_producer_process_terminations':5,'success_control':1,'no_model_provider_or_old_science_reads':0,'automatic_replay_count':0,'rows':rows,'OS_process_termination_not_powerloss_or_concurrency':True});ok=True
 finally:write(out/'preparation-finally.json',{'success':ok,'wall_s':time.perf_counter()-T,'self_CPU_s':time.process_time()-C,'peak_RSS_B':peak_rss(),'full_process_tree_CPU_RSS':None})
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);parser.add_argument('--size',type=int,default=9);a=parser.parse_args();run(a.output,a.size)
