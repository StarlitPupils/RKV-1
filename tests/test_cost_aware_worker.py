import sys,json,hashlib,tempfile,unittest,subprocess,time
from pathlib import Path
from unittest.mock import patch
from scripts.run_cost_aware_sources import run,query,canonical
from scripts.scifact_graph import build_model
from rkv1.store import Store
from rkv1.experiments.paper_retriever import PaperRetriever
class Workers(unittest.TestCase):
 def fixture(self,root):
  src=root/'src';src.mkdir();raw=b''.join(canonical({'doc_id':i,'title':'Owned alpha beta','abstract':['alpha '*(3+i*7)+' beta gamma evidence.']})+b'\n' for i in range(9));(src/'corpus.jsonl').write_bytes(raw);model,_=build_model(raw,[]);mr=canonical(model);mp=root/'model.json';mp.write_bytes(mr);store=Store.create(root/'store');sid=store.add(src)['snapshot_id'];return store,{'store_root_private':str(store.root),'snapshot_id':sid,'model_path_private':str(mp),'model_SHA':hashlib.sha256(mr).hexdigest()}
 def test_owned_all_three_roles_real_Store_source_proof_and_gold_read_guard(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);store,ctx=self.fixture(root);questions=[{'claim_id':str(i),'claim':q} for i,q in enumerate(['alpha','beta gamma','unknownword'])];old=Path.read_bytes
   def guarded(path):
    if 'gold' in path.name:raise AssertionError('Prediction read labels')
    return old(path)
   with patch.object(Path,'read_bytes',guarded):
    reports=[run(ctx,questions,m,root/m) for m in ('lexical','score_per_byte','length_only')]
   for r in reports:
    self.assertEqual(r['new_model_calls'],0);self.assertEqual(len(r['rows']),3);self.assertLessEqual(r['algorithm_phase_wall_s'],json.loads((root/r['method']/'finally-timing.json').read_bytes())['worker_full_wall_s'])
    with store.snapshot(ctx['snapshot_id']) as snap:
     for i in range(3):
      p=json.loads((root/r['method']/('query-'+str(i).zfill(3)+'.json')).read_bytes());self.assertLessEqual(p['admitted_record_B'],4096)
      for h in p['source_proof']:
       loc=h['locator'];raw=snap.read_range(loc['path'],loc['offset'],loc['length']);obj=json.loads(raw);self.assertEqual(hashlib.sha256(raw).hexdigest(),loc['sha256']);self.assertEqual(hashlib.sha256(canonical(obj['abstract'])).hexdigest(),h['abstract_sha256'])
   from scripts.audit_cost_aware_sources import audit_prediction
   model=json.loads(Path(ctx['model_path_private']).read_bytes())
   with store.snapshot(ctx['snapshot_id']) as snap:
    for method in ('lexical','score_per_byte','length_only'):
     row=json.loads((root/method/'query-000.json').read_bytes());self.assertGreater(audit_prediction(snap,model,'alpha',method,row)['source_bindings'],0);bad=json.loads(json.dumps(row));bad['admitted_record_B']+=1
     with self.assertRaises(AssertionError):audit_prediction(snap,model,'alpha',method,bad)
   api=PaperRetriever(store.root,ctx['snapshot_id'],ctx['model_path_private'],model_sha256=ctx['model_SHA']);self.assertEqual(reports[0]['rows'][0]['selected_ids'],api.query('alpha')['selected_ids'])
 def test_duplicate_ids_reject_before_output_and_damage_not_hidden(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);store,ctx=self.fixture(root)
   with self.assertRaises(ValueError):run(ctx,[{'claim_id':'1','claim':'alpha'}]*2,'score_per_byte',root/'bad')
   self.assertFalse((root/'bad').exists())
   with store.snapshot(ctx['snapshot_id']) as snap:key=snap.files['corpus.jsonl']['chunks'][0]['id']
   p=store.object_path(key);b=p.read_bytes();p.write_bytes(b[:-1]+bytes([b[-1]^1]))
   with self.assertRaises(ValueError):run(ctx,[{'claim_id':'1','claim':'alpha'}],'score_per_byte',root/'damaged')
   self.assertFalse(json.loads((root/'damaged/finally-timing.json').read_bytes())['success'])
 def test_fresh_owned_worker_process_input_and_parent_timers(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);store,ctx=self.fixture(root);context=root/'context.json';context.write_text(json.dumps(ctx));questions=root/'questions.json';questions.write_text(json.dumps([{'claim_id':'1','claim':'alpha'}]));out=root/'child';start=time.perf_counter();result=subprocess.run([sys.executable,str(Path.cwd()/'scripts/run_cost_aware_sources.py'),'--context',str(context),'--questions',str(questions),'--method','score_per_byte','--out',str(out)],capture_output=True);parent=time.perf_counter()-start;self.assertEqual(result.returncode,0,result.stderr.decode());body=json.loads((out/'finally-timing.json').read_bytes());process=json.loads((out/'process-finally.json').read_bytes());self.assertTrue(process['success']);self.assertLessEqual(body['worker_full_wall_s'],process['process_entry_to_finally_wall_s']);self.assertLessEqual(process['process_entry_to_finally_wall_s'],parent)
if __name__=='__main__':unittest.main()
