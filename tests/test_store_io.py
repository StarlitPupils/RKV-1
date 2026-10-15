import hashlib
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from rkv1.store import Store, OBJECT, _publish, _publish_rename, verify
from rkv1.store_v0_8 import Store as FrozenStore
from rkv1.store_benchmark import _fingerprint


class StoreIOTests(unittest.TestCase):
    def test_frozen_reference_and_all_io_policies_produce_identical_bytes(self):
        module = Path(__file__).resolve().parents[1] / "rkv1/store_v0_8.py"
        self.assertEqual(hashlib.sha256(module.read_bytes()).hexdigest(),
                         "89213a7f3d95d13f0005bc9e8fb1c42fee11b0e5f27e4887750f0e1e6ec9afc4")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source"; source.mkdir()
            stores = [FrozenStore.create(root / "frozen", compression="zlib", chunker="gear-v1", chunk_size=4096)]
            for io in ("reference", "bounded"):
                for pub in (("link", "rename") if os.name == "nt" else ("link",)):
                    stores.append(Store.create(root / f"{io}-{pub}", compression="zlib", chunker="gear-v1",
                                                chunk_size=4096, io_backend=io, publisher=pub))
            raw = random.Random(901).randbytes(120000)
            for i in (0, 1):
                (source / "a").write_bytes(raw if i == 0 else raw[:7011] + b"inserted" + raw[7011:])
                results = [s.add(source, label=str(i)) for s in stores]
                self.assertTrue(all(r == results[0] for r in results))
                self.assertTrue(all(_fingerprint(s.root) == _fingerprint(stores[0].root) for s in stores))
                for store, result in zip(stores, results):
                    reader = store.snapshot(result["snapshot_id"])
                    self.assertTrue(reader.process()["verified"])
                    self.assertEqual(reader.read_range("a", 4090, 80), (source / "a").read_bytes()[4090:4170])

    def test_bounded_exact_eof_stored_and_raw_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source"; source.mkdir()
            raw = random.Random(7).randbytes(10000); (source / "a").write_bytes(raw)
            store = Store.create(root / "cas", compression="raw", chunk_size=4096, io_backend="bounded")
            first = store.add(source); reader = store.snapshot(first["snapshot_id"])
            ref = reader.files["a"]["chunks"][0]; path = store.object_path(ref["id"]); good = path.read_bytes()
            for bad in (good[:-1], good + b"trailing", good + b"x" * 5000):
                path.write_bytes(bad)
                with self.assertRaisesRegex(ValueError, "size"):
                    reader.read_range("a", 0, 1)
                with self.assertRaises(ValueError): store.add(source, label="bad")
                self.assertEqual(store.stats()["snapshot_count"], 1)
            bad = bytearray(good); bad[-1] ^= 1; path.write_bytes(bad)
            with self.assertRaisesRegex(ValueError, "stored SHA-256"): reader.process()
            header = list(OBJECT.unpack(bad[:OBJECT.size])); header[-1] = hashlib.sha256(bad[OBJECT.size:]).digest()
            path.write_bytes(OBJECT.pack(*header) + bad[OBJECT.size:])
            with self.assertRaisesRegex(ValueError, "raw SHA-256"): reader.process()
            path.write_bytes(good)
            self.assertTrue(reader.process()["verified"])

    def test_invalid_io_options_fail_before_creating_store(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "cas"
            cases = [("bad", "link"), ("reference", "replace")]
            if os.name != "nt": cases.append(("reference", "rename"))
            for io, pub in cases:
                with self.assertRaises(ValueError): Store.create(root, compression="zlib", io_backend=io, publisher=pub)
                self.assertFalse(root.exists())

    def test_both_publishers_keep_fsync_and_never_replace(self):
        publishers = [_publish] + ([_publish_rename] if os.name == "nt" else [])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for i, publish in enumerate(publishers):
                path = root / str(i)
                with patch("rkv1.store.os.fsync", side_effect=OSError("failed sync")):
                    with self.assertRaisesRegex(OSError, "failed sync"): publish(path, b"payload")
                self.assertFalse(path.exists()); self.assertFalse(list(root.glob(".pending-*")))
                publish(path, b"original")
                with self.assertRaises(FileExistsError): publish(path, b"different")
                self.assertEqual(path.read_bytes(), b"original")
                self.assertFalse(list(root.glob(".pending-*")))

    def test_racing_publishers_keep_one_complete_winner(self):
        publishers = [_publish] + ([_publish_rename] if os.name == "nt" else [])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for i, publish in enumerate(publishers):
                path = root / str(i)
                payloads = [bytes([n]) * 9000 for n in range(4)]
                def attempt(data):
                    try:
                        publish(path, data)
                        return data
                    except FileExistsError:
                        return None
                with ThreadPoolExecutor(max_workers=4) as pool:
                    winners = [data for data in pool.map(attempt, payloads) if data is not None]
                self.assertEqual(len(winners), 1)
                self.assertEqual(path.read_bytes(), winners[0])
                self.assertFalse(list(root.glob(".pending-*")))

    def test_matched_io_campaign_and_evidence_release_pins(self):
        from rkv1.evidence_versions import VERSIONS, PROMPTS
        from rkv1.io_benchmark import io_benchmark, matrix
        self.assertEqual(list(VERSIONS), ["v1.2", "v1.3", "v1.4"])
        self.assertEqual(len({v["annotations"] for v in VERSIONS.values()}), 3)
        self.assertEqual(len(PROMPTS), 64)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); sources = []
            raw = random.Random(900).randbytes(70000)
            for i in (0, 1):
                source = root / f"v{i}"; source.mkdir(); sources.append(source)
                (source / "a").write_bytes(raw if i == 0 else raw[:7011] + b"insert" + raw[7011:])
            result = io_benchmark(sources, dataset="smoke", configs=matrix(compression="zlib", scale=4096),
                                  rounds=1, queries=2, warmup_queries=1)
            self.assertEqual(len(result["results"]), 8 if os.name == "nt" else 6)
            self.assertTrue(all(c["identical_complete_trees_and_ledgers"] for c in result["io_submission_comparisons"]))

    @unittest.skipUnless(os.name == "nt", "Windows no-replace rename")
    def test_rename_failed_snapshot_preserves_history_and_counts_orphans(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source"; source.mkdir()
            (source / "a").write_bytes(b"old" * 5000)
            store = Store.create(root / "cas", compression="zlib", chunk_size=4096,
                                 io_backend="bounded", publisher="rename")
            first = store.add(source, label="old"); before = store.stats()
            (source / "a").write_bytes(b"new" * 5000)
            def fail(path, data):
                if path.parent.name == "snapshots": raise OSError("failed snapshot")
                return _publish_rename(path, data)
            with patch("rkv1.store._publish_rename", side_effect=fail):
                with self.assertRaisesRegex(OSError, "failed snapshot"): store.add(source, label="new")
            after = store.stats()
            self.assertGreater(after["object_bytes"], before["object_bytes"])
            self.assertEqual(after["snapshot_count"], 1)
            self.assertTrue(verify(store.root, first["snapshot_id"], io_backend="bounded")["verified"])
