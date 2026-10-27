"""Frozen finite-program metamorphic mechanism campaign, not natural-language NLI."""
import argparse,json,subprocess,time
from pathlib import Path
from rkv1.store import Store
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from scripts.logic_fixture import encode
from scripts.logic_metamorphic import programs,queries,transformed,transform_atom,VARIANTS
from scripts.signed_logic import SignedVerifier
from scripts.audit_signed_logic import parse_source,oracle,literal,verify_certificate
from scripts.run_source_alignment import ledger,exclusive
from scripts.evidence_retrieval import encoded
ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/logic_metamorphic.py','scripts/run_logic_metamorphic.py','tests/test_logic_metamorphic.py','docs/LOGIC-METAMORPHIC.md','docs/logic-metamorphic-inputs.json','scripts/signed_logic.py','scripts/audit_signed_logic.py','scripts/logic_fixture.py')
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--freeze',required=True);a=p.parse_args();t=time.perf_counter();cpu=time.process_time();a.work.mkdir(exist_ok=False);a.out.mkdir(exist_ok=False);case_dir=a.work/'cases';case_dir.mkdir();sources=a.work/'all-sources';sources.mkdir();source=a.work/'source';source.mkdir();manifest=json.loads((ROOT/'docs/logic-metamorphic-inputs.json').read_bytes());checks=implementation_checksums()
 for n in TRACKED:assert (ROOT/n).read_bytes()==subprocess.check_output(['git','show',a.freeze+':'+n])
 for n,sha in checks.items():assert digest(subprocess.check_output(['git','show',a.freeze+':rkv1/'+n]))==sha
 store=Store.create(a.work/'store',compression='zlib',io_backend='bounded');records=[];snapshot_records=[];negative=[];correct=0;metamorphic=0;bindings=0;application_bytes=0;stages=[]
 def verdict(known,q):
  target=literal(q);support=target in known;opposite=(target[0],target[1],not target[2]) in known;return 'inconsistent' if support and opposite else 'supported' if support else 'refuted' if opposite else 'unknown'
 for index,program in enumerate(programs()):
  base_raw=encode(program);base_truth,_=oracle(parse_source(base_raw,'owned-reference','axioms.jsonl'),literal(queries()[0]));base_expected=[verdict(base_truth,q) for q in queries()];base_sid=None
  for variant in VARIANTS:
   stage_t=time.perf_counter();stage_cpu=time.process_time();raw=encode(transformed(program,variant,index));key=str(index)+'-'+variant;assert digest(raw)==manifest['source_sha256'][key];exclusive(sources/(key+'.jsonl'),raw);(source/'axioms.jsonl').write_bytes(raw);it=time.perf_counter();ic=time.process_time();commit=store.add(source);ingest={'wall_s':time.perf_counter()-it,'cpu_s':time.process_time()-ic};sid=commit['snapshot_id'];snapshot_records.append({'case':index,'variant':variant,'snapshot_id':sid,'source_sha256':digest(raw),'bytes':len(raw)});before=ledger(store.root);reader=SignedVerifier(store,sid,'axioms.jsonl');application_bytes+=len(raw);first_certificate=None
   for qi,q in enumerate(queries()):
    transformed_query=transform_atom(q,variant);certificate=reader.infer(transformed_query,work_budget=100000);exclusive(case_dir/(key+'-'+str(qi)+'.json'),encoded(certificate)+b'\n');audit=verify_certificate(store,sid,'axioms.jsonl',certificate);expected=base_expected[qi];assert certificate['complete'] and audit['closure_completeness_verified'] and certificate['verdict']==expected;correct+=1;bindings+=len(certificate['nodes']);application_bytes+=audit['original_source_application_returned_bytes'];metamorphic+=variant!='base';records.append({'case':index,'variant':variant,'query_index':qi,'verdict':certificate['verdict'],'expected_from_base_independent_closure':expected,'certificate_sha256':audit['certificate_sha256'],'proof_nodes':len(certificate['nodes']),'work_used':certificate['work_used']})
    if first_certificate is None:first_certificate=certificate
   assert before==ledger(store.root)
   if variant=='base':base_sid=sid
   else:
    try:verify_certificate(store,base_sid,'axioms.jsonl',first_certificate)
    except ValueError as exc:negative.append({'case':index,'variant':variant,'wrong_SID_rejected':True,'error_type':type(exc).__name__})
    else:raise AssertionError('Cross-source certificate accepted')
   stages.append({'case':index,'variant':variant,'ingest':ingest,'all_including_ingest_constructor27queries_and_independent_audit_wall_s':time.perf_counter()-stage_t,'cpu_s':time.process_time()-stage_cpu,'store_unchanged_during_queries':True})
 recovery=[]
 for e in snapshot_records:
  with store.snapshot(e['snapshot_id']) as snap:restored=snap.read_range('axioms.jsonl')
  assert len(restored)==e['bytes'] and digest(restored)==e['source_sha256'];application_bytes+=len(restored);recovery.append({'snapshot_id':e['snapshot_id'],'source_sha256':digest(restored)})
 retained={p.relative_to(a.work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in a.work.rglob('*') if p.is_file()};runtime={'rkv1/'+n:{'bytes':(ROOT/'rkv1'/n).stat().st_size,'sha256':sha} for n,sha in checks.items()};runtime.update({p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in (ROOT/'rkv1').rglob('*.html')});assessment={n:{'bytes':(ROOT/n).stat().st_size,'sha256':digest((ROOT/n).read_bytes())} for n in TRACKED};all_scripts={}
 for p in (ROOT/'scripts').rglob('*.py'):
  rel=p.relative_to(ROOT).as_posix();raw=p.read_bytes();assert raw==subprocess.check_output(['git','show',a.freeze+':'+rel]);all_scripts[rel]={'bytes':len(raw),'sha256':digest(raw)}
 report={'H1_independent_verdict_and_original_certificate_mechanism':correct==1296,'H2_three_metamorphic_verdict_invariants_and_cross_source_rejection':metamorphic==972 and len(negative)==36,'formal_workers':1,'formal_retries':0,'base_programs':12,'variants':list(VARIANTS),'source_ingests':48,'main_certificates':1296,'metamorphic_nonbase_comparisons':972,'cross_source_negative_controls':negative,'historical_full_source_recoveries':48,'records':records,'snapshots':snapshot_records,'stages':stages,'recovery':recovery,'source_record_bindings':bindings,'successful_constructor_auditor_full_recovery_application_source_bytes':application_bytes,'rejected_control_returned_bytes':None,'retained_work_files':retained,'retained_work_total_bytes':sum(e['bytes'] for e in retained.values()),'worker_wall_s':time.perf_counter()-t,'worker_cpu_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss(),'runtime_module_count':len(checks),'runtime_html_count':sum(n.endswith('.html') for n in runtime),'runtime_files':runtime,'assessment_programs':assessment,'all_existing_experimental_script_source_conservative_allocation':all_scripts,'freeze':a.freeze,'new_training_runs':0,'current_loaded_model_bytes':0,'historical_costs':'results/v0.65.0/measurement-context.json and all older model/source/training/snapshots retained','new_remote_model_calls':0,'scientific_entailment_verified':False,'generated_answers':0,'scope':'Owned finite-rule mechanism differential and metamorphic check only, no NL/scientific NLI/answer claim','physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None};exclusive(a.out/'raw-worker.json',encoded(report)+b'\n');exclusive(a.out/'source-checksums.json',encoded(checks)+b'\n');print(json.dumps({'H1':report['H1_independent_verdict_and_original_certificate_mechanism'],'H2':report['H2_three_metamorphic_verdict_invariants_and_cross_source_rejection'],'main':1296,'metamorphic':972,'negative':len(negative)}),flush=True)
if __name__=='__main__':main()
