import json
from pathlib import Path
import tempfile
import unittest
from rkv1.store import Store
from scripts.scifact_graph import paper_records,evidence_ids,build_model,verified_hits,ranking,admit,encoded


def claim(n,ids):
    return {'id':n,'claim':'Synthetic alpha claim','evidence':{str(k):[{'sentences':[0],'label':'SUPPORT'}] for k in ids},'cited_doc_ids':[99]}


class SciFactGraphTests(unittest.TestCase):
    def raw(self):return b''.join(json.dumps({'doc_id':i,'title':'alpha','abstract':['beta gamma']}).encode()+b'\r\n' for i in range(4))

    def test_paper_identity_not_text_merge_and_original_offsets(self):
        raw=self.raw();papers=paper_records(raw);self.assertEqual(len(papers),4)
        for key,r in papers.items():self.assertEqual('doc:'+str(json.loads(raw[r['offset']:r['offset']+r['length']])['doc_id']),key)
        with self.assertRaises(ValueError):paper_records(raw+raw[:raw.index(b'\r\n')+2])
        with self.assertRaises(ValueError):evidence_ids(claim(1,[99]),papers)
        bad=claim(1,[0]);bad['evidence']['0'][0]['sentences']=[1]
        with self.assertRaises(ValueError):evidence_ids(bad,papers)

    def test_train_only_cooccurrence_no_label_or_cited_query_leak(self):
        train=[claim(1,[0,1]),claim(1,[0,1]),claim(2,[0,1,2]),claim(3,[])];m,c=build_model(self.raw(),train)
        self.assertEqual(m['shared']['N'],4);self.assertEqual(m['graph']['doc:0']['doc:1'],2)
        self.assertEqual(c['annotated_training_rows'],3)
        degree=lambda g:sorted((len(x),sum(x.values())) for x in g.values())
        self.assertEqual(degree(m['graph']),degree(m['permuted_graph']))
        changed=json.loads(json.dumps(train))
        for x in changed:
            x['cited_doc_ids']=[0,1,2,3]
            for arr in x['evidence'].values():arr[0]['label']='CONTRADICT'
        self.assertEqual(encoded(m),encoded(build_model(self.raw(),changed)[0]))
        for method in ('lexical','graph','permuted_graph'):
            selected,used=admit(m,ranking(m,'alpha',method));self.assertLessEqual(used,4096);self.assertLessEqual(len(selected),12)

    def test_original_store_record_budget_and_corruption(self):
        raw=self.raw();m,c=build_model(raw,[]);size=m['shared']['locators']['doc:0']['length']
        self.assertEqual(admit(m,['doc:0'],max_source_bytes=size),(['doc:0'],size))
        self.assertEqual(admit(m,['doc:0'],max_source_bytes=size-1),([],0))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();(src/'corpus.jsonl').write_bytes(raw)
            store=Store.create(root/'store',compression='zlib',io_backend='bounded');sid=store.add(src)['snapshot_id']
            with store.snapshot(sid) as snap:
                hits=verified_hits(snap,m,['doc:0','doc:1']);self.assertEqual([h['paper_id'] for h in hits],['doc:0','doc:1'])
                ref=snap.files['corpus.jsonl']['chunks'][0]
            path=store.object_path(ref['id']);broken=bytearray(path.read_bytes());broken[-1]^=1;path.write_bytes(broken)
            with self.assertRaises(ValueError),store.snapshot(sid) as snap:verified_hits(snap,m,['doc:0'])
