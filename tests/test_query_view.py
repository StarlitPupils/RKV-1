from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from rkv1.memory import Memory
from rkv1.evidence_path import trace
from scripts.evidence_path_fixture import audit
from scripts.path_layout_fixture import sources
from scripts.query_view import QueryView
import scripts.query_view as view_module


class QueryViewTests(unittest.TestCase):
    def create(self,root,profile='compact-budget-v3'):
        src=root/'source';src.mkdir()
        for name,raw in sources(0,'separated').items():(src/name).write_bytes(raw)
        m=Memory.create(root/'memory',index_profile=profile);sid=m.add(src)['snapshot_id']
        return m,src,sid

    def test_original_proof_once_and_cleanup_and_fixed_sid(self):
        with tempfile.TemporaryDirectory() as temp:
            m,src,sid=self.create(Path(temp));proof=trace(m,'doc:0',snapshot=sid);original=m.lookup
            with patch.object(m,'_verified_hits',wraps=m._verified_hits) as verified,patch.object(view_module,'view',wraps=view_module.view) as builder:
                candidate=QueryView(m,sid)
                with candidate:
                    db=candidate.db;resources=candidate.resources;actual=trace(m,'doc:0',snapshot=sid)
                    with self.assertRaises(sqlite3.OperationalError):db.execute('DELETE FROM locators')
                    self.assertEqual(verified.call_count,3)
                    self.assertEqual(builder.call_count,1)
                    with self.assertRaises(ValueError):m.lookup('doc:0',snapshot='0'*64)
                    with self.assertRaises(ValueError):m.lookup('doc:0')
                self.assertEqual(actual,proof);self.assertEqual(audit(m,actual,snapshot=sid,root_key='doc:0')['bindings'],3)
                self.assertEqual(m.lookup,original);self.assertEqual(candidate.result()['view_builds'],1)
                self.assertTrue(candidate.result()['view_closed']);self.assertTrue(candidate.result()['resources_cleared'])
                self.assertEqual(resources.snapshots,{});self.assertEqual(resources.deltas,{})
                with self.assertRaises(RuntimeError):candidate.lookup('doc:0',snapshot=sid)
                with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
                with self.assertRaises(RuntimeError),candidate:pass
            for name,raw in sources(1,'separated').items():(src/name).write_bytes(raw)
            new=m.add(src)['snapshot_id']
            with QueryView(m,sid):self.assertEqual(trace(m,'doc:0',snapshot=sid),proof)
            with QueryView(m,new):self.assertNotEqual(trace(m,'doc:0',snapshot=new)['value'],proof['value'])

    def test_selected_source_corruption_mid_scope_and_next_scope_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            m,_,sid=self.create(Path(temp));original=m.lookup;candidate=QueryView(m,sid)
            with self.assertRaises(ValueError),candidate:
                m.lookup('doc:0',snapshot=sid)
                key=m.store.snapshot(sid).files['step-1.jsonl']['chunks'][0]['id'];path=m.store.object_path(key)
                raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
                m.lookup('doc:1',snapshot=sid)
            self.assertEqual(m.lookup,original);self.assertTrue(candidate.result()['view_closed'])
            with self.assertRaises(ValueError),QueryView(m,sid):trace(m,'doc:0',snapshot=sid)

    def test_new_scope_revalidates_base_delta_and_unsupported_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            m,src,sid=self.create(Path(temp),'compact-base-v3')
            for name,raw in sources(1,'separated').items():(src/name).write_bytes(raw)
            new=m.add(src)['snapshot_id'];manifest=m._manifest(new);self.assertTrue(manifest['deltas'])
            with QueryView(m,new):trace(m,'doc:0',snapshot=new)
            path=m.root/'indexes'/(manifest['deltas'][0]['sha256']+'.delta')
            raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
            original=m.lookup;bad=QueryView(m,new)
            with self.assertRaises(ValueError),bad:pass
            self.assertEqual(m.lookup,original);self.assertTrue(bad.result()['resources_cleared'])
        with tempfile.TemporaryDirectory() as temp:
            m,_,sid=self.create(Path(temp));manifest=m._manifest(sid)
            path=m.root/'indexes'/(manifest['base_snapshot_id']+'.sqlite');raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
            with self.assertRaises(ValueError),QueryView(m,sid):pass
        for profile in ('full-v1','compact-full-v2','compact-projection-v4'):
            with tempfile.TemporaryDirectory() as temp:
                m,_,sid=self.create(Path(temp),profile);original=m.lookup
                with self.assertRaises(ValueError),QueryView(m,sid):pass
                self.assertEqual(m.lookup,original)


if __name__=='__main__':unittest.main()
