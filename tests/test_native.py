import hashlib
import io
import json
import os
from pathlib import Path
import random
import struct
import tempfile
import unittest

from rkv1.core import Archive, assert_tree_equal, pack, unpack, verify
from rkv1.native import NativeCSV, load_native, select_decoder
from rkv1.transforms import csv_columns_decode, csv_columns_encode


class GearConfigurationTests(unittest.TestCase):
    def test_backend_configuration_rejected_before_empty_add(self):
        from rkv1.chunking import chunks, profile
        from rkv1.store import Store
        for backend, library in (("rust", None), ("python", "unused.dll"), ("bad", None)):
            with self.assertRaises(ValueError):
                list(chunks(io.BytesIO(b""), profile("gear-v1"), backend=backend, native_library=library))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source"; source.mkdir()
            store = Store.create(root / "cas", compression="zlib", chunker="gear-v1")
            with self.assertRaises(ValueError):
                store.add(source, chunker_backend="rust")
            self.assertEqual(store.stats()["snapshot_count"], 0)


@unittest.skipUnless(os.environ.get("RKV_NATIVE_LIBRARY"), "native release library not selected")
class GearIntegrationTests(unittest.TestCase):
    def test_exact_boundaries_across_buffers_and_profiles(self):
        from rkv1.chunking import chunks, profile
        rng = random.Random(20261016)
        library = Path(os.environ["RKV_NATIVE_LIBRARY"]).resolve()
        for raw in (b"", b"x", bytes(range(256)) * 320, b"\0" * 350000, rng.randbytes(200000)):
            for scale in (4096, 65536):
                settings = profile("gear-v1", scale)
                expected = list(chunks(io.BytesIO(raw), settings))
                for read_size in (17, 8192, 1 << 20):
                    actual = list(chunks(io.BytesIO(raw), settings, read_size=read_size,
                                         backend="rust", native_library=library))
                    self.assertEqual(actual, expected)
        # One-byte short reads, and the largest permitted chunk profile.
        for raw, scale, buffer in ((rng.randbytes(4097), 4096, 1), (b"\0" * ((8 << 20) + 17), 2 << 20, 1 << 20)):
            settings = profile("gear-v1", scale)
            self.assertEqual(list(chunks(io.BytesIO(raw), settings)),
                             list(chunks(io.BytesIO(raw), settings, read_size=buffer,
                                         backend="rust", native_library=library)))

    def test_native_state_bounds_and_missing_gear_provenance(self):
        from rkv1.native import load_native_gear, NativeGear
        native = load_native_gear(str(Path(os.environ["RKV_NATIVE_LIBRARY"]).resolve()))
        for scale, rolling, count in ((True, 0, 0), (5000, 0, 0), (4096, -1, 1),
                                       (4096, 1, 0), (4096, 0, 16384), (4096, 0, True)):
            with self.assertRaises(ValueError):
                native.scan(b"x", scale, rolling, count)
        with self.assertRaises(ValueError):
            native.scan(b"x" * ((8 << 20) + 1), 4096)
        with tempfile.TemporaryDirectory() as temp:
            original = native.provenance
            root = Path(temp); copied = root / original["library"]
            copied.write_bytes(Path(os.environ["RKV_NATIVE_LIBRARY"]).read_bytes())
            metadata = {**original}; metadata.pop("gear_abi")
            (root / "native.json").write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Gear"):
                NativeGear(copied)

    def test_store_tree_identical_and_old_objects_still_verified(self):
        from rkv1.store import Store
        from rkv1.store_benchmark import _fingerprint
        library = Path(os.environ["RKV_NATIVE_LIBRARY"]).resolve()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source"; source.mkdir()
            raw = random.Random(131).randbytes(200000)
            stores = [Store.create(root / f"cas-{i}", compression="zlib", chunker="gear-v1", chunk_size=4096) for i in (0, 1)]
            for version in range(2):
                (source / "a").write_bytes(raw if version == 0 else raw[:7011] + b"insert" + raw[7011:])
                left = stores[0].add(source, label=str(version))
                right = stores[1].add(source, label=str(version), chunker_backend="rust", native_library=library)
                self.assertEqual(left, right)
                self.assertEqual(_fingerprint(stores[0].root), _fingerprint(stores[1].root))
                for store, stats in zip(stores, (left, right)):
                    self.assertTrue(store.snapshot(stats["snapshot_id"]).process()["verified"])
            for store in stores:
                ref = store.snapshot(left["snapshot_id"]).header["files"][0]["chunks"][0]
                target = store.object_path(ref["id"])
                changed = bytearray(target.read_bytes()); changed[-1] ^= 1; target.write_bytes(changed)
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    store.add(source, chunker_backend="rust", native_library=library)

    def test_paired_version_campaign_smoke(self):
        from rkv1.gear_benchmark import gear_benchmark
        library = Path(os.environ["RKV_NATIVE_LIBRARY"]).resolve()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); sources = []
            raw = random.Random(1).randbytes(40000)
            for i in (0, 1):
                source = root / f"v{i}"; source.mkdir(); sources.append(source)
                (source / "a").write_bytes(raw if i == 0 else raw[:17] + b"new" + raw[17:])
            result = gear_benchmark(sources, library, rounds=1, queries=2, warmup_queries=1,
                                    include_controls=False, compression="zlib", scale=4096)
            self.assertTrue(result["backend_encoding_equivalence"][0]["identical_complete_tree"])
            self.assertEqual(len(result["results"]), 2)


