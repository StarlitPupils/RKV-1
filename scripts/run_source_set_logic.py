"""Owned multi-source inference protocol worker, no scientific/NL truth claim."""
import argparse,copy,json,subprocess,time
from pathlib import Path
from rkv1.store import Store
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from rkv1.benchmark import peak_rss
from scripts.source_set_logic import SourceSetVerifier
from scripts.audit_source_set_logic import verify_set_certificate
from scripts.source_set_fixture import sources,plan
from scripts.run_source_universe import meter
from scripts.run_source_alignment import ledger,exclusive
from scripts.evidence_retrieval import encoded
ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/source_set_logic.py','scripts/audit_source_set_logic.py','scripts/source_set_fixture.py','scripts/run_source_set_logic.py','tests/test_source_set_logic.py','docs/SOURCE-SET-LOGIC.md','docs/source-set-logic-inputs.json','scripts/signed_logic.py','scripts/audit_signed_logic.py','scripts/source_universe.py','scripts/audit_source_universe.py','scripts/run_source_universe.py')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--freeze',required=True);a=parser.parse_args();start=time.perf_counter();cpu=time.process_time();a.work.mkdir(exist_ok=False);a.out.mkdir(exist_ok=False);source=a.work/'source';source.mkdir();certdir=a.work/'certificates';certdir.mkdir();manifest=json.loads((ROOT/'docs/source-set-logic-inputs.json').read_bytes());assert digest(encoded(plan()))==manifest['plan_sha256'];checks=implementation_checksums()
 for n in TRACKED:assert (ROOT/n).read_bytes()==subprocess.check_output(['git','show',a.freeze+':'+n])
 store=Store.create(a.work/'store',compression='zlib',io_backend='bounded');sids={};ingests=[]
 for stage,updated in (('initial',False),('updated',True)):
  data=sources(updated);assert {n:{'bytes':len(raw),'sha256':digest(raw)} for n,raw in data.items()}==manifest['source_input_SHA'][stage]
  for name,raw in data.items():(source/name).write_bytes(raw)
  t=time.perf_counter();c=time.process_time();commit=store.add(source);sids[stage]=commit['snapshot_id'];ingests.append({'stage':stage,'commit':commit,'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c})
 sids['historical']=sids['initial'];before=ledger(store.root);records=[];certs={};sourceincomplete=0;workincomplete=0;complete=0;history=0;bindings=0;crossfile_nodes=0
 for row in plan():
  sid=sids[row['stage']];t=time.perf_counter();c=time.process_time()
  with meter() as load_traffic:
   engine=SourceSetVerifier(store,sid,row['paths'],source_byte_budget=row['source_byte_budget']);certificate=engine.infer(row['query'],work_budget=row['work_budget'])
  exclusive(certdir/(row['id']+'.json'),encoded(certificate)+b'\n')
  with meter() as audit_traffic:audit=verify_set_certificate(store,sid,certificate)
  assert certificate['verdict']==row['expected_verdict'] and certificate['complete']==row['expected_complete'];assert not certificate['scientific_entailment_verified'] and certificate['generated_answer'] is None;assert load_traffic['source_application_returned_bytes']<=row['source_byte_budget'];assert audit['application_source_returned_bytes']==audit_traffic['source_application_returned_bytes']
  if certificate['verdict']=='incomplete_source_set':
   assert load_traffic['source_read_calls']==0 and audit_traffic['source_read_calls']==0 and not audit['formal_derivation_verified'] and not certificate['source_grammar_verified'];sourceincomplete+=1
  else:
   assert audit['formal_derivation_verified'] and certificate['source_grammar_verified'];bindings+=len(certificate['nodes']);crossfile_nodes+=sum(n['kind']=='rule' and any(certificate['nodes'][r]['citation']['path']!=n['citation']['path'] for r in n['premise_proofs']) for n in certificate['nodes'])
   if certificate['complete']:assert audit['closure_completeness_verified'];complete+=1
   else:assert certificate['verdict']=='incomplete' and not audit['closure_completeness_verified'];workincomplete+=1
  if row['stage']=='historical':assert certificate==certs[row['id'].replace('historical-','initial-')];history+=1
  certs[row['id']]=certificate;records.append({**row,'snapshot_id':sid,'verdict':certificate['verdict'],'complete':certificate['complete'],'certificate_sha256':audit['certificate_sha256'],'proof_nodes':len(certificate['nodes']),'source_grammar_verified':certificate['source_grammar_verified'],'formal_derivation_verified':audit['formal_derivation_verified'],'closure_completeness_verified':audit['closure_completeness_verified'],'work_used':certificate['work_used'],'loader_and_inference_traffic':dict(load_traffic),'independent_audit_traffic':dict(audit_traffic),'constructor_infer_and_independent_audit_wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c})
 assert before==ledger(store.root);sample=next(c for key,c in certs.items() if key.startswith('initial-full') and c['complete'] and c['verdict']=='supported' and c['query']['predicate']=='reach');partial=next(c for c in certs.values() if c['verdict']=='incomplete');sourcepartial=next(c for c in certs.values() if c['verdict']=='incomplete_source_set');negative=[]
 for mode in ('tuple_path','offset','source_SHA','SID','premise','scope','extra','science','answer','source_scope','false_work_complete','false_source_complete'):
  c=copy.deepcopy(sample)
  if mode=='tuple_path':c['nodes'][0]['source_record_id'][0]='two.logic.jsonl'
  elif mode=='offset':c['nodes'][0]['citation']['offset']+=1
  elif mode=='source_SHA':c['source_scope']['source_records'][0]['sha256']='0'*64
  elif mode=='SID':c['snapshot_id']=sids['updated']
  elif mode=='premise':next(n for n in c['nodes'] if n['kind']=='rule')['premise_proofs']=[]
  elif mode=='scope':c['scope']='All scientific knowledge verified'
  elif mode=='extra':c['new_answer']='claim'
  elif mode=='science':c['scientific_entailment_verified']=True
  elif mode=='answer':c['generated_answer']='claim'
  elif mode=='source_scope':c['source_scope']['logical_closure_verified']=True
  elif mode=='false_work_complete':c=copy.deepcopy(partial);c['complete']=True;c['verdict']='unknown'
  else:c=copy.deepcopy(sourcepartial);c['complete']=True;c['verdict']='unknown'
  try:verify_set_certificate(store,sids['initial'],c)
  except ValueError as exc:negative.append({'mode':mode,'rejected':True,'error_type':type(exc).__name__})
  else:raise AssertionError('Tampered multi-source certificate accepted')
 recovery=[]
 for stage in ('initial','updated'):
  with store.snapshot(sids[stage]) as snap:
   for name,raw in sources(stage=='updated').items():
    actual=snap.read_range(name);assert actual==raw;recovery.append({'stage':stage,'path':name,'bytes':len(actual),'sha256':digest(actual)})
 assert before==ledger(store.root);runtime={'rkv1/'+n:{'bytes':(ROOT/'rkv1'/n).stat().st_size,'sha256':sha} for n,sha in checks.items()};runtime.update({p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in (ROOT/'rkv1').rglob('*.html')});programs={n:{'bytes':(ROOT/n).stat().st_size,'sha256':digest((ROOT/n).read_bytes())} for n in TRACKED};all_scripts={}
 for p in (ROOT/'scripts').rglob('*.py'):
  n=p.relative_to(ROOT).as_posix();raw=p.read_bytes();assert raw==subprocess.check_output(['git','show',a.freeze+':'+n]);all_scripts[n]={'bytes':len(raw),'sha256':digest(raw)}
 retained={p.relative_to(a.work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in a.work.rglob('*') if p.is_file()};report={'H1_all216expected_dispositions_and36independent_full_closures':len(records)==216 and complete==36,'H2_source_work_abstention_history_and12tamper_rejection':sourceincomplete==144 and workincomplete==36 and history==72 and len(negative)==12 and crossfile_nodes>0,'formal_workers':1,'formal_retries':0,'complete_certificates':complete,'incomplete_source_set':sourceincomplete,'incomplete_logical_work':workincomplete,'historical_certificate_objects_identical':history,'records':records,'negative_controls':negative,'original_record_bindings':bindings,'cross_file_rule_proof_nodes_in_all_successful_closures':crossfile_nodes,'recovery':recovery,'ingests':ingests,'CAS_unchanged_during_query_audit_recovery':True,'runtime_files':runtime,'runtime_module_count':len(checks),'runtime_html_count':sum(n.endswith('.html') for n in runtime),'assessment_programs':programs,'all_existing_experimental_script_source_conservative_allocation':all_scripts,'retained_work_files':retained,'retained_work_total_bytes':sum(e['bytes'] for e in retained.values()),'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss(),'freeze':a.freeze,'current_loaded_model_bytes':0,'new_training_runs':0,'new_remote_model_calls':0,'scientific_entailment_verified':False,'generated_answers':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'rejected_control_returned_bytes':None,'cold_cache':None,'cross_machine':None,'historical_costs':'All previoussource/model/training/snapshots retained;v067 and earlierreports','scope':'Only consequences under explicitly supplied signed axioms in eligible snapshot files, no NL extraction/scientific truth/global knowledge or answers','source_payload_bound_applies_to_loader_only_not_auditor_recovery_metadata_OS':True};exclusive(a.out/'raw-worker.json',encoded(report)+b'\n');exclusive(a.out/'source-checksums.json',encoded(checks)+b'\n');print(json.dumps({'H1':report['H1_all216expected_dispositions_and36independent_full_closures'],'H2':report['H2_source_work_abstention_history_and12tamper_rejection'],'complete':complete,'source_incomplete':sourceincomplete,'work_incomplete':workincomplete,'history':history,'negative':len(negative)}),flush=True)
if __name__=='__main__':main()
