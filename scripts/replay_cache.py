"""Experimental faithful v081 C replay; observer costs are new, original timings remain frozen."""
import argparse,atexit,json,time
from pathlib import Path
from rkv1.store import Store
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from scripts.bounded_membership import BoundedMembership
from scripts.node_lru import NodeLRU
from scripts.catalog_fixture import sources
from scripts.postings_transform import canonical,parse
from scripts.audit_catalog_commitment import verify
from scripts.cache_probe import CacheProbe
FIELDS=('hits','misses','hash_nodes','evictions','rewrites','max_retained_bound_B','max_provisional_bound_B')
def trace(cache):return {k:getattr(cache,k) for k in FIELDS}
def replay(store,original,packets,expected,request):
 original_get=NodeLRU.get;rows=[];files=leafs=source_B=0;sid=original['snapshot_id'];names=sorted(p for p in expected if p.endswith('.logic.jsonl'))
 with store.snapshot(sid) as snap:
  assert set(snap.files)==set(expected)
  for p,b in expected.items():assert snap.read_range(p)==b;files+=1;source_B+=len(b)
  leafs=len(names)
 with store.read_scope(sid) as scope:
  prover=BoundedMembership(scope,sid)
  try:
   assert trace(prover.cache)==original['bounded_cache_trace'][0] and prover.anchor_sha256==request['expected_anchor_sha256'];before=trace(prover.cache)
   with CacheProbe() as probe:
    for j,q in enumerate(request['requests']):
     old=packets[j];indices=[m['leaf_index'] for m in old['members']];probe.begin(prover.cache,indices);packet=prover.issue(q['paths']);r=probe.end();assert canonical(packet)==canonical(old) and digest(canonical(packet))==original['queries'][j]['packet_sha256'];returned=0
     for proof in packet['members']:
      p=proof['entry']['path'];raw=scope.read_range(p);assert raw==expected[p];checked=verify(packet['anchor'],proof,raw,expected_anchor_sha256=request['expected_anchor_sha256'],expected_snapshot_id=sid,expected_path=p);assert checked['original_selected_bytes_membership_verified'];returned+=len(raw)
     assert returned==original['queries'][j]['application_returned_B'];source_B+=returned;rows.append({'query_index':j,'packet_sha256':digest(canonical(packet)),'original_source_rechecked_B':returned,**r})
   after=trace(prover.cache);assert after==original['bounded_cache_trace'][-1] and NodeLRU.get is original_get
  finally:prover.close()
 assert NodeLRU.get is original_get
 return {'queries':rows,'original_initial_trace_matched':before,'original_final_trace_matched':after,'full_source_files_rechecked':files,'eligible_metadata_leaves':leafs,'original_packet_count':8,'original_membership_rechecks':16,'application_returned_B':source_B,'observer_restored':True,'new_scientific_questions':0,'new_training_runs':0,'new_model_calls':0,'not_original_performance_measurement':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--original-work',type=Path,required=True);p.add_argument('--original-report',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();start=time.perf_counter();cpu=time.process_time();status={'success':False}
 def done():
  with a.report.with_suffix('.finally.json').open('x',encoding='utf-8') as f:json.dump({**status,'replay_process_wall_s':time.perf_counter()-start,'replay_process_CPU_s':time.process_time()-cpu,'peak_RSS_B':peak_rss()},f,indent=2);f.write('\n')
 atexit.register(done);r=parse(a.original_report.read_bytes());assert r['method']=='bounded';q=parse((a.original_work/'late-requests.json').read_bytes());assert digest(canonical(q['requests']))==r['request_sha256'];packets=[parse((a.original_work/('query-'+str(j)+'.json')).read_bytes()) for j in range(8)];result=replay(Store(a.original_work/'store'),r,packets,sources(r['count']),q);result.update(round=r['round'],count=r['count'],original_report_SHA=digest(a.original_report.read_bytes()),original_request_SHA=r['request_sha256']);status['success']=True
 with a.report.open('xb') as f:f.write(canonical(result)+b'\n')
