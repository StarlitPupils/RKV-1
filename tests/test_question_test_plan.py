import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rkv1.core import digest
from scripts.evidence_retrieval import build_model,encoded
import scripts.run_question_test as runner


class SealedTestWorkerTests(unittest.TestCase):
    def test_actual_worker_loads_only_fixed_test_and_keeps_frozen_model(self):
        raw=b'{"a":"alpha fact","b":"beta fact"}';model,cost=build_model(raw,[]);model_raw=encoded(model)
        doc={'id':'synthetic-test','question':'alpha','proof':'sent1 -> hypothesis;',
             'meta':{'triples':{'sent1':'alpha fact'},'worldtree_provenance':{'sent1':{'uuid':'a'}}},
             'answer':'Do not use beta','hypothesis':'Do not use beta','context':'Do not use beta'}
        seen_doc={**doc,'id':'already-seen-dev','question':'previous question'}
        labels=encoded(doc)+b'\n'+encoded(seen_doc)+b'\n'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'docs').mkdir();inputs=root/'input';inputs.mkdir()
            (inputs/'corpus.json').write_bytes(raw);(inputs/'labels-test.jsonl').write_bytes(labels)
            (root/'docs/entailment-test-inputs.json').write_bytes(encoded({'seen_dev_question_ids':['already-seen-dev'],'seen_dev_question_sha256':[], 'files':{name:{'sha256':digest(content)} for name,content in (('corpus.json',raw),('labels-test.jsonl',labels))}}))
            model_path=root/'model.json';model_path.write_bytes(model_raw);freeze=root/'freeze.json';freeze.write_bytes(encoded({'model_sha256':digest(model_raw)}))
            args=argparse.Namespace(work=str(root/'worker'),inputs=str(inputs),model=str(model_path),model_freeze=str(freeze),round=1,method='graph',worker_report=str(root/'report.json'))
            with patch.object(runner,'ROOT',root):runner.worker(args)
            report=json.loads((root/'report.json').read_bytes())
            self.assertEqual(report['raw_test_rows'],2);self.assertEqual(report['scored_rows'],1);self.assertEqual(len(report['excluded']),1);self.assertEqual(report['test_sha256'],digest(labels))
            self.assertEqual(report['records'][0]['selected_ids'],['a'])
            self.assertTrue(report['records'][0]['ID_metrics']['complete_coverage'])
            self.assertEqual(model_path.read_bytes(),model_raw);self.assertTrue(report['store_unchanged'])
            # No train/dev files were made available in this directory.
            self.assertEqual({p.name for p in inputs.iterdir()},{'corpus.json','labels-test.jsonl'})
