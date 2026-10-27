import copy,hashlib,struct,unittest
from scripts.proof_frame import encode_frame,decode_frame,to_shared,from_shared,HEADER,MAX_JSON
from scripts.postings_transform import canonical

def owned():
 template={'format':'RKVSETLOGIC1','snapshot_id':'a'*64,'source_scope':{'owned':True},'query':{'predicate':'edge','arguments':['a','b'],'positive':True},'complete':True,'verdict':'supported','work_used':4,'work_budget':100,'nodes':[{'kind':'fact','atom':{'predicate':'edge','arguments':['a','b'],'positive':True},'source_record_id':['one.logic.jsonl','a'],'citation':{'owned':True}}],'support_proof':0,'refute_proof':None,'source_grammar_verified':True,'scientific_entailment_verified':False,'generated_answer':None,'scope':'Owned envelope; no semantic proof claim'};second=copy.deepcopy(template);second.update(query={'predicate':'edge','arguments':['b','a'],'positive':True},verdict='unknown',support_proof=None);return canonical([template,second])
class ProofFrameTests(unittest.TestCase):
 def test_plain_shared_zlib_exact_owned_bytes(self):
  raw=owned();sha=hashlib.sha256(raw).hexdigest()
  for method in ('plain','shared'):
   frame=encode_frame(raw,method=method,codec='zlib');self.assertEqual(decode_frame(frame,expected_root_sha256=sha),raw)
   from scripts.audit_proof_frame import verify_frame
   self.assertTrue(verify_frame(frame,raw)['independent_header_and_layout_bytes_verified'])
 def test_shared_reconstructs_order_fields_and_negative_false_null_without_semantic_claim(self):
  raw=owned();self.assertEqual(from_shared(to_shared(raw),len(raw)),raw)
  import json
  values=json.loads(raw);values[1].update(complete=False)
  with self.assertRaises(ValueError):to_shared(canonical(values))
 def test_wrong_expected_SHA_tamper_trailing_truncation_and_method_refused(self):
  raw=owned();sha=hashlib.sha256(raw).hexdigest();frame=encode_frame(raw,method='shared',codec='zlib')
  for bad in (frame[:-1],frame+b'x',frame[:HEADER.size]+bytes([frame[HEADER.size]^1])+frame[HEADER.size+1:],frame[:8]+b'\x02'+frame[9:]):
   with self.assertRaises(ValueError):decode_frame(bad,expected_root_sha256=sha)
  with self.assertRaises(ValueError):decode_frame(frame,expected_root_sha256='0'*64)
 def test_oversize_header_rejected_before_decompression(self):
  raw=owned();sha=hashlib.sha256(raw).hexdigest();frame=encode_frame(raw,method='plain',codec='zlib');parts=list(HEADER.unpack_from(frame));parts[3]=MAX_JSON+1;bad=HEADER.pack(*parts)+frame[HEADER.size:]
  with self.assertRaises(ValueError):decode_frame(bad,expected_root_sha256=sha)
 def test_noncanonical_unknownkeys_empty_and_query_expansion_mismatch_refused(self):
  import json
  raw=owned();values=json.loads(raw)
  for bad in (b'[]',json.dumps(values).encode(),canonical([{**values[0],'extra':'x'}])):
   with self.assertRaises(ValueError):to_shared(bad)
  with self.assertRaises(ValueError):from_shared(to_shared(raw),len(raw)-1)
 def test_internal_recomputed_hash_does_not_replace_external_trust_anchor(self):
  import json
  raw=owned();values=json.loads(raw);values[0]['snapshot_id']='b'*64;values[1]['snapshot_id']='b'*64;changed=canonical(values);frame=encode_frame(changed,method='shared',codec='zlib')
  with self.assertRaises(ValueError):decode_frame(frame,expected_root_sha256=hashlib.sha256(raw).hexdigest())
 def test_zstd_exact_and_trailing_frame_refused(self):
  try:import zstandard
  except ImportError:self.skipTest('Optionalzstd unavailable')
  raw=owned();sha=hashlib.sha256(raw).hexdigest()
  for method in ('plain','shared'):
   frame=encode_frame(raw,method=method,codec='zstd');self.assertEqual(decode_frame(frame,expected_root_sha256=sha),raw)
   from scripts.audit_proof_frame import verify_frame
   self.assertTrue(verify_frame(frame,raw)['independent_header_and_layout_bytes_verified'])
  frame=encode_frame(raw,method='plain',codec='zstd');parts=list(HEADER.unpack_from(frame));payload=frame[HEADER.size:]+zstandard.ZstdCompressor().compress(b'evil');parts[4]=len(payload);parts[6]=hashlib.sha256(payload).digest();bad=HEADER.pack(*parts)+payload
  with self.assertRaises(ValueError):decode_frame(bad,expected_root_sha256=sha)
 def test_owned_canonical_root_and_shared_payload_golden_SHA_and_header(self):
  raw=owned();shared=to_shared(raw);self.assertEqual(len(raw),1236);self.assertEqual(hashlib.sha256(raw).hexdigest(),'d62aee45dd6dab6d6556150b816a80662cd747ca56eb5695a056ac066bc24e14');self.assertEqual(len(shared),818);self.assertEqual(hashlib.sha256(shared).hexdigest(),'4fe711601c141530590b076dc09f9fa5413768f4a230cb8c2ad827c7b53dfe15');self.assertEqual(HEADER.size,90);frame=encode_frame(raw,method='shared',codec='zlib');fields=HEADER.unpack_from(frame);self.assertEqual(fields[:4],(b'RKVPRF1\n',1,0,1236))
 def test_actual_pinned_source_set_certificates_roundtrip_and_independent_layout(self):
  import tempfile
  from pathlib import Path
  from rkv1.store import Store
  from scripts.logic_fixture import fact,rule,literal,encode
  from scripts.source_set_logic import SourceSetVerifier
  from scripts.audit_source_set_logic import verify_set_certificate
  from scripts.audit_proof_frame import verify_frame
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'source';source.mkdir();(source/'one.logic.jsonl').write_bytes(encode([fact('f','edge','a','b'),rule('r',literal('reach','?x','?y'),literal('edge','?x','?y'))]));store=Store.create(root/'store',compression='zlib');sid=store.add(source)['snapshot_id'];engine=SourceSetVerifier(store,sid,['one.logic.jsonl']);certificates=[engine.infer(literal('reach','a','b'),work_budget=100000),engine.infer(literal('reach','b','a'),work_budget=100000)];raw=canonical(certificates);frame=encode_frame(raw,method='shared',codec='zlib');self.assertEqual(decode_frame(frame,expected_root_sha256=hashlib.sha256(raw).hexdigest()),raw);self.assertTrue(verify_frame(frame,raw)['independent_header_and_layout_bytes_verified'])
   for certificate in certificates:self.assertTrue(verify_set_certificate(store,sid,certificate)['closure_completeness_verified'])
 def test_existing_archive_reader_refuses_experimental_proof_frame(self):
  import tempfile
  from pathlib import Path
  from rkv1.core import Archive
  frame=encode_frame(owned(),method='plain',codec='zlib')
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'owned-proof.rkvproof';p.write_bytes(frame)
   with self.assertRaises(ValueError):Archive(p)
 def test_file_CLI_exclusive_output_and_wrong_trusted_SHA_leaves_no_file(self):
  import tempfile
  from pathlib import Path
  from scripts.proof_frame import main
  raw=owned();sha=hashlib.sha256(raw).hexdigest()
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'original.json';frame=root/'proof.rkvproof';restored=root/'restored.json';source.write_bytes(raw);main(['encode',str(source),str(frame),'--method','shared','--codec','zlib']);main(['decode',str(frame),str(restored),'--expected-root-sha256',sha]);self.assertEqual(restored.read_bytes(),raw)
   with self.assertRaises(FileExistsError):main(['decode',str(frame),str(restored),'--expected-root-sha256',sha])
   refused=root/'refused.json'
   with self.assertRaises(ValueError):main(['decode',str(frame),str(refused),'--expected-root-sha256','0'*64])
   self.assertFalse(refused.exists())
if __name__=='__main__':unittest.main()
