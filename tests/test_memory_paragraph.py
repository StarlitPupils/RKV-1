import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from rkv1.memory import Memory, _json
from rkv1.memory_paragraph import ParagraphIndex


class ParagraphRetrievalTests(unittest.TestCase):
    def make(self,root):
        src=root/'source';src.mkdir();path=src/'papers.json'
        docs={k:{'title':'Identical title','abstract':'rarebeacon café 雪','full_text':[{'paragraphs':['Calibration body.']}],
                 'qas':[{'question':'ANNOTATIONSECRETNEVERINDEXED'}]} for k in ('b','a','c')}
        path.write_bytes(_json(docs));m=Memory.create(root/'memory');sid=m.add(src)['snapshot_id']
        built=ParagraphIndex.create(m,root/'sidecar');return m,built['index'],src,path,docs,sid

    def test_contentless_units_stable_ties_full_identity_and_annotation_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);m,index,_,_,_,sid=self.make(root)
            before={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            out=index.search(m,'rarebeacon 雪',top_k=2)
            self.assertEqual([h['key'] for h in out['hits']],['qasper:a','qasper:b'])
            self.assertEqual([x['sentence'] for x in out['winning_source_units']],[0,0])
            for h in out['hits']:
                known=m.lookup(h['key'])['hits'][0]
                self.assertEqual({k:v for k,v in h.items() if k not in ('rank','citation_id')},
                                 {k:v for k,v in known.items() if k not in ('rank','citation_id')})
                self.assertEqual(h['locator']['snapshot_id'],sid)
            self.assertEqual(index.search(m,'ANNOTATIONSECRETNEVERINDEXED')['hits'],[])
            self.assertEqual(index.search(m,'the a')['hits'],[])
            db=sqlite3.connect(index.root/'index.sqlite')
            try:
                self.assertEqual(db.execute('SELECT count(*) FROM positions').fetchone()[0],9)
                self.assertTrue(all(t is None and b is None for t,b in db.execute('SELECT title,body FROM terms')))
            finally:db.close()
            self.assertEqual(before,{p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_stale_source_fails_history_explicit_and_new_build_keeps_original_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);m,index,src,path,docs,sid=self.make(root)
            old=index.search(m,'rarebeacon')['hits']
            docs['a']['abstract']+=' FUTUREBEACON';path.write_bytes(_json(docs));m.add(src,label='future')
            with self.assertRaisesRegex(ValueError,'snapshot mismatch'):index.search(m,'rarebeacon')
            self.assertEqual(index.search(m,'rarebeacon',snapshot=sid)['hits'],old)
            self.assertFalse(index.search(m,'FUTUREBEACON',snapshot=sid)['hits'])
            new=ParagraphIndex.create(m,root/'new')['index'];h,=new.search(m,'FUTUREBEACON')['hits']
            self.assertEqual(h['key'],'qasper:a');self.assertIn('FUTUREBEACON',h['sentences'][0])

    def test_corruption_in_sidecar_or_original_index_or_cas_is_not_served(self):
        for what in ('sidecar','memory-index','cas','source-binding'):
            with self.subTest(what=what),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);m,index,_,_,_,sid=self.make(root)
                if what=='source-binding':
                    p=index.root/'manifest.json';v=json.loads(p.read_bytes());v['source_files']={};p.write_bytes(_json(v))
                else:
                    if what=='sidecar':p=index.root/'index.sqlite'
                    elif what=='memory-index':p=m.root/'indexes'/(sid+'.sqlite')
                    else:
                        snap=m.store.snapshot(sid);ref=snap.files['papers.json']['chunks'][0];p=m.store.object_path(ref['id'])
                    raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
                with self.assertRaises(ValueError):index.search(m,'rarebeacon')

    def test_invalid_input_overlapping_root_and_existing_target_fail_without_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);m,index,_,_,_,_=self.make(root)
            for question,top_k in (('',20),(None,20),('rarebeacon',True),('rarebeacon',0),('rarebeacon',21)):
                with self.assertRaises(ValueError):index.search(m,question,top_k=top_k)
            with self.assertRaises(ValueError):ParagraphIndex.create(m,m.root/'forbidden')
            self.assertFalse((m.root/'forbidden').exists())
            before={p.name:p.read_bytes() for p in index.root.iterdir()}
            with self.assertRaises(FileExistsError):ParagraphIndex.create(m,index.root)
            self.assertEqual(before,{p.name:p.read_bytes() for p in index.root.iterdir()})
            original=Path.is_symlink
            for linked in (index.root,index.root/'manifest.json',index.root/'index.sqlite'):
                with patch.object(Path,'is_symlink',lambda p:p==linked or original(p)):
                    with self.assertRaisesRegex(ValueError,'Linked'):index.search(m,'rarebeacon')

    def test_empty_abstract_still_has_title_unit_and_document_key_not_indexed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir()
            (src/'metadata-secret-path.jsonl').write_bytes(_json({'doc_id':'METADATAKEYONLY','title':'Singular titlebeacon','abstract':[]})+b'\n')
            m=Memory.create(root/'memory');m.add(src);index=ParagraphIndex.create(m,root/'sidecar')['index']
            out=index.search(m,'titlebeacon');self.assertEqual(out['hits'][0]['sentences'],[])
            self.assertEqual(out['winning_source_units'][0]['sentence'],-1)
            self.assertEqual(index.search(m,'METADATAKEYONLY')['hits'],[])
