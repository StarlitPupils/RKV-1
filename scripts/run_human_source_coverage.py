"""One frozen controlled-English OWA benchmark worker; no model or unrestricted NLI."""
import argparse,hashlib,json,subprocess,time,zipfile
from pathlib import Path
from collections import Counter
from rkv1.core import digest
from rkv1.store import Store
from rkv1.controlled import implementation_checksums
from rkv1.benchmark import peak_rss
from scripts.postings_transform import parse
from scripts.proofwriter_english import EnglishCompiler as Compiler,UnsupportedEnglish as UnsupportedRepresentation
from scripts.human_source_coverage import HumanSourceCompiler
from scripts.audit_human_source_coverage import audit_human_compilation
from scripts.audit_proofwriter_english import audit_English_compilation as audit_compilation
from scripts.audit_proofwriter_representation import single as reference_query
from scripts.source_set_logic import SourceSetVerifier
from scripts.audit_source_set_logic import verify_set_certificate
from scripts.audit_signed_logic import VerificationCapacityExceeded
from scripts.run_source_universe import meter
from scripts.run_source_alignment import exclusive,ledger
from scripts.evidence_retrieval import encoded
ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/human_source_coverage.py','scripts/audit_human_source_coverage.py','scripts/run_human_source_coverage.py','tests/test_human_source_coverage.py','docs/HUMAN-SOURCE-COVERAGE.md','docs/human-source-coverage-inputs.json','scripts/proofwriter_english.py','scripts/proofwriter_representation.py','scripts/audit_proofwriter_english.py','scripts/audit_proofwriter_representation.py','scripts/source_set_logic.py','scripts/audit_source_set_logic.py')
METHODS=('canonical','human')
LABELS=('True','False','Unknown')
def gold_label(value):
 if value is True:return 'True'
 if value is False:return 'False'
 if value=='Unknown' and type(value) is str:return 'Unknown'
 raise ValueError('Unsupported official label')
def prediction_label(certificate):return {'supported':'True','refuted':'False','unknown':'Unknown'}.get(certificate['verdict']) if certificate['complete'] else None