class NativeConfigurationTests(unittest.TestCase):
    def test_backend_is_explicit(self):
        self.assertIsNone(select_decoder("python", None))
        for backend, library in (("rust", None), ("python", "unused.dll"), ("unknown", None)):
            with self.assertRaises(ValueError):
                select_decoder(backend, library)

    def test_identity_checked_before_loading(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            library = root / "candidate.dll"
            library.write_bytes(b"untrusted placeholder")
            with self.assertRaises(ValueError):
                NativeCSV(library)
            info = {"abi": 1, "library": library.name, "source_commit": "0" * 40,
                    "sha256": "0" * 64, "bytes": library.stat().st_size}
            metadata = root / "native.json"
            metadata.write_text(json.dumps(info))
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                NativeCSV(library)
            for invalid in ([], {**info, "source_commit": 7}, {**info, "bytes": True}):
                metadata.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):
                    NativeCSV(library)


@unittest.skipUnless(os.environ.get("RKV_NATIVE_LIBRARY"), "native release library not selected")
class NativeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = Path(os.environ["RKV_NATIVE_LIBRARY"]).resolve()
        cls.native = load_native(str(cls.library))

    def test_numeric_literals_and_newlines_exact(self):
        rng = random.Random(20261015)
        values = [b"+001", b"-0", b"1.", b".5", b"1.e+00", b" -2.1E-9\t", b"001e-02", b"\t+.001E+090 "]
        for columns in (2, 9, 82, 256):
            for rows in (2, 50, 1000):
                for delimiter in (b",", b";"):
                    raw = b'"opaque header"\r\n' + b"".join(
                        delimiter.join(rng.choice(values) for _ in range(columns)) + (b"\r\n" if r % 2 else b"\n")
                        for r in range(rows)) + b"opaque\0tail"
                    coded = csv_columns_encode(raw)
                    self.assertIsNotNone(coded)
                    self.assertEqual(self.native.decode(coded, len(raw)), csv_columns_decode(coded, len(raw)))
                    self.assertEqual(self.native.decode(coded, len(raw)), raw)

    def test_malformed_payloads_rejected(self):
        raw = b"header\n1,2\r\n3,4\nopaque\0tail"
        coded = csv_columns_encode(raw)
        bad = [b"", coded[:27], coded[:-1], coded + b"\n1", b"invalid!" + coded[8:]]
        for offset, value in ((8, 0), (9, 1), (10, 0), (12, 1), (28 + 7 + 11, 2)):
            changed = bytearray(coded); changed[offset] = value; bad.append(bytes(changed))
        # Reject an invalid cell while retaining a valid header/length.
        changed = bytearray(coded); changed[-1] = ord("x"); bad.append(bytes(changed))
        for value in bad:
            with self.subTest(payload=value):
                with self.assertRaises(ValueError):
                    csv_columns_decode(value, len(raw))
                with self.assertRaises(ValueError):
                    self.native.decode(value, len(raw))
        for expected in (True, 0, -1, 8 * 1048576 + 1, len(raw) + 1):
            with self.assertRaises(ValueError):
                self.native.decode(coded, expected)

    def test_archive_backends_and_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source"; source.mkdir()
            raw = b"header\n" + b"".join(
                b",".join(f"{i % 97}.{c * 73:03}".encode() for c in range(12)) + b"\r\n" for i in range(2000))
            (source / "table.csv").write_bytes(raw)
            for unit in (None, 4096):
                archive = root / f"{unit}.rkv"
                stats = pack(source, archive, 65536, compression="zlib", transform="csv-columns-v1", unit_size=unit)
                self.assertGreater(stats["transformed_chunks"], 0)
                options = {"decoder_backend": "rust", "native_library": self.library}
                with Archive(archive) as python, Archive(archive, **options) as rust:
                    for start, length in ((0, len(raw)), (4090, 40), (65530, 40), (len(raw), 0)):
                        self.assertEqual(python.read_range("table.csv", start, length), rust.read_range("table.csv", start, length))
                    # Even a faulty inverse must still pass exact block/unit hashes.
                    rust._csv_decoder = lambda coded, expected: b"x" * expected
                    with self.assertRaisesRegex(ValueError, "SHA-256"):
                        rust.read_range("table.csv", 0, 1)
                verify(archive, **options)
                restored = root / f"restored-{unit}"
                unpack(archive, restored, **options)
                assert_tree_equal(source, restored)

    def test_released_archive_fixtures(self):
        with tempfile.TemporaryDirectory() as temp:
            for version in (1, 2):
                fixture = json.loads((Path(__file__).parent / f"fixtures/v{version}.json").read_text())
                archive = Path(temp) / f"{version}.rkv"
                archive.write_bytes(bytes.fromhex(fixture["archive_hex"]))
                with Archive(archive, decoder_backend="rust", native_library=self.library) as reader:
                    for name, raw in fixture["files_hex"].items():
                        self.assertEqual(reader.read_range(name), bytes.fromhex(raw))

    def test_matched_campaign_smoke(self):
        from rkv1.native_benchmark import native_benchmark
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"; source.mkdir()
            (source / "table.csv").write_bytes(b"a,b,c\n" + b"123,0.10,+001e-02\r\n" * 4000)
            config = {"layout": "units-4", "chunk_size": 65536, "unit_size": 4096, "compression": "zlib",
                      "transform": "csv-columns-v1", "deduplicate": True, "index_cache_bytes": 65536}
            result = native_benchmark(source, self.library, configs=[config], rounds=1, queries=2, warmup_queries=1)
            self.assertEqual(len(result["results"]), 2)
            left, right = result["results"]
            self.assertEqual(left["storage"], right["storage"])
            self.assertEqual(left["verified_measured_roundtrips"], 1)
            self.assertTrue(all(r == -1 for _, r in result["restore_execution_order"][:2]))
            for a, b in zip(left["range_trials"], right["range_trials"]):
                for group in a["groups"]:
                    self.assertEqual(a["groups"][group]["request_sha256"], b["groups"][group]["request_sha256"])
