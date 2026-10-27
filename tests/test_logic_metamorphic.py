import unittest
from scripts.logic_fixture import encode
from scripts.audit_signed_logic import parse_source,oracle,literal
from scripts.logic_metamorphic import programs,transformed,transform_atom,queries,VARIANTS
class LogicMetamorphicTests(unittest.TestCase):
 def test_exact_counts_fixed_generation_and_distinct_programs(self):
  original=programs();self.assertEqual(original,programs());self.assertEqual(len(original),12);self.assertEqual(len({encode(p) for p in original}),12);self.assertEqual(len(queries()),27);self.assertTrue(all(len(p)==15 for p in original))
 def test_renaming_and_signflip_bijections_of_complete_independent_closure(self):
  for i,p in enumerate(programs()):
   base,_=oracle(parse_source(encode(p),'s','p'),literal(queries()[0]))
   for variant in VARIANTS:
    records=transformed(p,variant,i);known,_=oracle(parse_source(encode(records),'s','p'),literal(transform_atom(queries()[0],variant)));converted={literal(transform_atom({'predicate':a[0],'arguments':list(a[1]),'positive':a[2]},variant)) for a in base};self.assertEqual(known,converted)
 def test_transform_keeps_original_and_record_order_changes_only_line_order(self):
  p=programs()[0];raw=encode(p)
  for variant in VARIANTS:transformed(p,variant,0);self.assertEqual(encode(p),raw)
  changed=transformed(p,'record_order',0);self.assertNotEqual(changed,p);self.assertEqual(sorted(encode(changed).splitlines()),sorted(raw.splitlines()))
 def test_invalid_variant_refused_and_sign_transform_is_involution(self):
  for q in queries():self.assertEqual(transform_atom(transform_atom(q,'polarity_flip'),'polarity_flip'),q)
  with self.assertRaises(ValueError):transform_atom(queries()[0],'tuned_variant')
if __name__=='__main__':unittest.main()
