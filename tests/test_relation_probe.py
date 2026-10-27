import copy,hashlib,json,math,unittest
from scripts.relation_probe import features,words,labeled_pairs,fit,majority,RelationProbe,gradient,objective,DIMENSION,PARAMETERS
from scripts.evidence_retrieval import encoded

class RelationProbeTests(unittest.TestCase):
 def examples(self):return [{'claim':claim,'document':document,'target':y} for claim,document,y in [('alpha effect improves','alpha effect improves',1),('beta effect improves','beta effect improves',1),('alpha effect never improves','alpha effect improves',0),('beta effect never improves','beta effect improves',0)]]
 def test_hashed_channels_norm_negation_overlap_bias_and_order(self):
  x=features('alpha beta beta not','beta alpha');self.assertEqual(x,features('not beta alpha beta','alpha beta'));self.assertEqual(len(x),389)
  for start in (0,128,256):self.assertAlmostEqual(sum(v*v for v in x[start:start+128]),1.)
  self.assertEqual(x[384:],[1.,0.,1.,2/3,1.]);self.assertEqual(features('','')[388],1.)
  with self.assertRaises(ValueError):features(None,'alpha')
 def test_claim_only_ignores_document_and_both_source_channels(self):
  x=features('alpha not','alpha not',claim_only=True);self.assertEqual(x,features('alpha not','unrelated changed document',claim_only=True));self.assertTrue(all(v==0 for v in x[128:384]));self.assertEqual(x[385:388],[0.,0.,0.])
 def test_gradient_agrees_with_independent_finite_difference(self):
  matrix=[features('alpha','alpha'),features('alpha not','alpha')];labels=[1,0];weights=[.001*(i%5) for i in range(DIMENSION)];g=gradient(matrix,labels,weights)
  for i in (0,128,256,384,386,388):
   plus=list(weights);minus=list(weights);plus[i]+=1e-6;minus[i]-=1e-6;numeric=(objective(matrix,labels,plus)-objective(matrix,labels,minus))/2e-6;self.assertAlmostEqual(g[i],numeric,places=7)
 def test_fixed_training_determinism_and_no_verification_or_generated_answer(self):
  examples=self.examples();model,cost=fit(examples,'pair');again,cost2=fit(examples,'pair');self.assertEqual(model,again);self.assertEqual(cost,cost2);raw=encoded(model);probe=RelationProbe(raw,sha256=hashlib.sha256(raw).hexdigest())
  self.assertEqual([probe.predict(e['claim'],e['document'])['predicted_relation'] for e in examples],['SUPPORT','SUPPORT','CONTRADICT','CONTRADICT'])
  r=probe.predict('alpha','alpha');self.assertFalse(r['scientific_entailment_verified']);self.assertIsNone(r['generated_answer']);self.assertTrue(0<=r['support_score_uncalibrated']<=1)
  model['parameters']['epochs']=99;self.assertEqual(PARAMETERS['epochs'],200)
 def test_label_shuffle_preserves_marginal_and_majority_has_no_weights(self):
  examples=self.examples();_,cost=fit(examples,'permuted_pair');self.assertEqual(cost['class_counts_preserved_by_shuffle'],{'CONTRADICT':2,'SUPPORT':2});self.assertIsNotNone(cost['permuted_label_positions_changed'])
  model=majority(examples);self.assertIsNone(model['weights']);raw=encoded(model);probe=RelationProbe(raw,sha256=hashlib.sha256(raw).hexdigest());self.assertEqual(probe.predict('alpha','changed')['predicted_relation'],'SUPPORT')
 def test_wrong_model_SHA_nonfinite_weights_parameters_and_one_class_refused(self):
  model=majority(self.examples());raw=encoded(model)
  with self.assertRaises(ValueError):RelationProbe(raw,sha256='0'*64)
  for change in ('method','parameters','weights','classes'):
   bad=copy.deepcopy(model)
   if change=='method':bad['method']='oracle'
   elif change=='parameters':bad['parameters']['epochs']=199
   elif change=='weights':bad['method']='pair';bad['weights']=[math.nan]*389
   else:bad['training_class_counts']['SUPPORT']=0
   raw=encoded(bad)
   with self.assertRaises(ValueError):RelationProbe(raw,sha256=hashlib.sha256(raw).hexdigest())
  with self.assertRaises(ValueError):fit([{'claim':'alpha','document':'alpha','target':1}],'pair')
 def test_explicit_labels_duplicate_group_conflict_and_no_gold_unknown(self):
  papers={'doc:1':{'sentences':['alpha'], 'projection':'alpha'}}
  def row(id,claim,evidence):return {'id':id,'claim':claim,'evidence':evidence}
  def ev(label):return {'1':[{'sentences':[0],'label':label}]}
  examples,cost=labeled_pairs([row(1,'Alpha',ev('SUPPORT')),row(2,' alpha ',ev('SUPPORT')),row(3,'unknown',{}),row(4,'conflicting',ev('SUPPORT')),row(5,'conflicting',ev('CONTRADICT'))],papers)
  self.assertEqual(len(examples),1);self.assertEqual(examples[0]['target'],1);self.assertEqual(cost['unannotated_rows'],1);self.assertEqual(cost['ambiguous_unique_pairs'],1);self.assertEqual(examples[0]['original_claim_ids'],['1','2'])
  with self.assertRaises(ValueError):labeled_pairs([row(6,'alpha',ev('NOT_ENOUGH_INFO'))],papers)
  with self.assertRaises(ValueError):labeled_pairs([row(7,'alpha',{'1':[{'sentences':[True],'label':'SUPPORT'}]})],papers)

if __name__=='__main__':unittest.main()
