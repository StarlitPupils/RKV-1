import argparse,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from rkv1.core import digest
from scripts.evidence_retrieval import encoded,build_model as build_facts
from scripts.scifact_graph import build_model as build_papers
from scripts.supervised_expansion import learn
from scripts import run_expansion_transfer as runner

class ExpansionTransferWorkerTests(unittest.TestCase):
    def test_target_sourceID_literal_and_three_methods_with_no_retraining(self):
        facts={'fact-a':'cardiac injury reduction','fact-b':'vascular pressure reduction'};raw=encoded(facts);target,_=build_facts(raw,[]);target_raw=encoded(target)
        papers=b''.join(encoded({'doc_id':i,'title':title,'abstract':[body]})+b'\n' for i,title,body in ((1,'Cardiac protection','cardiac injury reduction'),(2,'Vascular protection','vascular pressure reduction')));source,_=build_papers(papers,[]);source_raw=encoded(source);side,_=learn(source,[{'question':'myocardial protection','gold_ids':['doc:1']},{'question':'arterial protection','gold_ids':['doc:2']}],base_sha256=digest(source_raw));side_raw=encoded(side)
        def doc(id,question,uuid,sentence):return {'id':id,'question':question,'proof':'sent1 -> hypothesis','meta':{'triples':{'sent1':sentence},'worldtree_provenance':{'sent1':{'uuid':uuid}}}}
        rows=[doc('toy1','myocardial injury','fact-a',facts['fact-a']),doc('toy2','arterial pressure','fact-b','different literal sentence'),doc('toy3','unknown mechanism','missing','unresolved target')]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'docs').mkdir();inputs=root/'inputs';inputs.mkdir();labels=b''.join(encoded(row)+b'\n' for row in rows);(inputs/'corpus.json').write_bytes(raw);(inputs/'labels-test.jsonl').write_bytes(labels)
            (root/'docs/entailment-test-inputs.json').write_bytes(encoded({'files':{'corpus.json':{'sha256':digest(raw)},'labels-test.jsonl':{'sha256':digest(labels)}},'seen_dev_question_ids':[],'seen_dev_question_sha256':[]}));(root/'docs/expansion-transfer-inputs.json').write_bytes(encoded({'source_training_question_sha256':[]}))
            for name,value in (('target.json',target_raw),('source.json',source_raw),('side.json',side_raw)):(root/name).write_bytes(value)
            freeze=root/'freeze.json';freeze.write_bytes(encoded({'model_sha256':digest(target_raw),'source_model_sha256':digest(source_raw),'sidecar_sha256':digest(side_raw)}))
            with patch.object(runner,'ROOT',root):
                for method in runner.METHODS:
                    report=root/(method+'.json');args=argparse.Namespace(work=root/method,inputs=inputs,model=root/'target.json',source_base=root/'source.json',sidecar=root/'side.json',model_freeze=freeze,round=1,method=method,worker_report=report);runner.worker(args);r=json.loads(report.read_bytes());self.assertEqual(r['scored_rows'],3);self.assertEqual(r['loaded_full_model_bytes'],len(target_raw)+(0 if method=='lexical' else len(source_raw)+len(side_raw)));self.assertTrue(r['store_unchanged']);self.assertEqual(r['recovery']['source_sha256'],digest(raw))
                    byid={x['question_id']:x for x in r['records']};self.assertIn('unresolved:',next(iter(byid['toy3']['gold_id_groups'])));self.assertTrue(any(x.startswith('nonliteral:') for x in byid['toy2']['literal_groups']))
                    self.assertTrue(all(x['admitted_record_bytes']<=4096 and len(x['selected_ids'])<=12 for x in r['records']))

if __name__=='__main__':unittest.main()
