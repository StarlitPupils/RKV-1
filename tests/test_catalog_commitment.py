import copy,hashlib,sys,unittest,tempfile
from pathlib import Path
from scripts.catalog_commitment import Catalogue,from_store
from scripts.audit_catalog_commitment import verify
from scripts.postings_transform import canonical
class CatalogueTests(unittest.TestCase):
 def rows(self,n):return [{'path':'file'+str(i).zfill(2)+'.logic.jsonl','bytes':1,'sha256':hashlib.sha256(bytes([i])).hexdigest()} for i in range(n)]
 def check(self,c,p,b):return verify(c.anchor,p,b,expected_anchor_sha256=c.anchor_sha256,expected_snapshot_id=c.sid,expected_path=p['entry']['path'])
 def test_all_small_balanced_unbalanced_leaves_and_independent_fullroot(self):
  for n in (1,2,3,4,5,7,8,9,15,16,17):
   c=Catalogue('a'*64,self.rows(n))
   def independent(rows):
    if len(rows)==1:return hashlib.sha256(bytes([0])+canonical(rows[0])).digest()
    k=1
    while k*2<len(rows):k*=2
    return hashlib.sha256(bytes([1])+independent(rows[:k])+independent(rows[k:])).digest()
   self.assertEqual(c.anchor['root_sha256'],independent(c.records).hex())
   for i,e in enumerate(c.records):self.assertTrue(self.check(c,c.proof(e['path']),bytes([i]))['original_selected_bytes_membership_verified'])
 def test_exact_payload_and_all_entry_and_path_tampering(self):
  c=Catalogue('a'*64,self.rows(3));p=c.proof(c.records[0]['path'])
  changes=[lambda x:x.update(leaf_index=1),lambda x:x.update(leaf_index=True),lambda x:x['entry'].update(bytes=2),lambda x:x['entry'].update(sha256='0'*64),lambda x:x['entry'].update(path='other.logic.jsonl'),lambda x:x['siblings'].append('0'*64),lambda x:x['siblings'].pop(),lambda x:x.update(snapshot_id='b'*64),lambda x:x.update(anchor_sha256='0'*64),lambda x:x.update(extra=0),lambda x:x.update(siblings=['0'*64]*len(x['siblings']))]
  for mutate in changes:
   bad=copy.deepcopy(p);mutate(bad)
   with self.assertRaises(ValueError):self.check(c,bad,b'\0')
  with self.assertRaises(ValueError):self.check(c,p,b'\1')
 def test_external_anchor_not_self_declared_SID_authentication(self):
  a=Catalogue('a'*64,self.rows(3));b=Catalogue('a'*64,self.rows(2));p=b.proof(b.records[0]['path'])
  with self.assertRaises(ValueError):verify(b.anchor,p,b'\0',expected_anchor_sha256=a.anchor_sha256,expected_snapshot_id=a.sid,expected_path=p['entry']['path'])
  # A malicious publisher can create a different anchor for the same SID: no trustless SID-only claim.
  self.assertTrue(self.check(b,p,b'\0')['anchor_requires_prior_trusted_full_manifest_validation'])
 def test_missing_extra_duplicate_unsorted_and_mutable_proof_copies(self):
  rows=self.rows(3)
  for invalid in ([],rows[::-1],rows+[rows[-1]],rows+[{'path':'../../bad.logic.jsonl','bytes':1,'sha256':'0'*64}]):
   with self.assertRaises(ValueError):Catalogue('a'*64,invalid)
  c=Catalogue('a'*64,rows);p=c.proof(rows[0]['path']);p['entry']['bytes']=10;self.assertEqual(c.proof(rows[0]['path'])['entry']['bytes'],1)
 def test_actual_store_initial_metadata_only_and_selected_exact_bytes(self):
  from rkv1.store import Store
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);src=d/'source';src.mkdir();(src/'one.logic.jsonl').write_bytes(b'owned1');(src/'two.logic.jsonl').write_bytes(b'owned2');(src/'notes.txt').write_bytes(b'unselected noneligible')
   store=Store.create(d/'store');sid=store.add(src)['snapshot_id'];c=from_store(store,sid)
   self.assertEqual(c.anchor['eligible_count'],2)
   with store.snapshot(sid) as s:self.assertTrue(self.check(c,c.proof('one.logic.jsonl'),s.read_range('one.logic.jsonl'))['original_selected_bytes_membership_verified'])
 def test_budget_and_strict_anchor_integer_bounds(self):
  c=Catalogue('a'*64,self.rows(3));p=c.proof(c.records[0]['path'])
  with self.assertRaises(ValueError):verify(c.anchor,p,b'\0',expected_anchor_sha256=c.anchor_sha256,expected_snapshot_id=c.sid,expected_path=p['entry']['path'],source_byte_budget=0)
  for key,value in (('eligible_count',True),('eligible_count',0),('eligible_count',4097),('eligible_payload_B',True),('eligible_payload_B',-1)):
   a=copy.deepcopy(c.anchor);a[key]=value
   with self.assertRaises(ValueError):verify(a,p,b'\0',expected_anchor_sha256=c.anchor_sha256,expected_snapshot_id=c.sid,expected_path=p['entry']['path'])
 def test_newHEAD_identical_eligible_root_still_changes_trusted_anchor(self):
  from rkv1.store import Store
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);src=d/'source';src.mkdir();(src/'one.logic.jsonl').write_bytes(b'owned');(src/'notes.txt').write_bytes(b'old')
   store=Store.create(d/'store');sid=store.add(src)['snapshot_id'];original=store.block
   def forbidden(*a,**kw):raise AssertionError('Catalogue construction read source payload')
   store.block=forbidden;c=from_store(store,sid);store.block=original
   (src/'notes.txt').write_bytes(b'new');new=store.add(src)['snapshot_id'];other=from_store(store,new)
   self.assertNotEqual(new,sid);self.assertEqual(other.anchor['root_sha256'],c.anchor['root_sha256']);self.assertNotEqual(other.anchor_sha256,c.anchor_sha256)
   proof=c.proof('one.logic.jsonl');self.assertTrue(self.check(c,proof,b'owned')['original_selected_bytes_membership_verified'])
   with self.assertRaises(ValueError):verify(other.anchor,proof,b'owned',expected_anchor_sha256=other.anchor_sha256,expected_snapshot_id=new,expected_path='one.logic.jsonl')
if __name__=='__main__':unittest.main()
