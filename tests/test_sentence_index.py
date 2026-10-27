import json,tempfile,unittest
from pathlib import Path
from rkv1.store import Store
from scripts.scifact_graph import build_model
from scripts.sentence_index import build_index,verified_units,ranking,admit,parent_ranking,verified_parent_hits

class SentenceIndexTests(unittest.TestCase):
    def test_no_text_identity_merge_and_exact_budget_live_source(self):
        raw=b''.join(json.dumps({'doc_id':i,'title':'alpha','abstract':['same β quote "','same β quote "']},ensure_ascii=False).encode()+b'\r\n' for i in range(2))
        paper,_=build_model(raw,[]);units,parts=build_index(raw,paper);self.assertEqual(parts['abstract_units'],4)
        chosen,used=admit(units,ranking(units,'same quote','lexical'));self.assertEqual(len(chosen),4)
        key=chosen[0];size=units['shared']['locators'][key]['length']
        self.assertEqual(admit(units,[key],max_source_bytes=size),([key],size));self.assertEqual(admit(units,[key],max_source_bytes=size-1),([],0))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();(source/'corpus.jsonl').write_bytes(raw)
            store=Store.create(root/'store',compression='zlib',io_backend='bounded');sid=store.add(source)['snapshot_id']
            with store.snapshot(sid) as snap:hits=verified_units(snap,units,chosen)
            self.assertEqual(len({h['locator']['offset'] for h in hits}),4)
            with store.snapshot(sid) as snap:ref=snap.files['corpus.jsonl']['chunks'][0]
            path=store.object_path(ref['id']);broken=bytearray(path.read_bytes());broken[-1]^=1;path.write_bytes(broken)
            with self.assertRaises(ValueError),store.snapshot(sid) as snap:verified_units(snap,units,[key])
    def test_source_model_SHA_and_selected_unit_parent_mismatch_refuse(self):
        import copy
        raw=json.dumps({'doc_id':1,'title':'title','abstract':['alpha','beta']}).encode()+b'\n';paper,_=build_model(raw,[])
        with self.assertRaises(ValueError):build_index(raw+b' ',paper)
        units,_=build_index(raw,paper)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();(source/'corpus.jsonl').write_bytes(raw);store=Store.create(root/'store',compression='zlib');sid=store.add(source)['snapshot_id']
            bad=copy.deepcopy(units);bad['shared']['locators']['doc:1:abstract:0']['sentence_index']=1
            with self.assertRaises(ValueError),store.snapshot(sid) as snap:verified_units(snap,bad,['doc:1:abstract:0'])
    def test_max_sentence_parent_dedup_tie_and_whole_record_budget(self):
        raw=b''.join(json.dumps({'doc_id':i,'title':'opaque title','abstract':['alpha','alpha beta']}).encode()+b'\n' for i in (2,1))
        paper,_=build_model(raw,[]);units,_=build_index(raw,paper);ranked,best=parent_ranking(units,'alpha beta')
        self.assertEqual(ranked,['doc:1','doc:2']);self.assertEqual(best['doc:1'],'doc:1:abstract:1')
        selected,used=admit(paper,ranked);self.assertEqual(used,len(raw))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();(src/'corpus.jsonl').write_bytes(raw);store=Store.create(root/'store',compression='zlib');sid=store.add(src)['snapshot_id']
            with store.snapshot(sid) as snap:hits,hints=verified_parent_hits(snap,paper,units,selected,best)
            self.assertEqual([h['paper_id'] for h in hits],selected);self.assertTrue(all(h['sentence_index']==1 for h in hints))
            self.assertEqual(sum(h['locator']['length'] for h in hits),used)
    def test_existing_public_API_refuses_new_index_schema(self):
        from rkv1.experiments.paper_retriever import PaperRetriever
        from rkv1.core import digest
        from scripts.scifact_graph import encoded
        raw=json.dumps({'doc_id':1,'title':'title','abstract':['alpha beta']}).encode()+b'\n';paper,_=build_model(raw,[]);index,_=build_index(raw,paper);index_raw=encoded(index)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'index.json';path.write_bytes(index_raw)
            with self.assertRaisesRegex(ValueError,'Unsupported paper model schema'):PaperRetriever(root/'absent-store','0'*64,path,model_sha256=digest(index_raw))

if __name__=='__main__':unittest.main()
