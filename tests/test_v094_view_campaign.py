import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from rkv1.store import Store
from rkv1.core import digest
from scripts.scifact_graph import build_model,encoded
from scripts.evidence_view_campaign import run
from scripts.view_slow_reference import rank_original
from scripts.audit_evidence_view_packet import check
from scripts.score_evidence_view_cohort import score_completed


class OwnedModelCampaign(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        src=self.root/'source';src.mkdir()
        self.raw=b''.join(json.dumps({'doc_id':i,'title':name,'abstract':['unrelated text','alpha beta '+name,'alpha alpha beta','same']},ensure_ascii=False).encode()+b'\r\n' for i,name in enumerate(['alpha','beta','gamma','alpha','beta','delta','beta','gamma','alpha']))
        (src/'corpus.jsonl').write_bytes(self.raw)
        self.store=Store.create(self.root/'store',compression='zlib',chunk_size=65536,io_backend='bounded');self.sid=self.store.add(src)['snapshot_id']
        model,_=build_model(self.raw,[]);self.model=self.root/'model.json';self.model.write_bytes(encoded(model));self.sha=digest(self.model.read_bytes())
        self.questions=[{'id':'owned-1','question':'alpha beta'},{'id':'owned-empty','question':'zzznomatch'}]

    def call(self,method,out,guard=None):return run(self.store.root,self.sid,self.model,self.sha,self.questions,method=method,out=out,guard=guard)

    def test_three_fresh_owned_campaigns_gold_file_never_read_and_reference_exact(self):
        gold=self.root/'gold-private.json';gold.write_text('{}')
        original=Path.read_bytes
        def guarded(path):
            if path==gold:raise AssertionError('Prediction must not open gold')
            return original(path)
        for method in ('whole_record','first_two','overlap_two'):
            out=self.root/method
            with patch.object(Path,'read_bytes',guarded):result=self.call(method,out)
            self.assertEqual(result['completed_queries'],2)
            self.assertFalse(result['gold_read_by_worker'])
            for i,q in enumerate(self.questions):
                row=json.loads((out/f'prediction-{i}.json').read_bytes());r=row['result']
                self.assertEqual(r['ordered_candidate_ids'],rank_original(self.raw,q['question']))
                if r['trusted_records']:
                    ref=check(self.raw,q['question'],r['trusted_records'],method,bytes.fromhex(r['view']['encoded_hex']),20000)
                    self.assertEqual(ref,r['source_verification']['available_original_sentence_indices'])
                else:self.assertEqual(r['view']['packet']['items'],[])

    def test_oracle_fields_and_normalized_duplicate_rejected_before_model_load(self):
        for cohort in ([{'id':'x','question':'alpha','evidence':{}}],[{'id':'a','question':' ALPHA '},{'id':'b','question':'alpha'}]):
            with self.assertRaises(ValueError):run(self.store.root,self.sid,self.root/'absent-model','0'*64,cohort,method='first_two',out=self.root/'never')
        self.assertFalse((self.root/'never').exists())

    def test_quota_stop_and_exclusive_output_preserve_original_partial_denominator(self):
        count=0
        def guard():
            nonlocal count
            count+=1
            if count==3:raise RuntimeError('ownedquota stop before second prediction')
        out=self.root/'partial'
        with self.assertRaises(RuntimeError):self.call('first_two',out,guard)
        fin=json.loads((out/'worker-finally.json').read_bytes())
        self.assertEqual((fin['completed_queries'],fin['planned_queries']),(1,2));self.assertFalse(fin['success'])
        old=(out/'prediction-0.json').read_bytes()
        with self.assertRaises(FileExistsError):self.call('first_two',out)
        self.assertEqual((out/'prediction-0.json').read_bytes(),old)

    def test_all_nine_predictions_and_reference_before_gold_load(self):
        folders=[]
        for n in range(3):
            for method in ('whole_record','first_two','overlap_two'):
                out=self.root/(str(n)+'-'+method);self.call(method,out);folders.append(out)
        seen=[]
        def reference(row,method):
            self.assertEqual(row['result']['ordered_candidate_ids'],rank_original(self.raw,row['question']))
            result=row['result']
            if not result['trusted_records']:return {}
            return check(self.raw,row['question'],result['trusted_records'],method,bytes.fromhex(result['view']['encoded_hex']),20000)
        def gold():
            seen.append('gold');return {'owned-1':{'0':[{'sentences':[1]}]},'owned-empty':{}}
        scored=score_completed(folders,self.questions,gold,reference)
        self.assertEqual(len(scored),18);self.assertEqual(seen,['gold'])
        self.assertTrue(all(x['source_only']['paper_recall'] is None for x in scored if x['id']=='owned-empty'))
        with self.assertRaises(ValueError):score_completed(folders[:8],self.questions,lambda:self.fail('Gold opened before all predictions'),reference)

    def test_corrupted_prediction_rejected_before_gold(self):
        folders=[]
        for n in range(3):
            for method in ('whole_record','first_two','overlap_two'):
                out=self.root/(str(n)+'-'+method);self.call(method,out);folders.append(out)
        p=folders[0]/'prediction-0.json';row=json.loads(p.read_bytes());row['result']['view']['sha256']='0'*64;p.write_text(json.dumps(row))
        with self.assertRaises(ValueError):score_completed(folders,self.questions,lambda:self.fail('Gold opened before view validation'),lambda row,method:row['result']['source_verification']['available_original_sentence_indices'])
