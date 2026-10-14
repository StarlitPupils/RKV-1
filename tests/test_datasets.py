from pathlib import Path
import hashlib
import io
import tempfile
import unittest
import zipfile
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

    def test_zip_members_preserve_cr_bytes_and_reuse_pinned_sources(self):
        raw = b"1.00,2.00\r3.00,4.00"
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("table.csv", raw)
            archive.writestr("../ignored", b"must not be extracted")
        metadata = {"url": "https://example.invalid/pinned.zip", "sha256": hashlib.sha256(buffer.getvalue()).hexdigest(),
                    "files": {"table.csv": hashlib.sha256(raw).hexdigest()}}
        with tempfile.TemporaryDirectory() as temp, patch.dict("rkv1.datasets.ZIP_DATASETS", {"test_zip": metadata}), \
                patch("rkv1.datasets._download", return_value=buffer.getvalue()) as download:
            root = Path(temp) / "raw"
            fetch_public(root, "test_zip")
            self.assertEqual((root / "table.csv").read_bytes(), raw)
            self.assertFalse((Path(temp) / "ignored").exists())
            fetch_public(root, "test_zip")
            download.assert_called_once()

    def test_zip_checksum_failure_does_not_write_earlier_valid_member(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("a.csv", b"valid")
            archive.writestr("b.csv", b"changed")
        metadata = {"url": "https://example.invalid/pinned.zip", "sha256": hashlib.sha256(buffer.getvalue()).hexdigest(),
                    "files": {"a.csv": hashlib.sha256(b"valid").hexdigest(), "b.csv": hashlib.sha256(b"expected").hexdigest()}}
        with tempfile.TemporaryDirectory() as temp, patch.dict("rkv1.datasets.ZIP_DATASETS", {"test_zip": metadata}), \
                patch("rkv1.datasets._download", return_value=buffer.getvalue()):
            root = Path(temp) / "raw"
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                fetch_public(root, "test_zip")
            self.assertEqual(list(root.iterdir()), [])
