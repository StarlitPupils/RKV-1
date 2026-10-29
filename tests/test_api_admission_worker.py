import json,hashlib,tempfile,unittest
from pathlib import Path
from scripts.run_api_admission_audit import run,canonical
from scripts.scifact_graph import build_model
from rkv1.store import Store
from rkv1.experiments.paper_retriever import PaperRetriever
class WorkerTests(unittest.TestCase):
 def test_owned16query_worker_full_source_and_missing_zero_kept_null(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);src=root/'src';src.mkdir();raw=b''.join(canonical({'doc_id':i,'title':'Owned alpha','abstract':['Owned alpha beta evidence.']})+b'\n' for i in range(9));(src/'corpus.jsonl').write_bytes(raw);model,_=build_model(raw,[]);mr=canonical(model);mp=root/'model.json';mp.write_bytes(mr);store=Store.create(root/'store');sid=store.add(src)['snapshot_id'];api=PaperRetriever(store.root,sid,mp,model_sha256=hashlib.sha256(mr).hexdigest());actual=api.query('alpha',method='lexical');h=[{'key':x['paper_id'],'title':x['title'],'sentences':x['abstract'],'locator':x['locator'],'source_bytes_verified':True} for x in actual['hits']];questions={str(i):'alpha' for i in range(16)};gold={i:{'id':int(i),'claim':'alpha','evidence':{'0':[{'label':'SUPPORT','sentences':[0]}]} if int(i)<12 else {}} for i in questions};hits={i:h for i in questions};ctx={'store_root_private':str(store.root),'snapshot_id':sid,'model_path_private':str(mp),'model_SHA':hashlib.sha256(mr).hexdigest(),'model_B':len(mr),'source_B':len(raw),'source_sha256':hashlib.sha256(raw).hexdigest()};expected={'queries':16,'old_selected_record_bindings':144,'annotated_gold_papers':12,'old_missing_gold_papers':0};report=run(ctx,questions,gold,hits,expected,root/'out');self.assertTrue(report['H1_exact_order_ids_source_and_metadata']);self.assertIsNone(report['H2_missing_self_oversize_strict_majority']);self.assertEqual(report['original_record_read_bindings'],144);self.assertTrue(json.loads((root/'out/finally-timing.json').read_bytes())['success'])
   with self.assertRaises(FileExistsError):run(ctx,questions,gold,hits,expected,root/'out')
if __name__=='__main__':unittest.main()
