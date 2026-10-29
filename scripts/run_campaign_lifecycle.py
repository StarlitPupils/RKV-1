"""Owned process-exit matrix. No real transport, no retry, no original science inputs."""
import json,subprocess,sys,os,time,shutil
from pathlib import Path
from scripts.campaign_inspector import inspect,write_report_marker,digest,canonical
CASES=('before_reservation','after_reservation','after_send_marker','after_response_persist','after_result_persist','after_final_persist','after_report_marker','success_control')
def ledger(folder):return {p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in folder.rglob('*') if p.is_file()}
def write(p,v):
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def run_case(case,folder,python):
 if case not in CASES:raise ValueError('Unknown boundary')
 folder=Path(folder);folder.mkdir(exist_ok=False);campaign=folder/'campaign';env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')};t=time.perf_counter();cpu=time.process_time();code=None
 try:
  with (folder/'child.log').open('xb') as f:code=subprocess.run([str(python),'-m','scripts.owned_campaign_exit','--case',case,'--out',str(campaign)],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60).returncode
 finally:write(folder/'parent.json',{'parent_full_wall_s':time.perf_counter()-t,'parent_CPU_s':time.process_time()-cpu,'exit_code':code,'retry':0})
 assert code==(0 if case=='success_control' else 77)
 before=ledger(campaign);a=inspect(campaign);assert ledger(campaign)==before and a['model_send_allowed'] is False
 send_before={k:v for k,v in before.items() if k.startswith('fake-send-')}
 if a['state'].startswith('closed_'):
  marker=write_report_marker(campaign);second=write_report_marker(campaign);assert second['already_bound'] is True and not marker['model_send_allowed'];expected={k:v for k,v in ledger(campaign).items() if k!='report-identity.json'};assert expected=={k:v for k,v in before.items() if k!='report-identity.json'}
 else:
  try:write_report_marker(campaign)
  except ValueError:pass
  else:raise AssertionError('Open campaign report must refuse')
  assert ledger(campaign)==before
 after=ledger(campaign);assert {k:v for k,v in after.items() if k.startswith('fake-send-')}==send_before
 result={'case':case,'exit_code':code,'before_inspection':a,'before_files':before,'after_files':after,'fake_send_markers':len(send_before),'inspector_or_report_additional_sends':0,'child_finally_present':(folder/'child-finally.json').exists(),'model_send_allowed':False};write(folder/'case.json',result);return result

def run_matrix(out,python,guard=None):
 out=Path(out);out.mkdir(exist_ok=False);start=time.perf_counter();cpu=time.process_time();success=False
 try:
  rows=[]
  for round_id in range(1,4):
   for case in CASES:
    if guard:guard()
    row=run_case(case,out/('round-'+str(round_id)+'-'+case),python);rows.append({'round':round_id,**row})
  base=out/'round-1-success_control/campaign';negatives=[]
  for kind in ('request_identity','raw_response','final_denominator','report_identity'):
   target=out/('negative-'+kind);shutil.copytree(base,target)
   if kind=='raw_response':p=target/'slot-00.response-private.bin';p.write_bytes(p.read_bytes()+b'x')
   else:
    name,field,value={'request_identity':('slot-00.result.json','request_sha256','0'*64),'final_denominator':('campaign-final.json','missing_planned_calls',1),'report_identity':('report-identity.json','campaign_identity_sha256','0'*64)}[kind];p=target/name;v=json.loads(p.read_bytes());v[field]=value;p.write_bytes(canonical(v))
   before=ledger(target)
   try:inspect(target)
   except ValueError:pass
   else:raise AssertionError('Corrupted campaign accepted')
   assert ledger(target)==before;negatives.append({'kind':kind,'refused':True,'additional_sends':0,'files':before})
  result={'fresh_children':24,'rounds':3,'rows':rows,'negative_controls':negatives,'new_remote_model_calls':0,'formal_retries':0,'owned_process_exit_not_power_loss':True};write(out/'matrix.json',result);success=True;return result
 finally:write(out/'matrix-finally.json',{'success':success,'body_wall_s':time.perf_counter()-start,'body_CPU_s':time.process_time()-cpu})
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();run_matrix(a.out,sys.executable)
