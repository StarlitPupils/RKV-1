"""Assessment-only bounded API evidence intervention; no retrieval or semantic proof claim."""
import hashlib,json,math,os,time
from pathlib import Path
from urllib.request import Request,build_opener
from rkv1.memory_model import NoRedirect,messages,validate_answer
from scripts.evidence_retrieval import question_identity
ENDPOINT='https://api.deepseek.com/chat/completions'
MODEL='deepseek-flash'
CONDITIONS=('empty','retrieved','rotated')
MAX_CALLS=48
MAX_OUTPUT_TOKENS=512
MAX_REQUEST_B=20000
MAX_RESPONSE_B=1<<20
class TransportPolicyError(ValueError):pass

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def gold_label(claim):
 labels={r['label'] for rows in claim['evidence'].values() for r in rows}
 if not labels:return 'INSUFFICIENT'
 if not labels<={'SUPPORT','CONTRADICT'} or len(labels)!=1:raise ValueError('Mixed or unsupported annotation labels')
 return next(iter(labels))
def plan(claims,training=()):
 old=[]
 for label in ('SUPPORT','CONTRADICT','INSUFFICIENT'):
  old.extend(sorted((c for c in claims if gold_label(c)==label),key=lambda c:c['id'])[:4])
 oldids={c['id'] for c in old};oldq={question_identity(c['claim']) for c in old};trainid={str(c['id']) for c in training};trainq={question_identity(c['claim']) for c in training};selected=[];seen=set()
 if len({str(c['id']) for c in claims})!=len(claims):raise ValueError('Duplicate claimID')
 for label,n in (('SUPPORT',6),('CONTRADICT',6),('INSUFFICIENT',4)):
  candidates=[]
  for c in claims:
   q=question_identity(c['claim'])
   if c['id'] in oldids or q in oldq or str(c['id']) in trainid or q in trainq or q in seen:continue
   if gold_label(c)==label:candidates.append(c)
  candidates.sort(key=lambda c:(sha(('rkv084-claim:'+str(c['id'])).encode()),str(c['id'])))
  chosen=[]
  for c in candidates:
   q=question_identity(c['claim'])
   if q in seen:continue
   chosen.append(c);seen.add(q)
   if len(chosen)==n:break
  if len(chosen)!=n:raise ValueError('Insufficient disjoint class stratum')
  selected.extend(chosen)
 selected=sorted(selected,key=lambda c:(sha(('rkv084-donor:'+str(c['id'])).encode()),str(c['id'])))
 donor={str(c['id']):str(selected[(i+1)%len(selected)]['id']) for i,c in enumerate(selected)}
 jobs=[{'claim_id':str(c['id']),'condition':condition,'donor_claim_id':donor[str(c['id'])] if condition=='rotated' else str(c['id'])} for c in selected for condition in CONDITIONS]
 jobs.sort(key=lambda j:sha(('rkv084-order:'+j['claim_id']+':'+j['condition']).encode()))
 return {'jobs':jobs,'selected_claim_ids':[str(c['id']) for c in selected],'class_counts':{'SUPPORT':6,'CONTRADICT':6,'INSUFFICIENT':4},'excluded_prior_API_ids':sorted(map(str,oldids)),'no_unseen_data_claim':True}

def request_body(claim,hits):
 if type(claim) is not str or not claim.strip() or len(claim.encode())>4096:raise ValueError('Invalid bounded claim')
 if len(hits)>12 or sum(h['locator']['length'] for h in hits)>4096:raise ValueError('Original record count/byte budget exceeded')
 if any(h.get('source_bytes_verified') is not True for h in hits):raise ValueError('Original source verification required')
 if len({h['citation_id'] for h in hits})!=len(hits):raise ValueError('Duplicate citation identity')
 body={'model':MODEL,'messages':messages(claim,hits),'temperature':0,'max_tokens':MAX_OUTPUT_TOKENS,'thinking':{'type':'disabled'},'response_format':{'type':'json_object'}}
 raw=canonical(body)
 if len(raw)>MAX_REQUEST_B:raise ValueError('Wire request byte budget exceeded')
 return body

def strict_content(content,hits):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('Duplicate JSON field')
   d[k]=v
  return d
 def nonfinite(value):raise ValueError('Nonfinite JSON constant')
 obj=json.loads(content,object_pairs_hook=pairs,parse_constant=nonfinite)
 if type(obj) is not dict or set(obj)!={'verdict','evidence','explanation'} or type(obj['explanation']) is not str or len(obj['explanation'].split())>35:raise ValueError('Exact output schema required')
 result=validate_answer(canonical(obj).decode(),hits)
 return result

