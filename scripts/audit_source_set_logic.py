"""Independent original-file scope/DAG/finite-grounding audit for multi-source logic."""
import re
from rkv1.core import digest
from scripts.postings_transform import canonical
from scripts.audit_signed_logic import parse_source,literal,replace,name,oracle
from scripts.audit_source_universe import audit_scope
SCOPE='Explicit signed binary Horn consequences inside the pinned eligible source universe only'
KEYS={'format','snapshot_id','source_scope','query','complete','verdict','work_used','work_budget','nodes','support_proof','refute_proof','source_grammar_verified','scientific_entailment_verified','generated_answer','scope'}
def validate_preflight(store,sid,scope):
 expected_keys={'format','snapshot_id','eligible_suffix','eligible_paths','caller_paths','source_byte_budget','eligible_payload_bytes','source_set_complete','status','reason','source_records','source_application_returned_bytes','source_grammar_verified','logical_closure_verified','scientific_entailment_verified','generated_answer','scope'}
 if type(scope) is not dict or set(scope)!=expected_keys or scope['format']!='RKVSCOPE1' or scope['snapshot_id']!=sid or scope['eligible_suffix']!='.logic.jsonl' or scope['scope']!='Only explicitly eligible machine-source paths; not natural-language or all scientific knowledge':raise ValueError('Scope schema differs')
 if any(scope[k] is not False for k in ('source_grammar_verified','logical_closure_verified','scientific_entailment_verified')) or scope['generated_answer'] is not None:raise ValueError('Source byte scope cannot verify grammar/logic/science')
 budget=scope['source_byte_budget'];paths=scope['caller_paths'];pattern=re.compile(r'[a-z][a-z0-9_-]*(?:/[a-z][a-z0-9_-]*)*\.logic\.jsonl\Z')
 if type(budget) is not int or not 0<=budget<=1048576 or type(paths) is not list or any(type(p) is not str or not pattern.fullmatch(p) for p in paths) or sorted(set(paths))!=paths:raise ValueError('Invalid source preflight input')
 with store.snapshot(sid) as snap:
  eligible=sorted(p for p in snap.files if p.endswith('.logic.jsonl'))
  if any(not pattern.fullmatch(p) for p in eligible):raise ValueError('Malformed eligible source')
  total=sum(snap.files[p]['size'] for p in eligible)
 reason='no_eligible_source_universe' if not eligible else 'eligible_file_count_cap' if len(eligible)>8 else 'caller_set_differs_from_snapshot_eligible_set' if paths!=eligible else 'source_payload_budget_insufficient' if total>budget else None
 if scope['eligible_paths']!=eligible or type(scope['eligible_payload_bytes']) is not int or scope['eligible_payload_bytes']!=total or scope['source_set_complete'] is not (reason is None) or scope['reason']!=reason or scope['status']!=('complete_source_set' if reason is None else 'incomplete_source_set'):raise ValueError('Source preflight differs from actual snapshot')
 if reason is not None:
  if scope['source_records']!=[] or type(scope['source_application_returned_bytes']) is not int or scope['source_application_returned_bytes']!=0:raise ValueError('Incomplete preflight contains payload claim')
  return False,0
 audit=audit_scope(store,sid,scope);return True,audit['auditor_application_returned_bytes']
