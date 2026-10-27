"""Experimental: bounded complete eligible-source coverage, no logical/NL verdict."""
import re
from rkv1.core import digest
SUFFIX='.logic.jsonl';MAX_BYTES=1<<20;MAX_FILES=8
VALID=re.compile(r'[a-z][a-z0-9_-]*(?:/[a-z][a-z0-9_-]*)*\.logic\.jsonl\Z')
def load_universe(store,snapshot_id,paths,*,source_byte_budget=MAX_BYTES):
 if type(snapshot_id) is not str or not snapshot_id or type(paths) is not list or any(type(p) is not str or not VALID.fullmatch(p) for p in paths) or len(set(paths))!=len(paths):raise ValueError('Explicit pinned snapshot and unique eligible paths required')
 if type(source_byte_budget) is not int or not 0<=source_byte_budget<=MAX_BYTES:raise ValueError('Bounded source payload budget required')
 paths=sorted(paths)
 with store.snapshot(snapshot_id) as snap:
  eligible=sorted(p for p in snap.files if p.endswith(SUFFIX))
  if any(not VALID.fullmatch(p) for p in eligible):raise ValueError('Malformed eligible source path cannot be ignored')
  total=sum(snap.files[p]['size'] for p in eligible);reason='no_eligible_source_universe' if not eligible else 'eligible_file_count_cap' if len(eligible)>MAX_FILES else 'caller_set_differs_from_snapshot_eligible_set' if paths!=eligible else 'source_payload_budget_insufficient' if total>source_byte_budget else None
  scope={'format':'RKVSCOPE1','snapshot_id':snapshot_id,'eligible_suffix':SUFFIX,'eligible_paths':eligible,'caller_paths':paths,'source_byte_budget':source_byte_budget,'eligible_payload_bytes':total,'source_set_complete':reason is None,'status':'complete_source_set' if reason is None else 'incomplete_source_set','reason':reason,'source_records':[],'source_application_returned_bytes':0,'source_grammar_verified':False,'logical_closure_verified':False,'scientific_entailment_verified':False,'generated_answer':None,'scope':'Only explicitly eligible machine-source paths; not natural-language or all scientific knowledge'}
  if reason:return scope,{}
  sources={}
  for path in eligible:
   raw=snap.read_range(path)
   if len(raw)!=snap.files[path]['size']:raise ValueError('Original source byte length differs')
   sources[path]=raw;scope['source_records'].append({'path':path,'bytes':len(raw),'sha256':digest(raw)});scope['source_application_returned_bytes']+=len(raw)
  if scope['source_application_returned_bytes']>source_byte_budget:raise ValueError('Source payload cap violated')
  return scope,sources
