"""One deterministic explanation worker over already-scored inputs; no remote model access."""
import argparse,json,time,hashlib,os
from pathlib import Path
from rkv1.store import Store
from rkv1.benchmark import peak_rss
from scripts.audit_api_admission_case import audit_case

def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def write(p,v):
 with p.open('xb') as f:f.write(canonical(v)+b'\n');f.flush();os.fsync(f.fileno())
def inventory(folder):return {p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in folder.rglob('*') if p.is_file()}
def run(context,questions,gold,hits,expected,out):
 out=Path(out);out.mkdir(exist_ok=False);start=time.perf_counter();cpu=time.process_time();success=False
 try:
  assert len(questions)==expected['queries'] and set(questions)==set(gold)==set(hits);raw=Path(context['model_path_private']).read_bytes();assert sha(raw)==context['model_SHA'] and len(raw)==context['model_B'];model=json.loads(raw);shared=model['shared'];assert shared['source_sha256']==context['source_sha256'];store=Store(context['store_root_private']);before=inventory(store.root);rows=[];selected_total=gold_total=missing=oversize=bindings=returned=0
  with store.snapshot(context['snapshot_id']) as snapshot:
   full=snapshot.read_range('corpus.jsonl');assert len(full)==context['source_B'] and sha(full)==context['source_sha256'];returned+=len(full)
   for qid,question in questions.items():
    row=gold[qid];assert str(row['id'])==qid and row['claim']==question;goldids={'doc:'+str(k) for k,v in row['evidence'].items() if v};result=audit_case(snapshot,shared,question,goldids,hits[qid]);selected_total+=len(result['selected_ids']);gold_total+=len(goldids);bindings+=result['original_record_checks'];returned+=result['application_returned_B']
    for event in result['gold_events'].values():
     if event['category']!='recovered':missing+=1;oversize+=event['self_exceeds_entire_budget']
    rows.append({'claim_id':qid,'question_SHA':sha(question.encode()),**result})
  assert selected_total==expected['old_selected_record_bindings'] and gold_total==expected['annotated_gold_papers'] and missing==expected['old_missing_gold_papers'] and before==inventory(store.root)
  report={'queries':len(rows),'old_selected_bindings':selected_total,'gold_papers':gold_total,'missing_gold_papers':missing,'self_oversize_among_missing':oversize,'H1_exact_order_ids_source_and_metadata':True,'H2_missing_self_oversize_strict_majority':oversize>missing/2 if missing else None,'rows':rows,'source_snapshot_id':context['snapshot_id'],'full_corpus_files_recovered':1,'original_record_read_bindings':bindings,'application_returned_B':returned,'store_unchanged':True,'new_model_calls':0,'new_training_runs':0,'no_new_scientific_evaluation':True}
  write(out/'worker.json',report);success=True;return report
 finally:write(out/'finally-timing.json',{'success':success,'worker_full_wall_s':time.perf_counter()-start,'worker_full_CPU_s':time.process_time()-cpu,'peak_RSS_B':peak_rss()})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=Path.cwd();d=root/'.tools/v084-draft';m=json.loads((root/'docs/api-admission-audit-inputs.json').read_bytes());context=json.loads((d/'retrieval-context-private.json').read_bytes());questions={x['claim_id']:x['claim'] for x in json.loads((d/'questions-private.json').read_bytes())};gold={str(x['id']):x for x in json.loads((d/'gold-private.json').read_bytes())};hits=json.loads((root/'.tools/api-intervention-v084-measured/retrieval-private.json').read_bytes());run(context,questions,gold,hits,m,a.out)
