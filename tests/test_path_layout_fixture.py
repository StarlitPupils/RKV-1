from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from rkv1.memory import Memory
from rkv1.evidence_path import trace
from scripts.evidence_path_fixture import corpus,audit
from scripts.path_layout_fixture import sources,manifest
from scripts.query_block_cache import QueryBlockCache


class PathLayoutTests(unittest.TestCase):
    def test_exact_records_and_fixed_geometry(self):
        frozen=json.loads(Path('docs/path-layout-inputs.json').read_text('utf-8'))
        self.assertEqual(manifest(),frozen)
        for epoch in range(13):
            files=sources(epoch,'separated')
            self.assertEqual(Counter(corpus(epoch).splitlines(keepends=True)),
                Counter(line for raw in files.values() for line in raw.splitlines(keepends=True)))
            for name,raw in files.items():
                self.assertTrue(32768<len(raw)<65536)
                for line in raw.splitlines():
                    key=json.loads(line)['doc_id']
                    if key<96:self.assertEqual(name,f'step-{key%3}.jsonl')
        with self.assertRaises(ValueError):sources(0,'other')

    def test_real_store_disjoint_blocks_and_same_proof_with_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir()
            for name,raw in sources(0,'separated').items():(src/name).write_bytes(raw)
            m=Memory.create(root/'memory');sid=m.add(src)['snapshot_id']
            files=m.store.snapshot(sid).files
            ids=[{c['id'] for c in entry['chunks']} for entry in files.values()]
            self.assertTrue(all(len(s)==1 for s in ids));self.assertEqual(len(set.union(*ids)),3)
            original=m.store.block
            for key in ('doc:0','doc:90','doc:93'):
                expected=trace(m,key,snapshot=sid)
                cache=QueryBlockCache(m.store,65536)
                with cache:actual=trace(m,key,snapshot=sid)
                self.assertEqual(actual,expected);self.assertEqual(actual['status'],'complete')
                self.assertEqual(audit(m,actual,snapshot=sid,root_key=key)['bindings'],3)
                self.assertEqual(cache.payload,0);self.assertEqual(m.store.block,original)
                self.assertGreaterEqual(cache.data['evictions'],2)


if __name__=='__main__':unittest.main()
