"""Explicit multi-source signed Horn closure, experiment-only and pinned scope."""
import copy
from rkv1.core import digest
from scripts.postings_transform import canonical
from scripts.signed_logic import SignedVerifier,compile_records,atom,MAX_RECORDS,MAX_RULES,MAX_WORK
from scripts.source_universe import load_universe
SCOPE='Explicit signed binary Horn consequences inside the pinned eligible source universe only'
class SourceSetVerifier(SignedVerifier):
 def __init__(self,store,snapshot_id,paths,*,source_byte_budget=1<<20):
  scope,sources=load_universe(store,snapshot_id,paths,source_byte_budget=source_byte_budget);self._source_scope=scope;self._snapshot=snapshot_id;self._path='';self._source_bytes=scope['eligible_payload_bytes'];self._sha=digest(canonical(scope));self._records={}
  if not scope['source_set_complete']:return
  rules=0
  for path,raw in sorted(sources.items()):
   for identifier,record in compile_records(raw,snapshot_id,path).items():
    self._records[(path,identifier)]=record;rules+=record['kind']=='rule'
    if len(self._records)>MAX_RECORDS or rules>MAX_RULES:raise ValueError('Combined source record/rule cap exceeded')
 def infer(self,query,*,work_budget=10000):
  query=atom(query)
  if type(work_budget) is not int or not 0<=work_budget<=MAX_WORK:raise ValueError('Bounded logical work budget required')
  if not self._source_scope['source_set_complete']:
   return {'format':'RKVSETLOGIC1','snapshot_id':self._snapshot,'source_scope':copy.deepcopy(self._source_scope),'query':query.value(),'complete':False,'verdict':'incomplete_source_set','work_used':0,'work_budget':work_budget,'nodes':[],'support_proof':None,'refute_proof':None,'source_grammar_verified':False,'scientific_entailment_verified':False,'generated_answer':None,'scope':SCOPE}
  result=super().infer(query.value(),work_budget=work_budget)
  for key in ('path','source_sha256','source_bytes'):del result[key]
  result.update(format='RKVSETLOGIC1',source_scope=copy.deepcopy(self._source_scope),source_grammar_verified=True,scope=SCOPE)
  for node in result['nodes']:node['source_record_id']=list(node['source_record_id'])
  return result
