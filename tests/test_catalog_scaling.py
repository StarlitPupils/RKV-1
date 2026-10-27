import sys,tempfile,unittest
from pathlib import Path
from rkv1.store import Store,Snapshot
from scripts.selected_witness import Witness
from scripts.audit_selected_witness import audit
from scripts.catalog_fixture import sources,queries,PATHS,COUNTS,ORDERS
from scripts.catalog_observer import observe_snapshots
class CatalogTests(unittest.TestCase):
 def test_fixture_grows_only_unselected_sources_and_keeps_opposite(self):
  a=sources(9);b=sources(64);self.assertEqual({p:a[p] for p in PATHS},{p:b[p] for p in PATHS});self.assertEqual(a['late.logic.jsonl'],b['late.logic.jsonl']);self.assertEqual(sum(p.endswith('.logic.jsonl') for p in b),64);self.assertNotIn('late.logic.jsonl',PATHS);self.assertEqual(len(queries()),8)
 def test_no_invalid_count_or_duplicate_order(self):
  for n in (True,8,4097,9.0):
   with self.assertRaises(ValueError):sources(n)
  self.assertEqual(len(ORDERS),3)
  for order in ORDERS:self.assertEqual(sorted(order),list(COUNTS))
 def test_observer_preserves_real_store_source_and_count_conservation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);src=root/'source';src.mkdir();data=sources(9)
   for p,b in data.items():(src/p).write_bytes(b)
   store=Store.create(root/'store',compression='zlib');sid=store.add(src)['snapshot_id'];size=sum(len(data[p]) for p in PATHS);original=(Snapshot.__init__,Snapshot.read_range)
   with observe_snapshots() as meter:
    c=Witness(store,sid,PATHS,source_byte_budget=size).infer(queries()[0][0],work_budget=100000);cut=len(meter['source_read_calls']);checked=audit(store,sid,c)
   self.assertEqual((Snapshot.__init__,Snapshot.read_range),original);self.assertTrue(c['support_evidence_found']);self.assertFalse(c['opposite_evidence_found']);self.assertEqual(sum(x['returned_bytes'] for x in meter['source_read_calls'][:cut]),size);self.assertEqual(sum(x['returned_bytes'] for x in meter['source_read_calls'][cut:]),checked['auditor_selected_source_application_returned_bytes']);self.assertGreater(meter['constructor_calls'],0);self.assertEqual(meter['failed_constructor_calls'],0);self.assertTrue(all(x['path'] in PATHS for x in meter['source_read_calls']))
 def test_exception_cleanup_and_original_validation_not_bypassed(self):
  original=(Snapshot.__init__,Snapshot.read_range)
  with tempfile.TemporaryDirectory() as tmp:
   store=Store.create(Path(tmp)/'store',compression='zlib')
   with observe_snapshots() as meter:
    with self.assertRaises(ValueError):store.snapshot('invalid-sid')
   self.assertEqual(meter['constructor_calls'],1);self.assertEqual(meter['failed_constructor_calls'],1);self.assertEqual(meter['source_read_calls'],[]);self.assertEqual((Snapshot.__init__,Snapshot.read_range),original)
if __name__=='__main__':unittest.main()
