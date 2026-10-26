from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from rkv1.memory import Memory
from rkv1.memory_index import QueryResources,view


class MemoryBatchTests(unittest.TestCase):
    def fixture(self,root,profile='compact-budget-v3'):
        src=root/'source';src.mkdir();raw=b''.join(json.dumps({'doc_id':i,'title':'Synthetic '+str(i),'abstract':['Synthetic evidence.']}).encode()+b'\r\n' for i in range(40))
        (src/'a.jsonl').write_bytes(raw)
        other=json.dumps({'doc_id':100,'title':'Second synthetic source','abstract':['Distinct original source.']}).encode()+b'\n'
        (src/'b.jsonl').write_bytes(other)
        m=Memory.create(root/'memory',index_profile=profile);sid=m.add(src)['snapshot_id'];return m,src,sid

    def test_exact_budget_duplicate_keys_multiple_files_and_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            m,src,sid=self.fixture(Path(temp));keys=['doc:0','doc:1','doc:0'];expected=[m.lookup(k,snapshot=sid)['hits'] for k in keys]
            required=sum(h['locator']['length'] for group in expected for h in group)
            original=m.lookup
            with patch.object(m,'_verified_hits',wraps=m._verified_hits) as verifier:
                result=m.lookup_many(keys,snapshot=sid,max_source_bytes=required)
                self.assertEqual(verifier.call_count,3)
            self.assertEqual([x['hits'] for x in result['results']],expected);self.assertEqual(result['admitted_source_bytes'],required)
            self.assertEqual(m.lookup,original)
            with patch.object(m,'_verified_hits',wraps=m._verified_hits) as verifier:
                with self.assertRaisesRegex(ValueError,'source-byte budget exceeded'):m.lookup_many(keys,snapshot=sid,max_source_bytes=required-1)
                self.assertEqual(verifier.call_count,0)
            self.assertEqual(m.lookup_many(['doc:999'],snapshot=sid,max_source_bytes=0)['results'],[{'source_key':'doc:999','hits':[]}])
            all_keys=['doc:'+str(i) for i in range(32)]
            self.assertEqual(len(m.lookup_many(all_keys,snapshot=sid)['results']),32)

    def test_invalid_inputs_reject_before_manifest_and_unsupported_profiles(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);m,_,sid=self.fixture(root)
            bad=[([],sid,1),(['doc:0']*33,sid,1),('doc:0',sid,1),((k for k in ['doc:0']),sid,1),([''],sid,1),(['a\x00'],sid,1),(['x'*513],sid,1),(['doc:0'],None,1),(['doc:0'],'bad',1),(['doc:0'],sid,True),(['doc:0'],sid,-1),(['doc:0'],sid,(32<<20)+1)]
            with patch.object(m,'_manifest',side_effect=AssertionError('No manifest access')):
                for keys,snapshot,budget in bad:
                    with self.assertRaises(ValueError):m.lookup_many(keys,snapshot=snapshot,max_source_bytes=budget)
            for profile in ('full-v1','compact-delta-v2','compact-projection-v4'):
                sub=root/profile;sub.mkdir();other,_,old_sid=self.fixture(sub,profile)
                with self.assertRaisesRegex(ValueError,'v3 manifest'):other.lookup_many(['doc:0'],snapshot=old_sid)

    def test_closed_resources_readonly_fixed_old_sid_and_corrupt_source_rejects(self):
        with tempfile.TemporaryDirectory() as temp:
            m,src,old_sid=self.fixture(Path(temp));expected=m.lookup('doc:1',snapshot=old_sid)['hits']
            raw=(src/'a.jsonl').read_bytes().replace(b'Synthetic evidence.',b'Synthetic changed.')
            (src/'a.jsonl').write_bytes(raw);new_sid=m.add(src)['snapshot_id'];self.assertNotEqual(old_sid,new_sid)
            opened=[];resources=[]
            @contextmanager
            def observed(*args,**kwargs):
                with view(*args,**kwargs) as db:
                    opened.append(db)
                    try:yield db
                    finally:
                        self.assertEqual(db.execute('PRAGMA query_only').fetchone()[0],1)
                        with self.assertRaises(sqlite3.OperationalError):db.execute('DELETE FROM locators')
            class Tracked(QueryResources):
                def __enter__(self):resources.append(self);return super().__enter__()
            with patch('rkv1.memory_index.view',observed),patch('rkv1.memory_index.QueryResources',Tracked):
                result=m.lookup_many(['doc:1'],snapshot=old_sid)
                self.assertEqual(result['results'][0]['hits'],expected)
                self.assertNotEqual(m.lookup_many(['doc:1'],snapshot=new_sid)['results'][0]['hits'],expected)
                with self.assertRaises(ValueError):m.lookup_many(['doc:1'],snapshot=old_sid,max_source_bytes=0)
            self.assertEqual(len(opened),3)
            for db in opened:
                with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
            self.assertTrue(all(not r.snapshots and not r.deltas for r in resources))
            original=m.lookup
            with m.store.snapshot(old_sid) as snap:ref=snap.files['a.jsonl']['chunks'][0]
            path=m.store.object_path(ref['id']);damaged=bytearray(path.read_bytes());damaged[-1]^=1;path.write_bytes(damaged)
            with self.assertRaises(ValueError):m.lookup_many(['doc:1'],snapshot=old_sid)
            self.assertEqual(m.lookup,original)

    def test_maximum_duplicate_occurrences_and_new_request_bad_base_or_delta(self):
        with tempfile.TemporaryDirectory() as temp:
            m,src,sid=self.fixture(Path(temp),'compact-base-v3')
            hit=m.lookup('doc:0',snapshot=sid)['hits'][0]
            result=m.lookup_many(['doc:0']*32,snapshot=sid,max_source_bytes=32*hit['locator']['length'])
            self.assertEqual(len(result['results']),32)
            self.assertEqual(result['admitted_source_bytes'],32*hit['locator']['length'])
            (src/'a.jsonl').write_bytes((src/'a.jsonl').read_bytes().replace(b'Synthetic evidence.',b'Synthetic changed.',1))
            new=m.add(src)['snapshot_id'];manifest=m._manifest(new);self.assertTrue(manifest['deltas'])
            path=m.root/'indexes'/(manifest['deltas'][0]['sha256']+'.delta')
            raw=path.read_bytes();damaged=bytearray(raw);damaged[-1]^=1;path.write_bytes(damaged)
            with self.assertRaises(ValueError):m.lookup_many(['doc:0'],snapshot=new)
            path.write_bytes(raw)
            base=m.root/'indexes'/(manifest['base_snapshot_id']+'.sqlite')
            damaged=bytearray(base.read_bytes());damaged[-1]^=1;base.write_bytes(damaged)
            with self.assertRaises(ValueError):m.lookup_many(['doc:0'],snapshot=new)
