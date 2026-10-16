import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib

from rkv1.core import digest
from rkv1.memory import Memory,_json
from rkv1 import memory_index as index


class MemoryQueryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        self.docs=[{'doc_id':i,'title':f'calibration beacon {i}',
                    'abstract':['rare silver variants '*(1+i%4),'stable precision '+str(i)]} for i in range(64)]
        self.write()
        self.memory=Memory.create(self.root/'memory')
        self.base=self.memory.add(self.source,label='base')['snapshot_id']

    def write(self):
        (self.source/'corpus.jsonl').write_bytes(b''.join(_json(d)+b'\r\n' for d in self.docs))

    def update(self):
        self.docs[0]['abstract'][0]+=' PREFIXPROBE '*300
        self.docs[20]['abstract'][0]='negative shift'
        self.docs[40]['abstract'][0]+=' SECONDPROBE'
        self.docs[-1]['title']='changed calibration silver'
        self.write();return self.memory.add(self.source,label='shift')['snapshot_id']

    def materialized(self,sid,question):
        value=self.memory._manifest(sid)
        with index.view(self.memory,value) as db:
            return db.execute('SELECT l.key,l.path,l.offset,l.length,lower(hex(l.sha)),l.kind,bm25(evidence) FROM evidence JOIN locators l ON l.rowid=evidence.rowid WHERE evidence MATCH ? ORDER BY bm25(evidence),l.key LIMIT 20',(question,)).fetchall()

    def test_deferred_offsets_match_eager_full_view_for_crossing_and_negative_shifts(self):
        sid=self.update();value=self.memory._manifest(sid)
        self.assertGreaterEqual(len(index.load_delta(self.memory,value['deltas'][0])['relocations']),3)
        for question in ('calibration','silver','PREFIXPROBE','SECONDPROBE','absentword'):
            expected=self.materialized(sid,question)
            with patch.object(index,'relocate',side_effect=AssertionError('query rewrote locators')):
                found=self.memory.search(question,snapshot=sid,top_k=20)['hits']
            self.assertEqual([r[0] for r in expected],[h['key'] for h in found])
            for row,hit in zip(expected,found):
                self.assertEqual(tuple(row[1:5]),tuple(hit['locator'][k] for k in ('path','offset','length','sha256')))
                self.assertEqual(row[5],'scifact-jsonl')
                self.assertAlmostEqual(row[6],hit['rank'],places=12)
        self.assertFalse(self.memory.search('PREFIXPROBE',snapshot=self.base)['hits'])

    def test_snapshot_and_overlay_reuse_ends_at_each_request(self):
        sid=self.update();original=self.memory.store.snapshot
        with patch.object(self.memory.store,'snapshot',wraps=original) as opened:
            self.memory.search('silver',snapshot=sid)
            self.assertEqual([c.args[0] for c in opened.call_args_list].count(self.base),1)
            self.assertEqual([c.args[0] for c in opened.call_args_list].count(sid),1)
            opened.reset_mock();self.memory.search('silver',snapshot=sid)
            self.assertEqual(opened.call_count,2)
        value=self.memory._manifest(sid);desc=value['deltas'][0]
        path=self.memory.root/'indexes'/(desc['sha256']+'.delta')
        original_read=Path.read_bytes;reads=[]
        def read(p):
            if p==path:reads.append(p)
            return original_read(p)
        with patch.object(Path,'read_bytes',read):self.memory.search('silver',snapshot=sid)
        self.assertEqual(reads,[path])

    def test_corruption_after_a_successful_query_is_detected_on_the_next_query(self):
        sid=self.update();value=self.memory._manifest(sid)
        with self.memory.store.snapshot(sid) as snap:
            ref=snap.files['corpus.jsonl']['chunks'][0]['id']
        paths=[self.memory.root/'cas/snapshots'/(self.base+'.rkvs'),
               self.memory.root/'cas/snapshots'/(sid+'.rkvs'),
               self.memory.root/'indexes'/(self.base+'.sqlite'),
               self.memory.root/'indexes'/(value['deltas'][0]['sha256']+'.delta'),
               self.memory.store.object_path(ref)]
        for path in paths:
            self.assertTrue(self.memory.search('calibration',snapshot=sid)['hits'])
            raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
            try:
                with self.assertRaises((ValueError,zlib.error)):self.memory.search('calibration',snapshot=sid)
            finally:path.write_bytes(raw)

    def test_invalid_relocations_fail_even_when_query_has_no_matches(self):
        sid=self.update();value=self.memory._manifest(sid);desc=value['deltas'][0]
        original=index.load_delta(self.memory,desc)
        changes=[]
        bad=copy.deepcopy(original);bad['relocations'][0][4]+=1;changes.append(bad)
        bad=copy.deepcopy(original);bad['relocations'].append(bad['relocations'][0][:]);changes.append(bad)
        bad=copy.deepcopy(original);bad['relocations'][0][3]=-10**9;changes.append(bad)
        bad=copy.deepcopy(original);bad['relocations'][0][3]=True;changes.append(bad)
        path=self.memory.root/'manifests'/(sid+'.json');before=path.read_bytes()
        for bad in changes:
            raw=_json(bad);encoded=zlib.compress(raw,6);sha=digest(encoded)
            (self.memory.root/'indexes'/(sha+'.delta')).write_bytes(encoded)
            changed=copy.deepcopy(value);changed['deltas'][0]={**desc,'sha256':sha,'raw_bytes':len(raw)}
            path.write_bytes(_json(changed))
            try:
                with self.assertRaises(ValueError):self.memory.search('absentword',snapshot=sid)
            finally:path.write_bytes(before)

    def test_upserted_locators_are_not_shifted_twice(self):
        self.docs[0]['abstract'][0]+=' prefix'
        self.docs[31]['abstract'][0]+=' UPSERTPROBE'
        self.write();sid=self.memory.add(self.source,label='upserts')['snapshot_id']
        found=self.memory.search('UPSERTPROBE',snapshot=sid)['hits'][0]
        expected=self.materialized(sid,'UPSERTPROBE')[0]
        self.assertEqual(found['locator']['offset'],expected[2])
        self.assertTrue(found['source_bytes_verified'])

    def test_resources_close_and_clear_on_failure_without_cross_request_state(self):
        opened=[];original=self.memory.store.snapshot
        def tracked(sid):
            snap=original(sid);snap.close=lambda:opened.append(sid);return snap
        with patch.object(self.memory.store,'snapshot',side_effect=tracked):
            resources=index.QueryResources(self.memory)
            with self.assertRaisesRegex(RuntimeError,'injected'):
                with resources:
                    resources.snapshot(self.base);resources.snapshot(self.base)
                    raise RuntimeError('injected')
            self.assertEqual(opened,[self.base]);self.assertEqual(resources.snapshots,{})
            self.assertEqual(resources.deltas,{})


if __name__=='__main__':unittest.main()
