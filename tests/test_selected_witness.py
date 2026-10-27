import copy,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from rkv1.store import Store,Snapshot
from scripts.source_set_fixture import sources
from scripts.logic_fixture import literal,encode,fact,rule
from scripts.selected_witness import Witness
from scripts.audit_selected_witness import audit
class SelectedWitnessTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.src=self.root/'source';self.src.mkdir()
  data=sources()
  for i in range(7):data['filler'+str(i)+'.logic.jsonl']=encode([fact('same','dummy','a','b')])
  data['opposite.logic.jsonl']=encode([fact('same','reach','a','c',False)])
  for n,b in data.items():(self.src/n).write_bytes(b)
  self.store=Store.create(self.root/'store',compression='zlib');self.sid=self.store.add(self.src)['snapshot_id'];self.paths=['one.logic.jsonl','two.logic.jsonl'];self.size=sum(len(data[p]) for p in self.paths);self.q=literal('reach','a','c')
 def engine(self,paths=None,budget=None):return Witness(self.store,self.sid,paths or self.paths,source_byte_budget=self.size if budget is None else budget)
 def check(self,c):return audit(self.store,self.sid,c)
 def test_more_than_eight_universe_sources_small_selection_original_DAG(self):
  c=self.engine().infer(self.q,work_budget=100000);self.assertGreater(len(c['selection']['eligible_paths']),8);self.assertTrue(c['support_evidence_found']);self.assertFalse(c['opposite_evidence_found']);self.assertFalse(c['selection']['full_eligible_selection']);self.assertIsNone(c['global_verdict']);self.assertTrue(self.check(c)['original_selected_DAG_verified'])
 def test_selected_expansion_keeps_positive_witness_and_finds_opposite(self):
  c=self.engine().infer(self.q,work_budget=100000);paths=self.paths+['opposite.logic.jsonl'];size=self.size+(self.src/'opposite.logic.jsonl').stat().st_size;expanded=self.engine(paths,size).infer(self.q,work_budget=100000);self.assertTrue(c['support_evidence_found'] and expanded['support_evidence_found'] and expanded['opposite_evidence_found']);self.assertIsNone(expanded['global_verdict']);self.check(expanded)
 def test_original_store_unselected_payload_never_read(self):
  original=Snapshot.read_range;seen=[]
  def read(s,path,*a,**kw):
   self.assertIn(path,self.paths);seen.append(path);return original(s,path,*a,**kw)
  with patch.object(Snapshot,'read_range',read):c=self.engine().infer(self.q,work_budget=100000);self.check(c)
  self.assertEqual(set(seen),set(self.paths))
 def test_budget_rejects_before_payload_not_fake_unknown(self):
  with patch.object(Snapshot,'read_range',side_effect=AssertionError('No reads')):
   with self.assertRaises(ValueError):self.engine(budget=self.size-1)
 def test_workzero_keeps_ground_fact_sound_no_global_unknown(self):
  c=self.engine().infer(literal('edge','a','b'),work_budget=0);self.assertTrue(c['support_evidence_found']);self.assertFalse(c['selected_closure_complete']);self.assertIsNone(c['global_verdict']);self.assertFalse(self.check(c)['selected_closure_verified'])
 def test_missing_premise_is_not_global_false_or_unknown(self):
  c=self.engine(['two.logic.jsonl'],self.size).infer(self.q,work_budget=100000);self.assertFalse(c['support_evidence_found']);self.assertFalse(c['opposite_evidence_found']);self.assertTrue(c['selected_closure_complete']);self.assertIsNone(c['global_verdict']);self.check(c)
 def test_forged_global_scope_DAG_and_flags_refused(self):
  c=self.engine().infer(self.q,work_budget=100000)
  for edit in ('global','universe','sha','path','flag','complete','extra'):
   bad=copy.deepcopy(c)
   if edit=='global':bad['global_verdict']='supported'
   elif edit=='universe':bad['selection']['eligible_paths']=self.paths
   elif edit=='sha':bad['nodes'][0]['citation']['sha256']='0'*64
   elif edit=='path':bad['nodes'][0]['citation']['path']='opposite.logic.jsonl'
   elif edit=='flag':bad['opposite_evidence_found']=True
   elif edit=='complete':bad['selection']['full_eligible_selection']=True
   else:bad['verdict']='unknown'
   with self.assertRaises(ValueError,msg=edit):self.check(bad)
 def test_oldSID_unchanged_after_new_HEAD(self):
  before=self.engine().infer(self.q,work_budget=100000);(self.src/'one.logic.jsonl').write_bytes(encode([fact('same','edge','c','b')]))
  new=self.store.add(self.src)['snapshot_id'];self.assertNotEqual(new,self.sid);self.assertEqual(before,self.engine().infer(self.q,work_budget=100000));self.check(before)

 def test_wrongSID_and_workzero_false_closure_refused(self):
  c=self.engine().infer(self.q,work_budget=0)
  with self.assertRaises(ValueError):
   from scripts.audit_selected_witness import audit
   audit(self.store,'invalid-sid',c)
  self.assertFalse(c['selected_closure_complete']);c['selected_closure_complete']=True
  with self.assertRaises(ValueError):self.check(c)

 def test_bad_selections_and_budget_types_have_no_payload_reads(self):
  cases=[([],self.size),(self.paths*2,self.size),(['../one.logic.jsonl'],self.size),(['missing.logic.jsonl'],self.size),(self.paths,True),(self.paths,-1),(self.paths,1048577),(self.paths,0)]
  with patch.object(Snapshot,'read_range',side_effect=AssertionError('No payload')):
   for paths,b in cases:
    with self.assertRaises(ValueError,msg=str((paths,b))):Witness(self.store,self.sid,paths,source_byte_budget=b)

 def test_combined_record_and_rule_caps_are_not_perfile(self):
  for records in ([fact('f'+str(i),'edge','a','b') for i in range(513)],[rule('r'+str(i),literal('reach','?x','?y'),literal('edge','?x','?y')) for i in range(33)]):
   for p in self.paths:(self.src/p).write_bytes(encode(records))
   sid=self.store.add(self.src)['snapshot_id']
   with self.assertRaisesRegex(ValueError,'Combined'):Witness(self.store,sid,self.paths)

 def test_actual_selected_source_byte_substitution_refused(self):
  c=self.engine().infer(self.q,work_budget=100000);original=Snapshot.read_range
  def altered(s,path,*a,**kw):
   raw=original(s,path,*a,**kw)
   return raw.replace(b'"positive":true',b'"positive":false',1) if path=='one.logic.jsonl' else raw
  with patch.object(Snapshot,'read_range',altered):
   with self.assertRaises(ValueError):self.check(c)

 def test_malformed_other_eligible_metadata_refuses_before_selected_payload(self):
  (self.src/'BAD.logic.jsonl').write_bytes(encode([fact('f','edge','a','b')]))
  sid=self.store.add(self.src)['snapshot_id']
  with patch.object(Snapshot,'read_range',side_effect=AssertionError('No payload')):
   with self.assertRaises(ValueError):Witness(self.store,sid,self.paths)

 def test_same_length_original_source_substitution_refused(self):
  c=self.engine().infer(self.q,work_budget=100000);original=Snapshot.read_range;changed=[]
  def altered(s,path,*a,**kw):
   raw=original(s,path,*a,**kw)
   if path=='one.logic.jsonl':
    replaced=raw.replace(b'"a"',b'"z"',1);self.assertEqual(len(replaced),len(raw));changed.append(replaced!=raw);return replaced
   return raw
  with patch.object(Snapshot,'read_range',altered):
   with self.assertRaises(ValueError):self.check(c)
  self.assertTrue(any(changed))

 def test_actual_producer_and_auditor_returned_byte_conservation(self):
  original=Snapshot.read_range;reads=[]
  def counted(s,path,*a,**kw):
   raw=original(s,path,*a,**kw);self.assertIn(path,self.paths);reads.append((path,len(raw)));return raw
  with patch.object(Snapshot,'read_range',counted):
   c=self.engine().infer(self.q,work_budget=100000);cut=len(reads);self.assertEqual(sum(n for _,n in reads),self.size);a=self.check(c)
  self.assertEqual(a['auditor_selected_source_application_returned_bytes'],sum(n for _,n in reads[cut:]));self.assertGreater(a['auditor_selected_source_application_returned_bytes'],self.size)
