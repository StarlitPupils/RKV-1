import sys,tempfile,unittest
from pathlib import Path
from scripts.bounded_membership import BoundedMembership
from scripts.late_membership import LateMembership
from scripts.catalog_fixture import sources
from scripts.postings_transform import canonical
from scripts.audit_catalog_commitment import verify
class CachedTests(unittest.TestCase):
 def test_initial_and_all_eight_late_requests_exact_with_original_bytes(self):
  from rkv1.store import Store
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);src=d/'source';src.mkdir();data=sources(9)
   for n,b in data.items():(src/n).write_bytes(b)
   store=Store.create(d/'store');sid=store.add(src)['snapshot_id']
   with store.read_scope(sid) as scope:
    a=LateMembership(scope,sid,'retained');c=BoundedMembership(scope,sid);self.assertEqual(a.anchor,c.anchor);names=sorted(p for p in scope.files if p.endswith('.logic.jsonl'))
    for j in range(8):
     x=j%9;y=(8-j)%9
     if x==y:y=(y+1)%9
     paths=sorted([names[x],names[y]]);packet=c.issue(paths);self.assertEqual(canonical(packet),canonical(a.issue(paths)));self.assertLessEqual(c.cache.bound_B(),65536)
     for proof in packet['members']:
      path=proof['entry']['path'];raw=scope.read_range(path);self.assertEqual(raw,data[path]);self.assertTrue(verify(a.anchor,proof,raw,expected_anchor_sha256=a.anchor_sha256,expected_snapshot_id=sid,expected_path=path)['original_selected_bytes_membership_verified'])
    self.assertGreater(c.cache.hits,0);self.assertGreater(c.retained_state_B(),0)
   with self.assertRaises(ValueError):c.issue(['one.logic.jsonl'])
   c.close();self.assertEqual(len(c.cache.entries),0)
 def test_source_payload_corruption_remains_rejected(self):
  from rkv1.store import Store
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);src=d/'source';src.mkdir();(src/'one.logic.jsonl').write_bytes(b'owned');store=Store.create(d/'store');sid=store.add(src)['snapshot_id']
   with store.read_scope(sid) as scope:
    c=BoundedMembership(scope,sid);path=store.object_path(scope.files['one.logic.jsonl']['chunks'][0]['id']);raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]));c.issue(['one.logic.jsonl'])
    with self.assertRaises(ValueError):scope.read_range('one.logic.jsonl')
    c.close()
 def test_small_budget_evictions_keep_exact_root_and_cached_corruption_refuses(self):
  from rkv1.store import Store
  from scripts.node_lru import NodeLRU
  from scripts.cached_membership import anchor_only,requested_members
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);src=d/'source';src.mkdir()
   for n,b in sources(9).items():(src/n).write_bytes(b)
   store=Store.create(d/'store');sid=store.add(src)['snapshot_id']
   with store.read_scope(sid) as scope:
    a=LateMembership(scope,sid,'retained');cache=NodeLRU(sid,9,capacity=4096);self.assertEqual(anchor_only(scope,sid,cache),a.anchor);names=sorted(p for p in scope.files if p.endswith('.logic.jsonl'))
    for p in (names[0],names[-1],names[3],names[0]):
     self.assertEqual(canonical(requested_members(scope,sid,[p],cache)),canonical(a.issue([p])));self.assertLessEqual(cache.bound_B(),4096)
    self.assertGreater(cache.evictions,0)
    c=BoundedMembership(scope,sid);record=c.cache.entries[(8,1)];c.cache.entries[(8,1)]=(b'x'*32,record[1])
    with self.assertRaises(ValueError):c.issue([names[0]])
    c.close();cache.close()
if __name__=='__main__':unittest.main()
