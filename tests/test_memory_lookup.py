import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rkv1.core import digest
from rkv1.memory import Memory, _json
from rkv1.memory_index import PROFILES


class KnownSourceTests(unittest.TestCase):
    def test_exact_identity_all_profiles_history_relocations_and_deletion(self):
        for profile in PROFILES:
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temp:
                root=Path(temp);src=root/'source';src.mkdir();path=src/'docs.jsonl'
                docs=[{'doc_id':i,'title':f'Beacon {i}','abstract':[f'Calibrate token{i:03d} café 雪.']} for i in range(20)]
                path.write_bytes(b''.join(_json(d)+b'\r\n' for d in docs))
                m=Memory.create(root/'memory',index_profile=profile);old=m.add(src)['snapshot_id']
                first=m.lookup('doc:19')['hits'][0]
                docs[0]['abstract'][0]+=' A longer revision shifts later records.'
                path.write_bytes(b''.join(_json(d)+b'\r\n' for d in docs));updated=m.add(src,label='shift')
                if profile in ('compact-base-v3','compact-budget-v3'):
                    self.assertEqual(updated['delta_depth'],1);self.assertGreater(updated['relocation_ranges'],0)
                out=m.lookup('doc:19');h,=out['hits'];self.assertEqual(out['scope'],'explicit-known-source')
                self.assertIsNone(h['rank']);self.assertEqual(h['citation_id'],'D0')
                found=m.search('token019')['hits'][0]
                self.assertEqual({k:v for k,v in h.items() if k!='rank'},{k:v for k,v in found.items() if k!='rank'})
                loc=h['locator'];self.assertEqual(digest(path.read_bytes()[loc['offset']:loc['offset']+loc['length']]),loc['sha256'])
                self.assertNotEqual(first['locator']['offset'],loc['offset'])
                self.assertEqual(m.lookup('doc:19',snapshot=old)['hits'][0],first)
                path.write_bytes(b''.join(_json(d)+b'\r\n' for d in docs[:-1]));m.add(src,label='delete')
                self.assertEqual(m.lookup('doc:19')['hits'],[])
                self.assertEqual(m.lookup('doc:19',snapshot=old)['hits'][0],first)

    def test_v4_annotation_rebinding_and_body_edit_match_verified_search(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();path=src/'papers.json'
            docs={str(i):{'title':'Beacon','abstract':f'token{i:03d} 雪','full_text':[{'paragraphs':['Calibration.']}],'qas':[]} for i in range(20)}
            path.write_bytes(_json(docs));m=Memory.create(root/'memory',index_profile='compact-projection-v4')
            old=m.add(src)['snapshot_id'];first=m.lookup('qasper:0')['hits'][0]
            for d in docs.values():d['qas']=[{'question':'ANNOTATIONSECRET'}]
            path.unlink();path=src/'renamed.json';path.write_text(json.dumps(docs,ensure_ascii=True),encoding='utf-8')
            added=m.add(src,label='rebind');self.assertEqual(added['overlay_rebindings'],20)
            h,=m.lookup('qasper:0')['hits'];self.assertEqual(h['sentences'],first['sentences'])
            self.assertEqual(h['locator']['path'],'renamed.json');self.assertNotIn('ANNOTATIONSECRET',str(h['sentences']))
            self.assertEqual(m.lookup('qasper:0',snapshot=old)['hits'][0],first)
            docs['0']['abstract']+=' EDITED';path.write_bytes(_json(docs));m.add(src,label='body')
            h,=m.lookup('qasper:0')['hits'];self.assertIn('EDITED',h['sentences'][0])
            found=m.search('token000')['hits'][0];self.assertEqual(h['locator'],found['locator'])

    def test_missing_invalid_and_sql_literal_keys_do_not_search_or_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();(src/'known.txt').write_text('the a',encoding='utf-8')
            m=Memory.create(root/'memory');m.add(src)
            before={p.relative_to(m.root):p.read_bytes() for p in m.root.rglob('*') if p.is_file()}
            with patch.object(m,'search',side_effect=AssertionError('lookup must not guess a query')):
                self.assertEqual(m.lookup('file:known.txt')['hits'][0]['sentences'],['the a'])
                self.assertEqual(m.lookup("' OR 1=1 --")['hits'],[])
                for key in ('',None,1,True,'x'*513,'null\x00key'):
                    with self.assertRaises(ValueError):m.lookup(key)
            self.assertEqual(before,{p.relative_to(m.root):p.read_bytes() for p in m.root.rglob('*') if p.is_file()})

    def test_corrupted_index_or_cas_is_not_served(self):
        for what in ('index','cas'):
            with self.subTest(what=what),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);src=root/'source';src.mkdir();(src/'a.txt').write_text('Evidence 雪.',encoding='utf-8')
                m=Memory.create(root/'memory');sid=m.add(src)['snapshot_id']
                if what=='index':path=m.root/'indexes'/(sid+'.sqlite')
                else:
                    ref=m.store.snapshot(sid).files['a.txt']['chunks'][0];path=m.store.object_path(ref['id'])
                raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
                with self.assertRaises(ValueError):m.lookup('file:a.txt')
