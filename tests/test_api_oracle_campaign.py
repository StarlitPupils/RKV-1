import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.api_oracle_campaign import run_trial,validate_plan
from scripts.api_intervention import canonical,sha
from scripts.audit_api_oracle import audit
from scripts.scifact_graph import build_model
from rkv1.store import Store
from tests.test_api_intervention import payload
class Checks(unittest.TestCase):
 def fixture_plan(self):
  q={str(i):'Owned alpha '+str(i) for i in range(24)};t={i:['7'] for i in q};p={'selected_claim_ids':list(q),'jobs':[{'claim_id':i,'condition':c,'cohort':'v084' if int(i)<12 else 'v087'} for i in q for c in ('retrieved','oracle')]};return p,q,t
 def test_bad_duplicate_role_and_no_key_create_no_campaign(self):
  p,q,t=self.fixture_plan();p['jobs'][0]=p['jobs'][1].copy()
  with self.assertRaises(ValueError):validate_plan(p,q,t)
  p,q,t=self.fixture_plan()
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'not-created'
   with patch.dict('os.environ',{'RKV_LLM_API_KEY':''}):
    with self.assertRaises(ValueError):run_trial({},p,q,t,out,before_call=lambda:True)
   self.assertFalse(out.exists())
 def test_owned48paired_source_guard_audit_tamper_and_quota_stop(self):
  p,q,t=self.fixture_plan()
  with tempfile.TemporaryDirectory() as tmp:
   r=Path(tmp);src=r/'src';src.mkdir();raw=b''.join(canonical({'doc_id':i,'title':'Owned alpha','abstract':['Owned alpha evidence.']})+b'\n' for i in range(9));(src/'corpus.jsonl').write_bytes(raw);model,_=build_model(raw,[]);mp=r/'model.json';mp.write_bytes(canonical(model));store=Store.create(r/'store');sid=store.add(src)['snapshot_id'];ctx={'store_root_private':str(store.root),'snapshot_id':sid,'model_path_private':str(mp),'model_SHA':sha(mp.read_bytes())};gold={i:{'id':int(i),'claim':q[i],'evidence':{'7':[{'label':'SUPPORT' if int(i)<12 else 'CONTRADICT','sentences':[0]}]}} for i in q};calls=[]
   def fake(body):calls.append(body);return payload('INSUFFICIENT',False)
   original=Path.read_bytes
   def guard(path):
    if 'gold' in path.name:raise AssertionError('Worker read verdict labels')
    return original(path)
   with patch.object(Path,'read_bytes',guard):result=run_trial(ctx,p,q,t,r/'trial',transport=fake)
   self.assertTrue(result['complete']);self.assertEqual(len(calls),48);self.assertEqual(result['new_remote_calls'],0);a=audit(r/'trial',store.root,p,q,gold,model);self.assertTrue(a['H1_mechanical_audit']);self.assertFalse(a['H2_oracle_quality_over_fresh_retrieval']);self.assertEqual(a['groups']['oracle']['planned'],24)
   f=r/'trial/slot-00.result.json';saved=f.read_bytes();bad=json.loads(saved);bad['request_sha256']='0'*64;f.write_text(json.dumps(bad))
   with self.assertRaises(AssertionError):audit(r/'trial',store.root,p,q,gold,model)
   f.write_bytes(saved);limited=run_trial(ctx,p,q,t,r/'limited',transport=fake,before_call=lambda:False);self.assertEqual(limited['attempted_calls'],0);self.assertEqual(limited['missing_planned_calls'],48);self.assertEqual(len(calls),48)
   def timeout(body):raise TimeoutError('owned')
   stopped=run_trial(ctx,p,q,t,r/'stopped',transport=timeout);self.assertEqual(stopped['attempted_calls'],1);self.assertEqual(stopped['missing_planned_calls'],47)
