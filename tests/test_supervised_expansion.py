import json,unittest
from scripts.evidence_retrieval import encoded,lexical
from scripts.scifact_graph import build_model
from rkv1.core import digest
from scripts.supervised_expansion import learn,ranking,query_expansion

class SupervisedExpansionTests(unittest.TestCase):
    def fixture(self):
        raw=b''.join(encoded({'doc_id':i,'title':title,'abstract':sentences})+b'\n' for i,title,sentences in ((1,'Cardiac protection',['cardiac injury reduction']),(2,'Vascular protection',['vascular pressure reduction']),(3,'Cellular mechanism',['cellular response modulation'])))
        base,_=build_model(raw,[]);rows=[{'question':'myocardial protection','gold_ids':['doc:1']},{'question':'arterial protection','gold_ids':['doc:2']},{'question':'intracellular mechanism','gold_ids':['doc:3']}]
        return base,rows
    def test_known_source_bridge_and_unchanged_lexical_baseline(self):
        base,rows=self.fixture();model,_=learn(base,rows,base_sha256=digest(encoded(base)))
        self.assertEqual(ranking(base,model,'myocardial','lexical'),lexical(base['shared'],'myocardial')[0]);self.assertEqual(ranking(base,model,'myocardial','lexical'),[])
        self.assertEqual(ranking(base,model,'myocardial','expansion')[0],'doc:1')
    def test_duplicate_normalized_questions_vote_once_and_gold_union(self):
        base,rows=self.fixture();model,cost=learn(base,rows,base_sha256=digest(encoded(base)));duplicate={**rows[0],'question':'  MYOCARDIAL   protection  '};again,cost2=learn(base,rows+[duplicate],base_sha256=digest(encoded(base)))
        self.assertEqual(model,again);self.assertEqual(cost2['unique_training_questions'],cost['unique_training_questions']);self.assertEqual(cost2['input_training_rows'],4)
        union,_=learn(base,[rows[0],{'question':duplicate['question'],'gold_ids':['doc:2']}],base_sha256=digest(encoded(base)))
        weights=query_expansion(union,'myocardial','expansion');self.assertIn('cardiac',weights);self.assertIn('vascular',weights)
    def test_query_budget_weight_and_original_term_exclusion(self):
        base,rows=self.fixture();model,_=learn(base,rows,base_sha256=digest(encoded(base)));weights=query_expansion(model,'myocardial cardiac','expansion')
        self.assertLessEqual(len(weights),8);self.assertNotIn('cardiac',weights);self.assertNotIn('myocardial',weights);self.assertAlmostEqual(sum(weights.values()),.25)
        self.assertEqual(query_expansion(model,'','expansion'),{})
    def test_permutation_preserves_edge_multiset_and_has_no_fixed_points(self):
        base,rows=self.fixture();model,cost=learn(base,rows,base_sha256=digest(encoded(base)))
        self.assertTrue(cost['control_available']);self.assertEqual(cost['control_fixed_points'],0);self.assertEqual(sorted(encoded(v) for v in model['expansion'].values()),sorted(encoded(v) for v in model['permuted_expansion'].values()))
        self.assertEqual(len(encoded(model['expansion'])),len(encoded(model['permuted_expansion'])))
    def test_empty_training_no_hidden_fallback_and_input_refusal(self):
        base,rows=self.fixture();model,cost=learn(base,[],base_sha256=digest(encoded(base)));self.assertFalse(cost['control_available']);self.assertEqual(model['expansion'],{})
        self.assertEqual(ranking(base,model,'cardiac','expansion'),ranking(base,model,'cardiac','lexical'))
        with self.assertRaises(ValueError):learn(base,rows,base_sha256='0'*64)
        with self.assertRaises(ValueError):learn(base,[{'question':'question','gold_ids':['doc:999']}],base_sha256=digest(encoded(base)))
        with self.assertRaises(ValueError):query_expansion(model,{'claim':'cardiac','evidence':{}},'expansion')
        with self.assertRaises(ValueError):ranking(base,model,'cardiac','unknown')
    def test_original_model_immutable_and_unused_labels_never_read(self):
        class Forbidden:
            def __str__(self):raise AssertionError('Verdict label consumed')
        base,rows=self.fixture();before=encoded(base);rows[0]['label']=Forbidden();model,_=learn(base,rows,base_sha256=digest(before));ranking(base,model,'myocardial','expansion');ranking(base,model,'myocardial','permuted_expansion');self.assertEqual(encoded(base),before)

if __name__=='__main__':unittest.main()
