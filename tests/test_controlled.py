import json
from pathlib import Path
import tempfile
import unittest

from rkv1.controlled import configuration, inventory, measure, request_groups


class ControlledTests(unittest.TestCase):
    def test_groups_include_cross_chunk_and_exclude_unavailable_categories(self):
        files = [{"path": "small", "bytes": 8192}, {"path": "large", "bytes": 2 << 20}]
        groups = request_groups(files, 65536, 100, 42)
        self.assertTrue(all(r["path"] == "small" for r in groups["small_file"]))
        self.assertTrue(all(r["path"] == "large" for r in groups["large_file"]))
        self.assertGreater(sum(r["path"] == "large" for r in groups["byte_weighted"]), 90)
        for request in groups["cross_chunk"]:
            self.assertNotEqual(request["offset"] // 65536, (request["offset"] + request["length"] - 1) // 65536)
        self.assertEqual(request_groups(files[:1], 65536, 3, 42)["cross_chunk"], [])

    def test_process_trials_verify_restoration_and_record_separate_phases(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.mkdir()
            (source / "a").write_bytes(b"scientific exact data\r\n" * 300)
            config = configuration("zlib", 512, False, queries=3)
            row = measure(source, config, repeats=2, warmups=0)
            self.assertTrue(row["bytewise_verified"])
            self.assertTrue(row["deterministic_archive_bytes"])
            self.assertEqual(len(row["encode_peak_rss_bytes"]["samples"]), 2)
            self.assertEqual(len(row["decode_peak_rss_bytes"]["samples"]), 2)
            self.assertEqual(row["storage"]["chunk_references"], row["storage"]["unique_chunks"])
            for mode in ("open_reader", "open_and_read"):
                self.assertEqual(row["range_reads"]["ranges"][mode]["cross_chunk"]["verified_requests"], 3)
            self.assertEqual(inventory(source)[0]["bytes"], (source / "a").stat().st_size)
