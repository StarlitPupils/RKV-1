import sys,unittest
from pathlib import Path
from scripts.cost_aware_order import order
from scripts.evidence_retrieval import admit
class OrderingTests(unittest.TestCase):
 def test_equal_raw_scores_prefer_lower_original_cost_and_keep_unmodified_baseline(self):
  loc={'a':{'length':3000},'b':{'length':1500},'c':{'length':1000}};scores={'a':2.,'b':2.,'c':.5};self.assertEqual(order(loc,['a','b','c'],scores,'lexical'),['a','b','c']);self.assertEqual(order(loc,['a','b','c'],scores,'score_per_byte'),['b','a','c']);self.assertEqual(order(loc,['a','b','c'],scores,'length_only'),['c','b','a']);self.assertEqual(admit({'shared':{'locators':loc}},order(loc,['a','b','c'],scores,'score_per_byte')),(['b','c'],2500))
 def test_exact_rational_tie_stable_identity_and_no_oversize_budget_bypass(self):
  loc={'a':{'length':1000},'b':{'length':2000},'c':{'length':4097}};scores={'a':1.,'b':2.,'c':100.};self.assertEqual(order(loc,['c','b','a'],scores,'score_per_byte'),['c','a','b']);self.assertEqual(admit({'shared':{'locators':loc}},order(loc,['c','b','a'],scores,'score_per_byte')),(['a','b'],3000))
 def test_invalid_source_score_universe_and_boolean_metadata_rejected(self):
  for score in (True,0.,-1.,float('nan'),float('inf')):
   with self.assertRaises(ValueError):order({'a':{'length':1}},['a'],{'a':score},'score_per_byte')
  with self.assertRaises(ValueError):order({'a':{'length':True}},['a'],{'a':1.},'score_per_byte')
  with self.assertRaises(ValueError):order({'a':{'length':1}},['a','a'],{'a':1.},'lexical')
  with self.assertRaises(ValueError):order({'a':{'length':1}},['a'],{},'lexical')
if __name__=='__main__':unittest.main()
