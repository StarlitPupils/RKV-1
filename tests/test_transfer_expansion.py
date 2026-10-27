import copy,unittest
from scripts.evidence_retrieval import encoded,lexical
from rkv1.core import digest
from scripts.scifact_graph import build_model
from scripts.supervised_expansion import learn
from scripts.transfer_expansion import TransferRetriever

class TransferExpansionTests(unittest.TestCase):
    def fixture(self):
        source_raw=b''.join(encoded({'doc_id':i,'title':t,'abstract':[s]})+b'\n' for i,t,s in ((1,'Cardiac protection','cardiac injury reduction'),(2,'Vascular protection','vascular pressure reduction')));source,_=build_model(source_raw,[])
        sidecar,_=learn(source,[{'question':'myocardial protection','gold_ids':['doc:1']},{'question':'arterial protection','gold_ids':['doc:2']}],base_sha256=digest(encoded(source)))
        target=copy.deepcopy(source);target['shared']['source_kind']='owned-distinct-target';target['shared']['source_sha256']=digest(b'ownedtarget')
        raw=tuple(encoded(x) for x in (source,sidecar,target));kwargs=dict(zip(('source_base_sha256','sidecar_sha256','target_base_sha256'),(digest(x) for x in raw)));return raw,kwargs,target
    def test_frozen_source_sidecar_targets_transfer_without_model_rewrite(self):
        raw,kwargs,target=self.fixture();model=TransferRetriever(*raw,**kwargs);self.assertEqual(model.query('myocardial','lexical'),lexical(target['shared'],'myocardial')[0]);self.assertEqual(model.query('myocardial','expansion')[0],'doc:1');self.assertEqual(model.metadata()['loaded_input_bytes'],sum(map(len,raw)));self.assertTrue(model.metadata()['source_associations_not_relabelled'])
    def test_original_sources_same_target_and_identity_mismatch_refused(self):
        raw,kwargs,_=self.fixture()
        for key in kwargs:
            bad={**kwargs,key:'0'*64}
            with self.assertRaises(ValueError):TransferRetriever(*raw,**bad)
        with self.assertRaises(ValueError):TransferRetriever(raw[0],raw[1],raw[0],**{**kwargs,'target_base_sha256':kwargs['source_base_sha256']})
    def test_private_binding_copy_and_question_only_methods(self):
        raw,kwargs,_=self.fixture();model=TransferRetriever(*raw,**kwargs);meta=model.metadata();meta['source_association_audit']['edges']=999;self.assertNotEqual(model.metadata()['source_association_audit']['edges'],999)
        with self.assertRaises(ValueError):model.query({'question':'myocardial'},'expansion')
        with self.assertRaises(ValueError):model.query('myocardial','unknown')
    def test_missing_target_terms_fallback_and_bad_source_sidecar_not_adapted(self):
        raw,kwargs,target=self.fixture();target['shared']['postings']={};new=encoded(target);model=TransferRetriever(raw[0],raw[1],new,**{**kwargs,'target_base_sha256':digest(new)});self.assertEqual(model.query('myocardial','expansion'),[])
        import json
        side=json.loads(raw[1]);side['base_model_sha256']=kwargs['target_base_sha256'];changed=encoded(side)
        with self.assertRaises(ValueError):TransferRetriever(raw[0],changed,raw[2],**{**kwargs,'sidecar_sha256':digest(changed)})

if __name__=='__main__':unittest.main()
