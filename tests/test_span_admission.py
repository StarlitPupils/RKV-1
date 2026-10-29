import hashlib,sys,tempfile,unittest
from pathlib import Path
from scripts.span_node_lru import SpanNodeLRU
from scripts.span_membership import SpanMembership
from scripts.node_lru import NodeLRU
from scripts.bounded_membership import BoundedMembership
from scripts.late_membership import LateMembership
from scripts.catalog_fixture import sources
from scripts.postings_transform import canonical
from scripts.audit_catalog_commitment import verify
from rkv1.snapshot_scope import tracked_size
from rkv1.store import Store
class SpanTests(unittest.TestCase):
 def graph(self,c):return sys.getsizeof(c)+tracked_size(tuple(getattr(c,k) for k in c.__slots__))-sys.getsizeof(tuple(getattr(c,k) for k in c.__slots__))
 def test_one_algorithm_delta_only_and_full_slots(self):
  original=Path('scripts/node_lru.py').read_text(encoding='utf-8');candidate=Path('scripts/span_node_lru.py').read_text(encoding='utf-8');original=original.split('\n',1)[1].replace('class NodeLRU:','class SpanNodeLRU:');candidate=candidate.split('\n',1)[1].replace('  if key[1]<64:return\n','');self.assertEqual(original,candidate);self.assertEqual(SpanNodeLRU.__slots__,NodeLRU.__slots__)
 def test_admission_boundary_and_exact_hits(self):
  c=SpanNodeLRU('a'*64,129)
  for n in (63,64,65):c.put((0,n),hashlib.sha256(bytes([n])).digest(),sid=c.sid)
  self.assertIsNone(c.get((0,63),sid=c.sid));self.assertEqual(set(c.entries),{(0,64),(0,65)})
  for n in (64,65):self.assertEqual(c.get((0,n),sid=c.sid),hashlib.sha256(bytes([n])).digest())
  self.assertLessEqual(self.graph(c),c.bound_B());self.assertLessEqual(c.bound_B(),65536)
 def test_full_graph_eviction_with_synthetic_ranges_only(self):
  c=SpanNodeLRU('a'*64,129,capacity=2048)
  for j in range(66):
   c.put((j,64),hashlib.sha256(bytes([j])).digest(),sid=c.sid);self.assertLessEqual(c.bound_B(),2048);self.assertLessEqual(self.graph(c),c.bound_B())
  self.assertGreater(c.evictions,0);self.assertIsNone(c.get((0,64),sid=c.sid));self.assertIsNotNone(c.get((65,64),sid=c.sid))
 def test_rejected_entry_still_validates_SID_range_and_value(self):
  c=SpanNodeLRU('a'*64,129)
  for key in ((True,1),(-1,1),(129,1),(0,0)):
   with self.assertRaises(ValueError):c.put(key,b'a'*32,sid=c.sid)
  with self.assertRaises(ValueError):c.put((0,1),b'x',sid=c.sid)
  with self.assertRaises(ValueError):c.put((0,1),b'a'*32,sid='b'*64)
  self.assertFalse(c.entries)
 def test_corruption_conflict_close_and_owner_isolation(self):
  c=SpanNodeLRU('a'*64,129);other=SpanNodeLRU('a'*64,129);c.put((0,64),b'a'*32,sid=c.sid)
  self.assertIsNone(other.get((0,64),sid=other.sid))
  with self.assertRaises(ValueError):c.put((0,64),b'b'*32,sid=c.sid)
  c.entries[(0,64)]=(b'b'*32,b'0'*32)
  with self.assertRaises(ValueError):c.get((0,64),sid=c.sid)
  c.close();self.assertFalse(c.entries)
  with self.assertRaises(ValueError):c.put((0,1),b'a'*32,sid=c.sid)
 def fixture(self,count):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);p=Path(temp.name);src=p/'src';src.mkdir();data=sources(count)
  for name,raw in data.items():(src/name).write_bytes(raw)
  store=Store.create(p/'store');sid=store.add(src)['snapshot_id'];return store,sid,data
 def test_four_roles_same_packets_original_bytes_and_expiry(self):
  for count in (9,17):
   store,sid,data=self.fixture(count)
   with store.read_scope(sid) as scope:
    roles=[LateMembership(scope,sid,'retained'),LateMembership(scope,sid,'ephemeral'),BoundedMembership(scope,sid),SpanMembership(scope,sid)];names=sorted(x for x in data if x.endswith('.logic.jsonl'))
    for j in range(8):
     a=j%count;b=(count-1-j)%count
     if a==b:b=(b+1)%count
     paths=sorted([names[a],names[b]]);packets=[p.issue(paths) for p in roles];self.assertTrue(all(canonical(p)==canonical(packets[0]) for p in packets))
     for member in packets[-1]['members']:
      name=member['entry']['path'];raw=scope.read_range(name);self.assertEqual(raw,data[name]);self.assertTrue(verify(packets[-1]['anchor'],member,raw,expected_anchor_sha256=roles[-1].anchor_sha256,expected_snapshot_id=sid,expected_path=name)['original_selected_bytes_membership_verified'])
    self.assertGreater(roles[-1].retained_state_B(),0);self.assertFalse(roles[-1].cache.entries)
    with self.assertRaises(ValueError):roles[-1].issue(['missing.logic.jsonl'])
    roles[-1].issue([names[0]])
   for p in roles:
    with self.assertRaises(ValueError):p.issue([names[0]])
    p.close()
 def test_cached_metadata_does_not_hide_source_CAS_damage(self):
  store,sid,data=self.fixture(9)
  with store.read_scope(sid) as scope:
   p=SpanMembership(scope,sid);name='one.logic.jsonl';object_path=store.object_path(scope.files[name]['chunks'][0]['id']);raw=object_path.read_bytes();object_path.write_bytes(raw[:-1]+bytes([raw[-1]^1]));p.issue([name])
   with self.assertRaises(ValueError):scope.read_range(name)
   p.close()
if __name__=='__main__':unittest.main()
