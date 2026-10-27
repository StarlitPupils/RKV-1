"""One frozen OWA representation-only benchmark worker; no English or model inference."""
import argparse,hashlib,json,subprocess,time,zipfile
from pathlib import Path
from collections import Counter
from rkv1.core import digest
from rkv1.store import Store
from rkv1.controlled import implementation_checksums
from rkv1.benchmark import peak_rss
from scripts.postings_transform import parse
from scripts.proofwriter_representation import Compiler,UnsupportedRepresentation
from scripts.audit_proofwriter_representation import audit_compilation,single as reference_query
from scripts.source_set_logic import SourceSetVerifier
from scripts.audit_source_set_logic import verify_set_certificate
from scripts.audit_signed_logic import VerificationCapacityExceeded
from scripts.run_source_universe import meter
from scripts.run_source_alignment import exclusive,ledger
from scripts.evidence_retrieval import encoded
ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/proofwriter_representation.py','scripts/audit_proofwriter_representation.py','scripts/run_proofwriter_representation.py','tests/test_proofwriter_representation.py','tests/test_proofwriter_representation_worker.py','docs/PROOFWRITER-REPRESENTATION.md','docs/proofwriter-representation-inputs.json','scripts/source_set_logic.py','scripts/audit_source_set_logic.py','scripts/signed_logic.py','scripts/audit_signed_logic.py','scripts/source_universe.py','scripts/audit_source_universe.py')
LABELS=('True','False','Unknown')
def gold_label(value):
 if value is True:return 'True'
 if value is False:return 'False'
 if value=='Unknown' and type(value) is str:return 'Unknown'
 raise ValueError('Unsupported official label')
def prediction_label(certificate):return {'supported':'True','refuted':'False','unknown':'Unknown'}.get(certificate['verdict']) if certificate['complete'] else None

