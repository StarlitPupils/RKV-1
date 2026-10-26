import itertools,unittest
from scripts.paper_capacity import capacity,support
from scripts.paper_gap import admission_trace

class PaperCapacityTests(unittest.TestCase):
    def test_greedy_independent_DP_equal_exhaustive_subsets(self):
        lengths=(1,4,5,8,10);loc={str(i):{'length':n} for i,n in enumerate(lengths)}
        for budget in range(36):
            for limit in range(1,4):
                expected=max(len(group) for n in range(limit+1) for group in itertools.combinations(lengths,n) if sum(group)<=budget)
                actual=capacity(loc,set(loc),budget=budget,limit=limit)
                self.assertEqual(actual['gold_aware_max_recovered'],expected)
    def test_original_bytes_boundary_and_prefix_waste(self):
        loc={'gold':{'length':4096},'too_big':{'length':4097},'irrelevant':{'length':1}}
        self.assertTrue(capacity(loc,['gold','gold'])['gold_complete_possible'])
        self.assertEqual(capacity(loc,['gold','gold'])['gold_total_original_bytes'],4096)
        self.assertFalse(capacity(loc,['too_big'])['gold_complete_possible'])
        trace=admission_trace(loc,['irrelevant','gold'],{'gold'})
        self.assertEqual(trace['counts']['byte_rejected'],1)
        self.assertTrue(capacity(loc,['gold'])['gold_complete_possible'])
        self.assertFalse(capacity(loc,['gold','irrelevant'])['gold_complete_possible'])
    def test_empty_denominator_and_invalid_source_rejected(self):
        self.assertIsNone(capacity({},[])['gold_aware_recall_ceiling'])
        self.assertIsNone(capacity({},[])['gold_complete_possible'])
        self.assertIsNone(support(0,0)['fraction']);self.assertFalse(support(0,0)['at_least_half_supported'])
        for loc,gold in (({},['missing']),({'x':{'length':True}},['x']),({'x':{'length':0}},['x'])):
            with self.assertRaises(ValueError):capacity(loc,gold)
        with self.assertRaises(ValueError):capacity({},[],budget=True)
        with self.assertRaises(ValueError):support(1,0)
    def test_real_worker_synthetic_capacity_and_input_SHA_rejection(self):
        import json,subprocess,sys,tempfile
        from pathlib import Path
        from rkv1.core import digest
        from scripts.evidence_retrieval import encoded,metrics
        model={'shared':{'source_kind':'scifact-whole-original-record-v1','source_sha256':'0'*64,
            'parameters':{'k1':1.2,'b':.75,'max_facts':12,'source_budget':4096,'seeds':6,'neighbors':6},
            'locators':{'doc:0':{'length':1000},'doc:1':{'length':2000},'doc:2':{'length':5000}}}}
        model_raw=encoded(model)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'model.json').write_bytes(model_raw);manifest={'model_sha256':digest(model_raw),'source_sha256':'0'*64,'methods':{}}
            for method in ('lexical','graph','permuted_graph'):
                records=[]
                for i in range(298):
                    gold=['doc:0','doc:1'] if i<21 else ['doc:2'] if i<188 else []
                    proof={'row_index':i,'question_id':i,'question_sha256':digest(str(i).encode()),'selected_ids':['doc:0'],
                        'admitted_record_bytes':1000,'gold_paper_ids':gold,'paper_metrics':metrics(['doc:0'],gold) if gold else None}
                    records.append({**proof,'proof_sha256':digest(encoded(proof))})
                raw=encoded({'round':1,'method':method,'model_sha256':digest(model_raw),'source_sha256':'0'*64,'retrieved_rows':298,'records':records})
                path=root/(method+'.json');path.write_bytes(raw);manifest['methods'][method]={'report_path':str(path),'report_sha256':digest(raw)}
            (root/'manifest.json').write_bytes(encoded(manifest));output=root/'result.json'
            args=[sys.executable,'-m','scripts.run_paper_capacity','--model',str(root/'model.json'),'--manifest',str(root/'manifest.json'),'--worker-report',str(output)]
            result=subprocess.run(args,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
            d=json.loads(output.read_bytes());self.assertEqual(d['gold_aware_complete_ceiling'],21)
            self.assertEqual(d['H1_incomplete_at_least_half_intrinsically_impossible']['numerator'],167)
            self.assertEqual(d['H2_missed_gold_at_least_half_single_over_budget']['denominator'],188)
            (root/'model.json').write_bytes(model_raw+b' ');result=subprocess.run(args,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(json.loads(output.read_bytes()),d)

if __name__=='__main__':unittest.main()
