"""Independent source/prompt/citation/annotation scorer; no model or candidate parser imports."""
import hashlib,json,math
from pathlib import Path
from rkv1.store import Store

def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def duplicate_guard(items):
 d={}
 for k,v in items:
  if k in d:raise ValueError('Duplicate JSON key')
  d[k]=v
 return d

def audit(folder,store_root,plan,questions,gold):
 folder=Path(folder);final=json.loads((folder/'campaign-final.json').read_bytes());assert len(plan['jobs'])==48 and len(questions)==16 and set(gold)==set(questions);assert final['planned_calls']==48 and final['attempted_calls']+final['missing_planned_calls']==48 and final['store_unchanged'];retrieval=json.loads((folder/'retrieval-private.json').read_bytes());assert set(retrieval)==set(questions);source_checks=bytes_read=0
 with Store(store_root).snapshot(final['source_snapshot_id']) as snap:
  for hits in retrieval.values():
   assert len(hits)<=12 and sum(h['locator']['length'] for h in hits)<=4096
   for j,h in enumerate(hits):
    loc=h['locator'];assert loc['snapshot_id']==snap.snapshot_id and loc['path']=='corpus.jsonl' and h['citation_id']=='D'+str(j) and h['source_bytes_verified'] is True;raw=snap.read_range(loc['path'],loc['offset'],loc['length']);assert sha(raw)==loc['sha256'];obj=json.loads(raw);assert 'doc:'+str(obj['doc_id'])==h['key'] and obj['title']==h['title'] and obj['abstract']==h['sentences'];source_checks+=1;bytes_read+=len(raw)
 rows=[];last_stamp=0;attempted=0
 for index,job in enumerate(plan['jobs']):
  goldrow=gold[job['claim_id']];labels={r['label'] for rs in goldrow['evidence'].values() for r in rs};assert len(labels)<=1;expected=next(iter(labels)) if labels else 'INSUFFICIENT';annotated={(str(doc),i) for doc,rs in goldrow['evidence'].items() for r in rs for i in r['sentences']};sets=[{(str(doc),i) for i in r['sentences']} for doc,rs in goldrow['evidence'].items() for r in rs];hits=[] if job['condition']=='empty' else retrieval[job['donor_claim_id']];stem='slot-'+str(index).zfill(2);reserved=folder/(stem+'.reserved.json');resultfile=folder/(stem+'.result.json');accepted=False;verdict=None;pairs=set();usage=None;response_model=None
  if reserved.exists():
   attempted+=1;res=json.loads(reserved.read_bytes());assert res['index']==index and res['job']==job and res['reserved_UTC_ns']>last_stamp;last_stamp=res['reserved_UTC_ns'];raw=(folder/(stem+'.request-private.json')).read_bytes();body=json.loads(raw);assert res['request_sha256']==sha(canonical(body)) and res['request_B']==len(canonical(body))<=20000 and set(body)=={'model','messages','temperature','max_tokens','thinking','response_format'} and body['model']=='deepseek-flash' and body['max_tokens']==512 and body['temperature']==0 and body['thinking']=={'type':'disabled'} and body['response_format']=={'type':'json_object'}
   prompt=json.loads(body['messages'][1]['content']);expected_evidence=[{'citation_id':h['citation_id'],'title':h['title'],'sentences':[{'sentence':i,'text':v} for i,v in enumerate(h['sentences'])]} for h in hits];assert prompt=={'claim':questions[job['claim_id']],'evidence':expected_evidence} and body['messages'][0]['role']=='system' and body['messages'][1]['role']=='user'
   if resultfile.exists():
    rec=json.loads(resultfile.read_bytes());assert rec['index']==index and rec['job']==job and rec['request_sha256']==res['request_sha256'] and rec['request_B']==res['request_B'] and rec['max_output_tokens']==512;accepted=rec['accepted'];usage=rec['usage'];response_model=rec.get('response_model')
    raw_response=folder/(stem+'.response-private.bin')
    if raw_response.exists():
     rb=raw_response.read_bytes();assert sha(rb)==rec['response_SHA'] and len(rb)==rec['response_B']<=1<<20
     if accepted:
      reply=json.loads(rb);assert reply.get('model')==rec['response_model'] and reply.get('usage')==rec['usage'] and reply['choices'][0]['message']['content']==rec['raw_model_content'] and reply['choices'][0].get('finish_reason')==rec['finish_reason']
    else:assert not accepted
    if accepted:
     assert rec['error'] is None and rec['finish_reason']=='stop';obj=json.loads(rec['raw_model_content'],object_pairs_hook=duplicate_guard);assert set(obj)=={'verdict','evidence','explanation'} and obj['verdict'] in ('SUPPORT','CONTRADICT','INSUFFICIENT') and type(obj['explanation']) is str and len(obj['explanation'].split())<=35 and type(obj['evidence']) is list;available={h['citation_id']:h for h in hits};bindings=[];seen=set()
     for cite in obj['evidence']:
      assert set(cite)=={'citation_id','sentence'} and cite['citation_id'] in available and type(cite['sentence']) is int;h=available[cite['citation_id']];i=cite['sentence'];assert 0<=i<len(h['sentences']) and (cite['citation_id'],i) not in seen;seen.add((cite['citation_id'],i));pairs.add((h['key'].removeprefix('doc:'),i));bindings.append({**cite,'key':h['key'],'locator':h['locator'],'sentence_sha256':sha(h['sentences'][i].encode())})
     assert obj['verdict']=='INSUFFICIENT' or bindings;assert rec['answer']['verdict']==obj['verdict'] and rec['answer']['evidence']==bindings and rec['answer']['citation_binding_valid'] is True and rec['answer']['scientific_entailment_verified'] is False;verdict=obj['verdict']
  else:assert not resultfile.exists()
  complete=bool(any(s<=pairs for s in sets));correct=accepted and verdict==expected;rows.append({'index':index,'claim_id':job['claim_id'],'condition':job['condition'],'attempted':reserved.exists(),'accepted':accepted,'gold_verdict':expected,'predicted_verdict':verdict,'correct':bool(correct),'complete_annotated_rationale':complete,'annotated_citation_precision':len(pairs&annotated)/len(pairs) if pairs and annotated else None,'grounded_annotated_correct':bool(correct and complete) if annotated else None,'usage':usage,'response_model':response_model,'citations':sorted([list(p) for p in pairs])})
 assert attempted==final['attempted_calls']
 groups={}
 for condition in ('empty','retrieved','rotated'):
  r=[x for x in rows if x['condition']==condition];assert len(r)==16;ann=[x for x in r if x['gold_verdict']!='INSUFFICIENT'];assert len(ann)==12
  groups[condition]={'planned':16,'attempted':sum(x['attempted'] for x in r),'accepted':sum(x['accepted'] for x in r),'correct':sum(x['correct'] for x in r),'annotated_denominator':12,'grounded_annotated_correct':sum(bool(x['grounded_annotated_correct']) for x in ann),'class_denominators':{c:sum(x['gold_verdict']==c for x in r) for c in ('SUPPORT','CONTRADICT','INSUFFICIENT')}}
 comparisons=[]
 for control in ('empty','rotated'):
  a={r['claim_id']:r for r in rows if r['condition']=='retrieved'};b={r['claim_id']:r for r in rows if r['condition']==control};wins=sum(a[i]['correct'] and not b[i]['correct'] for i in a);losses=sum(b[i]['correct'] and not a[i]['correct'] for i in a);n=wins+losses;tail=sum(math.comb(n,j) for j in range(min(wins,losses)+1))/2**n if n else 1;comparisons.append({'retrieved_vs':control,'win':wins,'loss':losses,'tie':16-n,'two_sided_exact_p_descriptive_only':min(1,2*tail) if n else 1})
 quality=final['complete'] and all(groups['retrieved'][k]>groups[c][k] for c in ('empty','rotated') for k in ('correct','grounded_annotated_correct'))
 return {'rows':rows,'groups':groups,'comparisons':comparisons,'complete':final['complete'],'source_records_independently_checked':source_checks,'source_application_B':bytes_read,'H1_mechanical_audit':True,'H2_retrieved_quality_over_both_controls':bool(quality),'no_independent_scientific_entailment_proof':True,'unannotated_is_annotation_proxy_not_absence_proof':True}
