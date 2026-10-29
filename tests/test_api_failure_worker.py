import unittest,tempfile,json
from pathlib import Path
from scripts.run_api_failure_diagnostic import run
from scripts.api_campaign import run_trial
from scripts.api_intervention import plan,canonical,sha
from scripts.audit_api_intervention import audit
from scripts.scifact_graph import build_model
from rkv1.store import Store
from tests.test_api_intervention import claim,payload
class WorkerTests(unittest.TestCase):
 def test_input_SHA_failure(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);f=p/'old';f.write_bytes(b'a')
   with self.assertRaises(AssertionError):run({'cohorts':[{},{}],'inputs':{str(f):{'bytes':1,'sha256':'0'*64}}},p/'out')
   self.assertFalse(json.loads((p/'out/body-finally.json').read_bytes())['success'])
 def test_owned96fake_original_sources_and_no_remote(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);src=r/'src';src.mkdir();raw=b''.join(canonical({'doc_id':i,'title':'Owned alpha','abstract':['Owned evidence supports alpha.']})+b'\n' for i in range(9));(src/'corpus.jsonl').write_bytes(raw);m,_=build_model(raw,[]);mp=r/'model.json';mp.write_bytes(canonical(m));store=Store.create(r/'store');sid=store.add(src)['snapshot_id'];config={'cohorts':[],'inputs':{}}
   for batch in range(2):
    claims=[claim(i+100*j+1000*batch,l) for j,l in enumerate(('SUPPORT','CONTRADICT','INSUFFICIENT')) for i in range(1,25)];p=plan(claims);by={str(x['id']):x for x in claims};q={i:by[i]['claim'] for i in p['selected_claim_ids']};gold={i:by[i] for i in q};d=r/('draft'+str(batch));d.mkdir();trial=r/('trial'+str(batch));run_trial(store.root,sid,mp,sha(mp.read_bytes()),p,q,trial,transport=lambda body:payload('INSUFFICIENT',False));a=audit(trial,store.root,p,q,gold);prior=r/('prior'+str(batch)+'.json');prior.write_bytes(canonical({'groups':a['groups']}))
    for name,obj in [('plan.json',p),('questions-private.json',[{'claim_id':i,'claim':q[i]} for i in q]),('gold-private.json',list(gold.values())),('retrieval-context-private.json',{'store_root_private':str(store.root)})]:(d/name).write_bytes(canonical(obj))
    config['cohorts'].append({'name':str(batch),'draft':str(d),'campaign':str(trial),'prior_derived':str(prior)})
   result=run(config,r/'out');self.assertEqual(result['old_output_count'],96);self.assertEqual(result['unique_questions'],32);self.assertEqual(result['new_model_calls'],0);self.assertEqual(sum(x['all_rows'] for x in result['groups'].values()),96)
