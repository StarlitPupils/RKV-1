"""Owned process-exit fixture; fake transport only; never real network."""
import sys,os,json,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path(__file__).resolve().parent))
from scripts.api_intervention import request_body,run_slot
from scripts.campaign_inspector import write_report_marker
CASES=('before_reservation','after_reservation','after_send_marker','after_response_persist','after_result_persist','after_final_persist','after_report_marker','success_control')
def durable(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def run(case,out):
 if case not in CASES:raise ValueError('Unknown fixed exit boundary')
 out=Path(out);out.mkdir(exist_ok=False);started=time.perf_counter();cpu=time.process_time();success=False
 try:
  for i in range(48 if case=='success_control' else 1):
   body=request_body('Owned fixture question',[]);job={'claim_id':str(i),'condition':'empty'};durable(out/('slot-'+str(i).zfill(2)+'.request-private.json'),body)
   if case=='before_reservation':os._exit(77)
   def fake(body):
    if case=='after_reservation':os._exit(77)
    durable(out/('fake-send-'+str(i).zfill(2)+'.json'),{'index':i,'owned_only':True})
    if case=='after_send_marker':os._exit(77)
    return {'model':'owned-local-fixture','usage':{'prompt_tokens':1,'completion_tokens':1},'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'verdict':'INSUFFICIENT','evidence':[],'explanation':'Owned fixture.'})}}]}
   if case=='after_response_persist':
    import scripts.api_intervention as a
    a.strict_content=lambda *args:os._exit(77)
   result=run_slot(out,i,job,body,[],transport=fake);assert result['accepted']
   if case=='after_result_persist':os._exit(77)
  n=48 if case=='success_control' else 1;durable(out/'campaign-final.json',{'planned_calls':48,'attempted_calls':n,'missing_planned_calls':48-n,'complete':n==48})
  if case=='after_final_persist':os._exit(77)
  write_report_marker(out)
  if case=='after_report_marker':os._exit(77)
  success=True
 finally:durable(out.parent/'child-finally.json',{'success':success,'body_wall_s':time.perf_counter()-started,'body_CPU_s':time.process_time()-cpu})
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.case,a.out)
