import json,sys,unittest
from pathlib import Path
from scripts.api_admission_audit import independent_order,trace
from scripts.evidence_retrieval import lexical,admit
from scripts.scifact_graph import build_model
class AdmissionTests(unittest.TestCase):
 def test_independent_order_matches_frozen_reference_on_owned_corpus_and_ties(self):
  raw=b''.join(json.dumps({'doc_id':i,'title':'Owned alpha' if i%2 else 'Owned beta','abstract':['alpha beta gamma' if i%3 else 'gamma gamma delta']}).encode()+b'\n' for i in range(17));model,_=build_model(raw,[])
  for q in ['alpha beta','gamma gamma','unknownword','THE and a','alpha DELTA 17']:
   a,s=independent_order(model['shared'],q);b,t=lexical(model['shared'],q);self.assertEqual(a,b)
   for k in s:self.assertAlmostEqual(s[k],t[k],places=12)
 def test_rank_budget_oversize_and_count_are_distinct(self):
  loc={str(i):{'length':1} for i in range(16)};loc['0']['length']=4097;ordered=list(map(str,range(15)));r=trace(loc,ordered,{'0','1','14','15'});self.assertEqual(r['gold_events']['0']['category'],'byte_rejected');self.assertTrue(r['gold_events']['0']['self_exceeds_entire_budget']);self.assertEqual(r['gold_events']['1']['category'],'recovered');self.assertEqual(r['gold_events']['14']['category'],'count_stop');self.assertEqual(r['gold_events']['15']['category'],'no_candidate')
 def test_cumulative_rejection_is_not_structurally_oversize(self):
  loc={'a':{'length':3000},'b':{'length':2000},'c':{'length':1000}};r=trace(loc,['a','b','c'],{'b'});self.assertEqual(r['selected_ids'],['a','c']);self.assertFalse(r['gold_events']['b']['self_exceeds_entire_budget']);self.assertEqual(r['gold_events']['b']['used_B_before'],3000);self.assertEqual(admit({'shared':{'locators':loc}},['a','b','c']),(['a','c'],4000))
 def test_unknown_and_boolean_length_rejected(self):
  with self.assertRaises(ValueError):trace({'a':{'length':True}},['a'],{'a'})
  with self.assertRaises(ValueError):trace({'a':{'length':1}},['a'],{'missing'})
if __name__=='__main__':unittest.main()
