from collections import Counter
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rkv1.core import digest
from rkv1.memory import Memory
from rkv1.evidence_path import trace
from scripts.path_layout_fixture import sources
from scripts.path_roles import PathRoles,ROLES


class PathRolesTests(unittest.TestCase):
    def test_original_proof_roles_conservation_once_and_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir()
            for name,raw in sources(0,'separated').items():(src/name).write_bytes(raw)
            m=Memory.create(root/'memory');sid=m.add(src)['snapshot_id']
            proof=trace(m,'doc:0',snapshot=sid)
            with patch.object(m.store,'block',wraps=m.store.block) as original:
                roles=PathRoles(m)
                with roles:actual=trace(m,'doc:0',snapshot=sid)
                result=roles.result();self.assertEqual(actual,proof)
                self.assertEqual(len(result['events']),original.call_count)
                self.assertTrue(result['methods_restored']);self.assertFalse(result['active'])
                counts=Counter()
                for event in result['events']:
                    self.assertIn(event['role'],ROLES);self.assertIsNone(event['error'])
                    self.assertEqual(event['returned_bytes'],event['expected_size']);counts.update(event['traffic'])
                self.assertEqual(dict(counts),roles.meter.data)
                self.assertGreater(sum(e['role']=='source_hit' for e in result['events']),0)
                before=dict(roles.meter.data);trace(m,'doc:0',snapshot=sid)
                self.assertEqual(roles.meter.data,before)

    def test_corruption_rejected_exception_cleanup_and_fresh_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir()
            raw=b'{"doc_id":0,"title":"test","abstract":["RKVVALUE a"]}\n';(src/'a.jsonl').write_bytes(raw)
            m=Memory.create(root/'memory');sid=m.add(src)['snapshot_id'];roles=PathRoles(m)
            with roles:trace(m,'doc:0',snapshot=sid)
            key=m.store.snapshot(sid).files['a.jsonl']['chunks'][0]['id'];path=m.store.object_path(key)
            bad=bytearray(path.read_bytes());bad[-1]^=1;path.write_bytes(bad)
            again=PathRoles(m)
            with self.assertRaises(ValueError),again:trace(m,'doc:0',snapshot=sid)
            rec=again.result();self.assertTrue(rec['methods_restored']);self.assertEqual(rec['final_role'],'other_trace')
            self.assertTrue(any(e['error']=='ValueError' for e in rec['events']))
            with self.assertRaises(ValueError):trace(m,'doc:0',snapshot=sid)


if __name__=='__main__':unittest.main()
