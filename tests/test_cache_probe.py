import sys,unittest
from pathlib import Path
from scripts.node_lru import NodeLRU
from scripts.cache_probe import CacheProbe
class ProbeTests(unittest.TestCase):
 def test_hit_miss_conservation_and_lost_initial_entry(self):
  c=NodeLRU('a'*64,17,capacity=4096);c.put((0,1),b'a'*32,sid=c.sid)
  original=NodeLRU.get
  with CacheProbe() as p:
   p.begin(c,[16]);self.assertEqual(c.get((0,1),sid=c.sid),b'a'*32);self.assertIsNone(c.get((1,1),sid=c.sid));r=p.end();self.assertEqual((r['hits'],r['misses']),(1,1));p.begin(c,[16])
   for i in range(1,17):c.put((i,1),bytes([i])*32,sid=c.sid)
   self.assertIsNone(c.get((0,1),sid=c.sid));r=p.end();self.assertEqual(r['initial_entries_lost_before_lookup_unique'],1)
  self.assertIs(NodeLRU.get,original)
 def test_exception_restoration_and_nested_scope_refusal(self):
  original=NodeLRU.get
  with self.assertRaises(RuntimeError):
   with CacheProbe():
    with self.assertRaises(ValueError):
     with CacheProbe():pass
    raise RuntimeError('Owned observer fault')
  self.assertIs(NodeLRU.get,original)
  with CacheProbe():pass
if __name__=='__main__':unittest.main()
