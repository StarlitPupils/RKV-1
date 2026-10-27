import sys,copy,tempfile,unittest,hashlib
from pathlib import Path
from scripts.compact_witness import compact,expand,encode_frame,decode_frame,MAGIC,HEADER
from rkv1.store import Store
from scripts.catalog_fixture import sources,PATHS
from scripts.selected_witness import Witness
from scripts.audit_selected_witness import audit
from scripts.logic_fixture import literal
from scripts.postings_transform import canonical,parse
from scripts.proof_frame import decode_frame as old_decode
class CompactTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);root=Path(self.temp.name);src=root/'source';src.mkdir()
  for p,b in sources(9).items():(src/p).write_bytes(b)
  self.store=Store.create(root/'store',compression='zlib');self.sid=self.store.add(src)['snapshot_id'];self.proof=Witness(self.store,self.sid,PATHS).infer(literal('reach','a','c'),work_budget=100000);self.raw=canonical(self.proof);self.sha=hashlib.sha256(self.raw).hexdigest()
 def test_exact_canonical_roundtrip_then_original_DAG(self):
  for method in ('plain','compact'):
   for codec in ('zlib','zstd'):
    framed=encode_frame(self.raw,method=method,codec=codec);restored=decode_frame(framed,store=self.store,snapshot_id=self.sid,expected_root_sha256=self.sha);self.assertEqual(restored,self.raw);self.assertTrue(audit(self.store,self.sid,parse(restored))['original_selected_DAG_verified'])
 def test_context_cannot_be_guessed_wrongSID_count_or_digest(self):
  body=compact(self.raw)
  with self.assertRaises(ValueError):expand(body,self.store,'0'*64)
  for edit in ('count','bool','digest','extra','global'):
   c=parse(body)
   if edit=='count':c['selection']['eligible_path_count']+=1
   elif edit=='bool':c['selection']['eligible_path_count']=True
   elif edit=='digest':c['selection']['eligible_paths_sha256']='0'*64
   elif edit=='extra':c['selection']['eligible_paths']=self.proof['selection']['eligible_paths']
   else:c['global_verdict']='supported'
   with self.assertRaises(ValueError,msg=edit):expand(canonical(c),self.store,self.sid)
 def test_old_reader_rejects_new_magic_new_reader_rejects_old_magic(self):
  frame=encode_frame(self.raw,method='compact',codec='zstd')
  with self.assertRaises(ValueError):old_decode(frame,expected_root_sha256=self.sha)
  bad=b'RKVPRF1\n'+frame[8:]
  with self.assertRaises(ValueError):decode_frame(bad,store=self.store,snapshot_id=self.sid,expected_root_sha256=self.sha)
 def test_external_root_identity_not_substituted_by_frame_hash(self):
  frame=encode_frame(self.raw,method='compact',codec='zstd')
  with self.assertRaises(ValueError):decode_frame(frame,store=self.store,snapshot_id=self.sid,expected_root_sha256='0'*64)
 def test_exact_schema_canonical_duplicate_and_bounds(self):
  for raw in (self.raw+b'\n',b'{}',self.raw.replace(b'"format":',b'"extra":1,"format":',1),b'{"format":1,"format":2}'):
   with self.assertRaises(ValueError):compact(raw)
  p=copy.deepcopy(self.proof);p['selection']['eligible_paths'].reverse()
  with self.assertRaises(ValueError):compact(canonical(p))
 def test_header_payload_corruption_truncation_and_trailing_refused(self):
  frame=encode_frame(self.raw,method='compact',codec='zstd')
  for bad in (frame[:-1],frame+b'x',frame[:HEADER.size]+bytes([frame[HEADER.size]^1])+frame[HEADER.size+1:],frame[:8]+b'\x02'+frame[9:]):
   with self.assertRaises(ValueError):decode_frame(bad,store=self.store,snapshot_id=self.sid,expected_root_sha256=self.sha)
 def test_compaction_is_detached_and_does_not_claim_global_science(self):
  before=canonical(self.proof);body=compact(before);self.assertEqual(canonical(self.proof),before);c=parse(body);self.assertNotIn('eligible_paths',c['selection']);self.assertIsNone(c['global_verdict']);self.assertFalse(c['scientific_entailment_verified']);self.assertEqual(expand(body,self.store,self.sid),before)
 def test_actual_stored_metadata_corruption_revalidates(self):
  body=compact(self.raw);path=self.store.root/'snapshots'/(self.sid+'.rkvs');raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
  with self.assertRaises(ValueError):expand(body,self.store,self.sid)
 def test_independent_auditor_does_not_call_producer_or_expander(self):
  from unittest.mock import patch
  from scripts.audit_compact_witness import verify
  frame=encode_frame(self.raw,method='compact',codec='zstd')
  with patch('scripts.compact_witness.compact',side_effect=AssertionError('Not independent')),patch('scripts.compact_witness.expand',side_effect=AssertionError('Not independent')):
   self.assertTrue(verify(frame,self.raw,self.store,self.sid)['independent_header_and_catalog_mapping_verified'])
 def test_independent_auditor_rejects_mismatched_original_and_wrongSID(self):
  from scripts.audit_compact_witness import verify
  frame=encode_frame(self.raw,method='compact',codec='zstd')
  for raw,sid in ((self.raw+b' ',self.sid),(self.raw,'0'*64)):
   with self.assertRaises(ValueError):verify(frame,raw,self.store,sid)
 def test_existing_plain_codec_is_output_equivalent_independent_baseline(self):
  from scripts.proof_frame import encode_frame as baseline_encode,decode_frame as baseline_decode
  from scripts.audit_compact_witness import verify
  for codec in ('zlib','zstd'):
   frame=baseline_encode(self.raw,method='plain',codec=codec)
   self.assertEqual(baseline_decode(frame,expected_root_sha256=self.sha),self.raw)
   self.assertTrue(verify(frame,self.raw,self.store,self.sid)['independent_header_and_catalog_mapping_verified'])
 def test_CLI_external_SHA_context_restore_and_exclusive_output(self):
  from scripts import compact_witness as module
  import subprocess,os
  root=self.store.root.parent;src=root/'root.json';src.write_bytes(self.raw);frame=root/'frame.bin';restored=root/'restored.json';env={**os.environ,'PYTHONPATH':str(Path.cwd())};script=Path(module.__file__)
  a=subprocess.run([sys.executable,str(script),'encode',str(src),str(frame),'--method','compact','--codec','zstd'],capture_output=True,env=env);self.assertEqual(a.returncode,0,a.stderr)
  args=[sys.executable,str(script),'decode',str(frame),str(restored),'--store',str(self.store.root),'--snapshot',self.sid,'--expected-root-sha256',self.sha]
  a=subprocess.run(args,capture_output=True,env=env);self.assertEqual(a.returncode,0,a.stderr);self.assertEqual(restored.read_bytes(),self.raw);a=subprocess.run(args,capture_output=True,env=env);self.assertNotEqual(a.returncode,0);self.assertEqual(restored.read_bytes(),self.raw)
if __name__=='__main__':unittest.main()
