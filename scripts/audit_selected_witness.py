"""Actual-universe preflight and independent original-source DAG checks for a selection."""
import copy
from rkv1.core import digest
from scripts.source_universe import VALID
from scripts.audit_source_set_logic import verify_set_certificate
from scripts.selected_witness import Projection,SCOPE,FIELDS

def audit(store,sid,c):
 """Original metadata preflight + existing independent original-file DAG/closure checker."""
 if type(c) is not dict or set(c)!=FIELDS or c['format']!='RKVSELECTWITNESS1' or c['snapshot_id']!=sid or c['global_verdict'] is not None or c['scientific_entailment_verified'] is not False or c['generated_answer'] is not None or c['scope']!=SCOPE or type(c['selected_closure_complete']) is not bool:raise ValueError('Partial witness cannot claim global verdict')
 selection=c['selection']
 if type(selection) is not dict or set(selection)!={'snapshot_id','eligible_paths','eligible_payload_bytes','selected_paths','selected_payload_bytes','source_byte_budget','full_eligible_selection'}:raise ValueError('Strict selection catalog required')
 # Independently enumerate ACTUAL snapshot, not a projected store.
 if type(selection['source_byte_budget']) is not int or not 0<=selection['source_byte_budget']<=1048576 or type(selection['selected_paths']) is not list or not 1<=len(selection['selected_paths'])<=8 or any(type(p) is not str or not VALID.fullmatch(p) for p in selection['selected_paths']) or sorted(set(selection['selected_paths']))!=selection['selected_paths']:raise ValueError('Invalid selected source bound')
 with store.snapshot(sid) as snap:
  universe=sorted(p for p in snap.files if p.endswith('.logic.jsonl'));paths=selection['selected_paths']
  if any(not VALID.fullmatch(p) for p in universe) or any(p not in universe for p in paths):raise ValueError('Actual eligible metadata differs')
  total=sum(snap.files[p]['size'] for p in universe);size=sum(snap.files[p]['size'] for p in paths)
  if selection['snapshot_id']!=sid or selection['eligible_paths']!=universe or type(selection['eligible_payload_bytes']) is not int or selection['eligible_payload_bytes']!=total or type(selection['selected_payload_bytes']) is not int or selection['selected_payload_bytes']!=size or size>selection['source_byte_budget'] or selection['full_eligible_selection'] is not (paths==universe):raise ValueError('Actual full universe cannot be replaced by selection')
  records=[]
  for path in paths:
   raw=snap.read_range(path)
   if len(raw)!=snap.files[path]['size']:raise ValueError('Actual source size differs')
   records.append({'path':path,'bytes':len(raw),'sha256':digest(raw)})
 for key,ref in (('support_evidence_found','support_proof'),('opposite_evidence_found','refute_proof')):
  if c[key] is not (c[ref] is not None):raise ValueError('Witness flag differs')
 # Construct a selected-domain certificate solely for independent checker reuse.
 # No inner complete-universe flag is exposed by the new format.
 inner={k:copy.deepcopy(c[k]) for k in ('snapshot_id','query','work_used','work_budget','nodes','support_proof','refute_proof')}
 ready=c['selected_closure_complete'];support=c['support_evidence_found'];opposite=c['opposite_evidence_found']
 inner.update(format='RKVSETLOGIC1',complete=ready,verdict='incomplete' if not ready else 'inconsistent' if support and opposite else 'supported' if support else 'refuted' if opposite else 'unknown',source_grammar_verified=True,scientific_entailment_verified=False,generated_answer=None,scope='Explicit signed binary Horn consequences inside the pinned eligible source universe only')
 inner['source_scope']={'format':'RKVSCOPE1','snapshot_id':sid,'eligible_suffix':'.logic.jsonl','eligible_paths':paths,'caller_paths':paths,'source_byte_budget':selection['source_byte_budget'],'eligible_payload_bytes':size,'source_set_complete':True,'status':'complete_source_set','reason':None,'source_records':records,'source_application_returned_bytes':size,'source_grammar_verified':False,'logical_closure_verified':False,'scientific_entailment_verified':False,'generated_answer':None,'scope':'Only explicitly eligible machine-source paths; not natural-language or all scientific knowledge'}
 checked=verify_set_certificate(Projection(store,paths),sid,inner)
 return {'actual_full_catalog_verified':True,'original_selected_DAG_verified':checked['formal_derivation_verified'],'selected_closure_verified':checked['closure_completeness_verified'],'global_verdict':None,'scientific_entailment_verified':False,'auditor_selected_source_application_returned_bytes':size+checked['application_source_returned_bytes'],'not_physical_or_all_system_IO':True}
