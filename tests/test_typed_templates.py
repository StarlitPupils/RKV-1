import sys,tempfile,unittest,copy
from pathlib import Path
from scripts.typed_templates import train,LearnedCompiler,delex
from rkv1.store import Store
from scripts.postings_transform import canonical,parse
from scripts.audit_human_source_coverage import audit_human_compilation

def row(sentence,representations,rules=None):
 triples={str(i):{'representation':r} for i,r in enumerate(representations)};rules={str(i+len(triples)):{'representation':r} for i,r in enumerate(rules or [])};return {'sentences':{'s':sentence},'triples':triples,'rules':rules,'mappings':{k:'s' for k in [*triples,*rules]}}
def fixture():
 return [row('Ada used to be warm and calm.',['("Ada" "is" "warm" "+")','("Ada" "is" "calm" "+")']),row('Ada sees Bob.',['("Ada" "sees" "Bob" "+")']),row('Bob was not warm.',['("Bob" "is" "warm" "-")']),row('If someone is warm then they are calm.',[],['((("someone" "is" "warm" "+")) -> ("someone" "is" "calm" "+"))']),row('Bob remains very calm.',['("Bob" "is" "calm" "+")'])]
class TemplateTests(unittest.TestCase):
 def setUp(self):self.model,self.control=train(fixture())
 def test_equal_byte_fixed_control_and_detached_training_input(self):
  rows=fixture();before=canonical(rows);a,b=train(rows);self.assertEqual(canonical(rows),before);self.assertEqual(len(canonical(a)),len(canonical(b)));self.assertNotEqual(a['templates'],b['templates'])
 def test_equality_preserving_ordered_entity_slots(self):
  self.assertEqual(delex('Bob sees Ada and Bob.',['Ada','Bob']),('$0 sees $1 and $0.',['Bob','Ada']))
 def test_multifact_source_transfers_only_known_train_entity_and_actual_postaudit(self):
  compiler=LearnedCompiler(self.model,world='OWA');source=row('Bob used to be warm and calm.',['("Bob" "is" "warm" "+")','("Bob" "is" "calm" "+")']);files,mapping=compiler.compile_sentences(source['sentences']);self.assertEqual(len(mapping),2)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);src=root/'source';src.mkdir();(src/'original.json').write_bytes(canonical(source))
   for p,b in files.items():(src/p).write_bytes(b)
   store=Store.create(root/'store',compression='zlib');sid=store.add(src)['snapshot_id'];self.assertTrue(audit_human_compilation(store,sid,mapping,sorted(files),world='OWA')['controlled_English_alignment_with_supplied_reference_verified']);bad=copy.deepcopy(mapping);bad[0]['original_English_sentence_sha256']='0'*64
   with self.assertRaises(ValueError):audit_human_compilation(store,sid,bad,sorted(files),world='OWA')
 def test_direction_negative_and_rule_variables_are_preserved(self):
  c=LearnedCompiler(self.model,world='OWA');forward,_=c.compile_sentences({'s':'Ada sees Bob.'});reverse,_=c.compile_sentences({'s':'Bob sees Ada.'});a=parse(forward['facts.logic.jsonl'])['atom'];b=parse(reverse['facts.logic.jsonl'])['atom'];self.assertEqual(a['arguments'],list(reversed(b['arguments'])));negative,_=c.compile_sentences({'s':'Bob was not warm.'});self.assertFalse(parse(negative['facts.logic.jsonl'])['atom']['positive']);rules,_=c.compile_sentences({'s':'If someone is warm then they are calm.'});r=parse(rules['rules.logic.jsonl']);self.assertEqual(r['head']['arguments'][0],'?v');self.assertEqual(r['premises'][0]['arguments'][0],'?v')
 def test_unknown_entity_phrase_and_ambiguous_supervision_abstain(self):
  c=LearnedCompiler(self.model,world='OWA')
  for sentence in ('Zed used to be warm and calm.','Bob is probably calm.'):
   with self.assertRaises(ValueError):c.compile_sentences({'s':sentence})
  rows=fixture()+[row('Ada sees Bob.',['("Ada" "sees" "Bob" "-")'])];model,_=train(rows);self.assertIn('$0 sees $1.',model['ambiguous_keys'])
  with self.assertRaises(ValueError):LearnedCompiler(model,world='OWA').compile_sentences({'s':'Ada sees Bob.'})
 def test_no_unmentioned_ground_name_is_silently_copied_from_supervision(self):
  rows=fixture()+[row('That person was unusually warm.',['("Ada" "is" "warm" "+")'])];model,_=train(rows);self.assertGreaterEqual(model['statistics']['unrepresentable_training_sentences'],1)
  with self.assertRaises(ValueError):LearnedCompiler(model,world='OWA').compile_sentences({'s':'That person was unusually warm.'})
 def test_model_SHA_loader_rejects_tamper_and_control_has_same_file_B(self):
  from scripts.typed_templates import load_model
  from rkv1.core import digest
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'model.json';raw=canonical(self.model)+b'\n';p.write_bytes(raw);self.assertEqual(load_model(p,digest(raw)),self.model)
   with self.assertRaises(ValueError):load_model(p,'0'*64)
   p.write_bytes(raw+b' ')
   with self.assertRaises(ValueError):load_model(p,digest(raw))
   self.assertEqual(len(raw),len(canonical(self.control)+b'\n'))
 def test_predictor_never_accepts_oracle_fields_and_guarded_full_run(self):
  from unittest.mock import patch
  import scripts.run_human_source_coverage as original
  from scripts.postings_transform import parse as unguarded_parse
  data=fixture()[0];data['id']='owned';data['questions']={'Q1':{'question':'Ada is warm.','representation':'("Ada" "is" "warm" "+")','answer':True},'Q2':{'question':'Ada is not warm.','representation':'("Ada" "is" "warm" "-")','answer':False},'Q3':{'question':'Ada is young.','representation':'("Ada" "is" "young" "+")','answer':'Unknown'}};state={'unlocked':False}
  class Guard(dict):
   def __getitem__(self,k):
    if not state['unlocked'] and k in ('triples','rules','mappings','answer','representation','QDep'):raise AssertionError('Oracle access:'+k)
    return super().__getitem__(k)
   def get(self,k,*a):
    if not state['unlocked'] and k in ('answer','representation','QDep'):raise AssertionError('Oracle get:'+k)
    return super().get(k,*a)
  def parsed(raw):
   row=unguarded_parse(raw);row['questions']={k:Guard(v) for k,v in row['questions'].items()};return Guard(row)
  def unlock(folder,predictions):
   self.assertTrue((folder/'predictions-before-gold.json').exists());self.assertEqual(len(predictions),3);state['unlocked']=True
  old=original.HumanSourceCompiler
  with tempfile.TemporaryDirectory() as tmp,patch.object(original,'parse',side_effect=parsed),patch.object(original,'HumanSourceCompiler',side_effect=lambda *,world:LearnedCompiler(self.model,world=world)):
   result=original.run_theory(canonical(data),Path(tmp),0,method='human',gold_observer=unlock)
  self.assertIs(original.HumanSourceCompiler,old);self.assertTrue(all(x['correct'] for x in result['records']));self.assertTrue(result['compilation_audit']['human_sentence_mappings_used_only_after_predictions'])
 def test_full_owned_worker_loads_model_once_and_baseline_does_not_load_model(self):
  from types import SimpleNamespace
  from unittest.mock import patch
  from scripts import run_typed_templates as runner
  from rkv1.core import digest
  data=fixture()[0];data['id']='owned';data['questions']={'Q1':{'question':'Ada is warm.','representation':'("Ada" "is" "warm" "+")','answer':True},'Q2':{'question':'Ada is not warm.','representation':'("Ada" "is" "warm" "-")','answer':False},'Q3':{'question':'Ada is young.','representation':'("Ada" "is" "young" "+")','answer':'Unknown'}}
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);prefix=root/'prefix.jsonl';raw=(canonical(data)+b'\n')*32;prefix.write_bytes(raw);meta=root/'input.json';meta.write_bytes(canonical({'prefix_path':str(prefix),'prefix_sha256':digest(raw),'prefix_bytes':len(raw)}));model=root/'model.json';mb=canonical(self.model)+b'\n';model.write_bytes(mb);modelmeta=root/'models.json';modelmeta.write_bytes(canonical({'models':{'learned':{'path':str(model),'sha256':digest(mb)}}}));report=root/'learned.json';original=runner.LearnedCompiler;calls=[]
   def factory(*a,**kw):calls.append(True);return original(*a,**kw)
   with patch.object(runner,'LearnedCompiler',side_effect=factory):runner.worker(SimpleNamespace(work=root/'work',input_meta=meta,model_meta=modelmeta,role='learned',round=1,report=report))
   result=parse(report.read_bytes());self.assertEqual(len(calls),1);self.assertEqual(result['correct'],96);self.assertEqual(result['original_recovery_theories'],32)
   baseline=root/'baseline.json'
   with patch.object(runner,'load_model',side_effect=AssertionError('Baseline must notloadmodel')):runner.worker(SimpleNamespace(work=root/'basework',input_meta=meta,model_meta=root/'absent-models.json',role='baseline',round=1,report=baseline))
   self.assertEqual(parse(baseline.read_bytes())['current_loaded_model_bytes'],0)
if __name__=='__main__':unittest.main()
