import sys,tempfile,unittest,copy
from pathlib import Path
from rkv1.snapshot_scope import SnapshotReadScope
from rkv1.store import Store
from scripts.pinned_metadata import PinnedMetadata
from scripts.catalog_fixture import sources,PATHS,queries
from scripts.selected_witness import Witness
from scripts.audit_selected_witness import audit
class SDKScopeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.src=self.root/'source';self.src.mkdir();self.data=sources(9)
  for p,b in self.data.items():(self.src/p).write_bytes(b)
  self.store=Store.create(self.root/'store',compression='zlib');self.sid=self.store.add(self.src)['snapshot_id']
 def test_generic_file_ranges_and_full_verify_match_original_snapshot(self):
  with self.store.snapshot(self.sid) as original,SnapshotReadScope(self.store,self.sid) as scope:
   self.assertEqual(scope.snapshot_id,self.sid);self.assertFalse(scope.closed)
   for p,raw in self.data.items():self.assertEqual(scope.read_range(p),raw);self.assertEqual(scope.read_range(p,1,min(10,len(raw)-1)),original.read_range(p,1,min(10,len(raw)-1)))
   self.assertEqual(scope.verify(),original.process())
   with scope.snapshot(self.sid) as view:self.assertEqual(view.verify(),original.process());self.assertEqual(view.snapshot_id,self.sid)
  self.assertTrue(scope.closed)
  for operation in (lambda:scope.read_range(PATHS[0]),lambda:scope.verify(),lambda:view.verify(),lambda:scope.files):
   with self.assertRaises(ValueError):operation()
 def test_all_oldexperimental_certificates_remain_exact(self):
  with PinnedMetadata(self.store,self.sid) as ref,SnapshotReadScope(self.store,self.sid) as scope:
   for q,_,_ in queries():
    a=Witness(ref,self.sid,PATHS).infer(q,work_budget=100000);b=Witness(scope,self.sid,PATHS).infer(q,work_budget=100000);self.assertEqual(a,b);self.assertTrue(audit(scope,self.sid,b)['original_selected_DAG_verified'])
 def test_nested_metadata_and_cap_exception_scope_cleanup(self):
  scope=SnapshotReadScope(self.store,self.sid)
  with self.assertRaises(RuntimeError):
   with scope:
    with self.assertRaises(TypeError):scope.files[PATHS[0]]['size']=0
    raise RuntimeError('owned')
  self.assertTrue(scope.closed)
  with self.assertRaises(ValueError):
   with SnapshotReadScope(self.store,self.sid,metadata_budget=0):pass
 def test_newHEAD_wrongSID_and_newscope_manifest_revalidation(self):
  with SnapshotReadScope(self.store,self.sid) as scope:
   (self.src/'notes.txt').write_bytes(b'Owned changed notes')
   newer=self.store.add(self.src)['snapshot_id'];self.assertNotEqual(newer,self.sid);self.assertEqual(scope.read_range('notes.txt'),self.data['notes.txt'])
   with self.assertRaises(ValueError):
    with scope.snapshot(newer):pass
   path=self.store.root/'snapshots'/(self.sid+'.rkvs');raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]));self.assertEqual(scope.read_range(PATHS[0]),self.data[PATHS[0]])
  with self.assertRaises(ValueError):
   with SnapshotReadScope(self.store,self.sid):pass
 def test_active_source_CAS_damage_still_fails_original_validator(self):
  with SnapshotReadScope(self.store,self.sid) as scope:
   identifier=scope.files[PATHS[0]]['chunks'][0]['id'];path=self.store.object_path(identifier);raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
   with self.assertRaises(ValueError):scope.read_range(PATHS[0])
 def test_explicit_store_API_and_default_snapshot_behavior(self):
  from rkv1.store import Snapshot
  fresh=self.store.snapshot(self.sid);self.assertIsInstance(fresh,Snapshot);self.assertIs(type(fresh.files),dict);self.assertEqual(fresh.read_range(PATHS[0]),self.data[PATHS[0]])
  with self.store.read_scope(self.sid) as scope:self.assertIsInstance(scope,SnapshotReadScope);self.assertEqual(scope.read_range(PATHS[0]),fresh.read_range(PATHS[0]))
if __name__=='__main__':unittest.main()
