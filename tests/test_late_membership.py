import sys,tempfile,unittest
from pathlib import Path
from rkv1.store import Store
from scripts.catalog_fixture import sources
from scripts.audit_catalog_commitment import verify
from scripts.postings_transform import canonical
from scripts.late_membership import LateMembership
from scripts.ephemeral_membership import anchor_only,requested_members
class LateTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);src=self.root/'src';src.mkdir();self.data=sources(9)
  for p,b in self.data.items():(src/p).write_bytes(b)
  self.store=Store.create(self.root/'store');self.sid=self.store.add(src)['snapshot_id']
 def test_initial_anchor_has_no_selection_and_does_not_read_source_CAS(self):
  original=self.store.block
  def fail(*a,**kw):raise AssertionError('Source CAS read before late request')
  self.store.block=fail
  with self.store.read_scope(self.sid) as scope:
   a=LateMembership(scope,self.sid,'retained');b=LateMembership(scope,self.sid,'ephemeral');self.assertEqual(a.anchor,b.anchor);self.assertEqual(anchor_only(scope,self.sid),a.anchor)
  self.store.block=original
 def test_eight_late_pairs_exact_and_independent_original_bytes(self):
  with self.store.read_scope(self.sid) as scope:
   a=LateMembership(scope,self.sid,'retained');b=LateMembership(scope,self.sid,'ephemeral');names=sorted(p for p in scope.files if p.endswith('.logic.jsonl'))
   for j in range(8):
    x=j%len(names);y=(len(names)-1-j)%len(names)
    if y==x:y=(y+1)%len(names)
    paths=sorted([names[x],names[y]]);pa=a.issue(paths);pb=b.issue(paths);self.assertEqual(canonical(pa),canonical(pb))
    for proof in pb['members']:
     p=proof['entry']['path'];raw=scope.read_range(p);self.assertEqual(raw,self.data[p]);self.assertTrue(verify(a.anchor,proof,raw,expected_anchor_sha256=a.anchor_sha256,expected_snapshot_id=self.sid,expected_path=p)['original_selected_bytes_membership_verified'])
   self.assertGreater(a.retained_state_B(),0);self.assertGreater(b.retained_state_B(),0)
 def test_same_lifetime_after_owner_close_and_explicit_close(self):
  with self.store.read_scope(self.sid) as scope:
   a=LateMembership(scope,self.sid,'retained');b=LateMembership(scope,self.sid,'ephemeral');a.close()
   with self.assertRaises(ValueError):a.issue(['one.logic.jsonl'])
   b.close()
   with self.assertRaises(ValueError):b.issue(['one.logic.jsonl'])
  with self.store.read_scope(self.sid) as scope:a=LateMembership(scope,self.sid,'retained');b=LateMembership(scope,self.sid,'ephemeral')
  for p in (a,b):
   with self.assertRaises(ValueError):p.issue(['one.logic.jsonl'])
 def test_wrongSID_invalid_missing_path_and_no_empty_issue(self):
  with self.store.read_scope(self.sid) as scope:
   for method in ('retained','ephemeral'):
    with self.assertRaises(ValueError):LateMembership(scope,'0'*64,method)
    prover=LateMembership(scope,self.sid,method)
    for paths in ([],['one.logic.jsonl']*2,['missing.logic.jsonl']):
     with self.assertRaises(ValueError):prover.issue(paths)
 def test_CAS_damage_not_hidden_by_membership_metadata(self):
  with self.store.read_scope(self.sid) as scope:
   a=LateMembership(scope,self.sid,'retained');b=LateMembership(scope,self.sid,'ephemeral');p='one.logic.jsonl';key=scope.files[p]['chunks'][0]['id'];object_path=self.store.object_path(key);raw=object_path.read_bytes();object_path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
   self.assertEqual(canonical(a.issue([p])),canonical(b.issue([p])))
   with self.assertRaises(ValueError):scope.read_range(p)
 def test_exception_during_late_request_does_not_leave_persistent_cache(self):
  with self.store.read_scope(self.sid) as scope:
   b=LateMembership(scope,self.sid,'ephemeral');before=b.retained_state_B()
   with self.assertRaises(ValueError):b.issue(['missing.logic.jsonl'])
   self.assertEqual(b.retained_state_B(),before);b.issue(['two.logic.jsonl']);self.assertEqual(b.retained_state_B(),before)
if __name__=='__main__':unittest.main()
