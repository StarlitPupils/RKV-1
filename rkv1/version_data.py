"""Pinned original QASPER v0.1/v0.2/v0.3 release bytes, without reserialization."""
import hashlib
from pathlib import Path
import tarfile
import tempfile
import urllib.request

from .controlled import inventory

VERSIONS = {
    "0.1": {"archive": "cd0cb8911342966fcc3eb91947af149cb7cf80b4f253ff9a6f0333f4752080dd",
            "train": "706d426159900f216d68173d595975610392c8cb944f5eab714985e08f10e768",
            "dev": "bc30979b6caf991bdb45e483478e75699bd16fcdcf66b957fe433bb63bdd833a"},
    "0.2": {"archive": "3efc2682f5449a12cd9aec813ad09601eda772b9fe4b1d06cd55080f9d97c41f",
            "train": "9e7dd7c249e5b46214632975a780399802a2ff9db7d120fe7fc66de405e630a8",
            "dev": "1b2e2ac60314246698867d382c08104439658cb723482a042bf123f223c191a7"},
    "0.3": {"archive": "a28fdf966db827bcee3d873107d6b6669864fb7ca8fbf73a192f5e39191bdb5a",
            "train": "9458bfe76074a8fa8d1685af02bcc73537aa6d338ad20591dfaff1946bc88bf4",
            "dev": "2ae7ee62a65b1c4225791c70de80c2aad4e8998cf1fd4f09a53103db4f21af93"}}


def fetch_versions(root):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    records = []
    for version, expected in VERSIONS.items():
        output = root / ("v" + version)
        names = {f"qasper-{split}-v{version}.json": expected[split] for split in ("train", "dev")}
        url = f"https://qasper-dataset.s3-us-west-2.amazonaws.com/qasper-train-dev-v{version}.tgz"
        if output.exists():
            files = inventory(output)
            if {f["path"]: f["sha256"] for f in files} != names:
                raise ValueError("Existing QASPER version differs from pinned release")
        else:
            archive = root / ("v" + version + ".tgz")
            if archive.exists():
                encoded = archive.read_bytes()
            else:
                with urllib.request.urlopen(url, timeout=60) as stream:
                    encoded = stream.read((32 << 20) + 1)
            if len(encoded) > 32 << 20 or hashlib.sha256(encoded).hexdigest() != expected["archive"]:
                raise ValueError("Pinned QASPER archive SHA-256 mismatch")
            with tempfile.TemporaryDirectory(prefix=".qasper-", dir=root) as temp:
                staged = Path(temp) / "version"; staged.mkdir()
                tar_path = Path(temp) / "input.tgz"; tar_path.write_bytes(encoded)
                with tarfile.open(tar_path) as tar:
                    for name, checksum in names.items():
                        member = tar.getmember(name)
                        if not member.isfile() or member.size > 64 << 20:
                            raise ValueError("Invalid pinned QASPER member")
                        raw = tar.extractfile(member).read()
                        if hashlib.sha256(raw).hexdigest() != checksum:
                            raise ValueError("Pinned QASPER member SHA-256 mismatch")
                        (staged / name).write_bytes(raw)
                staged.rename(output)
            files = inventory(output)
        records.append({"version": version, "source": str(output.resolve()), "url": url,
                        "archive_sha256": expected["archive"], "files": files,
                        "license": "CC BY 4.0", "dataset_card": "https://huggingface.co/datasets/allenai/qasper",
                        "original_paths_and_bytes": True})
    return records
