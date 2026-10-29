import json,sys,unittest,copy
from pathlib import Path
from scripts.audit_cost_aware_sources import reference_order,score_sources
from scripts.cost_aware_order import order
from scripts.scifact_graph import build_model
from scripts.evidence_retrieval import lexical
class AuditorTests(unittest.TestCase):
 def test_independent_crossproducts_match_candidate_on_owned_and_stable_ties(self):
  raw=b''.join(json.dumps({'doc_id':i,'title':'Owned alpha','abstract':['alpha '*i+' beta gamma.']}).encode()+b'\n' for i in range(17));model,_=build_model(raw,[])
  for q in ['alpha','beta','gamma alpha','unknownword']:
   ranked,scores=lexical(model['shared'],q)
   for m in ['lexical','score_per_byte','length_only']:self.assertEqual(reference_order(model['shared'],q,m),order(model['shared']['locators'],ranked,scores,m))
 def test_annotation_missing_is_null_not_NEI_or_zero_and_partial_recall_exact(self):
  self.assertIsNone(score_sources({'evidence':{}},['doc:1'])['complete']);g={'evidence':{'1':[{'sentences':[0]}],'2':[{'sentences':[1]}]}};s=score_sources(g,['doc:1']);self.assertEqual(s['recall_fraction'],[1,2]);self.assertFalse(s['complete']);self.assertTrue(score_sources(g,['doc:1','doc:2'])['complete'])
if __name__=='__main__':unittest.main()
