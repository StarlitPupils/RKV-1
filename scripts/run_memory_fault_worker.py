"""Owned child stops at a named existing publication boundary; runtime unchanged."""
import time,sys,os,json
T,C=time.perf_counter(),time.process_time()
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import rkv1.memory as memory_module
import rkv1.memory_index as index_module
from rkv1.memory import Memory
from rkv1.benchmark import peak_rss
from scripts.execution_receipts import append,exclusive,encoded,sha
from scripts.memory_fault_fixture import source
root=Path(sys.argv[1]);n=int(sys.argv[2]);point=sys.argv[3];anchor=sys.argv[4]
assert n in (9,17,129,513) and point in ('after_first_object','after_snapshot','after_index','before_HEAD','after_HEAD','success')
def wait(path):
 end=time.monotonic()+30
 while not path.exists():
  if time.monotonic()>end:raise TimeoutError('Owned barrier timeout')
  time.sleep(.005)
def marker(name,value):
 temporary=root/('.'+name+'.tmp')
 exclusive(temporary,encoded(value))
 temporary.rename(root/name)
def stop(phase,**extra):
 if point==phase:
  marker('FAULT_READY',{'phase':phase,'producer_pid':os.getpid(),**extra})
  while True:time.sleep(.01)
memory=None;old_publish=old_head=old_build=None;ok=False
try:
 (root/'source').mkdir();(root/'source'/'corpus.jsonl').write_bytes(source(n,0))
 memory=Memory.create(root/'memory',compression='zlib',chunk_size=4096)
 oldsid=memory.add(root/'source',label='owned-old')['snapshot_id']
 marker('BASELINE_READY',{'old_sid':oldsid,'producer_pid':os.getpid()});wait(root/'GO_UPDATE')
 append(root/'receipts',anchor,'update','reserved');append(root/'receipts',anchor,'update','started')
 (root/'source'/'corpus.jsonl').write_bytes(source(n,1))
 old_publish=memory.store._publish;old_head=memory_module._head;old_build=index_module.build
 first=[True]
 def publish(path,data):
  result=old_publish(path,data);parts=Path(path).relative_to(memory.store.root).parts
  if parts[0]=='objects' and first[0]:first[0]=False;stop('after_first_object')
  if parts[0]=='snapshots':stop('after_snapshot',new_sid=Path(path).stem)
  return result
 def build(m,sid,selected):
  result=old_build(m,sid,selected);stop('after_index',new_sid=sid);return result
 def head(path,value):
  if Path(path)==memory.root/'HEAD.json':stop('before_HEAD',new_sid=value['snapshot_id'])
  result=old_head(path,value)
  if Path(path)==memory.root/'HEAD.json':stop('after_HEAD',new_sid=value['snapshot_id'])
  return result
 memory.store._publish=publish;memory_module._head=head;index_module.build=build
 update=memory.add(root/'source',label='owned-new')
 raw=encoded({'old_sid':oldsid,'new_sid':update['snapshot_id'],'source_SHA':sha(source(n,1))})
 exclusive(root/'receipts'/'artifacts'/'update.bin',raw)
 append(root/'receipts',anchor,'update','artifact_verified',artifact={'bytes':len(raw),'sha256':sha(raw)})
 append(root/'receipts',anchor,'update','stage_completed');ok=True
finally:
 if old_publish is not None:memory.store._publish=old_publish;memory_module._head=old_head;index_module.build=old_build
 exclusive(root/'worker-finally.json',encoded({'success':ok,'entry_wall_s':time.perf_counter()-T,'entry_self_CPU_s':time.process_time()-C,'peak_RSS_B':peak_rss()}))