def verify_set_certificate(store,snapshot_id,certificate):
 c=certificate
 if type(c) is not dict or set(c)!=KEYS or c['format']!='RKVSETLOGIC1' or c['snapshot_id']!=snapshot_id or c['scope']!=SCOPE or c['scientific_entailment_verified'] is not False or c['generated_answer'] is not None or type(c['complete']) is not bool:raise ValueError('Strict multi-source logic certificate scope differs')
 if type(c['work_budget']) is not int or type(c['work_used']) is not int or not 0<=c['work_used']<=c['work_budget']<=100000:raise ValueError('Logical work metadata differs')
 query=literal(c['query']);ready,application=validate_preflight(store,snapshot_id,c['source_scope'])
 if not ready:
  if c['nodes']!=[] or c['support_proof'] is not None or c['refute_proof'] is not None or c['work_used']!=0 or c['complete'] or c['verdict']!='incomplete_source_set' or c['source_grammar_verified'] is not False:raise ValueError('Incomplete source set upgraded to logical verdict')
  return {'certificate_sha256':digest(canonical(c)),'source_set_complete':False,'source_preflight_verified':True,'formal_derivation_verified':False,'closure_completeness_verified':False,'verdict':c['verdict'],'application_source_returned_bytes':application,'scientific_entailment_verified':False,'generated_answer':None}
 if c['source_grammar_verified'] is not True or type(c['nodes']) is not list or len(c['nodes'])>101024:raise ValueError('Grammar/node bounds differ')
 records={};rules=0
 with store.snapshot(snapshot_id) as snap:
  for path in c['source_scope']['eligible_paths']:
   raw=snap.read_range(path);application+=len(raw)
   for identifier,record in parse_source(raw,snapshot_id,path).items():
    records[(path,identifier)]=record;rules+=record['kind']=='rule'
  if len(records)>1024 or rules>64:raise ValueError('Combined source grammar caps')
  atoms=[];seen=set();derived=0
  for i,node in enumerate(c['nodes']):
   identity=node.get('source_record_id') if type(node) is dict else None
   if type(identity) is not list or len(identity)!=2 or any(type(v) is not str for v in identity) or tuple(identity) not in records:raise ValueError('Unambiguous original path-record tuple required')
   record=records[tuple(identity)];keys={'kind','atom','source_record_id','citation'}|({'binding','premise_proofs'} if record['kind']=='rule' else set())
   if set(node)!=keys or node['kind']!=record['kind'] or node['citation']!=record['citation']:raise ValueError('Original record proof identity/citation differs')
   cite=record['citation'];raw=snap.read_range(cite['path'],cite['offset'],cite['length']);application+=len(raw)
   if digest(raw)!=cite['sha256']:raise ValueError('Original record SHA differs')
   value=literal(node['atom'])
   if value in seen:raise ValueError('Duplicate atom proof')
   if record['kind']=='fact':
    if value!=record['atom']:raise ValueError('Original fact differs')
   else:
    binding=node['binding'];refs=node['premise_proofs'];variables={v for p in record['premises'] for v in p[1] if v.startswith('?')}
    if type(binding) is not dict or set(binding)!=variables or any(not name(v) for v in binding.values()) or type(refs) is not list or len(refs)!=len(record['premises']) or any(type(r) is not int or not 0<=r<i for r in refs):raise ValueError('Ground binding/premise topology differs')
    if replace(record['head'],binding)!=value or any(replace(p,binding)!=atoms[r] for p,r in zip(record['premises'],refs)):raise ValueError('Original cross-file grounded rule differs')
    derived+=1
   atoms.append(value);seen.add(value)
 if derived>c['work_used']:raise ValueError('Derived proof count exceeds work metadata')
 for key,target in (('support_proof',query),('refute_proof',(query[0],query[1],not query[2]))):
  ref=c[key]
  if ref is not None and (type(ref) is not int or not 0<=ref<len(atoms) or atoms[ref]!=target):raise ValueError('Witness differs')
  if (ref is not None)!=(target in seen):raise ValueError('Witness coverage differs')
 groundings=None
 if c['complete']:
  expected,groundings=oracle(records,query)
  if expected!=seen:raise ValueError('Combined independent grounding closure differs')
 support=query in seen;refute=(query[0],query[1],not query[2]) in seen;verdict='incomplete' if not c['complete'] else 'inconsistent' if support and refute else 'supported' if support else 'refuted' if refute else 'unknown'
 if c['verdict']!=verdict:raise ValueError('Unsupported within-universe verdict')
 return {'certificate_sha256':digest(canonical(c)),'source_set_complete':True,'source_preflight_verified':True,'formal_derivation_verified':True,'closure_completeness_verified':c['complete'],'verdict':verdict,'independent_groundings':groundings,'application_source_returned_bytes':application,'scientific_entailment_verified':False,'generated_answer':None,'scope':SCOPE,'work_metadata_not_full_CPU_RAM_IO_guarantee':True}
