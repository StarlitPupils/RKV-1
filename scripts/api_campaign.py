"""Private prototype: question-only retrieval, fixed48one-shot API calls, no labels read."""
import atexit,json,os,time
from pathlib import Path
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from rkv1.experiments.paper_retriever import PaperRetriever
from scripts.api_intervention import CONDITIONS,MAX_CALLS,canonical,request_body,run_slot,http_transport

def write(path,value):
 with path.open('xb') as f:f.write(canonical(value)+b'\n');f.flush();os.fsync(f.fileno())
def validate_inputs(plan,questions):
 if set(questions)!={str(x) for x in plan['selected_claim_ids']} or len(questions)!=16 or len(plan['jobs'])!=48:raise ValueError('Exact16questions48jobs required')
 order=list(map(str,plan['selected_claim_ids']));expected_donor={i:order[(j+1)%len(order)] for j,i in enumerate(order)}
 pairs=set()
 for j in plan['jobs']:
  if set(j)!={'claim_id','condition','donor_claim_id'} or j['claim_id'] not in questions or j['donor_claim_id'] not in questions or j['condition'] not in CONDITIONS:raise ValueError('Unknown query/condition/donor')
  pair=(j['claim_id'],j['condition'])
  if pair in pairs:raise ValueError('Duplicate API condition')
  pairs.add(pair)
  if j['condition']=='rotated' and j['donor_claim_id']!=expected_donor[j['claim_id']]:raise ValueError('Frozen cyclic donor differs')
  if j['condition']!='rotated' and j['claim_id']!=j['donor_claim_id']:raise ValueError('Unexpected donor')
 if pairs!={(i,c) for i in questions for c in CONDITIONS}:raise ValueError('Missing conditions')

def run_trial(store_root,sid,model_path,model_sha,plan,questions,out,*,transport=None,before_call=None):
 validate_inputs(plan,questions)
 if transport is None and before_call is None:raise ValueError('Explicit current-window quota guard required')
 if transport is None and not os.environ.get('RKV_LLM_API_KEY'):raise ValueError('API key missing; no trial or reserved calls started')
 out=Path(out);out.mkdir(exist_ok=False);start=time.perf_counter();cpu=time.process_time();status={'success':False};returned=[];retrieval={};timers=[];before={p.relative_to(store_root).as_posix():(p.stat().st_size,digest(p.read_bytes())) for p in Path(store_root).rglob('*') if p.is_file()}
 try:
  t=time.perf_counter();c=time.process_time();api=PaperRetriever(store_root,sid,model_path,model_sha256=model_sha);construct={'wall_s':time.perf_counter()-t,'CPU_s':time.process_time()-c}
  for i in plan['selected_claim_ids']:
   t=time.perf_counter();c=time.process_time();result=api.query(questions[i],method='lexical',max_papers=12,source_byte_budget=4096);timers.append({'claim_id':i,'wall_s':time.perf_counter()-t,'CPU_s':time.process_time()-c});assert result['selected_source_identity_verified'] and result['admitted_record_bytes']<=4096
   retrieval[i]=[{'citation_id':'D'+str(j),'key':h['paper_id'],'title':h['title'],'sentences':h['abstract'],'locator':h['locator'],'source_bytes_verified':True} for j,h in enumerate(result['hits'])]
  write(out/'retrieval-private.json',retrieval);write(out/'retrieval-timing.json',{'constructor':construct,'queries':timers})
  stop=None
  for index,job in enumerate(plan['jobs']):
   if before_call is not None and not before_call():stop={'index':index,'type':'QuotaOrDeadlineStoppedBeforeReservation'};break
   hits=[] if job['condition']=='empty' else retrieval[job['donor_claim_id']];body=request_body(questions[job['claim_id']],hits);write(out/('slot-'+str(index).zfill(2)+'.request-private.json'),body)
   result=run_slot(out,index,job,body,hits,transport=http_transport if transport is None else transport);returned.append(result)
   if result['error'] and result['error']['type'] in ('HTTPError','URLError','TimeoutError','ConnectionError','SSLError','TransportPolicyError'):
    stop={'index':index,**result['error']};break
  after={p.relative_to(store_root).as_posix():(p.stat().st_size,digest(p.read_bytes())) for p in Path(store_root).rglob('*') if p.is_file()};assert before==after;status['success']=True
  summary={'planned_calls':MAX_CALLS,'attempted_calls':len(returned),'missing_planned_calls':MAX_CALLS-len(returned),'complete':len(returned)==MAX_CALLS,'transport_stop':stop,'store_unchanged':True,'source_snapshot_id':sid,'model_SHA':model_sha,'max_output_tokens':512,'new_remote_calls':len(returned) if transport is None else 0,'fixture_transport':transport is not None,'source_retrieval_not_entailment':True,'gold_labels_read_by_inference':False}
  write(out/'campaign-final.json',summary);return summary
 finally:write(out/'campaign-finally.json',{**status,'worker_full_wall_s':time.perf_counter()-start,'worker_full_CPU_s':time.process_time()-cpu,'peak_RSS_B':peak_rss()})
