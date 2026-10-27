import copy,unittest
from scripts.evidence_retrieval import encoded,admit
from rkv1.core import digest
from scripts.supervised_expansion import learn,ranking,query_expansion
from scripts.audit_supervised_expansion import validate,reference_ranking
from tests import test_supervised_expansion as training_fixture

class ExpansionAuditTests(unittest.TestCase):
    def fixture(self):
        base,rows=training_fixture.SupervisedExpansionTests().fixture();model,_=learn(base,rows,base_sha256=digest(encoded(base)));return base,model
    def test_independent_ranking_all_methods_and_query_forms(self):
        base,model=self.fixture();self.assertTrue(validate(base,model)['control_available'])
        for question in ('myocardial','myocardial myocardial cardiac','protection mechanism','unknown code999',''):
            for method in ('lexical','expansion','permuted_expansion'):self.assertEqual(ranking(base,model,question,method),reference_ranking(base,model,question,method))
        self.assertEqual(admit(base,ranking(base,model,'myocardial','expansion'),max_source_bytes=10),([],0))
    def test_rejects_bad_base_parameters_votes_and_duplicate_edges(self):
        base,model=self.fixture();first=next(iter(model['expansion']));bad=[]
        x=copy.deepcopy(model);x['base_model_sha256']='0'*64;bad.append(x)
        x=copy.deepcopy(model);x['parameters']['alpha']=1.;bad.append(x)
        x=copy.deepcopy(model);x['expansion'][first][0][1]=0;bad.append(x)
        x=copy.deepcopy(model);x['expansion'][first][0][2]=0;bad.append(x)
        x=copy.deepcopy(model);x['expansion'][first].append(x['expansion'][first][0]);bad.append(x)
        for value in bad:
            with self.assertRaises(ValueError):validate(base,value)
    def test_control_cannot_change_weights_or_fix_keys(self):
        base,model=self.fixture();first=next(iter(model['expansion']));x=copy.deepcopy(model);x['permuted_expansion'][first][0][1]+=1
        with self.assertRaises(ValueError):validate(base,x)
        x=copy.deepcopy(model);x['control_key_permutation']={q:q for q in x['expansion']};x['permuted_expansion']=copy.deepcopy(x['expansion'])
        with self.assertRaises(ValueError):validate(base,x)
    def test_exact_rational_vote_tie_is_canonical(self):
        base,model=self.fixture();model['expansion']={'myocardial':[['cardiac',1,3],['vascular',1,3]],'arterial':[['cardiac',1,6],['vascular',1,6]]}
        weights=query_expansion(model,'myocardial arterial','expansion');self.assertEqual(weights,{'cardiac':.125,'vascular':.125})

if __name__=='__main__':unittest.main()
