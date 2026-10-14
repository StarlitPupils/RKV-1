import hashlib
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
