"""Independent coverage proof check, no axiom grammar/closure/scientific proof."""
import re
from rkv1.core import digest
from scripts.evidence_retrieval import encoded
def audit_scope(store,snapshot_id,proof):
 required={'format','snapshot_id','eligible_suffix','eligible_paths','caller_paths','source_byte_budget','eligible_payload_bytes','source_set_complete','status','reason','source_records','source_application_returned_bytes','source_grammar_verified','logical_closure_verified','scientific_entailment_verified','generated_answer','scope'}
 if type(proof) is not dict or set(proof)!=required or proof.get('scope')!='Only explicitly eligible machine-source paths; not natural-language or all scientific knowledge':raise ValueError('Strict byte-coverage scope schema required')
 if any(type(proof.get(k)) is not int for k in ('eligible_payload_bytes','source_application_returned_bytes')):raise ValueError('Integer source payload metadata required')
 if type(proof) is not dict or proof.get('format')!='RKVSCOPE1' or proof.get('snapshot_id')!=snapshot_id or proof.get('eligible_suffix')!='.logic.jsonl' or proof.get('source_set_complete') is not True or proof.get('status')!='complete_source_set' or proof.get('reason') is not None:raise ValueError('Complete pinned source-set coverage proof required')
 if any(proof.get(k) is not False for k in ('source_grammar_verified','logical_closure_verified','scientific_entailment_verified')) or proof.get('generated_answer') is not None:raise ValueError('Coverage cannot certify grammar/logic/science')
 budget=proof.get('source_byte_budget')
 if type(budget) is not int or not 0<=budget<=1048576:raise ValueError('Payload cap')
 with store.snapshot(snapshot_id) as snap:
  eligible=sorted(p for p in snap.files if p.endswith('.logic.jsonl'));pattern=re.compile(r'[a-z][a-z0-9_-]*(?:/[a-z][a-z0-9_-]*)*\.logic\.jsonl\Z')
  if not 1<=len(eligible)<=8 or any(not pattern.fullmatch(p) for p in eligible) or proof.get('eligible_paths')!=eligible or proof.get('caller_paths')!=eligible:raise ValueError('Full pinned eligible source universe differs')
  total=sum(snap.files[p]['size'] for p in eligible)
  if total>budget or total!=proof.get('eligible_payload_bytes') or proof.get('source_application_returned_bytes')!=total:raise ValueError('Payload coverage metadata differs')
  records=[];application=0
  for path in eligible:
   raw=snap.read_range(path);application+=len(raw);records.append({'path':path,'bytes':len(raw),'sha256':digest(raw)})
  if records!=proof.get('source_records') or application!=total:raise ValueError('Original full source SHA/size differs')
 return {'source_set_coverage_verified':True,'scope_proof_sha256':digest(encoded(proof)),'auditor_application_returned_bytes':application,'source_grammar_verified':False,'logical_closure_verified':False,'scientific_entailment_verified':False,'generated_answer':None,'scope':'Pinned eligible file byte coverage only'}
