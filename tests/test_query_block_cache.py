import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from rkv1.store import Store
from scripts.query_block_cache import QueryBlockCache


class QueryBlockCacheTests(unittest.TestCase):
    def setup_store(self,root):
        src=root/'source';src.mkdir();(src/'a').write_bytes(b'A'*256);(src/'b').write_bytes(b'B'*256)
        store=Store.create(root/'store',compression='zlib');sid=store.add(src)['snapshot_id']
        refs=store.snapshot(sid).files
        return store,[refs[n]['chunks'][0] for n in ('a','b')]

    def test_hit_lru_and_oversize(self):
        with tempfile.TemporaryDirectory() as temp:
            store,(a,b)=self.setup_store(Path(temp))
            with patch.object(store,'block',wraps=store.block) as original:
                cache=QueryBlockCache(store,256)
                with cache:
                    self.assertEqual(store.block(a['id'],256),b'A'*256)
                    self.assertEqual(store.block(a['id'],256),b'A'*256)
                    store.block(b['id'],256);store.block(a['id'],256)
                    self.assertEqual(original.call_count,3);self.assertEqual(cache.data['hits'],1)
                    self.assertEqual(cache.data['evictions'],2);self.assertEqual(cache.payload,256)
                self.assertEqual(cache.result()['retained_payload_bytes_after_scope'],0)
                store.block(a['id'],256);self.assertEqual(original.call_count,4)
            small=QueryBlockCache(store,128)
            with small:store.block(a['id'],256);store.block(a['id'],256)
            self.assertEqual(small.data['oversize'],2);self.assertEqual(small.data['hits'],0)

    def test_wrong_size_and_cached_corruption_raise_and_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            store,(a,_)=self.setup_store(Path(temp));original=store.block;cache=QueryBlockCache(store)
            with self.assertRaises(ValueError),cache:
                store.block(a['id'],256);store.block(a['id'],255)
            self.assertEqual(store.block,original);self.assertEqual(cache.payload,0)
            with self.assertRaises(ValueError),QueryBlockCache(store) as bad:
                store.block(a['id'],256);bad.blocks[(a['id'],256)]=b'x'*256;store.block(a['id'],256)
            self.assertEqual(store.block,original)

    def test_new_scope_revalidates_changed_file(self):
        with tempfile.TemporaryDirectory() as temp:
            store,(a,_)=self.setup_store(Path(temp))
            with QueryBlockCache(store):store.block(a['id'],256)
            path=store.object_path(a['id']);raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
            with QueryBlockCache(store),self.assertRaises(ValueError):store.block(a['id'],256)
