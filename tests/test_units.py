import hashlib
import importlib.util
import json
from pathlib import Path
import random
import struct
import tempfile
import unittest
from unittest.mock import patch

from rkv1.core import Archive, MAGIC, assert_tree_equal, pack, unpack, verify
from rkv1.units import ENTRY


class UnitArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()

    def rewrite(self, archive, edit_header=None, edit_index=None):
        with Archive(archive) as reader:
            header = reader.header
            payload = bytearray(archive.read_bytes()[reader.body_start:])
        if edit_index:
            meta = next(iter(header["blocks"].values()))
            start = meta["offset"]
            index = bytearray(payload[start:start + meta["index_size"]])
            edit_index(index)
            payload[start:start + len(index)] = index
            meta["index_sha256"] = hashlib.sha256(index).hexdigest()
        if edit_header:
            edit_header(header)
        encoded = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
        archive.write_bytes(MAGIC + struct.pack("<Q", len(encoded)) + hashlib.sha256(encoded).digest() + encoded + payload)

    def test_v2_released_core_fixture_and_default_writer_remain_identical(self):
        fixture = json.loads((Path(__file__).parent / "fixtures/v2.json").read_text("utf-8"))
        archive = self.root / "v2.rkv"
        archive.write_bytes(bytes.fromhex(fixture["archive_hex"]))
        with Archive(archive) as reader:
            self.assertEqual(reader.header["version"], 2)
            for name, encoded in fixture["files_hex"].items():
                raw = bytes.fromhex(encoded)
                self.assertEqual(reader.read_range(name), raw)
                (self.source / name).write_bytes(raw)
        new = self.root / "default.rkv"
        pack(self.source, new, 65536, compression="zlib", transform="csv-columns-v1")
        self.assertEqual(new.read_bytes(), archive.read_bytes())

    def test_profiles_dedup_incremental_and_cross_boundaries(self):
        data = b'"x";"y"\r\n' + b"".join(f"{i % 7};+00{i % 31}.00\r\n".encode() for i in range(20000)) + b"tail"
        (self.source / "a.csv").write_bytes(data)
        (self.source / "b.csv").write_bytes(data)
        (self.source / "empty").write_bytes(b"")
        codecs = ["raw", "zlib"] + (["zstd"] if importlib.util.find_spec("zstandard") else [])
        for codec in codecs:
            for dedup in (True, False):
                for transform in (("none",) if codec == "raw" else ("none", "csv-columns-v1")):
                    with self.subTest(codec=codec, dedup=dedup, transform=transform):
                        name = f"{codec}-{dedup}-{transform}"
                        archive = self.root / (name + ".rkv")
                        stats = pack(self.source, archive, 16384, compression=codec, deduplicate=dedup,
                                     transform=transform, unit_size=4096)
                        self.assertEqual(stats["stored_bytes"], stats["metadata_bytes"] + stats["unit_index_bytes"] + stats["encoded_payload_bytes"])
                        with Archive(archive) as reader:
                            self.assertEqual(reader.header["version"], 3)
                            for offset, length in ((0, 1), (4090, 40), (16380, 40), (len(data) - 1, 1), (len(data), 0), (0, len(data))):
                                self.assertEqual(reader.read_range("a.csv", offset, length), data[offset:offset + length])
                            self.assertEqual(reader.read_range("empty"), b"")
                        out = self.root / (name + "-out")
                        unpack(archive, out)
                        assert_tree_equal(self.source, out)
                        copy = self.root / (name + "-copy.rkv")
                        reused = pack(self.source, copy, 16384, compression=codec, deduplicate=dedup,
                                      transform=transform, unit_size=4096, base=archive)
                        self.assertEqual(reused["reused_chunks"], reused["unique_chunks"])
                        self.assertEqual(copy.read_bytes(), archive.read_bytes())

    def test_partial_read_decodes_only_touched_units(self):
        raw = random.Random(42).randbytes(40000)
        (self.source / "a").write_bytes(raw)
        archive = self.root / "data.rkv"
        pack(self.source, archive, 32768, unit_size=4096, compression="raw")
        from rkv1.units import decode_unit
        with Archive(archive) as reader, patch("rkv1.core.decode_unit", wraps=decode_unit) as decoder:
            self.assertEqual(reader.read_range("a", 4100, 20), raw[4100:4120])
            self.assertEqual(decoder.call_count, 1)
            self.assertEqual(reader.read_range("a", 8190, 10), raw[8190:8200])
            self.assertEqual(decoder.call_count, 3)
            self.assertEqual(reader.read_range("a", 32760, 20), raw[32760:32780])
            self.assertEqual(decoder.call_count, 5)

    def test_unit_work_ledger_and_bounded_index_cache(self):
        raw = random.Random(44).randbytes(40000)
        (self.source / "a").write_bytes(raw)
        archive = self.root / "data.rkv"
        pack(self.source, archive, 16384, unit_size=4096, compression="raw")
        from rkv1.read_benchmark import touched_bytes
        from rkv1.units import validate_index
        with Archive(archive, index_cache_bytes=700) as reader, patch("rkv1.core.validate_index", wraps=validate_index) as checked:
            work = touched_bytes(reader.header, {"path": "a", "offset": 8190, "length": 10}, reader)
            self.assertEqual(work["decoded_raw_bytes"], 8192)
            self.assertEqual(work["unit_decodes"], 2)
            self.assertEqual(work["referenced_index_bytes"], 4 * ENTRY.size)
            self.assertEqual(checked.call_count, 1)
            reader.read_range("a", 0, 1)
            self.assertEqual(checked.call_count, 1)
            reader.read_range("a", 16384, 1)
            reader.read_range("a", 0, 1)
            self.assertEqual(checked.call_count, 3)
            self.assertLessEqual(reader._index_bytes, reader.index_cache_bytes)

    def test_untouched_corruption_is_scoped_and_full_verify_fails(self):
        raw = random.Random(43).randbytes(16000)
        (self.source / "a").write_bytes(raw)
        archive = self.root / "data.rkv"
        pack(self.source, archive, 16384, unit_size=4096, compression="raw")
        with Archive(archive) as reader:
            key = next(iter(reader.header["blocks"]))
            meta = reader.header["blocks"][key]
            _, offsets, _ = reader.unit_index(key)
            bad_offset = reader.body_start + meta["offset"] + offsets[2]
        stored = bytearray(archive.read_bytes())
        stored[bad_offset] ^= 1
        archive.write_bytes(stored)
        with Archive(archive) as reader:
            self.assertEqual(reader.read_range("a", 0, 16), raw[:16])
            with self.assertRaisesRegex(ValueError, "Unit SHA-256"):
                reader.read_range("a", 8192, 16)
        with self.assertRaises(ValueError):
            verify(archive)

    def test_index_corruption_detected_before_payload_read(self):
        (self.source / "a").write_bytes(b"x" * 12000)
        archive = self.root / "data.rkv"
        pack(self.source, archive, 16384, unit_size=4096)
        with Archive(archive) as reader:
            bad_offset = reader.body_start
        stored = bytearray(archive.read_bytes())
        stored[bad_offset] ^= 1
        archive.write_bytes(stored)
        with Archive(archive) as reader:
            with self.assertRaisesRegex(ValueError, "index SHA-256"):
                reader.read_range("a", 0, 1)

    def test_invalid_authenticated_entries_and_manifest_bounds_rejected(self):
        (self.source / "a").write_bytes(b"scientific bytes" * 900)
        edits = ((0, "<I", 0), (4, "<I", 999999), (8, "<I", 999999),
                 (12, "<B", 9), (13, "<B", 9), (14, "<H", 1))
        for position, fmt, value in edits:
            archive = self.root / f"invalid-{position}.rkv"
            pack(self.source, archive, 16384, unit_size=4096)
            self.rewrite(archive, edit_index=lambda b, p=position, f=fmt, v=value: struct.pack_into(f, b, p, v))
            with self.assertRaises(ValueError):
                verify(archive)
        for field, value in (("unit_count", 999999999), ("index_size", 1), ("codec", "raw")):
            archive = self.root / (field + ".rkv")
            pack(self.source, archive, 16384, unit_size=4096)
            self.rewrite(archive, edit_header=lambda h, f=field, v=value: next(iter(h["blocks"].values())).__setitem__(f, v))
            with self.assertRaises(ValueError):
                Archive(archive)

    def test_parent_hash_full_read_and_file_hash_remain_enforced(self):
        (self.source / "a").write_bytes(b"x" * 12000)
        archive = self.root / "data.rkv"
        pack(self.source, archive, 16384, unit_size=4096)
        def wrong_parent(header):
            key = next(iter(header["blocks"]))
            other = "0" * 64
            header["blocks"][other] = header["blocks"].pop(key)
            header["files"][0]["chunks"] = [other]
        self.rewrite(archive, edit_header=wrong_parent)
        with self.assertRaisesRegex(ValueError, "Block SHA-256"):
            verify(archive)

    def test_empty_archive_tail_units_cache_budget_and_invalid_policy(self):
        archive = self.root / "empty.rkv"
        pack(self.source, archive, 4096, unit_size=4096)
        self.assertEqual(verify(archive)["verified_files"], 0)
        (self.source / "tiny").write_bytes(b"a")
        pack(self.source, self.root / "tiny.rkv", 4096, unit_size=4096)
        with Archive(self.root / "tiny.rkv", index_cache_bytes=0) as reader:
            self.assertEqual(reader.read_range("tiny"), b"a")
            self.assertEqual(len(reader._indexes), 0)
        with self.assertRaises(ValueError):
            Archive(archive, index_cache_bytes=-1)
        for unit in (0, 1024, 8192, True):
            with self.assertRaises(ValueError):
                pack(self.source, self.root / "invalid.rkv", 4096, unit_size=unit)
        with self.assertRaisesRegex(ValueError, "unit size"):
            pack(self.source, self.root / "base-mismatch.rkv", 4096, base=archive)

    def test_failed_unit_restore_is_not_published(self):
        (self.source / "a").write_bytes(b"x" * 5000)
        archive = self.root / "data.rkv"
        pack(self.source, archive, 8192, unit_size=4096)
        stored = bytearray(archive.read_bytes()); stored[-1] ^= 1; archive.write_bytes(stored)
        out = self.root / "failed"
        with self.assertRaises(ValueError):
            unpack(archive, out)
        self.assertFalse(out.exists())