def run_theory(raw,work,index,*,gold_observer=None,method='human'):
 start=time.perf_counter();cpu=time.process_time();folder=Path(work)/('theory-'+str(index));folder.mkdir(exist_ok=False);row=parse(raw);questions=row['questions'];assert type(questions) is dict and questions;rows=[];before_gold=[];error=None;store=None;mapping=[];compiled={};constructor_stats=None;compilation_audit=None;compilation_audit_error=None;recovery=None;ingest=None;source_bytes=None;proof_bindings=0;original_bindings=0
 try:
  if len(raw)>1<<20:raise UnsupportedRepresentation('Original theory size cap')
  compiler=HumanSourceCompiler(world='OWA') if method=='human' else Compiler(world='OWA');compiled,mapping=compiler.compile_sentences(row['sentences']) if method=='human' else compiler.compile(row['triples'],row['rules']);source=folder/'source';source.mkdir();exclusive(source/'original.json',raw)
  for n,value in compiled.items():exclusive(source/n,value)
  exclusive(folder/'private-compilation-map.json',encoded(mapping)+b'\n');store=Store.create(folder/'store',compression='zlib',io_backend='bounded');t=time.perf_counter();c=time.process_time();commit=store.add(source);ingest={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'commit':commit};sid=commit['snapshot_id'];before=ledger(store.root)
  with meter() as constructor_stats:engine=SourceSetVerifier(store,sid,sorted(compiled),source_byte_budget=1<<20)
 except (ValueError,VerificationCapacityExceeded) as exc:error=type(exc).__name__+':'+str(exc)
 # Every controlled-English prediction saved before reading any answer/depth/proof field for this theory.
 for question_index,qid in enumerate(sorted(questions)):
  question=questions[qid];certificate=None;failure=error;t=time.perf_counter();c=time.process_time()
  if failure is None:
   try:
    query=compiler.ground(question['question']);certificate=engine.infer(query,work_budget=100000)
   except (ValueError,VerificationCapacityExceeded) as exc:failure=type(exc).__name__+':'+str(exc)
  output={'question_id':qid,'original_English_query_sha256':digest(question['question'].encode('utf-8')) if type(question['question']) is str else digest(encoded(question['question'])),'predicted_label':prediction_label(certificate) if certificate else None,'engine_verdict':certificate['verdict'] if certificate else None,'engine_complete':certificate['complete'] if certificate else False,'prediction_failure':failure,'prediction_wall_s':time.perf_counter()-t,'prediction_cpu_s':time.process_time()-c,'certificate_sha256':digest(encoded(certificate)) if certificate else None,'scientific_entailment_verified':False,'generated_answer':None};exclusive(folder/('query-'+str(question_index)+'-prediction.json'),encoded(output)+b'\n')
  if certificate is not None:exclusive(folder/('query-'+str(question_index)+'-private-certificate.json'),encoded(certificate)+b'\n')
  before_gold.append((qid,output,certificate))
 exclusive(folder/'predictions-before-gold.json',encoded([x[1] for x in before_gold])+b'\n')
 if gold_observer:gold_observer(folder,before_gold)
 # Independent compilation and complete-source proof audit precede score acceptance, after predictions.
 if store is not None and error is None:
  try:
   with meter() as stats:compilation_audit=(audit_human_compilation if method=='human' else audit_compilation)(store,sid,mapping,sorted(compiled),world='OWA')
   compilation_audit['observed_source_payload_returned_bytes']=stats['source_application_returned_bytes'];original_bindings=compilation_audit['original_English_bindings'];assert compilation_audit['controlled_English_alignment_with_supplied_reference_verified']
  except (ValueError,VerificationCapacityExceeded) as exc:compilation_audit_error=type(exc).__name__+':'+str(exc)
 for qid,output,certificate in before_gold:
  accepted=False;audit=None;audit_error=None;t=time.perf_counter();c=time.process_time()
  if certificate is not None:
   try:
    if certificate['query']!=reference_query(questions[qid]['representation']):raise ValueError('Independent query translation differs')
    with meter() as stats:audit=verify_set_certificate(store,sid,certificate)
    audit['observed_source_payload_returned_bytes']=stats['source_application_returned_bytes'];proof_bindings+=len(certificate['nodes']);accepted=audit['closure_completeness_verified'] and compilation_audit is not None and output['predicted_label'] is not None
   except (ValueError,VerificationCapacityExceeded) as exc:audit_error=type(exc).__name__+':'+str(exc)
  label=gold_label(questions[qid]['answer']);depth=questions[qid].get('QDep');correct=accepted and output['predicted_label']==label;rows.append({**output,'gold':label,'QDep_after_prediction':depth,'accepted_controlled_English_with_reference_alignment':accepted,'correct':correct,'independent_audit_error':audit_error,'independent_audit_wall_s':time.perf_counter()-t,'independent_audit_cpu_s':time.process_time()-c,'independent_audit':audit})
 if store is not None:
  assert ledger(store.root)==before
  with store.snapshot(sid) as snap:
   original=snap.read_range('original.json');assert original==raw
   for n,value in compiled.items():assert snap.read_range(n)==value
  recovery={'original_bytes':len(raw),'original_sha256':digest(raw),'derived_files':{n:{'bytes':len(v),'sha256':digest(v)} for n,v in compiled.items()}};assert ledger(store.root)==before
 retained={p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in folder.rglob('*') if p.is_file()};return {'method':method,'theory_index':index,'theory_id':row.get('id'),'original_record_sha256':digest(raw),'original_record_bytes':len(raw),'questions':len(questions),'records':rows,'compilation_failure':error,'compilation_audit':compilation_audit,'compilation_audit_error':compilation_audit_error,'constructor_source_stats':dict(constructor_stats) if constructor_stats is not None else None,'ingest':ingest,'recovery':recovery,'source_English_bindings':original_bindings,'derived_record_DAG_bindings':proof_bindings,'retained_files':retained,'retained_total_bytes':sum(e['bytes'] for e in retained.values()),'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-cpu,'predictions_persisted_before_gold':True,'controlled_English_is_only_predictor_source':True,'supplied_formal_reference_and_gold_not_used_as_predictor_input':True}

def worker(a):
 start=time.perf_counter();cpu=time.process_time();folder=Path(a.work);folder.mkdir(exist_ok=False);manifest=parse((ROOT/'docs/human-source-coverage-inputs.json').read_bytes());input_meta=parse(Path(a.input_meta).read_bytes());prefix=Path(input_meta['prefix_path']).read_bytes();assert len(prefix)==input_meta['prefix_bytes'] and digest(prefix)==input_meta['prefix_sha256'];raw_rows=prefix.splitlines(keepends=True);assert len(raw_rows)==32;theories=[]
 for index,raw in enumerate(raw_rows):
  record=run_theory(raw,folder,index,method=a.method);exclusive(folder/('theory-'+str(index)+'-aggregate.json'),encoded(record)+b'\n');theories.append(record)
 allrows=[r for t in theories for r in t['records']];total=len(allrows);correct=sum(r['correct'] for r in allrows);accepted=sum(r['accepted_controlled_English_with_reference_alignment'] for r in allrows);classes={label:{'total':sum(r['gold']==label for r in allrows),'correct':sum(r['gold']==label and r['correct'] for r in allrows)} for label in LABELS};sourcefail=[t for t in theories if t['compilation_failure']];retained={p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in folder.rglob('*') if p.is_file()};report={'round':a.round,'method':a.method,'theories':32,'questions':total,'correct':correct,'accepted':accepted,'allquestions_accuracy':correct/total if total else None,'H1_human_accuracy_at_least95percent_and3classes':a.method=='human' and total>0 and correct*100>=95*total and all(v['total']>0 for v in classes.values()),'H2_human_allquestions_accepted_and32recoveries':a.method=='human' and accepted==total and all(t['recovery'] and t['compilation_audit'] for t in theories),'classes':classes,'abstained_or_failed':sum(not r['accepted_controlled_English_with_reference_alignment'] for r in allrows),'accepted_wrong':sum(r['accepted_controlled_English_with_reference_alignment'] and not r['correct'] for r in allrows),'source_compilation_failure_theories':len(sourcefail),'source_failure_counts':dict(Counter(t['compilation_failure'] for t in sourcefail)),'query_failure_counts':dict(Counter(r['prediction_failure'] for r in allrows if r['prediction_failure'])),'source_reference_alignment_failed_theories':sum(t['compilation_audit_error'] is not None for t in theories),'theory_records':theories,'original_recovery_theories':sum(t['recovery'] is not None for t in theories),'source_English_bindings':sum(t['source_English_bindings'] for t in theories),'derived_record_DAG_bindings':sum(t['derived_record_DAG_bindings'] for t in theories),'retained_all_work_files':retained,'retained_all_work_bytes':sum(e['bytes'] for e in retained.values()),'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss(),'new_training_runs':0,'current_loaded_model_bytes':0,'new_remote_model_calls':0,'scientific_entailment_verified':False,'unrestricted_English_NLI_verified':False,'generated_answers':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,'scope':'Same32officialParaRules NatLang theories: canonical English positivecontrol vs actualhuman sentences only, no canonical/mapping fallback forhuman predictor, unsupported staysallquestiondenominator','faster_abstention_not_a_performance_benefit':True};exclusive(Path(a.worker_report),encoded(report)+b'\n');print(json.dumps({'method':a.method,'round':a.round,'questions':total,'correct':correct,'accepted':accepted,'sourcefailtheories':len(sourcefail)}),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--input-meta',type=Path,required=True);p.add_argument('--worker-report',type=Path,required=True);p.add_argument('--method',choices=METHODS,required=True);p.add_argument('--round',type=int,required=True);a=p.parse_args();worker(a)
if __name__=='__main__':main()
