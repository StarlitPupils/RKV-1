"""Private CPU-only source-selection prototype; gold is not an input to predictions."""
import time
_PROCESS_WALL=time.perf_counter();_PROCESS_CPU=time.process_time()
import json,hashlib,os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from rkv1.experiments.paper_retriever import PaperRetriever
from rkv1.benchmark import peak_rss
from scripts.evidence_retrieval import lexical,admit
from scripts.cost_aware_order import order,METHODS

def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def write(path,value):
 with path.open('xb') as f:f.write(canonical(value)+b'\n');f.flush();os.fsync(f.fileno())
def query(api,question,method):
 if method=='lexical':return api.query(question,method='lexical',max_papers=12,source_byte_budget=4096)
 model=api._model;ranked,scores=lexical(model['shared'],question);ranked=order(model['shared']['locators'],ranked,scores,method);selected,used=admit(model,ranked,max_facts=12,max_source_bytes=4096);hits=[]
 with api._store.snapshot(api._sid) as snap:
  api._source(snap)
  for key in selected:
   loc=model['shared']['locators'][key];raw=snap.read_range('corpus.jsonl',loc['offset'],loc['length']);assert sha(raw)==loc['sha256'];obj=json.loads(raw);assert 'doc:'+str(obj['doc_id'])==key and type(obj['title']) is str and type(obj['abstract']) is list and all(type(s) is str for s in obj['abstract']);hits.append({'paper_id':key,'title':obj['title'],'abstract':obj['abstract'],'locator':{'snapshot_id':snap.snapshot_id,'path':'corpus.jsonl',**loc},'title_sha256':sha(obj['title'].encode()),'abstract_sha256':sha(canonical(obj['abstract']))})
 return {'method':method,'selected_ids':selected,'admitted_record_bytes':used,'hits':hits,'selected_source_identity_verified':True,'scientific_entailment_verified':False}
def run(context,questions,method,out):
 if method not in METHODS or type(questions) is not list or not questions or len({q['claim_id'] for q in questions})!=len(questions) or any(set(q)!={'claim_id','claim'} for q in questions):raise ValueError('Explicit unique question-only workload required')
 out=Path(out);out.mkdir(exist_ok=False);start=time.perf_counter();cpu=time.process_time();ok=False;rows=[];phase_wall=phase_CPU=returned=bindings=0
 try:
  t=time.perf_counter();c=time.process_time();api=PaperRetriever(context['store_root_private'],context['snapshot_id'],context['model_path_private'],model_sha256=context['model_SHA']);ctor={'wall_s':time.perf_counter()-t,'CPU_s':time.process_time()-c};phase_wall+=ctor['wall_s'];phase_CPU+=ctor['CPU_s']
  for i,q in enumerate(questions):
   t=time.perf_counter();c=time.process_time();result=query(api,q['claim'],method);assert result['admitted_record_bytes']<=4096 and len(result['selected_ids'])<=12 and result['selected_source_identity_verified'];proof=[{k:h[k] for k in ('paper_id','locator','title_sha256','abstract_sha256')} for h in result['hits']];bindings+=len(proof);returned+=result['admitted_record_bytes'];rec={'index':i,'claim_id':q['claim_id'],'question_SHA':sha(q['claim'].encode()),'selected_ids':result['selected_ids'],'admitted_record_B':result['admitted_record_bytes'],'source_proof':proof,'scientific_entailment_verified':False};write(out/('query-'+str(i).zfill(3)+'.json'),rec);wall=time.perf_counter()-t;elapsed_CPU=time.process_time()-c;phase_wall+=wall;phase_CPU+=elapsed_CPU;rows.append({'index':i,'claim_id':q['claim_id'],'wall_s':wall,'CPU_s':elapsed_CPU,'proof_SHA':sha(canonical(rec)),'selected_ids':result['selected_ids'],'admitted_record_B':result['admitted_record_bytes']})
  summary={'method':method,'questions':len(questions),'constructor':ctor,'rows':rows,'algorithm_phase_wall_s':phase_wall,'algorithm_phase_CPU_s':phase_CPU,'application_returned_B':returned,'original_source_bindings':bindings,'source_snapshot_id':context['snapshot_id'],'model_SHA':context['model_SHA'],'new_training_runs':0,'new_model_calls':0,'gold_read_by_prediction':False};write(out/'worker.json',summary);ok=True;return summary
 finally:write(out/'finally-timing.json',{'success':ok,'worker_full_wall_s':time.perf_counter()-start,'worker_full_CPU_s':time.process_time()-cpu,'peak_RSS_B':peak_rss()})

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--context',type=Path,required=True);parser.add_argument('--questions',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--method',choices=METHODS,required=True);args=parser.parse_args();status={'success':False}
 try:
  context=json.loads(args.context.read_bytes());questions=json.loads(args.questions.read_bytes());run(context,questions,args.method,args.out);status['success']=True
 finally:
  if args.out.exists():write(args.out/'process-finally.json',{**status,'process_entry_to_finally_wall_s':time.perf_counter()-_PROCESS_WALL,'process_CPU_s':time.process_time()-_PROCESS_CPU,'peak_RSS_B':peak_rss(),'timer_scope':'module time import to finally before footer write; parent includes interpreter startup and footer write'})
