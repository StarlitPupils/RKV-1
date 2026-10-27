"""One-worker eligible-source coverage experiment, no inference or NL verdict."""
import argparse,copy,json,subprocess,time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from rkv1.store import Store,Snapshot
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from rkv1.benchmark import peak_rss
from scripts.source_universe import load_universe
from scripts.audit_source_universe import audit_scope
from scripts.source_universe_fixture import sources,plan
from scripts.run_source_alignment import ledger,exclusive
from scripts.evidence_retrieval import encoded
ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/source_universe.py','scripts/audit_source_universe.py','scripts/source_universe_fixture.py','scripts/run_source_universe.py','tests/test_source_universe.py','docs/SOURCE-UNIVERSE.md','docs/source-universe-inputs.json')
@contextmanager
def meter():
 original=Snapshot.read_range;stats={'source_read_calls':0,'source_application_returned_bytes':0}
 def observed(snapshot,path,*args,**kwargs):
  raw=original(snapshot,path,*args,**kwargs)
  if path.endswith('.logic.jsonl'):stats['source_read_calls']+=1;stats['source_application_returned_bytes']+=len(raw)
  return raw
 with patch.object(Snapshot,'read_range',new=observed):yield stats
 assert Snapshot.read_range is original

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--freeze',required=True);a=parser.parse_args();start=time.perf_counter();cpu=time.process_time();a.work.mkdir(exist_ok=False);a.out.mkdir(exist_ok=False);source=a.work/'source';source.mkdir();proofs=a.work/'proofs';proofs.mkdir();manifest=json.loads((ROOT/'docs/source-universe-inputs.json').read_bytes());assert digest(encoded(plan()))==manifest['plan_sha256'];checks=implementation_checksums()
 for n in TRACKED:assert (ROOT/n).read_bytes()==subprocess.check_output(['git','show',a.freeze+':'+n])
 store=Store.create(a.work/'store',compression='zlib',io_backend='bounded');sids={};ingests=[]
 for stage,updated in (('initial',False),('updated',True)):
  data=sources(updated);assert {n:{'bytes':len(raw),'sha256':digest(raw)} for n,raw in data.items()}==manifest['source_input_SHA'][stage]
  for name,raw in data.items():(source/name).write_bytes(raw)
  t=time.perf_counter();c=time.process_time();result=store.add(source);sids[stage]=result['snapshot_id'];ingests.append({'stage':stage,'result':result,'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'source_files':{n:{'bytes':len(raw),'sha256':digest(raw)} for n,raw in data.items()}})
 sids['historical']=sids['initial'];records=[];scope_records={};complete=0;incomplete_zero=0;complete_sample=None;historical=0
 for row in plan():
  sid=sids[row['stage']];before=ledger(store.root);t=time.perf_counter();c=time.process_time()
  with meter() as loaded:proof,payload=load_universe(store,sid,row['paths'],source_byte_budget=row['source_byte_budget'])
  exclusive(proofs/(row['id']+'.json'),encoded(proof)+b'\n');assert proof['source_set_complete']==row['expected_complete'];assert proof['source_application_returned_bytes']==loaded['source_application_returned_bytes']<=row['source_byte_budget'];assert all(proof[k] is False for k in ('source_grammar_verified','logical_closure_verified','scientific_entailment_verified')) and proof['generated_answer'] is None
  audit=None;observed_audit=None
  if row['expected_complete']:
   with meter() as observed_audit:audit=audit_scope(store,sid,proof)
   assert audit['source_set_coverage_verified'] and audit['auditor_application_returned_bytes']==observed_audit['source_application_returned_bytes'];data=sources(row['stage']=='updated');assert payload=={n:raw for n,raw in data.items() if n.endswith('.logic.jsonl')};complete+=1
   if complete_sample is None:complete_sample=proof
  else:assert proof['status']=='incomplete_source_set' and not payload and loaded['source_read_calls']==0;incomplete_zero+=1
  if row['stage']=='historical':assert proof==scope_records[row['id'].replace('historical-','initial-')];historical+=1
  scope_records[row['id']]=proof;assert before==ledger(store.root);records.append({**row,'snapshot_id':sid,'actual_complete':proof['source_set_complete'],'status':proof['status'],'reason':proof['reason'],'scope_proof_sha256':digest(encoded(proof)),'loader_observed':dict(loaded),'independent_auditor_observed':dict(observed_audit) if observed_audit is not None else None,'independent_scope_coverage_verified':audit['source_set_coverage_verified'] if audit else False,'wall_s_including_loader_meter_and_independent_audit':time.perf_counter()-t,'cpu_s':time.process_time()-c,'CAS_unchanged':True})
 negatives=[]
 for mode in ('path','hash','source','science','logic','grammar','budget','incomplete_input','scope','extra'):
  p=copy.deepcopy(complete_sample)
  if mode=='path':p['eligible_paths']=p['eligible_paths'][:1]
  elif mode=='hash':p['source_records'][0]['sha256']='0'*64
  elif mode=='source':p['snapshot_id']=sids['updated']
  elif mode in ('science','logic','grammar'):p[{'science':'scientific_entailment_verified','logic':'logical_closure_verified','grammar':'source_grammar_verified'}[mode]]=True
  elif mode=='budget':p['source_byte_budget']=0
  elif mode=='scope':p['scope']='All scientific knowledge verified'
  elif mode=='extra':p['injected_answer']='claimed answer'
  else:p['source_set_complete']=False
  try:audit_scope(store,sids['initial'],p)
  except ValueError as exc:negatives.append({'mode':mode,'rejected':True,'error_type':type(exc).__name__})
  else:raise AssertionError('Invalid complete coverage input accepted')
 recovery=[]
 for stage in ('initial','updated'):
  with store.snapshot(sids[stage]) as snap:
   for name,expected in sources(stage=='updated').items():
    raw=snap.read_range(name);assert raw==expected;recovery.append({'stage':stage,'path':name,'bytes':len(raw),'sha256':digest(raw)})
 runtime={'rkv1/'+n:{'bytes':(ROOT/'rkv1'/n).stat().st_size,'sha256':sha} for n,sha in checks.items()};runtime.update({p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in (ROOT/'rkv1').rglob('*.html')});programs={n:{'bytes':(ROOT/n).stat().st_size,'sha256':digest((ROOT/n).read_bytes())} for n in TRACKED};all_scripts={}
 for p in (ROOT/'scripts').rglob('*.py'):
  name=p.relative_to(ROOT).as_posix();raw=p.read_bytes();assert raw==subprocess.check_output(['git','show',a.freeze+':'+name]);all_scripts[name]={'bytes':len(raw),'sha256':digest(raw)}
 retained={p.relative_to(a.work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in a.work.rglob('*') if p.is_file()};report={'H1_all36source_set_dispositions_and12independent_complete_checks':len(records)==36 and complete==12,'H2_all24preflight_incomplete_zero_payload_read_12history_invariance_10invalid_complete_inputs':incomplete_zero==24 and historical==12 and len(negatives)==10,'formal_workers':1,'formal_retries':0,'complete':complete,'incomplete_zero_source_reads':incomplete_zero,'historical_proof_equal':historical,'records':records,'negative_controls':negatives,'recovery':recovery,'ingests':ingests,'runtime_files':runtime,'runtime_module_count':len(checks),'runtime_html_count':sum(n.endswith('.html') for n in runtime),'assessment_programs':programs,'all_existing_experimental_script_source_conservative_allocation':all_scripts,'retained_work_files':retained,'retained_work_total_bytes':sum(e['bytes'] for e in retained.values()),'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss(),'freeze':a.freeze,'current_loaded_model_bytes':0,'new_training_runs':0,'new_remote_model_calls':0,'source_grammar_verified':False,'logical_closure_verified':False,'scientific_entailment_verified':False,'generated_answers':0,'source_payload_budget_scope':'Loader source application-return bytes only; independent audit/recovery add reads, metadata/SQLite/OS/physicalIO excluded','rejected_control_bytes':None,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,'historical_costs':'All older source/model/training/snapshots retained, see v066 and earlierreports','scope':'Eligible source-set coverage only; no cross-file rule inference, natural-language extraction, scientific NLI, global unknown or answers'};exclusive(a.out/'raw-worker.json',encoded(report)+b'\n');exclusive(a.out/'source-checksums.json',encoded(checks)+b'\n');print(json.dumps({'H1':report['H1_all36source_set_dispositions_and12independent_complete_checks'],'H2':report['H2_all24preflight_incomplete_zero_payload_read_12history_invariance_10invalid_complete_inputs'],'complete':complete,'incomplete':incomplete_zero}),flush=True)
if __name__=='__main__':main()
