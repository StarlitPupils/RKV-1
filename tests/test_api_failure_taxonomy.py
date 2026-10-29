import unittest
from scripts.api_failure_taxonomy import classify,summarize
class Checks(unittest.TestCase):
 def test_all_categories(self):
  cases=[([],[],False,None,'unannotated_proxy'),(['a'],[],True,False,'no_annotated_paper_available'),(['a'],['a'],False,False,'annotated_paper_available_verdict_wrong'),(['a'],['a'],True,False,'verdict_correct_rationale_incomplete'),(['a'],['a'],True,True,'grounded_correct')]
  for a,b,c,d,e in cases:self.assertEqual(classify(a,b,c,d),e)
 def test_missing_denominator(self):self.assertIsNone(summarize(['grounded_correct'])['missing_paper_strict_majority'])
 def test_half_is_not_majority(self):self.assertFalse(summarize(['no_annotated_paper_available','annotated_paper_available_verdict_wrong'])['missing_paper_strict_majority'])
 def test_grounding_contradictions(self):
  for a,b,c,d in [(['a'],[],True,True),(['a'],['a'],False,True),([],[],True,False)]:
   with self.assertRaises(ValueError):classify(a,b,c,d)
 def test_any_gold_is_not_all(self):self.assertEqual(classify(['a','b'],['a'],True,True),'grounded_correct')
