"""Private independent source/root/file/packet audit. No timing-benefit scoring on owned preflight."""
import hashlib,json
from pathlib import Path
from scripts.catalog_fixture import sources
from scripts.postings_transform import canonical
from scripts.audit_catalog_commitment import verify
from rkv1.store import Store
from rkv1.core import digest

def audit_case(work,r,parent):
 assert parent['exit_code']==0 and parent['error'] is None and parent['formal_retries']==0 and parent['ready_observed']
 assert len(r['queries'])==8 and set(r['negative_controls'])=={'wrong_anchor','wrong_original','missing_path','closed_owner'} and r['closed_prover_fields_released'] and r['constructor_completed_before_requests_generated']
 footer=json.loads((work/'finally-timing.json').read_bytes());assert footer['success'] and footer['worker_full_wall_s']>=r['algorithm_phase_wall_s']>=0 and footer['worker_full_CPU_s']>=0
 files={p.relative_to(work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in work.rglob('*') if p.is_file() and p.name!='finally-timing.json'};assert files==r['all_worker_files_before_finally'] and sum(x['bytes'] for x in files.values())==r['retained_B_before_finally']
 expected=sources(r['count']);store=Store(work/'store');records=[];file_count=members=returned=0
 with store.snapshot(r['snapshot_id']) as snap:
  assert set(snap.files)==set(expected)
  for name,raw in expected.items():assert snap.read_range(name)==raw;file_count+=1
  for name in sorted(snap.files):
   if name.endswith('.logic.jsonl'):records.append({'path':name,'bytes':snap.files[name]['size'],'sha256':snap.files[name]['sha256']})
 def tree(lo,n):
  if n==1:return hashlib.sha256(bytes([0])+canonical(records[lo])).digest()
  split=1
  while split*2<n:split*=2
  return hashlib.sha256(bytes([1])+tree(lo,split)+tree(lo+split,n-split)).digest()
 anchor={'format':'RKVCATALOGANCHOR1','snapshot_id':r['snapshot_id'],'eligible_count':len(records),'eligible_payload_B':sum(e['bytes'] for e in records),'root_sha256':tree(0,len(records)).hex()};request=json.loads((work/'late-requests.json').read_bytes());assert request['expected_anchor_sha256']==digest(canonical(anchor)) and r['request_sha256']==request['request_sha256']==digest(canonical(request['requests']))
 for j,q in enumerate(r['queries']):
  packet=json.loads((work/('query-'+str(j)+'.json')).read_bytes());assert packet['anchor']==anchor and q['query_index']==j and q['paths']==request['requests'][j]['paths'] and digest(canonical(packet))==q['packet_sha256'] and len(canonical(packet))==q['packet_B'];size=0
  for proof in packet['members']:
   name=proof['entry']['path'];raw=expected[name];assert verify(anchor,proof,raw,expected_anchor_sha256=request['expected_anchor_sha256'],expected_snapshot_id=r['snapshot_id'],expected_path=name)['original_selected_bytes_membership_verified'];size+=len(raw);members+=1
  assert size==q['application_returned_B'];returned+=size
 assert members==16 and returned==r['query_application_returned_B']
 if r['method'] in ('bounded','span'):assert len(r['bounded_cache_trace'])==2 and all(t['max_retained_bound_B']<=65536 for t in r['bounded_cache_trace']) and r['bounded_cache_capacity_B']==65536
 else:assert r['bounded_cache_trace'] is None and r['bounded_cache_capacity_B'] is None
 return {'fresh_roots':1,'eligible_leaves':len(records),'files':file_count,'members':members,'packets':8,'no_owned_preflight_speed_scoring':True}
