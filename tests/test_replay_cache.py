import sys,tempfile,unittest
from pathlib import Path
from scripts.replay_cache import replay,trace
from scripts.bounded_membership import BoundedMembership
from scripts.catalog_fixture import sources
from scripts.postings_transform import canonical
from rkv1.store import Store
class ReplayTests(unittest.TestCase):
 def test_owned_case_packet_and_all_cache_counters_exact(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);src=d/'src';src.mkdir();data=sources(9)
   for p,b in data.items():(src/p).write_bytes(b)
   store=Store.create(d/'store');sid=store.add(src)['snapshot_id'];names=sorted(p for p in data if p.endswith('.logic.jsonl'));packets=[];rows=[];requests=[]
   with store.read_scope(sid) as scope:
    c=BoundedMembership(scope,sid);initial=trace(c.cache)
    for j in range(8):
     x=j%9;y=(8-j)%9
     if x==y:y=(y+1)%9
     paths=sorted([names[x],names[y]]);q=c.issue(paths);packets.append(q);requests.append({'query_index':j,'paths':paths})
     from rkv1.core import digest
     rows.append({'packet_sha256':digest(canonical(q)),'application_returned_B':sum(len(data[p]) for p in paths)})
    original={'snapshot_id':sid,'bounded_cache_trace':[initial,trace(c.cache)],'queries':rows};request={'requests':requests,'expected_anchor_sha256':c.anchor_sha256};c.close()
   result=replay(store,original,packets,data,request);self.assertTrue(result['observer_restored']);self.assertEqual(result['full_source_files_rechecked'],10);self.assertEqual(len(result['queries']),8)
if __name__=='__main__':unittest.main()
