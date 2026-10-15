"""Pinned original main annotation tables from three official Evidence Inference releases."""
import hashlib
from pathlib import Path
import tempfile
import urllib.request

from .controlled import inventory

VERSIONS = {
    "v1.2": {"commit": "7960e549a381f86ea848dee7beb11ecec1aa71af",
             "annotations": "0740089bd7328373cc85fcb97577929ad80a7972853e62c378526e3a513c7510"},
    "v1.3": {"commit": "ee792854566dd1d57ea44ff2248f5f6fa57da246",
             "annotations": "4575992073fce48e9d85fe22ba59e3fe3949245c12ad9ca2287338a765312cc2"},
    "v1.4": {"commit": "411fd36aa28425253dd6063f382c41e3191f7b41",
             "annotations": "d0b113693ca87b650ea4461cb6194e381c8b898f9382ca73bcb7df139801d6be"}}
PROMPTS = "6c429854720c375248cdb87913ce2df3c3bc5c26d3276134349f61d4445f3dda"
RELEASES = "https://github.com/jayded/evidence-inference/releases"


def fetch_versions(root):
    root = Path(root).resolve(); root.mkdir(parents=True, exist_ok=True)
    records = []
    for version, spec in VERSIONS.items():
        output = root / version
        expected = {"annotations/annotations_merged.csv": spec["annotations"],
                    "annotations/prompts_merged.csv": PROMPTS}
        urls = {name: f"https://raw.githubusercontent.com/jayded/evidence-inference/{spec['commit']}/{name}"
                for name in expected}
        if not output.exists():
            with tempfile.TemporaryDirectory(prefix=".evidence-", dir=root) as temp:
                staged = Path(temp) / "version"; (staged / "annotations").mkdir(parents=True)
                for name, checksum in expected.items():
                    with urllib.request.urlopen(urls[name], timeout=60) as stream:
                        raw = stream.read((16 << 20) + 1)
                    if len(raw) > 16 << 20 or hashlib.sha256(raw).hexdigest() != checksum:
                        raise ValueError("Pinned Evidence Inference file SHA-256 mismatch")
                    (staged / name).write_bytes(raw)
                if not staged.resolve().is_relative_to(root) or not output.resolve().is_relative_to(root):
                    raise ValueError("Invalid staged Evidence Inference path")
                staged.rename(output)
        files = inventory(output)
        if {f["path"]: f["sha256"] for f in files} != expected:
            raise ValueError("Existing Evidence Inference files differ from pinned release")
        records.append({"version": version, "source": str(output.resolve()), "source_commit": spec["commit"],
                        "release_url": RELEASES + "/tag/" + version, "file_urls": urls, "files": files,
                        "license": "MIT (official repository LICENSE)",
                        "license_url": f"https://github.com/jayded/evidence-inference/blob/{spec['commit']}/LICENSE",
                        "scope": "Two original main merged annotation/prompt CSV tables; not full articles, supplementary tables or the whole repository",
                        "original_paths_and_bytes": True})
    return records
