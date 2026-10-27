import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.postings_transform import canonical,parse as strict_parse
from scripts.run_proofwriter_english import run_theory
from scripts import run_proofwriter_english as runner
class EnglishWorkerTests(unittest.TestCase):
 def source(self):return {'id':'owned-English','triples':{'t':{'text':'Mira is warm.','representation':'("Mira" "is" "warm" "+")'}},'rules':{'r':{'text':'All warm people are calm.','representation':'((("someone" "is" "warm" "+")) -> ("someone" "is" "calm" "+"))'}},'questions':{'Q1':{'question':'Mira is calm.','representation':'("Mira" "is" "calm" "+")','answer':True,'QDep':1},'Q2':{'question':'Mira is not calm.','representation':'("Mira" "is" "calm" "-")','answer':False,'QDep':1},'Q3':{'question':'Mira is rough.','representation':'("Mira" "is" "rough" "+")','answer':'Unknown','QDep':0}}}
 def test_English_only_predicts_all_before_formal_reference_gold_and_allclasses(self):
  phase={'predictions_saved':False}
  class Guard(dict):
   def __getitem__(self,key):
    if key in ('representation','answer','QDep') and not phase['predictions_saved']:raise AssertionError('Oracle representation/gold used before predictions saved')
    return super().__getitem__(key)
  def guarded_parse(raw):
   row=strict_parse(raw)
   for field in ('triples','rules','questions'):row[field]={key:Guard(value) for key,value in row[field].items()}
   return row
  def observer(folder,predictions):self.assertTrue((folder/'predictions-before-gold.json').exists());phase['predictions_saved']=True
  with tempfile.TemporaryDirectory() as tmp,patch.object(runner,'parse',side_effect=guarded_parse):
   result=run_theory(canonical(self.source()),Path(tmp),0,gold_observer=observer);self.assertEqual(result['questions'],3);self.assertEqual(sum(r['correct'] for r in result['records']),3);self.assertTrue(result['compilation_audit']['controlled_English_alignment_with_supplied_reference_verified']);self.assertTrue(result['supplied_formal_reference_and_gold_not_used_as_predictor_input']);self.assertEqual(result['recovery']['original_sha256'],result['original_record_sha256'])
 def test_unsupported_allquestions_and_wrong_translation_alignment_stay_denominator(self):
  with tempfile.TemporaryDirectory() as tmp:
   row=self.source();row['triples']['t']['text']='Mira is possibly warm.';result=run_theory(canonical(row),Path(tmp),0);self.assertEqual(result['questions'],3);self.assertTrue(all(not r['correct'] and r['prediction_failure'] for r in result['records']))
   row=self.source();row['triples']['t']['representation']='("Mira" "is" "warm" "-")';result=run_theory(canonical(row),Path(tmp),1);self.assertEqual(result['questions'],3);self.assertIsNotNone(result['compilation_audit_error']);self.assertEqual(sum(r['correct'] for r in result['records']),0);self.assertEqual(result['records'][0]['predicted_label'],'True');self.assertTrue(all(not r['accepted_controlled_English_with_reference_alignment'] for r in result['records']))
if __name__=='__main__':unittest.main()
