import hashlib
import json
from pathlib import Path
import random
import struct
import tempfile
import unittest

from rkv1.codecs import decompress
from rkv1.core import Archive, MAGIC, assert_tree_equal, pack, unpack, verify
from rkv1.transforms import CSV_HEADER, CSV_MAGIC, csv_columns_decode, csv_columns_encode


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "input"
        self.source.mkdir()

    def test_released_v1_fixture_still_decodes(self):
        fixture = json.loads((Path(__file__).parent / "fixtures/v1.json").read_text("utf-8"))
        path = self.root / "v1.rkv"
        path.write_bytes(bytes.fromhex(fixture["archive_hex"]))
        with Archive(path) as reader:
            self.assertEqual(reader.header["version"], 1)
            for name, value in fixture["files_hex"].items():
                self.assertEqual(reader.read_range(name), bytes.fromhex(value))
        self.assertEqual(verify(path)["verified_files"], 3)
        new = self.root / "v2.rkv"
        unpack(path, self.root / "restored")
        stats = pack(self.root / "restored", new, 1024, base=path)
        self.assertEqual(stats["reused_chunks"], stats["unique_chunks"])
        verify(new)

    def test_all_profiles_dedup_modes_and_ranges(self):
        raw = b"scientific source data\r\n" * 100
        (self.source / "a").write_bytes(raw)
        (self.source / "b").write_bytes(raw)
        for codec in ("raw", "zlib", "zstd"):
            if codec == "zstd":
                try:
                    import zstandard
                except ImportError:
                    continue
            for dedup in (False, True):
                with self.subTest(codec=codec, dedup=dedup):
                    archive = self.root / f"{codec}-{dedup}.rkv"
                    stats = pack(self.source, archive, 512, compression=codec, deduplicate=dedup)
                    if not dedup:
                        self.assertEqual(stats["chunk_references"], stats["unique_chunks"])
                    with Archive(archive) as reader:
                        self.assertEqual(reader.read_range("a", 500, 40), raw[500:540])
                        self.assertEqual(reader.read_range("b"), raw)
                    restored = self.root / f"out-{codec}-{dedup}"
                    unpack(archive, restored)
                    assert_tree_equal(self.source, restored)

    def test_zstd_rejects_extra_frame_truncation_and_false_sizes(self):
        try:
            import zstandard as zstd
        except ImportError:
            self.skipTest("Zstd optional dependency unavailable")
        raw = b"abc" * 1000
        encoded = zstd.ZstdCompressor().compress(raw)
        self.assertEqual(decompress(encoded, "zstd", len(raw)), raw)
        for data, expected in [(encoded + encoded, len(raw)), (encoded[:-1], len(raw)), (encoded, 1),
                               (zstd.ZstdCompressor(write_content_size=False).compress(raw), len(raw))]:
            with self.assertRaises(ValueError):
                decompress(data, "zstd", expected)

    def test_no_dedup_corruption_and_policy_mismatch(self):
        (self.source / "a").write_bytes(b"A" * 1024)
        archive = self.root / "data.rkv"
        pack(self.source, archive, 512, deduplicate=False)
        with Archive(archive) as reader:
            header = reader.header
            payload = archive.read_bytes()[reader.body_start:]
        header["deduplicate"] = True
        encoded = json.dumps(header).encode()
        archive.write_bytes(MAGIC + struct.pack("<Q", len(encoded)) + hashlib.sha256(encoded).digest() + encoded + payload)
        with self.assertRaises(ValueError):
            verify(archive)

    def test_transform_preserves_literal_numbers_and_mixed_line_endings(self):
        raw = b'"a";"b";"c"\r\n+01.00; -0.0 ;1e-09\n002;3.1400;9E+2\r\n4.;.50;-0001\npartial'
        coded = csv_columns_encode(raw)
        self.assertIsNotNone(coded)
        self.assertEqual(csv_columns_decode(coded, len(raw)), raw)
        with self.assertRaises(ValueError):
            csv_columns_decode(coded + b"junk", len(raw))
        with self.assertRaises(ValueError):
            csv_columns_decode(coded, len(raw) + 1)

    def test_unsupported_csv_returns_none(self):
        for raw in [b"plain text\nmore text\nend\n", b'h1,h2\n"1",2\n3,4\n',
                    b"h1,h2\n1,2\n3,4,5\n", b"h1,h2\n1,NaN\n3,4\n", b"h1,h2\n1,2\n"]:
            self.assertIsNone(csv_columns_encode(raw))

    def test_malformed_transform_dimensions_and_excess_cells(self):
        raw = b"a,b\n1,2\n3,4\n"
        coded = bytearray(csv_columns_encode(raw))
        coded[9] = 1  # Reserved flags must be zero.
        with self.assertRaises(ValueError):
            csv_columns_decode(bytes(coded), len(raw))
        excessive = CSV_MAGIC + CSV_HEADER.pack(ord(","), 0, 2, 2, 0, 0, 1024) + b"\0\0" + b"\n" * 100000
        with self.assertRaises(ValueError):
            csv_columns_decode(excessive, 1024)

    def test_csv_randomized_exact_roundtrip(self):
        rng = random.Random(20261014)
        values = [b"1.00", b"-0", b"+0002", b" .3 ", b"1e-06", b"9.99E+07"]
        for _ in range(40):
            rows, cols = rng.randrange(2, 30), rng.randrange(2, 10)
            delimiter = rng.choice([b",", b";"])
            raw = b"boundary/header\n"
            for r in range(rows):
                raw += delimiter.join(rng.choice(values) for _ in range(cols)) + rng.choice([b"\n", b"\r\n"])
            raw += b"tail"
            coded = csv_columns_encode(raw)
            self.assertEqual(csv_columns_decode(coded, len(raw)), raw)

    def test_csv_archive_adaptive_selection_and_random_read(self):
        raw = b'"x";"y"\n' + b"".join(f"{i % 3};{i % 23}.0000\n".encode() for i in range(10000))
        (self.source / "table.csv").write_bytes(raw)
        archive = self.root / "csv.rkv"
        stats = pack(self.source, archive, 65536, transform="csv-columns-v1")
        self.assertGreater(stats["transformed_chunks"], 0)
        with Archive(archive) as reader:
            self.assertEqual(reader.read_range("table.csv", 65530, 40), raw[65530:65570])
            self.assertEqual(reader.read_range("table.csv"), raw)
        unpack(archive, self.root / "restored")
        assert_tree_equal(self.source, self.root / "restored")

    def test_base_policy_change_is_rejected(self):
        (self.source / "a").write_bytes(b"source" * 100)
        archive = self.root / "base.rkv"
        pack(self.source, archive)
        with self.assertRaises(ValueError):
            pack(self.source, self.root / "new.rkv", base=archive, compression="raw")


if __name__ == "__main__":
    unittest.main()
