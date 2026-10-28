import sys,copy,tempfile,unittest
from pathlib import Path
from scripts.pinned_metadata import PinnedMetadata
from rkv1.store import Store,Snapshot
from scripts.catalog_fixture import sources,PATHS,queries
from scripts.selected_witness import Witness
from scripts.audit_selected_witness import audit
from scripts.catalog_observer import observe_snapshots
from scripts.logic_fixture import literal,encode,fact
class PinnedTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.src=self.root/'source';self.src.mkdir()
  for p,b in sources(9).items():(self.src/p).write_bytes(b)
  self.store=Store.create(self.root/'store',compression='zlib');self.sid=self.store.add(self.src)['snapshot_id']
 def test_same_certificate_original_DAG_and_source_traffic_with_one_constructor(self):
  baseline=[Witness(self.store,self.sid,PATHS).infer(q,work_budget=100000) for q,_,_ in queries()]
  with observe_snapshots() as meter:
   with PinnedMetadata(self.store,self.sid) as scoped:
    for before,(q,_,_) in zip(baseline,queries()):
     after=Witness(scoped,self.sid,PATHS).infer(q,work_budget=100000);self.assertEqual(before,after);self.assertTrue(audit(scoped,self.sid,after)['original_selected_DAG_verified'])
   self.assertEqual(meter['constructor_calls'],1);self.assertTrue(all(x['path'] in PATHS for x in meter['source_read_calls']))
 def test_metadata_readonly_nested_and_views_expire(self):
  scope=PinnedMetadata(self.store,self.sid)
  with scope as scoped:
   with scoped.snapshot(self.sid) as view:
    with self.assertRaises(TypeError):view.files['new']=1
    with self.assertRaises(TypeError):view.files['one.logic.jsonl']['size']=0
    with self.assertRaises(TypeError):view.files['one.logic.jsonl']['chunks'][0]['size']=0
    self.assertGreater(scoped.tracked_metadata_bytes,0)
  with self.assertRaises(ValueError):view.read_range('one.logic.jsonl')
  with self.assertRaises(ValueError):_ = view.files
  with self.assertRaises(ValueError):scope.__enter__()
 def test_new_HEAD_never_changes_old_pinned_scope_and_wrongSID_refused(self):
  before=Witness(self.store,self.sid,PATHS).infer(literal('reach','a','c'),work_budget=100000)
  with PinnedMetadata(self.store,self.sid) as scoped:
   (self.src/'one.logic.jsonl').write_bytes(encode([fact('new','edge','c','b')]))
   new=self.store.add(self.src)['snapshot_id'];self.assertNotEqual(new,self.sid)
   self.assertEqual(before,Witness(scoped,self.sid,PATHS).infer(literal('reach','a','c'),work_budget=100000))
   with self.assertRaises(ValueError):
    with scoped.snapshot(new):pass
 def test_initial_manifest_corruption_rejected_and_new_scope_revalidates(self):
  path=self.store.root/'snapshots'/(self.sid+'.rkvs');raw=path.read_bytes()
  with PinnedMetadata(self.store,self.sid) as scoped:
   path.write_bytes(raw[:-1]+bytes([raw[-1]^1]));c=Witness(scoped,self.sid,PATHS).infer(literal('reach','a','c'),work_budget=100000);self.assertTrue(audit(scoped,self.sid,c)['original_selected_DAG_verified'])
  with self.assertRaises(ValueError):
   with PinnedMetadata(self.store,self.sid):pass
 def test_original_CAS_block_validation_still_rejects_actual_damage(self):
  with PinnedMetadata(self.store,self.sid) as scoped:
   with scoped.snapshot(self.sid) as view:identifier=view.files['one.logic.jsonl']['chunks'][0]['id']
   path=self.store.object_path(identifier);raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
   with self.assertRaises(ValueError):
    with scoped.snapshot(self.sid) as view:view.read_range('one.logic.jsonl')
 def test_budget_and_exception_cleanup_keep_methods_unchanged(self):
  original=(Snapshot.__init__,Snapshot.read_range)
  with self.assertRaises(ValueError):
   with PinnedMetadata(self.store,self.sid,metadata_budget=0):pass
  scope=PinnedMetadata(self.store,self.sid)
  with self.assertRaises(RuntimeError):
   with scope:raise RuntimeError('owned exception')
  with self.assertRaises(ValueError):
   with scope.snapshot(self.sid):pass
  self.assertEqual((Snapshot.__init__,Snapshot.read_range),original)
 def test_four_role_worker_proofs_match_and_OFF_counts_null(self):
  from scripts.run_pinned_metadata import run
  reports=[run(self.root/(method+meter),9,1,method,meter) for method,meter in (('fresh','off'),('pinned','off'),('fresh','on'),('pinned','on'))]
  self.assertTrue(all([q['certificate_sha256'] for q in r['queries']]==[q['certificate_sha256'] for q in reports[0]['queries']] for r in reports))
  self.assertIsNone(reports[0]['observer']);self.assertIsNone(reports[1]['observer']);self.assertTrue(all(q['observed_source_calls'] is None for r in reports[:2] for q in r['queries']));self.assertGreater(reports[2]['observer']['constructor_calls'],1);self.assertEqual(reports[3]['observer']['constructor_calls'],1);self.assertGreater(reports[1]['tracked_pinned_metadata_B'],0)
if __name__=='__main__':unittest.main()
