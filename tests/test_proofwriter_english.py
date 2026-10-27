import unittest
from scripts.proofwriter_english import EnglishCompiler
from scripts.proofwriter_representation import Compiler
class ControlledEnglishTests(unittest.TestCase):
 def test_direct_properties_relations_negative_and_subjectorder(self):
  e=EnglishCompiler(world='OWA');s=Compiler(world='OWA')
  pairs=[('Mira is warm.','("Mira" "is" "warm" "+")'),('The fox sees the bear.','("fox" "sees" "bear" "+")'),('The fox does not see the bear.','("fox" "sees" "bear" "-")'),('Mira is not warm.','("Mira" "is" "warm" "-")'),('The bald eagle sees the fox.','("bald eagle" "sees" "fox" "+")')]
  for text,formal in pairs:self.assertEqual(e.ground(text),s.ground(formal))
  self.assertNotEqual(e.ground('The fox sees the bear.'),e.ground('The bear sees the fox.'))
 def test_rules_pronouns_ellipsis_explicit_negative_and_generic(self):
  e=EnglishCompiler(world='OWA');s=Compiler(world='OWA')
  pairs=[('If someone sees the fox then they eat the bald eagle.','((("someone" "sees" "fox" "+")) -> ("someone" "eats" "bald eagle" "+"))'),('If someone is warm and not calm then they are rough.','((("someone" "is" "warm" "+") ("someone" "is" "calm" "~")) -> ("someone" "is" "rough" "+"))'),('If something sees the fox and it eats the bear then the bear is rough.','((("something" "sees" "fox" "+") ("something" "eats" "bear" "+")) -> ("bear" "is" "rough" "+"))'),('All warm, calm people are rough.','((("someone" "is" "warm" "+") ("someone" "is" "calm" "+")) -> ("someone" "is" "rough" "+"))'),('Warm things are calm.','((("something" "is" "warm" "+")) -> ("something" "is" "calm" "+"))')]
  for text,formal in pairs:self.assertEqual(s.rule(e.rule_representation(text)),s.rule(formal))
 def test_no_symbolic_gold_or_proof_field_access(self):
  class TextOnly(dict):
   def __getitem__(self,key):
    if key!='text':raise AssertionError('Non-English oracle field read')
    return super().__getitem__(key)
  files,_=EnglishCompiler(world='OWA').compile({'t':TextOnly(text='Mira is warm.')},{'r':TextOnly(text='All warm people are calm.')});self.assertEqual(set(files),{'facts.logic.jsonl','rules.logic.jsonl'})
 def test_unsupported_language_unbound_pronoun_and_CWA_abstain(self):
  e=EnglishCompiler(world='OWA')
  for value in ('Mira may be warm.','It is warm.','Mira is warm','Mira is probably warm.','Mira is warm. Another sentence.','If Mira is warm then she is calm.'):
   with self.assertRaises(ValueError):e.rule_representation(value) if value.startswith('If') else e.ground(value)
  with self.assertRaises(ValueError):EnglishCompiler(world='CWA')
if __name__=='__main__':unittest.main()
