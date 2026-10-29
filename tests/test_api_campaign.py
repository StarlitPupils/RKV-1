import json,sys,tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
from scripts.api_campaign import run_trial,validate_inputs
from scripts.api_intervention import plan,canonical,sha
from tests.test_api_intervention import claim,payload
from scripts.scifact_graph import build_model
from rkv1.store import Store
class CampaignTests(unittest.TestCase):
 def test_owned48responses_gold_read_guard_original_Store_and_durable_failures(self):
  claims=[claim(i+100*j,l) for j,l in enumerate(('SUPPORT','CONTRADICT','INSUFFICIENT')) for i in range(1,25)];p=plan(claims);byid={str(c['id']):c['claim'] for c in claims};questions={i:byid[i] for i in p['selected_claim_ids']}
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);src=root/'src';src.mkdir();raw=b''.join(canonical({'doc_id':i,'title':'Owned alpha','abstract':['Owned evidence supports synthetic alpha.']})+b'\n' for i in range(9));(src/'corpus.jsonl').write_bytes(raw);model,_=build_model(raw,[]);modelraw=canonical(model);mp=root/'model.json';mp.write_bytes(modelraw);store=Store.create(root/'store');sid=store.add(src)['snapshot_id'];calls=[]
   def transport(body):calls.append(body);return payload('INSUFFICIENT',False)
   original=Path.read_bytes
   def guard(path):
    if 'gold' in path.name:raise AssertionError('Inference accessed labels')
    return original(path)
   with patch.object(Path,'read_bytes',guard):result=run_trial(store.root,sid,mp,sha(modelraw),p,questions,root/'trial',transport=transport)
   from scripts.audit_api_intervention import audit
   gold={str(c['id']):c for c in claims if str(c['id']) in questions};a=audit(root/'trial',store.root,p,questions,gold);self.assertTrue(a['H1_mechanical_audit']);self.assertFalse(a['H2_retrieved_quality_over_both_controls']);self.assertEqual(a['groups']['retrieved']['correct'],4);self.assertEqual(len(a['rows']),48)
   record=root/'trial/slot-00.result.json';saved=record.read_bytes();bad=json.loads(saved);bad['request_sha256']='0'*64;record.write_text(json.dumps(bad))
   with self.assertRaises(AssertionError):audit(root/'trial',store.root,p,questions,gold)
   record.write_bytes(saved)
   self.assertTrue(result['complete']);self.assertEqual(len(calls),48);self.assertEqual(result['new_remote_calls'],0);self.assertEqual(len(list((root/'trial').glob('*.reserved.json'))),48)
   requests=[json.loads(f.read_bytes()) for f in (root/'trial').glob('*.request-private.json')];self.assertTrue(all('gold' not in canonical(b).decode() for b in requests));self.assertEqual(sum(not json.loads(b['messages'][1]['content'])['evidence'] for b in requests),16)
   def broken(body):raise TimeoutError('private transport detail')
   limited=run_trial(store.root,sid,mp,sha(modelraw),p,questions,root/'limited',transport=transport,before_call=lambda:False);self.assertEqual(limited['attempted_calls'],0);self.assertEqual(limited['missing_planned_calls'],48);self.assertFalse(list((root/'limited').glob('*.reserved.json')));partial=audit(root/'limited',store.root,p,questions,gold);self.assertFalse(partial['complete']);self.assertFalse(partial['H2_retrieved_quality_over_both_controls'])
   stopped=run_trial(store.root,sid,mp,sha(modelraw),p,questions,root/'stopped',transport=broken);self.assertFalse(stopped['complete']);self.assertEqual(stopped['attempted_calls'],1);self.assertEqual(stopped['missing_planned_calls'],47)
 def test_bad_conditions_and_key_missing_create_no_trial(self):
  with self.assertRaises(ValueError):validate_inputs({'jobs':[],'selected_claim_ids':[]},{})
  rows=[claim(i+100*j,l) for j,l in enumerate(('SUPPORT','CONTRADICT','INSUFFICIENT')) for i in range(1,25)];p=plan(rows);byid={str(c['id']):c['claim'] for c in rows};questions={i:byid[i] for i in p['selected_claim_ids']}
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'not-created'
   with patch.dict(os.environ,{'RKV_LLM_API_KEY':''}):
    with self.assertRaises(ValueError):run_trial(Path(tmp)/'unused-store','a'*64,Path(tmp)/'unused-model','b'*64,p,questions,out,before_call=lambda:True)
   self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
