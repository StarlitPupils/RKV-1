import importlib.util,json,tempfile,unittest
from pathlib import Path
from rkv1.core import digest
from rkv1.store import Store
from scripts.scifact_graph import build_model,encoded,ranking,admit
from rkv1.experiments import paper_retriever as api

class PaperRetrieverDraftTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.raw=b''.join(json.dumps({'doc_id':i,'title':t,'abstract':['Exact original beta evidence.']}).encode()+b'\r\n' for i,t in enumerate(('alpha','beta','gamma','alpha')))
        train=[{'id':1,'claim':'training only','evidence':{'0':[{'sentences':[0]}],'1':[{'sentences':[0]}]}}]
        self.model,_=build_model(self.raw,train);self.modelraw=encoded(self.model);self.path=self.root/'model.json';self.path.write_bytes(self.modelraw)
        self.src=self.root/'source';self.src.mkdir();(self.src/'corpus.jsonl').write_bytes(self.raw)
        self.store=Store.create(self.root/'store',compression='zlib',chunk_size=65536,io_backend='bounded');self.sid=self.store.add(self.src)['snapshot_id']
        self.reader=self.open()
    def open(self,sid=None,path=None,sha=None):return api.PaperRetriever(self.store.root,sid or self.sid,path or self.path,model_sha256=sha or digest(self.modelraw))
    def test_methods_match_frozen_assessment_and_original_records(self):
        for method in ('lexical','graph','permuted_graph'):
            result=self.reader.query('alpha beta',method=method);selected,used=admit(self.model,ranking(self.model,'alpha beta',method))
            self.assertEqual(result['selected_ids'],selected);self.assertEqual(result['admitted_record_bytes'],used)
            self.assertFalse(result['scientific_entailment_verified']);self.assertIsNone(result['generated_answer'])
            for hit in result['hits']:
                loc=hit['locator'];self.assertEqual(loc['snapshot_id'],self.sid)
                original=self.raw[loc['offset']:loc['offset']+loc['length']];self.assertEqual(digest(original),loc['sha256'])
                obj=json.loads(original);self.assertEqual(hit['title'],obj['title']);self.assertEqual(hit['abstract'],obj['abstract'])
        size=self.model['shared']['locators']['doc:0']['length']
        self.assertEqual(self.reader.query('alpha',max_papers=1,source_byte_budget=size)['selected_ids'],['doc:0'])
        self.assertEqual(self.reader.query('alpha',source_byte_budget=0)['hits'],[])
    def test_old_snapshot_remains_pinned_and_new_mismatch_rejected(self):
        before=self.reader.query('alpha');(self.src/'corpus.jsonl').write_bytes(self.raw.replace(b'alpha',b'omega'))
        newer=self.store.add(self.src)['snapshot_id'];self.assertNotEqual(newer,self.sid)
        self.assertEqual(self.reader.query('alpha'),before)
        with self.assertRaises(ValueError):self.open(sid=newer)
    def test_new_request_detects_selected_CAS_corruption(self):
        self.reader.query('alpha')
        with self.store.snapshot(self.sid) as snapshot:ref=snapshot.files['corpus.jsonl']['chunks'][0]
        path=self.store.object_path(ref['id']);raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
        with self.assertRaises(ValueError):self.reader.query('alpha')
    def test_instance_model_is_pinned_but_fresh_loader_rejects_changed_file(self):
        before=self.reader.query('alpha',method='graph');self.path.write_bytes(b'{}')
        self.assertEqual(self.reader.query('alpha',method='graph'),before)
        with self.assertRaises(ValueError):self.open()
    def test_returned_hit_mutation_does_not_change_next_request(self):
        before=self.reader.query('alpha');modified=self.reader.query('alpha')
        modified['hits'][0]['abstract'][0]='caller local edit';modified['hits'][0]['locator']['offset']=999
        self.assertEqual(self.reader.query('alpha'),before)
    def test_input_limits_and_metadata_copy(self):
        info=self.reader.model_info();info['parameters']['max_facts']=99
        self.assertEqual(self.reader.model_info()['parameters']['max_facts'],12)
        for query in (None,{},'', ' ', 'a\0b','a'*4097):
            with self.assertRaises(ValueError):self.reader.query(query)
        for kwargs in ({'method':'bad'},{'max_papers':True},{'max_papers':13},{'source_byte_budget':-1},{'source_byte_budget':4097}):
            with self.assertRaises(ValueError):self.reader.query('alpha',**kwargs)
    def test_model_SHA_schema_duplicate_nonfinite_and_size(self):
        with self.assertRaises(ValueError):self.open(sha='0'*64)
        for raw in (b'{"shared":{},"shared":{}}',b'{"value":NaN}',encoded({**self.model,'shared':{**self.model['shared'],'source_kind':'other'}})):
            p=self.root/'bad.json';p.write_bytes(raw)
            with self.assertRaises(ValueError):self.open(path=p,sha=digest(raw))
        p=self.root/'big.json';p.write_bytes(b' '*(api.MAX_MODEL_BYTES+1))
        with self.assertRaises(ValueError):self.open(path=p,sha=digest(p.read_bytes()))
    def test_malformed_locator_graph_and_posting_fail_as_ValueError(self):
        import copy
        cases=[]
        for replacement in (None,{}, {'offset':True,'length':2,'sha256':'0'*64}):
            m=copy.deepcopy(self.model);m['shared']['locators']['doc:0']=replacement;cases.append(m)
        m=copy.deepcopy(self.model);m['shared']['locators']['doc:1']['offset']=0;cases.append(m)
        m=copy.deepcopy(self.model);m['graph']['doc:1']=None;cases.append(m)
        m=copy.deepcopy(self.model);m['graph']['doc:0']['doc:1']=True;cases.append(m)
        m=copy.deepcopy(self.model);m['shared']['postings']['alpha']['doc:0']=99;cases.append(m)
        for m in cases:
            raw=encoded(m);p=self.root/'malformed.json';p.write_bytes(raw)
            with self.assertRaises(ValueError):self.open(path=p,sha=digest(raw))

if __name__=='__main__':unittest.main()
