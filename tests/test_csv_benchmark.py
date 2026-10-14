from contextlib import redirect_stderr
import hashlib
import importlib.util
import io
from pathlib import Path
import random
import tempfile
import unittest

from rkv1.controlled import implementation_checksums
from rkv1.csv_benchmark import BASELINE_SHA256, csv_benchmark
from rkv1.experiments.csv_v0_3 import csv_columns_decode as legacy_decode
from rkv1.transforms import csv_columns_decode, csv_columns_encode


class CSVBenchmarkTests(unittest.TestCase):
    def test_legacy_snapshot_and_nested_implementation_guard(self):
        path = Path(__file__).parents[1] / "rkv1/experiments/csv_v0_3.py"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), BASELINE_SHA256)
        self.assertIn("experiments/csv_v0_3.py", implementation_checksums())

    def test_optimized_decoder_matches_frozen_decoder_on_wide_literal_tables(self):
        rng = random.Random(42)
        values = [b"+001", b"-0", b"1.2300", b".5", b" -2e+03 ", b"0", b"001e-02"]
        for columns, rows in ((2, 3), (82, 400), (256, 100)):
            lines = [b"literal header" + b"\r\n"]
            for row in range(rows):
                lines.append(b";".join(rng.choice(values) for _ in range(columns)) + (b"\r\n" if row % 2 else b"\n"))
            raw = b"".join(lines) + b"boundary suffix"
            coded = csv_columns_encode(raw)
            self.assertIsNotNone(coded)
            self.assertEqual(csv_columns_decode(coded, len(raw)), legacy_decode(coded, len(raw)))
            self.assertEqual(csv_columns_decode(coded, len(raw)), raw)

    def test_cr_only_bytes_fall_back_without_normalization(self):
        self.assertIsNone(csv_columns_encode(b"a;b\r1;2\r3;4\r"))

    @unittest.skipUnless(importlib.util.find_spec("zstandard"), "Optional zstandard not installed")
    def test_pair_uses_same_archive_queries_and_exact_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.mkdir()
            (source / "a.csv").write_bytes(b"x;y\n" + b"1.00;2.00\n" * 1000)
            with redirect_stderr(io.StringIO()):
                report = csv_benchmark(source, rounds=1, queries=2, warmup_queries=1)
            self.assertEqual(report["verified_measured_roundtrips"], 6)
            self.assertEqual(report["verified_warmup_roundtrips"], 6)
            for codec in ("zlib", "zstd"):
                pair = [r for r in report["results"] if r["configuration"]["compression"] == codec and r["variant"] != "plain"]
                self.assertEqual(pair[0]["storage"]["archive_sha256"], pair[1]["storage"]["archive_sha256"])
                for mode in ("open_reader", "open_and_read"):
                    a = next(t for t in pair[0]["range_trials"] if t["mode"] == mode)
                    b = next(t for t in pair[1]["range_trials"] if t["mode"] == mode)
                    self.assertEqual(a["groups"]["byte_weighted"]["request_sha256"], b["groups"]["byte_weighted"]["request_sha256"])
                self.assertTrue(all(t["bytewise_verified"] for r in pair for t in r["decode_trials"]))
