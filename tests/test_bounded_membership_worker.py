import json,sys,tempfile,unittest
from pathlib import Path
from scripts.run_bounded_membership import execute_case
class BoundedWorkerTests(unittest.TestCase):
 def test_three_methods_real_IPC_same_packets_scope_and_fixed_budget(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for m in ('retained','ephemeral','bounded'):execute_case(root/m,9,1,m,root/(m+'.json'),Path(sys.executable),timeout_s=60)
   reports=[json.loads((root/(m+'.json')).read_bytes()) for m in ('retained','ephemeral','bounded')]
   for r in reports[1:]:self.assertEqual([q['packet_sha256'] for q in r['queries']],[q['packet_sha256'] for q in reports[0]['queries']]);self.assertEqual(r['request_sha256'],reports[0]['request_sha256'])
   for r in reports:self.assertTrue(r['closed_prover_fields_released']);self.assertEqual(len(r['negative_controls']),4)
   c=reports[-1];self.assertEqual(c['bounded_cache_capacity_B'],65536);self.assertEqual(len(c['bounded_cache_trace']),2)
   for s in c['bounded_cache_trace']:self.assertLessEqual(s['max_retained_bound_B'],65536)
