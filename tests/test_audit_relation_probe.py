import hashlib,unittest
from scripts.relation_probe import features,fit,majority,RelationProbe
from scripts.audit_relation_probe import reference_features,reference_predict,relation_metrics
from scripts.analyze_relation_probe import independent_metrics
from scripts.evidence_retrieval import encoded

class RelationAuditTests(unittest.TestCase):
 def test_independent_features_predictions_and_all_denominator_categories(self):
  examples=[{'claim':q,'document':d,'target':y} for q,d,y in [('alpha gains','alpha gains',1),('beta gains','beta gains',1),('alpha never gains','alpha gains',0),('beta never gains','beta gains',0)]]
  for claim,document in [('', ''),('alpha alpha not','alpha beta'),('数字 1.5','Numbers 15 1 5'),('without effect','no change')]:
   for only in (False,True):self.assertEqual(features(claim,document,claim_only=only),reference_features(claim,document,only))
  for method in ('majority','pair','claim_only','permuted_pair'):
   model=majority(examples) if method=='majority' else fit(examples,method)[0];raw=encoded(model);probe=RelationProbe(raw,sha256=hashlib.sha256(raw).hexdigest())
   for claim,document in [('alpha gains','alpha gains'),('beta never gains','beta gains')]:self.assertEqual(probe.predict(claim,document),reference_predict(model,claim,document))
  gold={'a':'SUPPORT','b':'CONTRADICT','c':'SUPPORT','d':None};pred={'a':'SUPPORT','b':'SUPPORT','d':'CONTRADICT','unknown':'CONTRADICT'};r=relation_metrics(gold,pred);self.assertEqual(r,independent_metrics(gold,pred));self.assertEqual(r['all_selected_pairs'],4);self.assertEqual(r['all_explicit_labeled_gold_pairs'],3);self.assertEqual(r['retrieved_explicit_gold_pairs'],2);self.assertEqual(r['missing_explicit_gold_pairs'],1);self.assertEqual(r['ambiguous_gold_pairs'],1);self.assertEqual(r['selected_without_gold_annotation'],1);self.assertEqual(r['conditional_accuracy_on_retrieved_labeled_gold'],.5);self.assertEqual(r['all_labeled_gold_correct_coverage'],1/3);self.assertEqual(r['balanced_accuracy_on_retrieved_labeled_gold'],.5)
  self.assertIsNone(relation_metrics({'a':'SUPPORT'},{})['balanced_accuracy_on_retrieved_labeled_gold'])
  with self.assertRaises(ValueError):relation_metrics({'a':'NOT_ENOUGH_INFO'},{})

if __name__=='__main__':unittest.main()
