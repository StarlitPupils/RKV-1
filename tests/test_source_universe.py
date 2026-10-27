import copy,tempfile,unittest
from pathlib import Path
from rkv1.store import Store
from scripts.source_universe import load_universe
from scripts.audit_source_universe import audit_scope
class UniverseTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir();(self.source/'one.logic.jsonl').write_bytes(b'owned explicit source one\n');(self.source/'two.logic.jsonl').write_bytes(b'owned explicit source two\n');(self.source/'science.txt').write_bytes(b'not an eligible machine axiom source');self.store=Store.create(self.root/'store',compression='zlib');self.sid=self.store.add(self.source)['snapshot_id'];self.paths=['one.logic.jsonl','two.logic.jsonl']
 def test_all_eligible_bytes_exact_budget_and_independent_audit(self):
  n=sum((self.source/p).stat().st_size for p in self.paths);proof,sources=load_universe(self.store,self.sid,self.paths,source_byte_budget=n);self.assertTrue(proof['source_set_complete']);self.assertEqual(set(sources),set(self.paths));self.assertTrue(audit_scope(self.store,self.sid,proof)['source_set_coverage_verified']);self.assertFalse(proof['source_grammar_verified']);self.assertFalse(proof['logical_closure_verified'])
 def test_missing_and_budget_minus_one_abstain_without_source_reads(self):
  from unittest.mock import patch
  from rkv1.store import Snapshot
  # Spy only on application source reads; snapshot metadata reads are outside payload accounting.
  n=sum((self.source/p).stat().st_size for p in self.paths)
  for paths,budget in ((self.paths[:1],n),(self.paths,n-1),(self.paths,0)):
   with patch.object(Snapshot,'read_range',side_effect=AssertionError('Preflight failure must read no source payload')):proof,sources=load_universe(self.store,self.sid,paths,source_byte_budget=budget)
   self.assertFalse(proof['source_set_complete']);self.assertEqual(proof['status'],'incomplete_source_set');self.assertEqual(sources,{});self.assertEqual(proof['source_application_returned_bytes'],0)
 def test_new_file_changes_current_universe_but_oldSID_stays_complete(self):
  old,_=load_universe(self.store,self.sid,self.paths);(self.source/'late.logic.jsonl').write_bytes(b'explicit late counterevidence');new=self.store.add(self.source)['snapshot_id'];current,_=load_universe(self.store,new,self.paths);self.assertFalse(current['source_set_complete']);self.assertEqual(load_universe(self.store,self.sid,self.paths)[0],old);self.assertTrue(audit_scope(self.store,self.sid,old)['source_set_coverage_verified'])
 def test_duplicate_path_invalid_cap_and_malformed_eligible_file_refused(self):
  for paths,b in ((self.paths*2,100),(self.paths,True),(self.paths,-1),(self.paths,1048577),(['../one.logic.jsonl'],100)):
   with self.assertRaises(ValueError):load_universe(self.store,self.sid,paths,source_byte_budget=b)
  (self.source/'INVALID.logic.jsonl').write_bytes(b'x');new=self.store.add(self.source)['snapshot_id']
  with self.assertRaises(ValueError):load_universe(self.store,new,self.paths)
 def test_forged_coverage_sourcehash_paths_crossSID_and_semantic_flags_refused(self):
  original,_=load_universe(self.store,self.sid,self.paths)
  for mode in ('path','hash','source','science','logic','grammar','budget','complete','scope','extra'):
   p=copy.deepcopy(original)
   if mode=='path':p['eligible_paths']=p['eligible_paths'][:1]
   elif mode=='hash':p['source_records'][0]['sha256']='0'*64
   elif mode=='source':p['snapshot_id']='0'*64
   elif mode in ('science','logic','grammar'):p[{'science':'scientific_entailment_verified','logic':'logical_closure_verified','grammar':'source_grammar_verified'}[mode]]=True
   elif mode=='budget':p['source_byte_budget']=0
   elif mode=='scope':p['scope']='All scientific knowledge verified'
   elif mode=='extra':p['injected_answer']='claimed answer'
   else:p['source_set_complete']=False
   with self.assertRaises(ValueError):audit_scope(self.store,self.sid,p)
 def test_path_permutation_canonicalizes_and_empty_or_overcount_is_incomplete(self):
  self.assertEqual(load_universe(self.store,self.sid,self.paths)[0],load_universe(self.store,self.sid,list(reversed(self.paths)))[0]);(self.source/'one.logic.jsonl').unlink();(self.source/'two.logic.jsonl').unlink();empty=self.store.add(self.source)['snapshot_id'];proof,_=load_universe(self.store,empty,[]);self.assertFalse(proof['source_set_complete'])
  for i in range(9):(self.source/('file'+str(i)+'.logic.jsonl')).write_bytes(b'x')
  over=self.store.add(self.source)['snapshot_id'];proof,_=load_universe(self.store,over,['file'+str(i)+'.logic.jsonl' for i in range(9)]);self.assertEqual(proof['reason'],'eligible_file_count_cap')
 def test_fixed36case_plan_has12complete24incomplete_and_late_source(self):
  from scripts.source_universe_fixture import plan,sources
  rows=plan();self.assertEqual(len(rows),36);self.assertEqual(sum(r['expected_complete'] for r in rows),12);self.assertEqual(len({r['id'] for r in rows}),36);self.assertEqual(len(sources(True)),len(sources(False))+1)
  for row in rows:self.assertEqual(row['expected_complete'],len(set(row['paths']))==(3 if row['stage']=='updated' else 2) and row['source_byte_budget']>=row['payload_total_bytes'])
 def test_loader_meter_counts_actual_returns_and_restores_after_exception(self):
  from scripts.run_source_universe import meter
  from rkv1.store import Snapshot
  original=Snapshot.read_range
  with meter() as stats:
   with self.store.snapshot(self.sid) as snap:raw=snap.read_range(self.paths[0])
  self.assertEqual(stats,{'source_read_calls':1,'source_application_returned_bytes':len(raw)});self.assertIs(Snapshot.read_range,original)
  with self.assertRaises(RuntimeError):
   with meter():raise RuntimeError('owned observer cleanup failure')
  self.assertIs(Snapshot.read_range,original)
if __name__=='__main__':unittest.main()
