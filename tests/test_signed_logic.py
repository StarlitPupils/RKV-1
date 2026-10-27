import copy,json,tempfile,unittest
from pathlib import Path
from rkv1.store import Store
from scripts.signed_logic import SignedVerifier,compile_records,atom
from scripts.audit_signed_logic import verify_certificate,oracle,parse_source,VerificationCapacityExceeded
from scripts.logic_fixture import fixture,encode,literal
class SignedLogicTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir();self.data=fixture();self.raw=encode(self.data['initial']);(self.source/'axioms.jsonl').write_bytes(self.raw);self.store=Store.create(self.root/'store',compression='zlib');self.sid=self.store.add(self.source)['snapshot_id']
 def engine(self):return SignedVerifier(self.store,self.sid,'axioms.jsonl')
 def check(self,c,sid=None):return verify_certificate(self.store,sid or self.sid,'axioms.jsonl',c)
 def test_all_four_verdicts_independent_oracle_history_and_no_explosion(self):
  before=[]
  for row in self.data['queries']:
   c=self.engine().infer(row['query'],work_budget=100000);self.assertEqual(c['verdict'],row['initial']);self.assertTrue(self.check(c)['closure_completeness_verified']);before.append(c)
  (self.source/'axioms.jsonl').write_bytes(encode(self.data['updated']));new=self.store.add(self.source)['snapshot_id'];self.assertNotEqual(new,self.sid)
  for row,old in zip(self.data['queries'],before):
   self.assertEqual(self.engine().infer(row['query'],work_budget=100000),old);c=SignedVerifier(self.store,new,'axioms.jsonl').infer(row['query'],work_budget=100000);self.assertEqual(c['verdict'],row['updated']);self.assertTrue(self.check(c,new)['formal_derivation_verified']);self.assertFalse(c['scientific_entailment_verified']);self.assertIsNone(c['generated_answer'])
 def test_budget_is_incomplete_not_unknown_and_partial_proofs_sound(self):
  c=self.engine().infer(literal('unrelated','c0','c1'),work_budget=0);self.assertFalse(c['complete']);self.assertEqual(c['verdict'],'incomplete');self.assertFalse(self.check(c)['closure_completeness_verified'])
  for b in (-1,True,100001):
   with self.assertRaises(ValueError):self.engine().infer(literal('a','a','b'),work_budget=b)
 def test_tampered_atom_rule_premise_verdict_source_and_false_completeness_refused(self):
  original=self.engine().infer(literal('influence','c0','c2'),work_budget=100000)
  for kind in ('atom','rule','premise','verdict','source','closure'):
   c=copy.deepcopy(original)
   if kind=='atom':c['nodes'][0]['atom']['arguments'].reverse()
   elif kind=='rule':next(n for n in c['nodes'] if n['kind']=='rule')['source_record_id']='r_repeat'
   elif kind=='premise':next(n for n in c['nodes'] if n['kind']=='rule')['premise_proofs']=[]
   elif kind=='verdict':c['verdict']='unknown'
   elif kind=='source':c['snapshot_id']='0'*64
   else:c=self.engine().infer(literal('unrelated','c0','c1'),work_budget=0);c['complete']=True;c['verdict']='unknown'
   with self.assertRaises(ValueError):self.check(c)
 def test_grammar_duplicate_keys_ids_unsafe_variables_signs_and_function_terms_refused(self):
  examples=[b'{"id":"a","id":"b"}\n',encode(self.data['initial'][:1]*2),encode([{'id':'unsafe','kind':'rule','head':literal('a','?z','?x'),'premises':[literal('b','?x','?y')]}]),encode([{'id':'a','kind':'fact','atom':literal('a','f(x)','b')}]),encode([{'id':'a','kind':'fact','atom':literal('a','a','b',1)}])]
  for raw in examples:
   with self.assertRaises(ValueError):compile_records(raw,self.sid,'x')
   with self.assertRaises(ValueError):parse_source(raw,self.sid,'x')
 def test_explicit_negative_query_is_symmetric_no_negation_as_failure(self):
  c=self.engine().infer(literal('activate','b0','a0',False),work_budget=100000);self.assertEqual(c['verdict'],'supported');self.check(c)
  c=self.engine().infer(literal('unknown','a0','b0',False),work_budget=100000);self.assertEqual(c['verdict'],'unknown');self.check(c)
 def test_certificate_missing_complete_node_duplicate_node_and_forward_reference_refused(self):
  original=self.engine().infer(literal('influence','c0','c2'),work_budget=100000)
  for mode in ('missing','duplicate','forward'):
   c=copy.deepcopy(original)
   if mode=='missing':c['nodes'].pop()
   elif mode=='duplicate':c['nodes'].append(copy.deepcopy(c['nodes'][0]))
   else:
    i=next(i for i,n in enumerate(c['nodes']) if n['kind']=='rule');c['nodes'][i]['premise_proofs'][0]=i
   with self.assertRaises(ValueError):self.check(c)
 def test_grounding_verifier_capacity_distinct_from_unknown(self):
  from scripts.audit_signed_logic import grounded_steps
  records=parse_source(self.raw,self.sid,'x')
  with self.assertRaises(VerificationCapacityExceeded):list(grounded_steps(records,{'a','b','c'},limit=1))
 def test_owned_wordorder_pairs_have_identical_old_feature_vectors(self):
  from scripts.relation_probe import features
  for p in self.data['collision_pairs']:
   a,b=p['claims'];self.assertEqual(features(a,p['document']),features(b,p['document']));self.assertEqual(features(a,p['document'],claim_only=True),features(b,p['document'],claim_only=True));self.assertNotEqual(p['gold'][0],p['gold'][1])
if __name__=='__main__':unittest.main()
