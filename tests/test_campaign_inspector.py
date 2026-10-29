import unittest,tempfile,json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from scripts.campaign_inspector import inspect,write_report_marker
from scripts.api_intervention import request_body,run_slot
from tests.test_api_intervention import payload
class Checks(unittest.TestCase):
 def test_absent_and_unknown_fixed_budget(self):
  self.assertFalse(inspect('owned-no-such-folder')['model_send_allowed'])
  with self.assertRaises(ValueError):inspect('owned-no-such-folder',1)
 def test_ownedslot_closed_partial_readonly_and_bad_final(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);body=request_body('Owned question',[]);job={'claim_id':'1','condition':'empty'};(p/'slot-00.request-private.json').write_text(json.dumps(body));run_slot(p,0,job,body,[],transport=lambda b:payload('INSUFFICIENT',False));f={'planned_calls':48,'attempted_calls':1,'missing_planned_calls':47,'complete':False};(p/'campaign-final.json').write_text(json.dumps(f));before={x.name:x.read_bytes() for x in p.iterdir()};a=inspect(p);self.assertEqual(a['state'],'closed_incomplete');self.assertFalse(a['model_send_allowed']);self.assertEqual(before,{x.name:x.read_bytes() for x in p.iterdir()});f['missing_planned_calls']=46;(p/'campaign-final.json').write_text(json.dumps(f))
   with self.assertRaises(ValueError):inspect(p)
 def test_duplicate_fields_refused(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'slot-00.reserved.json').write_text('{"index":0,"index":1}')
   with self.assertRaises(ValueError):inspect(p)

 def test_unknown_slot_index_or_suffix_refused(self):
  for name in ('slot-48.reserved.json','slot-00.private','slot-000.result.json'):
   with tempfile.TemporaryDirectory() as t:
    p=Path(t);(p/name).write_bytes(b'{}')
    with self.assertRaises(ValueError):inspect(p)
 def test_report_marker_open_or_unbound_refused(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)
   with self.assertRaises(ValueError):write_report_marker(p)
   (p/'report-identity.json').write_text('{"campaign_identity_sha256":"bad","mechanical_marker_not_scientific_audit":true}')
   with self.assertRaises(ValueError):inspect(p)
 def test_report_only_marker_idempotent_and_tamper_refusal(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);body=request_body('Owned question',[]);job={'claim_id':'1','condition':'empty'};(p/'slot-00.request-private.json').write_text(json.dumps(body));run_slot(p,0,job,body,[],transport=lambda b:payload('INSUFFICIENT',False));(p/'campaign-final.json').write_text(json.dumps({'planned_calls':48,'attempted_calls':1,'missing_planned_calls':47,'complete':False}));self.assertFalse(write_report_marker(p)['already_bound']);before={x.name:x.read_bytes() for x in p.iterdir()};self.assertTrue(write_report_marker(p)['already_bound']);self.assertEqual(before,{x.name:x.read_bytes() for x in p.iterdir()});self.assertEqual(inspect(p)['state'],'closed_incomplete_report_bound');(p/'note').write_bytes(b'new')
   with self.assertRaises(ValueError):inspect(p)

 def test_owned_process_exit_after_response_is_ambiguous_and_no_replay(self):
  import subprocess,sys
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);out=p/'campaign';child=Path.cwd()/'scripts/owned_campaign_exit.py';result=subprocess.run([sys.executable,str(child),'--case','after_response_persist','--out',str(out)],capture_output=True,timeout=15);self.assertEqual(result.returncode,77,result.stderr);a=inspect(out);self.assertEqual(a['state'],'open_ambiguous');self.assertEqual((a['reserved'],a['responses'],a['results']),(1,1,0));self.assertFalse(a['model_send_allowed']);self.assertFalse((p/'child-finally.json').exists());before={x.name:x.read_bytes() for x in out.iterdir()};self.assertEqual(a,inspect(out));self.assertEqual(before,{x.name:x.read_bytes() for x in out.iterdir()})
