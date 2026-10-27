import copy,json,tempfile,unittest
from pathlib import Path
from rkv1.store import Store
from scripts.postings_transform import canonical
from scripts.source_set_logic import SourceSetVerifier
from scripts.audit_source_set_logic import verify_set_certificate
from scripts.proofwriter_representation import Compiler,UnsupportedRepresentation
from scripts.audit_proofwriter_representation import single,rule,audit_compilation
F='("Mira" "is" "warm" "+")';R='((("someone" "is" "warm" "+")) -> ("someone" "is" "calm" "+"))';Q='("Mira" "is" "calm" "+")'
class RepresentationTests(unittest.TestCase):
 def test_atomic_unary_binary_explicit_sign_and_case_injective(self):
  c=Compiler(world='OWA')
  for s in (F,Q,'("Mira" "sees" "fox" "-")','("bald eagle" "is" "rough" "-")'):self.assertEqual(c.ground(s),single(s))
  self.assertNotEqual(c.ground(F),c.ground(F.replace('Mira','mira')));self.assertNotEqual(c.ground('("Mira" "warm" "fox" "+")')['predicate'],c.ground(F)['predicate'])
 def test_rule_multiple_premises_variables_and_constants_independent(self):
  for s in (R,'((("something" "sees" "fox" "+") ("something" "is" "rough" "-")) -> ("fox" "is" "warm" "+"))'):self.assertEqual(Compiler(world='OWA').rule(s),rule(s))
 def test_malformed_injection_unbounded_unsupported_and_mixedvars_refused(self):
  for s in ('__import__("os")',F+' trailing','("Mira" "is" "warm" "~")','("someone" "is" "warm" "+")','("bad_name" "is" "warm" "+")','("Mira" "is" "->" "+")','("Mira" "is" "(" "+")'):
   with self.assertRaises(ValueError):Compiler(world='OWA').ground(s)
   with self.assertRaises(ValueError):single(s)
  with self.assertRaises(ValueError):Compiler(world='OWA').rule('((("someone" "is" "warm" "+")) -> ("something" "is" "calm" "+"))')
 def test_original_to_derived_mapping_actualStore_fullaudit_and_query(self):
  row={'triples':{'triple1':{'representation':F,'text':'untrusted original language unused'}},'rules':{'rule1':{'representation':R,'text':'unused'}},'questions':{'Q1':{'representation':Q,'answer':True}}};compiled,mapping=Compiler(world='OWA').compile(row['triples'],row['rules'])
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'source';source.mkdir();(source/'original.json').write_bytes(canonical(row))
   for p,raw in compiled.items():(source/p).write_bytes(raw)
   store=Store.create(root/'store',compression='zlib');sid=store.add(source)['snapshot_id'];audit=audit_compilation(store,sid,mapping,list(compiled),world='OWA');self.assertTrue(audit['independent_compilation_verified']);self.assertFalse(audit['English_translation_verified']);query=Compiler(world='OWA').ground(Q);certificate=SourceSetVerifier(store,sid,list(compiled)).infer(query,work_budget=100000);self.assertEqual(certificate['verdict'],'supported');self.assertTrue(verify_set_certificate(store,sid,certificate)['closure_completeness_verified'])
   bad=copy.deepcopy(mapping);bad[0]['original_JSON_pointer'][1]='triple2'
   with self.assertRaises(ValueError):audit_compilation(store,sid,bad,list(compiled),world='OWA')
 def test_model_inputs_do_not_access_text_gold_questions_or_derived_proofs(self):
  class RepresentationsOnly(dict):
   def __getitem__(self,key):
    if key!='representation':raise AssertionError('Forbidden field accessed')
    return super().__getitem__(key)
  facts={'triple1':RepresentationsOnly(representation=F)};rules={'rule1':RepresentationsOnly(representation=R)};compiled,_=Compiler(world='OWA').compile(facts,rules);self.assertEqual(set(compiled),{'facts.logic.jsonl','rules.logic.jsonl'})
 def test_empty_rules_supported_and_unsafe_head_rejected_by_engine(self):
  source,mapping=Compiler(world='OWA').compile({'t':{'representation':F}},{});self.assertEqual(list(source),['facts.logic.jsonl']);self.assertEqual(mapping[0]['compiled_record_id'],'f0')
  unsafe='((("Mira" "is" "warm" "+")) -> ("someone" "is" "calm" "+"))';compiled,_=Compiler(world='OWA').compile({'t':{'representation':F}},{'r':{'representation':unsafe}})
  from scripts.signed_logic import compile_records
  with self.assertRaises(ValueError):compile_records(compiled['rules.logic.jsonl'],'s','x')
 def test_independent_original_derived_tamper_refused(self):
  row={'triples':{'t':{'representation':F}},'rules':{}};compiled,mapping=Compiler(world='OWA').compile(row['triples'],row['rules'])
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'s';source.mkdir();(source/'original.json').write_bytes(canonical(row));(source/'facts.logic.jsonl').write_bytes(compiled['facts.logic.jsonl'].replace(b'true',b'false'));store=Store.create(root/'store',compression='zlib');sid=store.add(source)['snapshot_id']
   with self.assertRaises(ValueError):audit_compilation(store,sid,mapping,list(compiled),world='OWA')
 def test_OWA_tilde_premise_is_explicit_negative_not_absence_and_CWA_refused(self):
  negative='((("someone" "is" "warm" "~")) -> ("someone" "is" "calm" "+"))'
  self.assertEqual(Compiler(world='OWA').rule(negative),rule(negative))
  with self.assertRaises(ValueError):Compiler(world='CWA')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for sign in ('+','-'):
    row={'triples':{'t':{'representation':F.replace('"+"','"'+sign+'"')}},'rules':{'r':{'representation':negative}}};compiled,mapping=Compiler(world='OWA').compile(row['triples'],row['rules']);source=root/sign;source.mkdir();(source/'original.json').write_bytes(canonical(row))
    for path,raw in compiled.items():(source/path).write_bytes(raw)
    store=Store.create(root/('store'+sign),compression='zlib');sid=store.add(source)['snapshot_id'];self.assertTrue(audit_compilation(store,sid,mapping,list(compiled),world='OWA')['independent_compilation_verified']);certificate=SourceSetVerifier(store,sid,list(compiled)).infer(Compiler(world='OWA').ground(Q),work_budget=100000);self.assertEqual(certificate['verdict'],'supported' if sign=='-' else 'unknown')
if __name__=='__main__':unittest.main()
