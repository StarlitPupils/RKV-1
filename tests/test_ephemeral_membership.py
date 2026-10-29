import contextlib,hashlib,sys,tempfile,unittest
from pathlib import Path
from scripts.ephemeral_membership import requested_members
from scripts.catalog_commitment import Catalogue,from_store
from scripts.audit_catalog_commitment import verify
from scripts.postings_transform import canonical
class OwnedReader:
 def __init__(self,rows):self.files={e['path']:{'size':e['bytes'],'sha256':e['sha256']} for e in rows}
 @contextlib.contextmanager
 def snapshot(self,sid):yield self
class EphemeralTests(unittest.TestCase):
 def rows(self,n):return [{'path':'f'+str(i).zfill(2)+'.logic.jsonl','bytes':1,'sha256':hashlib.sha256(bytes([i])).hexdigest()} for i in range(n)]
 def test_all_small_tree_shapes_each_late_path_exact_old_proof(self):
  for n in (1,2,3,5,7,8,9,15,16,17):
   rows=self.rows(n);ref=Catalogue('a'*64,rows);reader=OwnedReader(rows)
   for i,e in enumerate(rows):
    packet=requested_members(reader,ref.sid,[e['path']]);self.assertEqual(packet['anchor'],ref.anchor);self.assertEqual(packet['members'],[ref.proof(e['path'])]);self.assertTrue(verify(ref.anchor,packet['members'][0],bytes([i]),expected_anchor_sha256=ref.anchor_sha256,expected_snapshot_id=ref.sid,expected_path=e['path'])['original_selected_bytes_membership_verified'])
 def test_multiple_requests_leave_prior_output_unchanged(self):
  rows=self.rows(9);reader=OwnedReader(rows);ref=Catalogue('a'*64,rows);first=requested_members(reader,ref.sid,[rows[0]['path'],rows[-1]['path']]);before=canonical(first);second=requested_members(reader,ref.sid,[rows[4]['path']]);self.assertEqual(canonical(first),before);self.assertEqual(second['members'],[ref.proof(rows[4]['path'])]);self.assertEqual(set(first),{'anchor','members'})
 def test_missing_duplicate_bad_SID_and_path_refused(self):
  reader=OwnedReader(self.rows(2))
  for paths in ([],['missing.logic.jsonl'],['f00.logic.jsonl']*2,['../bad.logic.jsonl']):
   with self.assertRaises(ValueError):requested_members(reader,'a'*64,paths)
  with self.assertRaises(ValueError):requested_members(reader,'HEAD',['f00.logic.jsonl'])
 def test_actual_Store_payload_validation_and_held_scope_equivalence(self):
  from rkv1.store import Store
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);src=d/'source';src.mkdir()
   for n in ('one.logic.jsonl','two.logic.jsonl'):(src/n).write_bytes(n.encode())
   store=Store.create(d/'store');sid=store.add(src)['snapshot_id'];ref=from_store(store,sid)
   with store.read_scope(sid) as scope:
    packet=requested_members(scope,sid,['two.logic.jsonl','one.logic.jsonl']);self.assertEqual(packet['members'],[ref.proof(p) for p in sorted(['one.logic.jsonl','two.logic.jsonl'])])
    for proof in packet['members']:
     path=proof['entry']['path'];raw=scope.read_range(path);self.assertEqual(raw,path.encode());self.assertTrue(verify(ref.anchor,proof,raw,expected_anchor_sha256=ref.anchor_sha256,expected_snapshot_id=sid,expected_path=path)['original_selected_bytes_membership_verified'])
if __name__=='__main__':unittest.main()
