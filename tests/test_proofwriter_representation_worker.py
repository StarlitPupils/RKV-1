import json,tempfile,unittest
from pathlib import Path
from scripts.postings_transform import canonical
from scripts.run_proofwriter_representation import run_theory
from tests.test_proofwriter_representation import F,R,Q
class WorkerTests(unittest.TestCase):
 def test_real_store_predictions_persist_before_gold_and_all_supported_unsupported_denominators(self):
  row={'id':'owned','triples':{'t':{'representation':F}},'rules':{'r':{'representation':R}},'questions':{'Q1':{'representation':Q,'answer':True,'QDep':1},'Q2':{'representation':Q.replace('"+"','"-"'),'answer':False,'QDep':1},'Q3':{'representation':Q.replace('calm','rough'),'answer':'Unknown','QDep':0},'Q4':{'representation':Q.replace('Mira','bad_name'),'answer':'Unknown','QDep':0}}};seen=[]
  def observe(folder,predictions):
   self.assertTrue((folder/'predictions-before-gold.json').is_file());self.assertEqual(len(predictions),4);self.assertTrue(all((folder/('query-'+str(i)+'-prediction.json')).is_file() for i in range(4)));seen.append(True)
  with tempfile.TemporaryDirectory() as tmp:
   result=run_theory(canonical(row),Path(tmp),0,gold_observer=observe);self.assertTrue(seen);self.assertEqual(result['questions'],4);self.assertEqual(sum(r['correct'] for r in result['records']),3);self.assertEqual(sum(r['accepted_formal_representation_only'] for r in result['records']),3);self.assertEqual(result['records'][3]['prediction_failure'].split(':')[0],'UnsupportedRepresentation');self.assertTrue(result['compilation_audit']['independent_compilation_verified']);self.assertEqual(result['recovery']['original_sha256'],result['original_record_sha256']);self.assertTrue(all(r['scientific_entailment_verified'] is False and r['generated_answer'] is None for r in result['records']))
   row['triples']['t']['representation']='unsupported'
   result=run_theory(canonical(row),Path(tmp),1);self.assertEqual(result['questions'],4);self.assertEqual(sum(r['correct'] for r in result['records']),0);self.assertTrue(all(r['prediction_failure'] is not None for r in result['records']));self.assertIsNone(result['compilation_audit'])
if __name__=='__main__':unittest.main()