def run_theory(raw,work,index,*,gold_observer=None):
 start=time.perf_counter();cpu=time.process_time();folder=Path(work)/('theory-'+str(index));folder.mkdir(exist_ok=False);row=parse(raw);questions=row['questions'];assert type(questions) is dict and questions;rows=[];before_gold=[];error=None;store=None;mapping=[];compiled={};constructor_stats=None;compilation_audit=None;compilation_audit_error=None;recovery=None;ingest=None;source_bytes=None;proof_bindings=0;original_bindings=0
 try:
  if len(raw)>1<<20:raise UnsupportedRepresentation('Original theory size cap')
  compiler=Compiler(world='OWA');compiled,mapping=compiler.compile(row['triples'],row['rules']);source=folder/'source';source.mkdir();exclusive(source/'original.json',raw)
  for n,value in compiled.items():exclusive(source/n,value)
  exclusive(folder/'private-compilation-map.json',encoded(mapping)+b'\n');store=Store.create(folder/'store',compression='zlib',io_backend='bounded');t=time.perf_counter();c=time.process_time();commit=store.add(source);ingest={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'commit':commit};sid=commit['snapshot_id'];before=ledger(store.root)
  with meter() as constructor_stats:engine=SourceSetVerifier(store,sid,sorted(compiled),source_byte_budget=1<<20)
 except (ValueError,VerificationCapacityExceeded) as exc:error=type(exc).__name__+':'+str(exc)
 # Every representation prediction saved before reading any answer/depth/proof field for this theory.
 for question_index,qid in enumerate(sorted(questions)):
  question=questions[qid];certificate=None;failure=error;t=time.perf_counter();c=time.process_time()
  if failure is None:
   try:
    query=compiler.ground(question['representation']);certificate=engine.infer(query,work_budget=100000)
   except (ValueError,VerificationCapacityExceeded) as exc:failure=type(exc).__name__+':'+str(exc)
  output={'question_id':qid,'query_representation_sha256':digest(question['representation'].encode('utf-8')) if type(question['representation']) is str else digest(encoded(question['representation'])),'predicted_label':prediction_label(certificate) if certificate else None,'engine_verdict':certificate['verdict'] if certificate else None,'engine_complete':certificate['complete'] if certificate else False,'prediction_failure':failure,'prediction_wall_s':time.perf_counter()-t,'prediction_cpu_s':time.process_time()-c,'certificate_sha256':digest(encoded(certificate)) if certificate else None,'scientific_entailment_verified':False,'generated_answer':None};exclusive(folder/('query-'+str(question_index)+'-prediction.json'),encoded(output)+b'\n')
  if certificate is not None:exclusive(folder/('query-'+str(question_index)+'-private-certificate.json'),encoded(certificate)+b'\n')
  before_gold.append((qid,output,certificate))
 exclusive(folder/'predictions-before-gold.json',encoded([x[1] for x in before_gold])+b'\n')
 if gold_observer:gold_observer(folder,before_gold)
 # Independent compilation and complete-source proof audit precede score acceptance, after predictions.
 if store is not None and error is None:
  try:
   with meter() as stats:compilation_audit=audit_compilation(store,sid,mapping,sorted(compiled),world='OWA')
   compilation_audit['observed_source_payload_returned_bytes']=stats['source_application_returned_bytes'];original_bindings=compilation_audit['original_representation_bindings'];assert compilation_audit['independent_compilation_verified']
  except (ValueError,VerificationCapacityExceeded) as exc:compilation_audit_error=type(exc).__name__+':'+str(exc)
 for qid,output,certificate in before_gold:
  accepted=False;audit=None;audit_error=None;t=time.perf_counter();c=time.process_time()
  if certificate is not None:
   try:
    if certificate['query']!=reference_query(questions[qid]['representation']):raise ValueError('Independent query translation differs')
    with meter() as stats:audit=verify_set_certificate(store,sid,certificate)
    audit['observed_source_payload_returned_bytes']=stats['source_application_returned_bytes'];proof_bindings+=len(certificate['nodes']);accepted=audit['closure_completeness_verified'] and compilation_audit is not None and output['predicted_label'] is not None
   except (ValueError,VerificationCapacityExceeded) as exc:audit_error=type(exc).__name__+':'+str(exc)
  label=gold_label(questions[qid]['answer']);depth=questions[qid].get('QDep');correct=accepted and output['predicted_label']==label;rows.append({**output,'gold':label,'QDep_after_prediction':depth,'accepted_formal_representation_only':accepted,'correct':correct,'independent_audit_error':audit_error,'independent_audit_wall_s':time.perf_counter()-t,'independent_audit_cpu_s':time.process_time()-c,'independent_audit':audit})
 if store is not None:
  assert ledger(store.root)==before
  with store.snapshot(sid) as snap:
   original=snap.read_range('original.json');assert original==raw
   for n,value in compiled.items():assert snap.read_range(n)==value
  recovery={'original_bytes':len(raw),'original_sha256':digest(raw),'derived_files':{n:{'bytes':len(v),'sha256':digest(v)} for n,v in compiled.items()}};assert ledger(store.root)==before
 retained={p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in folder.rglob('*') if p.is_file()};return {'theory_index':index,'theory_id':row.get('id'),'original_record_sha256':digest(raw),'original_record_bytes':len(raw),'questions':len(questions),'records':rows,'compilation_failure':error,'compilation_audit':compilation_audit,'compilation_audit_error':compilation_audit_error,'constructor_source_stats':dict(constructor_stats) if constructor_stats is not None else None,'ingest':ingest,'recovery':recovery,'source_representation_bindings':original_bindings,'derived_record_DAG_bindings':proof_bindings,'retained_files':retained,'retained_total_bytes':sum(e['bytes'] for e in retained.values()),'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-cpu,'predictions_persisted_before_gold':True,'raw_English_or_gold_used_as_reasoner_input':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--freeze',required=True);a=p.parse_args();start=time.perf_counter();cpu=time.process_time();a.work.mkdir(exist_ok=False);a.out.mkdir(exist_ok=False);manifest=parse((ROOT/'docs/proofwriter-representation-inputs.json').read_bytes());archive=Path(manifest['archive']['path']);assert archive.stat().st_size==manifest['archive']['bytes'];sha=hashlib.sha256()
 with archive.open('rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''):sha.update(chunk)
 assert sha.hexdigest()==manifest['archive']['sha256'];checks=implementation_checksums()
 for n in TRACKED:assert (ROOT/n).read_bytes()==subprocess.check_output(['git','show',a.freeze+':'+n])
 raw_rows=[]
 with zipfile.ZipFile(archive) as z,z.open(manifest['member']) as f:
  for _ in range(64):
   raw=f.readline()
   if not raw:raise ValueError('Official fixed64theory prefix not present')
   raw_rows.append(raw)
 prefix=b''.join(raw_rows);exclusive(a.work/'private-frozen-dev64.jsonl',prefix);exclusive(a.out/'first-access-input-SHA.json',encoded({'archive_SHA':sha.hexdigest(),'member':manifest['member'],'theories':64,'prefix_bytes':len(prefix),'prefix_sha256':digest(prefix),'frozen_before_any_dev_predictions_or_gold_scoring':True})+b'\n');theories=[]
 for index,raw in enumerate(raw_rows):
  record=run_theory(raw,a.work,index);exclusive(a.work/('theory-'+str(index)+'-aggregate.json'),encoded(record)+b'\n');theories.append(record)
  print('theory',index,'questions',record['questions'],'accepted',sum(r['accepted_formal_representation_only'] for r in record['records']),flush=True)
 all_rows=[r for t in theories for r in t['records']];total=len(all_rows);correct=sum(r['correct'] for r in all_rows);accepted=sum(r['accepted_formal_representation_only'] for r in all_rows);confusion={label:{prediction:sum(r['gold']==label and (r['predicted_label'] if r['accepted_formal_representation_only'] else 'abstain')==prediction for r in all_rows) for prediction in (*LABELS,'abstain')} for label in LABELS};depths={str(depth):{'total':sum(r['QDep_after_prediction']==depth for r in all_rows),'correct':sum(r['QDep_after_prediction']==depth and r['correct'] for r in all_rows)} for depth in sorted({r['QDep_after_prediction'] for r in all_rows},key=str)};classes={label:{'total':sum(r['gold']==label for r in all_rows),'correct':sum(r['gold']==label and r['correct'] for r in all_rows),'predicted':sum(r['predicted_label']==label for r in all_rows)} for label in LABELS};H1=total>0 and correct*100>=95*total and all(e['total']>0 for e in classes.values());H2=accepted==total and all(t['compilation_audit'] and t['compilation_audit']['independent_compilation_verified'] and t['recovery'] for t in theories);runtime={'rkv1/'+n:{'bytes':(ROOT/'rkv1'/n).stat().st_size,'sha256':v} for n,v in checks.items()};runtime.update({p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in (ROOT/'rkv1').rglob('*.html')});programs={n:{'bytes':(ROOT/n).stat().st_size,'sha256':digest((ROOT/n).read_bytes())} for n in TRACKED};all_scripts={}
 for p in (ROOT/'scripts').rglob('*.py'):
  n=p.relative_to(ROOT).as_posix();raw=p.read_bytes();assert raw==subprocess.check_output(['git','show',a.freeze+':'+n]);all_scripts[n]={'bytes':len(raw),'sha256':digest(raw)}
 retained={p.relative_to(a.work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in a.work.rglob('*') if p.is_file()};report={'H1_all_questions_formal_label_accuracy_at_least95percent_all3goldclasses':H1,'H2_all_questions_accepted_original_translation_and_complete_closure_all64recoveries':H2,'formal_workers':1,'formal_retries':0,'theories':len(theories),'questions':total,'correct':correct,'all_questions_accuracy':correct/total if total else None,'accepted':accepted,'classes':classes,'confusion_gold_rows_prediction_columns':confusion,'QDep_after_prediction_groups':depths,'verdicts':dict(Counter(r['engine_verdict'] or 'no_certificate' for r in all_rows)),'prediction_failure_counts':dict(Counter(r['prediction_failure'] for r in all_rows if r['prediction_failure'])),'audit_failure_counts':dict(Counter(r['independent_audit_error'] for r in all_rows if r['independent_audit_error'])),'source_representation_bindings':sum(t['source_representation_bindings'] for t in theories),'derived_record_DAG_bindings':sum(t['derived_record_DAG_bindings'] for t in theories),'theory_records':theories,'runtime_files':runtime,'runtime_module_count':len(checks),'runtime_html_count':sum(n.endswith('.html') for n in runtime),'assessment_programs':programs,'all_existing_experimental_script_source_conservative_allocation':all_scripts,'retained_work_files':retained,'retained_work_total_bytes':sum(e['bytes'] for e in retained.values()),'archive_retained_bytes':archive.stat().st_size,'archive_sha256':sha.hexdigest(),'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss(),'freeze':a.freeze,'new_training_runs':0,'current_loaded_model_bytes':0,'new_remote_model_calls':0,'scientific_entailment_verified':False,'English_translation_verified':False,'generated_answers':0,'rejected_or_failed_source_bytes':None,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,'scope':'Official artificial OWA supplied formal representations only, no NL parsing/scientific NLI, source retrieval or generated answer benefit','historical_costs':'All previousscience/model/training/source/snapshots retained, see v068 and earlier reports'};exclusive(a.out/'raw-worker.json',encoded(report)+b'\n');exclusive(a.out/'source-checksums.json',encoded(checks)+b'\n');print(json.dumps({'H1':H1,'H2':H2,'theories':64,'questions':total,'correct':correct,'accepted':accepted}),flush=True)
if __name__=='__main__':main()
