import argparse,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from rkv1.core import digest
from scripts.evidence_retrieval import encoded
from scripts.scifact_graph import build_model
from scripts.supervised_expansion import learn
from scripts import run_supervised_expansion as runner

class ExpansionWorkerTests(unittest.TestCase):
    def test_original_source_all_three_roles_baseline_no_sidecar_load_and_bad_base_refusal(self):
        raw=b''.join(encoded({'doc_id':i,'title':title,'abstract':[body]})+b'\n' for i,title,body in ((1,'Cardiac protection','cardiac injury reduction'),(2,'Vascular protection','vascular pressure reduction'),(3,'Cellular mechanism','cellular response modulation')))
        training=[{'id':1000,'claim':'myocardial protection','evidence':{'1':[{'sentences':[0],'label':'SUPPORT'}]}}];base,_=build_model(raw,training);base_raw=encoded(base);side,_=learn(base,[{'question':'myocardial protection','gold_ids':['doc:1']},{'question':'arterial protection','gold_ids':['doc:2']}],base_sha256=digest(base_raw));side_raw=encoded(side)
        dev=[{'id':2001,'claim':'myocardial injury','evidence':{'1':[{'sentences':[0],'label':'SUPPORT'}]}},{'id':2002,'claim':'arterial pressure','evidence':{'2':[{'sentences':[0],'label':'CONTRADICT'}]}},{'id':2003,'claim':'unknown mechanism','evidence':{}}]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inputs=root/'inputs';inputs.mkdir();(root/'docs').mkdir();files={'corpus.jsonl':raw,'claims_train.jsonl':b''.join(encoded(x)+b'\n' for x in training),'claims_dev.jsonl':b''.join(encoded(x)+b'\n' for x in dev)}
            for name,value in files.items():(inputs/name).write_bytes(value)
            (root/'docs/scifact-graph-inputs.json').write_bytes(encoded({'files':{name:{'sha256':digest(value)} for name,value in files.items()}}));base_file=root/'base.json';base_file.write_bytes(base_raw);side_file=root/'side.json';side_file.write_bytes(side_raw);freeze=root/'freeze.json';freeze.write_bytes(encoded({'model_sha256':digest(base_raw),'sidecar_sha256':digest(side_raw)}))
            with patch.object(runner,'ROOT',root):
                for method in runner.METHODS:
                    report=root/(method+'.json');args=argparse.Namespace(work=root/method,inputs=inputs,model=base_file,sidecar=side_file,model_freeze=freeze,round=1,method=method,worker_report=report);runner.worker(args);r=json.loads(report.read_bytes());self.assertEqual(r['retrieved_rows'],3);self.assertEqual(r['annotated_scored_rows'],2);self.assertEqual(r['unannotated_rows'],1);self.assertTrue(r['store_unchanged']);self.assertEqual(r['sidecar_load']['bytes'],0 if method=='lexical' else len(side_raw));self.assertEqual(r['loaded_full_model_bytes'],len(base_raw)+(0 if method=='lexical' else len(side_raw)))
                    self.assertEqual(r['recovery']['source_sha256'],digest(raw));self.assertTrue(all(x['admitted_record_bytes']<=4096 and len(x['selected_ids'])<=12 for x in r['records']))
                base_file.write_bytes(base_raw+b' ');args.work=root/'bad';args.worker_report=root/'bad.json'
                with self.assertRaises(AssertionError):runner.worker(args)
                self.assertFalse(args.worker_report.exists())

if __name__=='__main__':unittest.main()
