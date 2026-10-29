import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from scripts.audit_api_admission_case import audit_case
from scripts.scifact_graph import build_model
from rkv1.store import Store
from rkv1.experiments.paper_retriever import PaperRetriever
class Cases(unittest.TestCase):
 def test_actual_owned_Store_proofs_and_tamper_refusal(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);src=root/'src';src.mkdir();raw=b''.join(json.dumps({'doc_id':i,'title':'Owned alpha','abstract':['alpha beta evidence.']}).encode()+b'\n' for i in range(9));(src/'corpus.jsonl').write_bytes(raw);model,_=build_model(raw,[]);mr=json.dumps(model).encode();mp=root/'model.json';mp.write_bytes(mr);store=Store.create(root/'store');sid=store.add(src)['snapshot_id'];api=PaperRetriever(store.root,sid,mp,model_sha256=hashlib.sha256(mr).hexdigest());actual=api.query('alpha',method='lexical');hits=[{'key':h['paper_id'],'title':h['title'],'sentences':h['abstract'],'locator':h['locator'],'source_bytes_verified':True} for h in actual['hits']]
   with store.snapshot(sid) as snapshot:
    out=audit_case(snapshot,model['shared'],'alpha',{'doc:0'},hits);self.assertEqual(out['gold_events']['doc:0']['category'],'recovered');self.assertEqual(out['original_record_checks'],9)
    for kind in ('order','SHA','title'):
     changed=copy.deepcopy(hits)
     if kind=='order':changed.reverse()
     if kind=='SHA':changed[0]['locator']['sha256']='0'*64
     if kind=='title':changed[0]['title']='Unbound'
     with self.assertRaises(AssertionError):audit_case(snapshot,model['shared'],'alpha',{'doc:0'},changed)
if __name__=='__main__':unittest.main()
