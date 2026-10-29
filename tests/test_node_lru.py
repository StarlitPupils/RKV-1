import hashlib,sys,unittest
from pathlib import Path
from scripts.node_lru import NodeLRU
from rkv1.snapshot_scope import tracked_size
class NodeTests(unittest.TestCase):
 def test_hit_miss_and_exact_fullgraph_upper_bound(self):
  c=NodeLRU('a'*64,17);self.assertIsNone(c.get((0,1),sid=c.sid));c.put((0,1),b'a'*32,sid=c.sid);self.assertEqual(c.get((0,1),sid=c.sid),b'a'*32);self.assertLessEqual(sys.getsizeof(c)+tracked_size(tuple(getattr(c,k) for k in c.__slots__))-sys.getsizeof(tuple(getattr(c,k) for k in c.__slots__)),c.bound_B());self.assertLessEqual(c.bound_B(),c.capacity)
 def test_eviction_in_small_owned_tree_without_scale_pretest(self):
  c=NodeLRU('a'*64,17,capacity=4096)
  for j in range(17):c.put((j,1),hashlib.sha256(bytes([j])).digest(),sid=c.sid);self.assertLessEqual(c.bound_B(),4096);self.assertLessEqual(sys.getsizeof(c)+tracked_size(tuple(getattr(c,k) for k in c.__slots__))-sys.getsizeof(tuple(getattr(c,k) for k in c.__slots__)),c.bound_B())
  self.assertGreater(c.evictions,0);self.assertIsNone(c.get((0,1),sid=c.sid));self.assertIsNotNone(c.get((16,1),sid=c.sid))
 def test_bad_key_SID_size_and_metadata_corruption_refused(self):
  c=NodeLRU('a'*64,9)
  for key in ((True,1),(-1,1),(8,2),(0,0)):
   with self.assertRaises(ValueError):c.get(key,sid=c.sid)
  with self.assertRaises(ValueError):c.put((0,1),b'x',sid=c.sid)
  with self.assertRaises(ValueError):c.get((0,1),sid='b'*64)
  c.put((0,1),b'a'*32,sid=c.sid);c.entries[(0,1)]=(b'b'*32,b'0'*32)
  with self.assertRaises(ValueError):c.get((0,1),sid=c.sid)
 def test_closed_refuses_and_conflicting_same_key_refuses(self):
  c=NodeLRU('a'*64,9);c.put((0,1),b'a'*32,sid=c.sid)
  with self.assertRaises(ValueError):c.put((0,1),b'b'*32,sid=c.sid)
  c.close();self.assertEqual(len(c.entries),0)
  with self.assertRaises(ValueError):c.get((0,1),sid=c.sid)
  for cap in (True,0,1024,65537):
   with self.assertRaises(ValueError):NodeLRU('a'*64,9,capacity=cap)
if __name__=='__main__':unittest.main()
