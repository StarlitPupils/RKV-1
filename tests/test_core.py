import hashlib
import json
from pathlib import Path
import random
import struct
import tempfile
import unittest
import zlib

from rkv1.core import (Archive, MAGIC, MAX_HEADER, PREFIX_SIZE, assert_tree_equal, digest,
                       pack, unpack, valid_path, validate_manifest, verify)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "input"
        self.source.mkdir()
        self.archive = self.root / "data.rkv"

    def write(self, path, content):
        target = self.source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def fixture(self):
        self.write("empty", b"")
        self.write("unicode/数据.txt", "物理：ΔE=mc²\r\n\x00".encode("utf-8"))
        self.write("binary", bytes(range(256)) * 7)
        self.write("noise", random.Random(42).randbytes(4097))
        self.write("zeros", b"\0" * 8192)
        self.write("copy", (self.source / "noise").read_bytes())

    def load(self):
        with Archive(self.archive) as reader:
            raw = self.archive.read_bytes()
            return reader.header, raw[reader.body_start:]

    def save(self, header, payload=b""):
        raw = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode()
        self.archive.write_bytes(MAGIC + struct.pack("<Q", len(raw)) + hashlib.sha256(raw).digest() + raw + payload)

    def test_roundtrip_varied_binary_and_chunk_boundaries(self):
        self.fixture()
        for size in [1, 7, 64, 1024, 1 << 20]:
            with self.subTest(size=size):
                pack(self.source, self.archive, size, overwrite=True)
                dest = self.root / f"out-{size}"
                unpack(self.archive, dest)
                assert_tree_equal(self.source, dest)
                self.assertEqual(verify(self.archive)["verified_files"], 6)

    def test_deterministic_archive(self):
        self.fixture()
        pack(self.source, self.archive, 512)
        second = self.root / "second.rkv"
        pack(self.source, second, 512)
        self.assertEqual(self.archive.read_bytes(), second.read_bytes())

    def test_dedup_and_raw_fallback(self):
        raw = random.Random(4).randbytes(1024)
        self.write("a", raw)
        self.write("b", raw)
        result = pack(self.source, self.archive, 1024)
        self.assertEqual((result["unique_chunks"], result["chunk_references"]), (1, 2))
        with Archive(self.archive) as reader:
            self.assertEqual(next(iter(reader.header["blocks"].values()))["codec"], "raw")

    def test_range_reads_and_invalid_bounds(self):
        raw = random.Random(7).randbytes(2500)
        self.write("a", raw)
        pack(self.source, self.archive, 512)
        with Archive(self.archive) as reader:
            for start, length in [(0, 0), (2500, 0), (511, 3), (0, 2500), (2000, 500)]:
                self.assertEqual(reader.read_range("a", start, length), raw[start:start+length])
            for start, length in [(-1, 1), (2500, 1), (0, -1), (True, 1)]:
                with self.assertRaises(ValueError):
                    reader.read_range("a", start, length)

    def test_empty_archive_and_empty_files(self):
        pack(self.source, self.archive)
        unpack(self.archive, self.root / "empty")
        self.assertEqual(list((self.root / "empty").iterdir()), [])
        self.write("empty", b"")
        pack(self.source, self.archive, overwrite=True)
        self.assertEqual(verify(self.archive)["verified_files"], 1)

    def test_incremental_is_self_contained(self):
        self.write("a", b"A" * 512 + b"B" * 512)
        pack(self.source, self.archive, 512)
        self.write("a", b"A" * 512 + b"C" * 512)
        new = self.root / "new.rkv"
        result = pack(self.source, new, 512, base=self.archive)
        self.assertEqual((result["reused_chunks"], result["new_chunks"]), (1, 1))
        self.archive.unlink()
        unpack(new, self.root / "out")
        assert_tree_equal(self.source, self.root / "out")

    def test_incremental_rejects_corrupt_reused_block(self):
        self.write("a", b"A" * 1024)
        pack(self.source, self.archive, 512)
        raw = bytearray(self.archive.read_bytes())
        raw[-1] ^= 1
        self.archive.write_bytes(raw)
        new = self.root / "new.rkv"
        with self.assertRaises(ValueError):
            pack(self.source, new, 512, base=self.archive)
        self.assertFalse(new.exists())

    def test_each_archive_byte_flip_detected(self):
        self.write("a", bytes(range(64)))
        pack(self.source, self.archive)
        original = self.archive.read_bytes()
        for offset in range(len(original)):
            damaged = bytearray(original)
            damaged[offset] ^= 1
            self.archive.write_bytes(damaged)
            with self.assertRaises(ValueError, msg=str(offset)):
                verify(self.archive)

    def test_every_truncation_and_trailing_bytes_rejected(self):
        self.write("a", b"A" * 1024)
        pack(self.source, self.archive)
        original = self.archive.read_bytes()
        for size in range(len(original)):
            self.archive.write_bytes(original[:size])
            with self.assertRaises(ValueError):
                verify(self.archive)
        self.archive.write_bytes(original + b"garbage")
        with self.assertRaises(ValueError):
            verify(self.archive)

    def test_failed_restore_is_not_published(self):
        self.write("a", b"A" * 128)
        pack(self.source, self.archive)
        header, body = self.load()
        header["files"][0]["sha256"] = "0" * 64
        self.save(header, body)
        destination = self.root / "out"
        with self.assertRaises(ValueError):
            unpack(self.archive, destination)
        self.assertFalse(destination.exists())

    def test_path_traversal_and_windows_aliases(self):
        for path in ["../x", "/x", "C:/x", "a\\b", "a/../b", "a//b", "./a", "a/", "a.", "a ", "NUL.txt", "a:stream", "a/CON", "a/COM¹", "a\0b"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                valid_path(path)
        valid_path("数据/a-b.txt")

    def test_duplicate_and_parent_file_paths_rejected(self):
        self.write("a", b"")
        pack(self.source, self.archive)
        header, _ = self.load()
        for path in ["a", "A", "a/b"]:
            bad = json.loads(json.dumps(header))
            bad["files"].append({**bad["files"][0], "path": path})
            with self.assertRaises(ValueError):
                validate_manifest(bad, 0)

    def test_wrong_schema_offsets_sizes_and_hashes(self):
        self.write("a", b"A" * 1024)
        pack(self.source, self.archive, 512)
        header, body = self.load()
        key = next(iter(header["blocks"]))
        for field, value in [("offset", 1), ("raw_size", 513), ("raw_size", True), ("stored_size", -1), ("codec", "unknown")]:
            bad = json.loads(json.dumps(header))
            bad["blocks"][key][field] = value
            self.save(bad, body)
            with self.assertRaises(ValueError):
                verify(self.archive)

    def test_duplicate_json_keys_and_oversize_header(self):
        raw = b'{"version":1,"version":1}'
        self.archive.write_bytes(MAGIC + struct.pack("<Q", len(raw)) + hashlib.sha256(raw).digest() + raw)
        with self.assertRaises(ValueError):
            verify(self.archive)
        self.archive.write_bytes(MAGIC + struct.pack("<Q", MAX_HEADER + 1))
        with self.assertRaises(ValueError):
            verify(self.archive)

    def test_output_bounds_and_extra_zlib_stream(self):
        raw = b"A" * 1024
        self.write("a", raw)
        pack(self.source, self.archive)
        header, body = self.load()
        for payload in [zlib.compress(raw * 2), body + zlib.compress(b"extra")]:
            bad = json.loads(json.dumps(header))
            next(iter(bad["blocks"].values()))["stored_size"] = len(payload)
            self.save(bad, payload)
            with self.assertRaises(ValueError):
                verify(self.archive)

    def test_overwrite_is_explicit_and_archive_outside_source(self):
        self.write("a", b"data")
        pack(self.source, self.archive)
        with self.assertRaises(FileExistsError):
            pack(self.source, self.archive)
        with self.assertRaises(ValueError):
            pack(self.source, self.source / "self.rkv")
        with self.assertRaises(FileExistsError):
            unpack(self.archive, self.source)

    def test_symlink_rejected(self):
        self.write("a", b"data")
        try:
            (self.source / "link").symlink_to(self.source / "a")
        except OSError:
            self.skipTest("Symlinks not permitted by this OS account")
        with self.assertRaises(ValueError):
            pack(self.source, self.archive)

    def test_seeded_randomized_roundtrips(self):
        rng = random.Random(20261014)
        for i in range(40):
            size = rng.randrange(4096)
            self.write("random", rng.randbytes(size))
            pack(self.source, self.archive, rng.randrange(1, 1024), overwrite=True)
            with Archive(self.archive) as reader:
                self.assertEqual(reader.read_range("random"), (self.source / "random").read_bytes())


if __name__ == "__main__":
    unittest.main()
