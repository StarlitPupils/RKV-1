import tempfile
from pathlib import Path
import unittest

from rkv1.benchmark import _worker, incremental_experiment


class BenchmarkTests(unittest.TestCase):
    def test_worker_checks_both_formats_and_records_samples(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.mkdir()
            (source / "data").write_bytes(b"scientific evidence\r\n" * 100)
            for method in ("tar-zlib-6", "rkv1-zlib-dedup"):
                row = _worker(source, method, 2, 1, 3, 42, 512)
                self.assertTrue(row["bytewise_verified"])
                self.assertEqual(len(row["encode_s"]["samples"]), 2)
                self.assertEqual(len(row["random_read_s"]["samples"]), 3)
                self.assertGreater(row["worker_peak_rss_bytes"], 0)
            experiment = incremental_experiment(source, 512)
            self.assertTrue(all(row["bytewise_verified"] for row in experiment["runs"]))
            self.assertGreater(experiment["runs"][1]["reused_chunks"], 0)
