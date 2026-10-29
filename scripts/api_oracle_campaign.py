"""Paired actual retrieval and annotation-aware paper control; no verdict labels in prompt."""
import json,os,time
from pathlib import Path
from scripts.api_intervention import canonical,sha,request_body,run_slot,http_transport
from scripts.oracle_source_plan import oracle_papers
from scripts.api_campaign import write
from rkv1.experiments.paper_retriever import PaperRetriever
from rkv1.store import Store
from rkv1.benchmark import peak_rss
CONDITIONS=('retrieved','oracle')
def validate_plan(plan,questions,targets):
 if len(questions)!=24 or set(questions)!=set(targets) or set(questions)!=set(plan['selected_claim_ids']) or len(plan['jobs'])!=48:raise ValueError('Exact24questions/48pairedjobs required')
 pairs=set()
 for j in plan['jobs']:
  if set(j)!={'claim_id','condition','cohort'} or j['claim_id'] not in questions or j['condition'] not in CONDITIONS or j['cohort'] not in ('v084','v087'):raise ValueError('Unknown fixed role or cohort')
  pair=(j['claim_id'],j['condition'])
  if pair in pairs:raise ValueError('Duplicate role slot')
  pairs.add(pair)
 if pairs!={(i,c) for i in questions for c in CONDITIONS}:raise ValueError('Missing paired condition')
 if any(not v for v in targets.values()):raise ValueError('Annotated-only fixed cohort required')
def prepare_actual(context,questions):
 api=PaperRetriever(context['store_root_private'],context['snapshot_id'],context['model_path_private'],model_sha256=context['model_SHA']);out={}
 for i,q in questions.items():
  result=api.query(q,method='lexical',max_papers=12,source_byte_budget=4096);assert result['selected_source_identity_verified'];out[i]=[{'citation_id':'D'+str(j),'key':h['paper_id'],'title':h['title'],'sentences':h['abstract'],'locator':h['locator'],'source_bytes_verified':True} for j,h in enumerate(result['hits'])]
 return out

def prepare_oracle(context,targets):
 raw=Path(context['model_path_private']).read_bytes();assert sha(raw)==context['model_SHA'];model=json.loads(raw);locators=model['shared']['locators'];out={};omissions={}
 with Store(context['store_root_private']).snapshot(context['snapshot_id']) as snap:
  for i,ids in targets.items():
   selection=oracle_papers(locators,['doc:'+str(x) for x in ids]);hits=[]
   for j,key in enumerate(selection['selected_ids']):
    loc={'snapshot_id':snap.snapshot_id,'path':'corpus.jsonl',**locators[key]};raw=snap.read_range(loc['path'],loc['offset'],loc['length']);assert sha(raw)==loc['sha256'];obj=json.loads(raw);assert 'doc:'+str(obj['doc_id'])==key;hits.append({'citation_id':'D'+str(j),'key':key,'title':obj['title'],'sentences':obj['abstract'],'locator':loc,'source_bytes_verified':True})
   out[i]=hits;omissions[i]=selection
 return out,omissions

def run_trial(context,plan,questions,targets,out,*,transport=None,before_call=None):
 validate_plan(plan,questions,targets)
 if transport is None and (before_call is None or not os.environ.get('RKV_LLM_API_KEY')):raise ValueError('Explicit quota guard and local key required')
 out=Path(out);out.mkdir(exist_ok=False);t=time.perf_counter();cpu=time.process_time();success=False;store=Path(context['store_root_private']);before={p.relative_to(store).as_posix():(p.stat().st_size,sha(p.read_bytes())) for p in store.rglob('*') if p.is_file()}
 try:
  phase=time.perf_counter();actual=prepare_actual(context,questions);write(out/'actual-retrieval-private.json',actual);actual_done=time.time_ns();oracle,omissions=prepare_oracle(context,targets);arms={i:{'retrieved':actual[i],'oracle':oracle[i]} for i in questions};write(out/'retrieval-private.json',arms);write(out/'oracle-selection-private.json',omissions);write(out/'preparation-timing.json',{'full_wall_s':time.perf_counter()-phase,'actual_retrieval_persisted_UTC_ns':actual_done,'oracle_then_prepared':True,'oracle_annotation_aware_not_deployable':True});returned=[];stop=None
  for index,job in enumerate(plan['jobs']):
   if before_call is not None and not before_call():stop={'index':index,'type':'QuotaOrDeadlineStoppedBeforeReservation'};break
   hits=arms[job['claim_id']][job['condition']];body=request_body(questions[job['claim_id']],hits);write(out/('slot-'+str(index).zfill(2)+'.request-private.json'),body);result=run_slot(out,index,job,body,hits,transport=http_transport if transport is None else transport);returned.append(result)
   if result['error'] and result['error']['type'] in ('HTTPError','URLError','TimeoutError','ConnectionError','SSLError','TransportPolicyError'):stop={'index':index,**result['error']};break
  after={p.relative_to(store).as_posix():(p.stat().st_size,sha(p.read_bytes())) for p in store.rglob('*') if p.is_file()};assert before==after
  summary={'planned_calls':48,'attempted_calls':len(returned),'missing_planned_calls':48-len(returned),'complete':len(returned)==48,'transport_stop':stop,'store_unchanged':True,'source_snapshot_id':context['snapshot_id'],'model_SHA':context['model_SHA'],'max_output_tokens':512,'new_remote_calls':len(returned) if transport is None else 0,'oracle_annotation_aware_not_deployable':True,'gold_verdicts_read_by_API_worker':False};write(out/'campaign-final.json',summary);success=True;return summary
 finally:write(out/'campaign-finally.json',{'success':success,'worker_full_wall_s':time.perf_counter()-t,'worker_full_CPU_s':time.process_time()-cpu,'peak_RSS_B':peak_rss()})
