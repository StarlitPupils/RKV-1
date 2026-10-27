import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from rkv1.core import digest
from rkv1.store import Store
from scripts.scifact_graph import build_model,encoded
from scripts.sentence_index import build_index

class SentenceParentWorkerTests(unittest.TestCase):
    def test_three_real_workers_source_proofs_hint_and_overlap_exclusion(self):
        source=b''.join(json.dumps({'doc_id':i,'title':'source title','abstract':['alpha beta','gamma delta']}).encode()+b'\n' for i in (1,2))
        train=[{'id':9,'claim':'seen training claim','evidence':{}}];paper,_=build_model(source,train);paper_raw=encoded(paper);index,_=build_index(source,paper);index_raw=encoded(index)
        claims=[{'id':1,'claim':'alpha beta','evidence':{'1':[{'sentences':[0],'label':'SUPPORT'}]}},
            {'id':2,'claim':'delta','evidence':{}},{'id':9,'claim':'excluded by training ID','evidence':{}}]
        dev=b''.join(encoded(c)+b'\n' for c in claims)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inputs=root/'inputs';inputs.mkdir();(inputs/'corpus.jsonl').write_bytes(source);(inputs/'claims_dev.jsonl').write_bytes(dev)
            (root/'paper.json').write_bytes(paper_raw);(root/'index.json').write_bytes(index_raw)
            reference=Store.create(root/'reference-store',compression='zlib',chunk_size=65536,io_backend='bounded');src=root/'source';src.mkdir();(src/'corpus.jsonl').write_bytes(source)
            sid=reference.add(src,label='scifact-graph-transfer')['snapshot_id']
            manifest={'files':{'corpus.jsonl':{'sha256':digest(source)},'claims_dev.jsonl':{'sha256':digest(dev)}},'paper_model_sha256':digest(paper_raw),'expected_source_snapshot_id':sid}
            (root/'manifest.json').write_bytes(encoded(manifest));(root/'freeze.json').write_bytes(encoded({'source_sha256':digest(source),'paper_model_sha256':digest(paper_raw),'sentence_index_sha256':digest(index_raw)}))
            for method in ('paper_lexical','paper_graph','sentence_max'):
                output=root/(method+'.json');args=[sys.executable,'-m','scripts.run_sentence_parent','--inputs',str(inputs),'--model',str(root/'paper.json'),'--index',str(root/'index.json'),'--index-freeze',str(root/'freeze.json'),'--manifest',str(root/'manifest.json'),'--work',str(root/method),'--round','1','--method',method,'--worker-report',str(output)]
                result=subprocess.run(args,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr);d=json.loads(output.read_bytes())
                self.assertEqual(d['retrieved_rows'],2);self.assertEqual(d['annotated_rows'],1);self.assertEqual(d['unannotated_rows'],1);self.assertEqual(len(d['excluded']),1)
                self.assertTrue(d['store_unchanged']);self.assertTrue(d['full_source_recovery']['source_SHA_match'])
                annotated=next(r for r in d['records'] if r['paper_metrics'] is not None);self.assertTrue(annotated['paper_metrics']['complete_coverage'])
                if method=='sentence_max':self.assertEqual(annotated['hint_metrics']['rate'],1);self.assertGreater(d['model_load']['sentence_index_loaded_bytes'],0)
                else:self.assertIsNone(annotated['hint_metrics']);self.assertEqual(d['model_load']['sentence_index_loaded_bytes'],0)
                self.assertEqual((root/'paper.json').read_bytes(),paper_raw);self.assertEqual((root/'index.json').read_bytes(),index_raw)

if __name__=='__main__':unittest.main()
