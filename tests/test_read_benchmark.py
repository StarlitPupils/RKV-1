from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest

from rkv1.core import pack
from rkv1.controlled import request_groups
from rkv1.read_benchmark import read_benchmark, round_seed, range_trial, touched_bytes


class ReadBenchmarkTests(unittest.TestCase):
    def test_paired_seeds_keep_non_crossing_queries_identical(self):
        files = [{"path": "small", "bytes": 8192}, {"path": "large", "bytes": 2 << 20}]
        seed = round_seed(42, 0, 0)
        small = request_groups(files, 65536, 10, seed)
        big = request_groups(files, 1048576, 10, seed)
        for group in ("byte_weighted", "small_file", "large_file"):
            self.assertEqual(small[group], big[group])
        self.assertNotEqual(small["cross_chunk"], big["cross_chunk"])
        self.assertNotEqual(seed, round_seed(42, 0, 1))
        self.assertNotEqual(seed, round_seed(42, 1, 0))

    def test_work_ledger_counts_partial_final_and_crossing_chunks(self):
        header = {"chunk_size": 4, "files": [{"path": "a", "size": 10, "chunks": ["x", "y", "z"]}],
                  "blocks": {"x": {"raw_size": 4, "stored_size": 3}, "y": {"raw_size": 4, "stored_size": 2},
                             "z": {"raw_size": 2, "stored_size": 2}}}
        self.assertEqual(touched_bytes(header, {"path": "a", "offset": 7, "length": 3}),
                         {"requested_bytes": 3, "chunk_decodes": 2, "decoded_raw_bytes": 6, "stored_payload_bytes": 4})
        self.assertEqual(touched_bytes(header, {"path": "a", "offset": 8, "length": 0})["chunk_decodes"], 0)

    def test_repeated_workers_pair_modes_and_separate_warmup_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.mkdir()
            (source / "science.txt").write_bytes(b"exact scientific evidence\r\n" * 600)
            with redirect_stderr(io.StringIO()):
                report = read_benchmark(source, sessions=1, rounds=2, queries=3, warmup_queries=1,
                                        codecs=("raw", "zlib"), chunks=(512, 1024))
            self.assertEqual(len(report["results"]), 4)
            self.assertIsNone(report["unmeasured"]["cold_os_cache"])
            fingerprints = {}
            for row in report["results"]:
                self.assertTrue(row["full_archive_verified"])
                self.assertEqual(len(row["trials"]), 4)
                for trial in row["trials"]:
                    self.assertTrue(trial["bytewise_verified"])
                    self.assertEqual(trial["cache"]["pre_read_bytes"], row["storage"]["stored_bytes"])
                    self.assertFalse(trial["cache"]["os_cache_evicted"])
                    for group in ("byte_weighted", "small_file", "cross_chunk"):
                        result = trial["groups"][group]
                        self.assertEqual(result["verified_requests"], 3)
                        self.assertEqual(result["verified_warmup_requests"], 1)
                        self.assertEqual(len(result["latency_s"]["samples"]), 3)
                        if trial["mode"] == "open_and_read":
                            for total, opened, read, closed in zip(result["latency_s"]["samples"],
                                                                 result["open_s"]["samples"], result["read_s"]["samples"],
                                                                 result["close_s"]["samples"]):
                                self.assertAlmostEqual(total, opened + read + closed)
                    self.assertIsNone(trial["groups"]["large_file"]["latency_s"])
                    key = trial["round"]
                    digest = trial["groups"]["byte_weighted"]["request_sha256"]
                    fingerprints.setdefault(key, digest)
                    self.assertEqual(fingerprints[key], digest)
                group = row["aggregate"]["open_reader"]["groups"]["byte_weighted"]
                self.assertEqual(group["verified_requests"], 6)
                self.assertEqual(len(group["round_p95_s"]["samples"]), 2)

    def test_comparison_rejects_changed_source(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.mkdir()
            file = source / "a"
            file.write_bytes(b"a" * 8192)
            archive = Path(temp) / "data.rkv"
            pack(source, archive, 512)
            file.write_bytes(b"b" * 8192)
            settings = {"mode": "open_reader", "chunk_size": 512, "queries": 2, "warmup_queries": 0,
                        "query_seed": 42, "session": 0, "round": 0}
            with self.assertRaisesRegex(ValueError, "byte-range mismatch"):
                range_trial(source, archive, settings)

    def test_empty_inputs_and_invalid_controls_fail_before_trials(self):
        with tempfile.TemporaryDirectory() as temp:
            for options in ({"sessions": 0}, {"rounds": 0}, {"queries": 0}, {"rounds": 1.5},
                            {"warmup_queries": -1}, {"codecs": ("invalid",)}, {"chunks": (0,)},
                            {"chunks": (512, 512)}):
                with self.assertRaises(ValueError):
                    read_benchmark(temp, **options)
            with self.assertRaisesRegex(ValueError, "nonempty file"):
                read_benchmark(temp)
