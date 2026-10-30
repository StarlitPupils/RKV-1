import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from rkv1.core import digest
from rkv1.store import Store
from rkv1.experiments.paper_retriever import PaperRetriever
from scripts.scifact_graph import build_model,encoded
from rkv1.experiments.paper_session import PaperSession
from scripts.reader_session_fixture import corpus,requests


class OwnedSessionChecks(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.src=self.root/'source';self.src.mkdir();self.store=Store.create(self.root/'store',compression='zlib',chunk_size=65536,io_backend='bounded')
        self.versions=[]
        for revision in range(3):
            raw=corpus(9,revision);(self.src/'corpus.jsonl').write_bytes(raw);sid=self.store.add(self.src,label='owned-session')['snapshot_id']
            model,_=build_model(raw,[]);p=self.root/('model-'+str(revision)+'.json');p.write_bytes(encoded(model));self.versions.append((sid,p,digest(p.read_bytes())))
    def call(self,s,revision,q='alpha',**kwargs):
        sid,p,sha=self.versions[revision]
        return s.query(q,snapshot_id=sid,model_path=p,model_sha256=sha,**kwargs)

    def test_exact_fresh_packets_across_updates_history_empty_and_budgets(self):
        s=PaperSession(self.store.root,reader_capacity=2)
        for revision in range(3):
            for old,q in requests(revision):
                sid,p,sha=self.versions[old]
                for method in ('lexical','graph','permuted_graph'):
                    self.assertEqual(self.call(s,old,q,method=method),PaperRetriever(self.store.root,sid,p,model_sha256=sha).query(q,method=method))
        self.assertGreater(s.info()['hits'],0);self.assertGreater(s.info()['evictions'],0)
        self.assertLessEqual(s.info()['retained_readers'],2)
        self.assertEqual(self.call(s,2,source_byte_budget=0)['hits'],[])

    def test_model_tamper_on_cached_hit_is_rejected_and_never_rebound(self):
        s=PaperSession(self.store.root);before=self.call(s,0);p=self.versions[0][1];raw=p.read_bytes();p.write_bytes(b'{}')
        with self.assertRaises(ValueError):self.call(s,0)
        p.write_bytes(raw);self.assertEqual(self.call(s,0),before)
        sid,p,sha=self.versions[0]
        with self.assertRaises(ValueError):s.query('alpha',snapshot_id=self.versions[1][0],model_path=p,model_sha256=sha)
        self.assertEqual(self.call(s,0),before)

    def test_selected_CAS_corruption_on_hit_refused_without_cached_evidence(self):
        s=PaperSession(self.store.root);self.call(s,0)
        with self.store.snapshot(self.versions[0][0]) as snap:ref=snap.files['corpus.jsonl']['chunks'][0]
        p=self.store.object_path(ref['id']);raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        with self.assertRaises(ValueError):self.call(s,0)
        p.write_bytes(raw);self.assertTrue(self.call(s,0)['selected_source_identity_verified'])

    def test_replies_and_info_mutation_cannot_poison_future_queries(self):
        s=PaperSession(self.store.root);original=self.call(s,0);changed=self.call(s,0)
        changed['hits'][0]['abstract'][0]='local edit';changed['hits'][0]['locator']['offset']=999
        info=s.info();info['reader_capacity']=99
        self.assertEqual(self.call(s,0),original);self.assertEqual(s.info()['reader_capacity'],2)

    def test_disabled_session_loads_each_time_and_close_releases_readers(self):
        for capacity in (0,1,2):
            with PaperSession(self.store.root,reader_capacity=capacity) as s:
                self.call(s,0);self.call(s,0);info=s.info()
                self.assertEqual(info['hits'],0 if capacity==0 else 1)
                self.assertEqual(info['retained_readers'],min(capacity,1))
            self.assertTrue(s.info()['closed']);self.assertEqual(s.info()['retained_readers'],0)
            with self.assertRaises(ValueError):self.call(s,0)
            s.close()

    def test_invalid_inputs_rejected_before_model_file_read(self):
        s=PaperSession(self.store.root)
        with patch.object(Path,'open',side_effect=AssertionError('No model IO allowed')):
            for q,kwargs in [('',{}),('alpha',{'max_papers':True}),('alpha',{'source_byte_budget':4097}),('alpha',{'method':'oracle'})]:
                with self.assertRaises(ValueError):self.call(s,0,q,**kwargs)
        for bad in (-1,5,True,1.5):
            with self.assertRaises(ValueError):PaperSession(self.store.root,reader_capacity=bad)
        self.assertEqual(s.info()['requests'],0)
