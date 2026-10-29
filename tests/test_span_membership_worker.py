import copy,json,sys,unittest,tempfile
from pathlib import Path
from scripts.audit_span_membership import audit_case
class SpanAuditTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from scripts.run_span_membership import execute_case
  cls.temp=tempfile.TemporaryDirectory();cls.folder=Path(cls.temp.name)
  for method in ('retained','ephemeral','bounded','span'):execute_case(cls.folder/method,9,1,method,cls.folder/(method+'.json'),Path(sys.executable),timeout_s=60)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def setUp(self):self.folder=type(self).folder
 def test_four_role_packets_request_identity_and_cache_bounds(self):
  rows=[json.loads((self.folder/(m+'.json')).read_bytes()) for m in ('retained','ephemeral','bounded','span')]
  for row in rows[1:]:self.assertEqual(row['request_sha256'],rows[0]['request_sha256']);self.assertEqual([q['packet_sha256'] for q in row['queries']],[q['packet_sha256'] for q in rows[0]['queries']])
  for row in rows[2:]:self.assertTrue(all(t['max_retained_bound_B']<=65536 for t in row['bounded_cache_trace']))
 def test_all_four_actual_owned_cases_full_source_and_independent_root(self):
  for method in ('retained','ephemeral','bounded','span'):
   r=json.loads((self.folder/(method+'.json')).read_bytes());p=json.loads((self.folder/(method+'.parent.json')).read_bytes());self.assertEqual(audit_case(self.folder/method,r,p),{'fresh_roots':1,'eligible_leaves':9,'files':10,'members':16,'packets':8,'no_owned_preflight_speed_scoring':True})
 def test_five_report_tamper_controls_without_mutating_original_cases(self):
  r=json.loads((self.folder/'span.json').read_bytes());p=json.loads((self.folder/'span.parent.json').read_bytes())
  for label in ('packet','file','control','request','returned'):
   changed=copy.deepcopy(r)
   if label=='packet':changed['queries'][0]['packet_sha256']='0'*64
   if label=='file':changed['all_worker_files_before_finally'].pop(next(iter(changed['all_worker_files_before_finally'])))
   if label=='control':changed['negative_controls']=[]
   if label=='request':changed['request_sha256']='0'*64
   if label=='returned':changed['query_application_returned_B']+=1
   with self.assertRaises(AssertionError):audit_case(self.folder/'span',changed,p)
if __name__=='__main__':unittest.main()
