import hashlib
import importlib.util
import io
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from rkv1.chunking import chunks, profile
from rkv1.core import assert_tree_equal, digest
from rkv1.store import Store, OBJECT, SNAPSHOT_MAGIC, _record, unpack, verify


class ChunkingTests(unittest.TestCase):
    def test_buffers_determinism_and_bounds(self):
        rng = random.Random(711)
        for raw in (b"", b"x", b"\0" * 40000, rng.randbytes(100000)):
            for mode in ("fixed", "gear-v1"):
                settings = profile(mode, 4096)
                expected = list(chunks(io.BytesIO(raw), settings))
                self.assertEqual(b"".join(expected), raw)
                for buffer in (1, 17, 8192):
                    self.assertEqual(list(chunks(io.BytesIO(raw), settings, read_size=buffer)), expected)
                for item in expected[:-1]:
                    self.assertTrue(settings.get("min_size", 4096) <= len(item) <= settings.get("max_size", 4096))
        for mode, size in (("fixed", True), ("gear-v1", 5000), ("other", 4096), ("gear-v1", 8388608)):
            with self.assertRaises(ValueError):
                profile(mode, size)

    def test_middle_insertion_resynchronizes_on_seeded_data(self):
        raw = random.Random(123).randbytes(500000)
        changed = raw[:7011] + b"inserted bytes\0" + raw[7011:]
        def ids(data, mode):
            return {digest(b) for b in chunks(io.BytesIO(data), profile(mode, 4096))}
        old_cdc, new_cdc = ids(raw, "gear-v1"), ids(changed, "gear-v1")
        old_fixed, new_fixed = ids(raw, "fixed"), ids(changed, "fixed")
        self.assertGreater(len(old_cdc & new_cdc) / len(old_cdc), .8)
        self.assertLess(len(old_fixed & new_fixed) / len(old_fixed), .1)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.source = self.root / "source"; self.source.mkdir()

    def test_profiles_versions_and_real_physical_reuse(self):
        raw = random.Random(9).randbytes(160000)
        (self.source / "a.bin").write_bytes(raw)
        (self.source / "duplicate.bin").write_bytes(raw)
        (self.source / "empty").write_bytes(b"")
        codecs = ["raw", "zlib"] + (["zstd"] if importlib.util.find_spec("zstandard") else [])
        for codec in codecs:
            for mode in ("fixed", "gear-v1"):
                with self.subTest(codec=codec, mode=mode):
                    store = Store.create(self.root / f"{codec}-{mode}", compression=codec, chunker=mode, chunk_size=4096)
                    initial = store.stats()["logical_file_bytes"]
                    first = store.add(self.source, label="first")
                    before = store.stats(); second = store.add(self.source, label="second"); after = store.stats()
                    self.assertEqual(before["logical_file_bytes"] - initial, first["new_written_bytes"])
                    self.assertEqual(second["new_objects"], 0)
                    self.assertEqual(after["object_count"], before["object_count"])
                    self.assertEqual(after["logical_file_bytes"] - before["logical_file_bytes"], second["new_snapshot_bytes"])
                    repeated = store.add(self.source, label="first")
                    self.assertEqual(repeated["snapshot_id"], first["snapshot_id"])
                    self.assertEqual(repeated["new_written_bytes"], 0)
                    reader = store.snapshot(first["snapshot_id"])
                    for start, length in ((0, 1), (4090, 80), (65530, 40), (len(raw), 0), (0, len(raw))):
                        self.assertEqual(reader.read_range("a.bin", start, length), raw[start:start + length])
                    self.assertEqual(reader.read_range("empty"), b"")
                    with self.assertRaises(ValueError): reader.read_range("a.bin", -1, 1)
                    verify(store.root, first["snapshot_id"])
                    restored = self.root / f"restore-{codec}-{mode}"
                    unpack(store.root, second["snapshot_id"], restored); assert_tree_equal(self.source, restored)

    def test_corruption_scope_and_reuse_fail_closed(self):
        (self.source / "a").write_bytes(random.Random(27).randbytes(40000))
        store = Store.create(self.root / "cas", compression="raw", chunk_size=4096)
        stats = store.add(self.source)
        reader = store.snapshot(stats["snapshot_id"])
        refs = reader.files["a"]["chunks"]
        bad = store.object_path(refs[-1]["id"]); saved = bad.read_bytes()
        changed = bytearray(saved); changed[-1] ^= 1; bad.write_bytes(changed)
        self.assertEqual(reader.read_range("a", 0, 1), (self.source / "a").read_bytes()[:1])
        with self.assertRaisesRegex(ValueError, "stored SHA-256"): reader.process()
        with self.assertRaises(ValueError): store.add(self.source, label="new")
        self.assertEqual(store.stats()["snapshot_count"], 1)
        # Repair the stored digest to show raw SHA remains independently required.
        header = list(OBJECT.unpack(changed[:OBJECT.size])); header[-1] = hashlib.sha256(changed[OBJECT.size:]).digest()
        bad.write_bytes(OBJECT.pack(*header) + changed[OBJECT.size:])
        with self.assertRaisesRegex(ValueError, "raw SHA-256"): reader.process()
        bad.write_bytes(saved)
        self.assertTrue(reader.process()["verified"])

    def test_manifest_paths_sizes_and_final_file_hash(self):
        (self.source / "a").write_bytes(b"x" * 20000)
        store = Store.create(self.root / "cas", compression="zlib", chunk_size=4096)
        good = store.snapshot(store.add(self.source)["snapshot_id"])
        edits = [lambda h: h["files"][0].update(path="../outside"),
                 lambda h: h["files"][0].update(size=True),
                 lambda h: h["files"][0]["chunks"][0].update(size=1),
                 lambda h: h.update(config_sha256="0" * 64)]
        for edit in edits:
            header = json.loads(json.dumps(good.header)); edit(header)
            raw = _record(SNAPSHOT_MAGIC, header); key = hashlib.sha256(raw[48:]).hexdigest()
            (store.root / "snapshots" / (key + ".rkvs")).write_bytes(raw)
            with self.assertRaises(ValueError): store.snapshot(key)
        header = json.loads(json.dumps(good.header)); header["files"][0]["sha256"] = "0" * 64
        raw = _record(SNAPSHOT_MAGIC, header); key = hashlib.sha256(raw[48:]).hexdigest()
        (store.root / "snapshots" / (key + ".rkvs")).write_bytes(raw)
        reader = store.snapshot(key)
        with self.assertRaisesRegex(ValueError, "file SHA-256"): reader.process()
        with self.assertRaises(ValueError): unpack(store.root, key, self.root / "failed-restore")
        self.assertFalse((self.root / "failed-restore").exists())
        with self.assertRaises(ValueError): store.add(store.root)
        with self.assertRaises(ValueError): unpack(store.root, good.snapshot_id, store.root / "restored")

    def test_failed_publish_counts_orphans_and_preserves_snapshots(self):
        import rkv1.store as module
        (self.source / "a").write_bytes(b"original" * 4000)
        store = Store.create(self.root / "cas", compression="zlib", chunk_size=4096)
        good = store.add(self.source, label="original")
        before = store.stats(); (self.source / "a").write_bytes(b"new bytes" * 4000)
        original = module._publish
        def fail_snapshot(path, data):
            if path.parent.name == "snapshots": raise OSError("simulated failed publication")
            return original(path, data)
        with patch.object(module, "_publish", side_effect=fail_snapshot):
            with self.assertRaises(OSError): store.add(self.source, label="failed")
        after = store.stats()
        self.assertEqual(after["snapshot_count"], before["snapshot_count"])
        self.assertGreater(after["object_bytes"], before["object_bytes"])
        self.assertTrue(verify(store.root, good["snapshot_id"])["verified"])
        with self.assertRaises(FileExistsError): Store.create(store.root)

    def test_original_version_pins_and_matched_protocol(self):
        from rkv1.version_data import VERSIONS
        from rkv1.store_benchmark import version_benchmark
        self.assertEqual(list(VERSIONS), ["0.1", "0.2", "0.3"])
        raw = random.Random(21).randbytes(140000)
        sources = []
        for i in range(2):
            source = self.root / f"v{i}"; source.mkdir(); sources.append(source)
            (source / "a").write_bytes(raw if i == 0 else raw[:7011] + b"insert" + raw[7011:])
        configs = [{"name": kind, "kind": kind, "chunker": "fixed", "chunk_size": 4096, "compression": "zlib"}
                   for kind in ("archive", "isolated", "shared")]
        result = version_benchmark(sources, configs=configs, rounds=1, queries=2, warmup_queries=1)
        self.assertEqual(len(result["results"]), 3)
        self.assertTrue(result["cas_encoding_equivalence"][0]["identical_object_union"])
        rows = {r["configuration"]["kind"]: r for r in result["results"]}
        self.assertLess(rows["shared"]["storage"]["logical_file_bytes"], rows["isolated"]["storage"]["logical_file_bytes"])
        self.assertEqual(len(result["sequence_execution_order"]), 6)
