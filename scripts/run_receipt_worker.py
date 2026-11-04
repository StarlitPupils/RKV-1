import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import os,sys,time
from pathlib import Path
from scripts.execution_receipts import append,exclusive,sha
folder=Path(sys.argv[1]);anchor=sys.argv[2];mode=sys.argv[3]
def fault(point):
 if mode==point:os._exit(76)
 if mode=='kill_'+point:
  exclusive(folder/'READY',point.encode())
  while True:time.sleep(.01)
for stage in ('one','two','three'):
 active=stage=='two'
 if active:fault('before_reserve')
 append(folder,anchor,stage,'reserved')
 if active:fault('after_reserve')
 append(folder,anchor,stage,'started')
 if active:fault('after_started')
 raw=('owned-'+stage).encode()
 if active and mode=='partial_artifact':exclusive(folder/'artifacts'/(stage+'.bin'),raw[:2]);os._exit(76)
 exclusive(folder/'artifacts'/(stage+'.bin'),raw)
 if active:fault('after_artifact')
 append(folder,anchor,stage,'artifact_verified',artifact={'bytes':len(raw),'sha256':sha(raw)})
 if active:fault('after_receipt')
 append(folder,anchor,stage,'stage_completed')
 if active:fault('after_stage_footer')
if mode=='exit_nonzero_allstages':os._exit(76)
