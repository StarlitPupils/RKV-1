import json,sys,tempfile,unittest
from pathlib import Path
from scripts.run_late_membership import execute_case
class LateWorkerTests(unittest.TestCase):
 def test_actual_parent_after_ready_eight_requests_and_exact_two_methods(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for method in ('retained','ephemeral'):execute_case(root/method,9,1,method,root/(method+'.json'),Path(sys.executable),timeout_s=60)
   a=json.loads((root/'retained.json').read_bytes());b=json.loads((root/'ephemeral.json').read_bytes());self.assertEqual([q['packet_sha256'] for q in a['queries']],[q['packet_sha256'] for q in b['queries']]);self.assertEqual(a['request_sha256'],b['request_sha256'])
   for method in ('retained','ephemeral'):
    r=json.loads((root/(method+'.json')).read_bytes());self.assertEqual(len(r['negative_controls']),4);self.assertTrue(r['constructor_completed_before_requests_generated']);self.assertTrue(r['closed_prover_fields_released']);self.assertIsNone(json.loads((root/(method+'.parent.json')).read_bytes())['error']);self.assertTrue(json.loads((root/method/'finally-timing.json').read_bytes())['success'])
