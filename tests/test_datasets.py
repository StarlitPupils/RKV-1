from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rkv1.datasets import fetch_public


class DatasetTests(unittest.TestCase):
    def test_changed_upstream_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "raw"
            root.mkdir()
            (root / "iris.csv").write_bytes(b"not the pinned dataset")
            with self.assertRaises(ValueError):
                fetch_public(root)

    def test_failed_download_does_not_write_new_data(self):
        with tempfile.TemporaryDirectory() as temp, patch("rkv1.datasets._download", side_effect=ValueError("checksum")):
            root = Path(temp) / "raw"
            with self.assertRaises(ValueError):
                fetch_public(root)
            self.assertEqual(list(root.iterdir()), [])
