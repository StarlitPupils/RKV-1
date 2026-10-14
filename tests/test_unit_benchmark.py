from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest

from rkv1.unit_benchmark import matrix, unit_benchmark


class UnitBenchmarkTests(unittest.TestCase):
    def test_matrix_retains_plain_small_block_and_cache_controls(self):
        configs = matrix("superconductivity")
        self.assertEqual(len(configs), 21)
        self.assertTrue(any(c["layout"] == "flat-16" and c["transform"] == "none" for c in configs))
        self.assertTrue(any(c["layout"] == "units-64-no-cache" and c["index_cache_bytes"] == 0 for c in configs))

    def test_workers_verify_units_match_requests_and_count_actual_decode_work(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"; source.mkdir()
            (source / "a").write_bytes(b"scientific exact evidence\r\n" * 400)
            common = {"compression": "zlib", "deduplicate": True, "transform": "none", "index_cache_bytes": 1 << 20}
            configs = [{**common, "layout": "flat", "chunk_size": 16384, "unit_size": None},
                       {**common, "layout": "units", "chunk_size": 16384, "unit_size": 4096}]
            with redirect_stderr(io.StringIO()):
                report = unit_benchmark(source, configs=configs, rounds=1, queries=2, warmup_queries=1)
            self.assertEqual(len(report["results"]), 2)
            plans = set()
            for row in report["results"]:
                self.assertTrue(row["bytewise_verified"])
                for trial in row["range_trials"]:
                    result = trial["groups"]["byte_weighted"]
                    plans.add(result["request_sha256"])
                    self.assertEqual(result["verified_requests"], 2)
                    if row["configuration"]["unit_size"]:
                        self.assertGreater(result["work"]["unit_decodes"], 0)
                        self.assertEqual(result["work"]["chunk_decodes"], 0)
            self.assertEqual(len(plans), 1)
