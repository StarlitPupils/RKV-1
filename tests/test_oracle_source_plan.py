import unittest
from scripts.oracle_source_plan import oracle_papers
class Checks(unittest.TestCase):
 def test_exact_whole_record_budget_and_order(self):
  a=oracle_papers({'a':{'length':4096},'b':{'length':1}},['b','a','a']);self.assertEqual(a['selected_ids'],['a']);self.assertEqual(a['original_record_B'],4096);self.assertEqual(a['rejections'][0]['reason'],'remaining_byte_budget')
 def test_unknown_or_bad_source_rejected(self):
  for loc,ids in [({},['a']),({'a':{'length':0}},['a'])]:
   with self.assertRaises(ValueError):oracle_papers(loc,ids)
 def test_oversize_not_split_or_dropped_denominator(self):
  x=oracle_papers({'a':{'length':4097}},['a']);self.assertEqual(x['selected_ids'],[]);self.assertEqual(len(x['rejections']),1)
 def test_empty_and_count_bound(self):
  self.assertEqual(oracle_papers({},[])['selected_ids'],[]);x=oracle_papers({'a':{'length':1},'b':{'length':1}},['a','b'],count=1);self.assertEqual(x['rejections'][0]['reason'],'count_stop')