def http_transport(body):
 key=os.environ.get('RKV_LLM_API_KEY','')
 if not key:raise ValueError('RKV_LLM_API_KEY missing')
 headers={'Content-Type':'application/json','Authorization':'Bearer '+key}
 try:
  with build_opener(NoRedirect()).open(Request(ENDPOINT,data=canonical(body),headers=headers),timeout=90) as response:raw=response.read(MAX_RESPONSE_B+1)
 except ValueError as exc:raise TransportPolicyError('API transport policy refused') from exc
 if len(raw)>MAX_RESPONSE_B:raise TransportPolicyError('Response size exceeded')
 return raw

def run_slot(folder,index,job,body,hits,*,transport=http_transport):
 folder=Path(folder)
 if type(index) is not int or not 0<=index<MAX_CALLS:raise ValueError('Call budget exceeded')
 # Durable reservation before any transport. An interrupted/failed request is never automatically retried.
 reservation=folder/('slot-'+str(index).zfill(2)+'.reserved.json');raw=canonical(body)
 if len(raw)>MAX_REQUEST_B or body.get('model')!=MODEL or body.get('max_tokens')!=MAX_OUTPUT_TOKENS:raise ValueError('Frozen request budget/model differs')
 with reservation.open('xb') as f:f.write(canonical({'index':index,'job':job,'request_sha256':sha(raw),'request_B':len(raw),'reserved_UTC_ns':time.time_ns()}));f.flush();os.fsync(f.fileno())
 start=time.perf_counter();result={'index':index,'job':job,'attempt_reserved':True,'request_sha256':sha(raw),'request_B':len(raw),'max_output_tokens':MAX_OUTPUT_TOKENS,'accepted':False,'answer':None,'error':None,'usage':None,'remote_model_weights_SHA':None}
 try:
  transported=transport(body);response_raw=transported if type(transported) is bytes else canonical(transported)
  if len(response_raw)>MAX_RESPONSE_B:raise ValueError('Response size exceeded')
  with (folder/('slot-'+str(index).zfill(2)+'.response-private.bin')).open('xb') as f:f.write(response_raw);f.flush();os.fsync(f.fileno())
  result['response_SHA']=sha(response_raw);result['response_B']=len(response_raw);payload=json.loads(response_raw);result['response_model']=payload.get('model');result['response_id']=payload.get('id');result['response_created']=payload.get('created');result['system_fingerprint']=payload.get('system_fingerprint');result['usage']=payload.get('usage');choice=payload['choices'][0];result['finish_reason']=choice.get('finish_reason');content=choice['message']['content'];result['raw_model_content']=content
  if result['finish_reason']!='stop':raise ValueError('Non-stop or truncated output')
  result['answer']=strict_content(content,hits);result['accepted']=True
 except Exception as exc:result['error']={'type':type(exc).__name__,'HTTP_status':getattr(exc,'code',None)}
 finally:
  result['request_wall_s']=time.perf_counter()-start
  with (folder/('slot-'+str(index).zfill(2)+'.result.json')).open('xb') as f:f.write(canonical(result));f.flush();os.fsync(f.fileno())
 return result

def score(gold,record):
 expected=gold_label(gold);answer=record['answer'] if record['accepted'] else None;pairs={(x['key'].removeprefix('doc:'),x['sentence']) for x in answer['evidence']} if answer else set();rationale=any({(str(doc),i) for i in r['sentences']}<=pairs for doc,rows in gold['evidence'].items() for r in rows)
 annotated={(str(doc),i) for doc,rows in gold['evidence'].items() for r in rows for i in r['sentences']};precision=len(pairs&annotated)/len(pairs) if pairs and annotated else None
 verdict=bool(answer and answer['verdict']==expected)
 return {'gold_verdict':expected,'verdict_correct':verdict,'annotated_citation_precision':precision,'annotation_coverage_not_exhaustive':True,'complete_annotated_rationale':rationale,'verdict_and_rationale':verdict and rationale if expected!='INSUFFICIENT' else None,'annotation_proxy_correct':verdict,'unannotated_is_not_proof_of_no_evidence':expected=='INSUFFICIENT','citation_binding_is_not_entailment':True}
