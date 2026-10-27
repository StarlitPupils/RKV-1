"""One owned restricted-logic worker, exact source certificates and old BOW collision diagnostic."""
import argparse,copy,json,subprocess,sys,time
from pathlib import Path
from rkv1.store import Store
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from scripts.signed_logic import SignedVerifier
from scripts.audit_signed_logic import verify_certificate
from scripts.logic_fixture import fixture,encode,literal
from scripts.relation_probe import RelationProbe,features
from scripts.run_source_alignment import exclusive,ledger
from scripts.evidence_retrieval import encoded
ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/signed_logic.py','scripts/audit_signed_logic.py','scripts/logic_fixture.py','scripts/run_signed_logic.py','tests/test_signed_logic.py','docs/SIGNED-LOGIC.md','docs/signed-logic-inputs.json')
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--freeze',required=True);args=p.parse_args();start=time.perf_counter();cpu=time.process_time();args.work.mkdir(exist_ok=False);args.out.mkdir(exist_ok=False)
 manifest=json.loads((ROOT/'docs/signed-logic-inputs.json').read_bytes());data=fixture();initial=encode(data['initial']);updated=encode(data['updated']);assert digest(initial)==manifest['initial_axioms_sha256'] and digest(updated)==manifest['updated_axioms_sha256'];checks=implementation_checksums()
 for name in TRACKED:assert (ROOT/name).read_bytes()==subprocess.check_output(['git','show',args.freeze+':'+name])
 cases=args.work/'cases';cases.mkdir();source=args.work/'source';source.mkdir();exclusive(source/'axioms.jsonl',initial);store=Store.create(args.work/'store',compression='zlib',io_backend='bounded');ingests=[]
 def ingest():
  t=time.perf_counter();c=time.process_time();result=store.add(source);ingests.append({'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'result':result});return result['snapshot_id']
 first=ingest();records=[];certificates=[];audits=[];bindings=0;bytes_read=0;times=[];stability=[]
 def stage(sid,label,expected_key):
  nonlocal bindings,bytes_read
  before=ledger(store.root);t=time.perf_counter();c=time.process_time();reader=SignedVerifier(store,sid,'axioms.jsonl');bytes_read+=len(initial) if sid==first else len(updated)
  for row in data['queries']:
   certificate=reader.infer(row['query'],work_budget=100000);exclusive(cases/(label+'-'+row['id']+'-certificate.json'),encoded(certificate)+b'\n');audit=verify_certificate(store,sid,'axioms.jsonl',certificate);assert certificate['complete'] and certificate['verdict']==row[expected_key];assert audit['formal_derivation_verified'] and audit['closure_completeness_verified'];bindings+=len(certificate['nodes']);bytes_read+=audit['original_source_application_returned_bytes'];certificates.append(certificate);audits.append(audit);records.append({'stage':label,'query_id':row['id'],'expected':row[expected_key],'verdict':certificate['verdict'],'certificate_sha256':audit['certificate_sha256'],'source_sha256':certificate['source_sha256'],'proof_nodes':len(certificate['nodes']),'work_used':certificate['work_used']})
  assert before==ledger(store.root);times.append({'stage':label,'full_constructor_infer_and_independent_audit_wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'store_unchanged':True})
 stage(first,'initial','initial')
 (source/'axioms.jsonl').write_bytes(updated);second=ingest();stage(second,'updated','updated');stage(first,'historical','initial');assert [r['certificate_sha256'] for r in records[:24]]==[r['certificate_sha256'] for r in records[48:]]
 before_controls=ledger(store.root);budget_records=[];reader=SignedVerifier(store,first,'axioms.jsonl');bytes_read+=len(initial)
 for row in [data['queries'][16],data['queries'][17],data['queries'][21]]:
  certificate=reader.infer(row['query'],work_budget=0);audit=verify_certificate(store,first,'axioms.jsonl',certificate);assert certificate['verdict']=='incomplete' and not audit['closure_completeness_verified'];certificates.append(certificate);audits.append(audit);bytes_read+=audit['original_source_application_returned_bytes'];bindings+=len(certificate['nodes']);budget_records.append({'query_id':row['id'],'verdict':certificate['verdict'],'work_used':certificate['work_used'],'certificate_sha256':audit['certificate_sha256']})
 tamper_records=[];original=certificates[16]
 for kind in ('atom','rule','premise','verdict','source','false_complete'):
  certificate=copy.deepcopy(original)
  if kind=='atom':certificate['nodes'][0]['atom']['arguments'].reverse()
  elif kind=='rule':next(n for n in certificate['nodes'] if n['kind']=='rule')['source_record_id']='r_repeat'
  elif kind=='premise':next(n for n in certificate['nodes'] if n['kind']=='rule')['premise_proofs']=[]
  elif kind=='verdict':certificate['verdict']='unknown'
  elif kind=='source':certificate['snapshot_id']=second
  else:certificate=copy.deepcopy(certificates[-1]);certificate['complete']=True;certificate['verdict']='unknown'
  try:verify_certificate(store,first,'axioms.jsonl',certificate)
  except ValueError as exc:tamper_records.append({'kind':kind,'rejected':True,'error_type':type(exc).__name__})
  else:raise AssertionError('Tampered certificate accepted: '+kind)
 models={};collision=[];model_load_start=time.perf_counter();model_cpu_start=time.process_time()
 for method,entry in manifest['existing_v064_models'].items():
  raw=Path(entry['path']).read_bytes();assert len(raw)==entry['bytes'] and digest(raw)==entry['sha256'];models[method]=RelationProbe(raw,sha256=entry['sha256'])
 model_load={'wall_s':time.perf_counter()-model_load_start,'cpu_s':time.process_time()-model_cpu_start,'all_model_bytes':sum(e['bytes'] for e in manifest['existing_v064_models'].values())};t=time.perf_counter();c=time.process_time()
 for i,pair in enumerate(data['collision_pairs']):
  left,right=pair['claims'];document=pair['document'];assert features(left,document)==features(right,document) and features(left,document,claim_only=True)==features(right,document,claim_only=True)
  for method,model in models.items():
   predictions=[model.predict(q,document) for q in pair['claims']];assert predictions[0]==predictions[1];correct=sum(p['predicted_relation']==gold for p,gold in zip(predictions,pair['gold']));collision.append({'pair_id':i,'method':method,'feature_vectors_identical':True,'predicted_relations':[p['predicted_relation'] for p in predictions],'gold_relations':pair['gold'],'correct':correct,'denominator':2,'scientific_entailment_verified':False})
 collision_cost={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};assert len(collision)==32 and all(r['correct']==1 for r in collision)
 recovery=[]
 for sid,raw in ((first,initial),(second,updated)):
  with store.snapshot(sid) as snap:restored=snap.read_range('axioms.jsonl')
  assert restored==raw;bytes_read+=len(restored);recovery.append({'snapshot_id':sid,'source_sha256':digest(restored),'bytes':len(restored)})
 assert before_controls==ledger(store.root)
 exclusive(args.work/'private-certificates.json',encoded(certificates)+b'\n');exclusive(args.work/'private-independent-audits.json',encoded(audits)+b'\n');retained={p.relative_to(args.work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in args.work.rglob('*') if p.is_file()};programs={n:{'sha256':digest((ROOT/n).read_bytes()),'bytes':(ROOT/n).stat().st_size} for n in TRACKED};runtime={n:{'sha256':sha,'bytes':(ROOT/'rkv1'/n).stat().st_size} for n,sha in checks.items()}
 # The actual HTML is recorded separately from Python, discovered explicitly.
 html_files={p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in (ROOT/'rkv1').rglob('*.html')};assert len(html_files)==1
 H1=len(records)==72 and all(r['verdict']==r['expected'] for r in records) and len(budget_records)==3 and len(tamper_records)==6;H2=len(collision)==32 and all(r['correct']==1 and r['feature_vectors_identical'] for r in collision)
 report={'H1_restricted_logic_mechanism':H1,'H2_owned_BOW_direction_collision':H2,'formal_workers':1,'formal_retries':0,'main_certificates':72,'budget_incomplete_controls':budget_records,'tamper_controls':tamper_records,'source_record_bindings_for_successful_certificates':bindings,'successful_constructor_certificate_audit_and_full_recovery_source_application_returned_bytes':bytes_read,'failed_tamper_audit_returned_bytes':None,'records':records,'owned_collision_records':collision,'owned_collision_predictions':64,'each_model_owned_correct':8,'each_model_owned_denominator':16,'synthetic_not_scientific_validation':True,'historical_certificate_SHA_identical':True,'recovery':recovery,'ingests':ingests,'stages':times,'model_load':model_load,'collision_cost':collision_cost,'retained_work_files':retained,'retained_work_total_bytes':sum(v['bytes'] for v in retained.values()),'all_loaded_models':manifest['existing_v064_models'],'runtime_python':runtime,'runtime_HTML':html_files,'all_candidate_programs_protocol_tests_inputs':programs,'full_process_observed_peak_rss_bytes':peak_rss(),'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'freeze':args.freeze,'new_training_runs':0,'new_remote_model_calls':0,'scientific_entailment_verified':False,'generated_answers':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,'not_charged_as_success':'Failed tamper reads are uninstrumented null, not zero; application returns exclude SQLite/metadata/OS physical reads; logical work is not full CPU/RAM cap; reuse of all previous training/models retained as historical cost'}
 exclusive(args.out/'raw-worker.json',encoded(report)+b'\n');exclusive(args.out/'source-checksums.json',encoded(checks)+b'\n');print(json.dumps({'H1':H1,'H2':H2,'main_certificates':72,'owned_BOW_predictions':64}),flush=True)
if __name__=='__main__':main()
