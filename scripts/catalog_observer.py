"""Experimental observer: actual Snapshot constructor calls/time + range-returned source bytes."""
import time
from contextlib import contextmanager
from unittest.mock import patch
from rkv1.store import Snapshot
@contextmanager
def observe_snapshots():
 init=Snapshot.__init__;read=Snapshot.read_range
 state={'constructor_calls':0,'constructor_wall_s':0.,'constructor_cpu_s':0.,'source_read_calls':[],'failed_constructor_calls':0}
 def measured_init(self,*args,**kwargs):
  state['constructor_calls']+=1;t=time.perf_counter();c=time.process_time()
  try:return init(self,*args,**kwargs)
  except BaseException:state['failed_constructor_calls']+=1;raise
  finally:state['constructor_wall_s']+=time.perf_counter()-t;state['constructor_cpu_s']+=time.process_time()-c
 def measured_read(self,path,*args,**kwargs):
  raw=read(self,path,*args,**kwargs);state['source_read_calls'].append({'path':path,'returned_bytes':len(raw)});return raw
 with patch.object(Snapshot,'__init__',measured_init),patch.object(Snapshot,'read_range',measured_read):yield state
