import unittest
from scripts.paper_gap import admission_trace,graph_exposure

class PaperGapTests(unittest.TestCase):
    def test_exact_byte_reject_then_skip_continue_and_count_stop(self):
        loc={k:{'length':v} for k,v in {'a':4,'b':9,'c':2,'d':1,'e':1}.items()}
        out=admission_trace(loc,['a','b','c','c','d'],set(loc),max_facts=2,budget=6)
        self.assertEqual(out['selected_ids'],['a','c']);self.assertEqual(out['admitted_bytes'],6)
        self.assertEqual(out['counts'],{'recovered':2,'no_candidate':1,'byte_rejected':1,'count_stop':1})
        self.assertEqual(out['gold_categories']['d'],'count_stop')
    def test_invalid_limits_source_and_length(self):
        for args in ({'budget':True},{'budget':-1},{'max_facts':False}):
            with self.assertRaises(ValueError):admission_trace({},[],set(),**args)
        with self.assertRaises(ValueError):admission_trace({},[],{'missing'})
        with self.assertRaises(ValueError):admission_trace({'a':{'length':0}},['a'],{'a'})
    def test_graph_seed_scope_and_new_neighbor(self):
        model={'graph':{'a':{'b':1,'x':2},'last':{'z':1}},'permuted_graph':{}}
        self.assertEqual(graph_exposure(model,['a','b','c','d','e','f','last'],'graph'),
            {'active_seed_count':1,'neighbor_union_count':2,'novel_nonlexical_neighbor_count':1})
        self.assertEqual(graph_exposure(model,['a'],'lexical')['active_seed_count'],0)
        with self.assertRaises(ValueError):graph_exposure(model,[],'other')
    def test_real_worker_fixed_input_and_tamper_rejected(self):
        import json,subprocess,sys,tempfile
        from pathlib import Path
        from scripts.scifact_graph import build_model
        from scripts.evidence_retrieval import encoded,ranking,admit,question_identity,metrics
        from rkv1.core import digest
        raw=b''.join(json.dumps({'doc_id':i,'title':'Synthetic alpha','abstract':['Synthetic beta.']}).encode()+b'\n' for i in range(3))
        model,_=build_model(raw,[]);model_raw=encoded(model);question='Synthetic alpha';selected,used=admit(model,ranking(model,question,'lexical'))
        proof={'row_index':0,'question_id':9,'question_sha256':question_identity(question),'selected_ids':selected,
            'admitted_record_bytes':used,'gold_paper_ids':['doc:0'],'paper_metrics':metrics(selected,{'doc:0'})}
        report=encoded({'round':1,'method':'lexical','model_sha256':digest(model_raw),'source_sha256':digest(raw),'retrieved_rows':1,
            'records':[{**proof,'proof_sha256':digest(encoded(proof)),'ranked_candidates':3}]})
        queries=encoded([{'row_index':0,'question':question,'selected_ids':selected}])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'model.json').write_bytes(model_raw);(p/'report.json').write_bytes(report);(p/'queries.json').write_bytes(queries)
            (p/'manifest.json').write_bytes(encoded({'model_sha256':digest(model_raw),'source_sha256':digest(raw),
                'methods':{'lexical':{'report_sha256':digest(report),'queries_sha256':digest(queries)}}}))
            args=[sys.executable,'-m','scripts.run_paper_gap','--method','lexical','--model',str(p/'model.json'),'--manifest',str(p/'manifest.json'),
                '--report',str(p/'report.json'),'--queries',str(p/'queries.json'),'--output',str(p/'output.json')]
            result=subprocess.run(args,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads((p/'output.json').read_bytes())['counts']['recovered'],1)
            (p/'queries.json').write_bytes(queries+b' ');result=subprocess.run(args,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('Frozen diagnostic input SHA differs',result.stderr)

if __name__=='__main__':unittest.main()
