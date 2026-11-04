import json,tempfile,unittest
from pathlib import Path
from scripts.execution_receipts import create,append,inspect,encoded,sha,exclusive
from scripts.run_receipt_matrix import run

class ReceiptObservabilityTests(unittest.TestCase):
 def test_process_exit_requires_external_bound_witness(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'case';anchor=create(p,'owned',['one'])
   append(p,anchor,'one','reserved');append(p,anchor,'one','started')
   exclusive(p/'artifacts'/'one.bin',b'x');append(p,anchor,'one','artifact_verified',artifact={'bytes':1,'sha256':sha(b'x')});append(p,anchor,'one','stage_completed')
   self.assertFalse(inspect(p,anchor)['campaign_complete'])
   w=Path(td)/'w.json';v={'schema':1,'run_id':'owned','plan_SHA':anchor,'events_SHA':sha((p/'events.jsonl').read_bytes()),'child_pid':1,'observed_exit_code':False};exclusive(w,encoded(v))
   with self.assertRaises(ValueError):inspect(p,anchor,witness_path=w,expected_witness_SHA=sha(w.read_bytes()))
   v['observed_exit_code']=0;v['run_id']='other';w.write_bytes(encoded(v))
   with self.assertRaises(ValueError):inspect(p,anchor,witness_path=w,expected_witness_SHA=sha(w.read_bytes()))
 def test_invalid_append_preserves_failure_lock(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'case';anchor=create(p,'owned',['one','two'])
   with self.assertRaises(ValueError):append(p,anchor,'two','reserved')
   self.assertEqual((p/'events.jsonl').read_bytes(),b'');self.assertTrue((p/'writer.lock').exists())
   with self.assertRaises(FileExistsError):append(p,anchor,'one','reserved')
   self.assertFalse(inspect(p,anchor)['automatic_replay_permitted'])
 def test_plan_schema_and_truncated_log_refuse(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'case'
   with self.assertRaises(ValueError):create(p,'owned',['../bad'])
   self.assertFalse(p.exists());anchor=create(p,'owned',['one'])
   (p/'events.jsonl').write_bytes(b'{')
   with self.assertRaises(ValueError):inspect(p,anchor)
 def test_twelve_fresh_children_and_fifteen_corruption_controls(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'matrix';run(p);v=json.loads((p/'summary.json').read_bytes())
   self.assertEqual(v['completed_owned_cases'],12);self.assertEqual(len(v['corruption_and_stale_lock_controls']),15)
   self.assertEqual(sum(r['inspection']['campaign_complete'] for r in v['rows']),1)
   self.assertEqual(v['actual_OS_kill_cases'],2)
