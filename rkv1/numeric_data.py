"""Pinned small original binary recordings; no sample conversion or resampling."""
import hashlib
from pathlib import Path
import random
import tempfile
from urllib.request import urlopen

from .controlled import inventory

SPECS = {
    "eeg": {"base": "https://physionet.org/files/eegmmidb/1.0.0/",
        "page": "https://physionet.org/content/eegmmidb/1.0.0/",
        "files": {"S001/S001R01.edf": (1275936, "4743b736131a7e147c150e8b37711029b6cda5e356c4b3e8261a03cdcaaf8b0c")},
        "scope": "One original EDF+ recording S001R01; includes embedded header and annotation channel; not all EEGMMIDB",
        "layout": "EDF+ int16 little-endian signal samples; original header and annotations also retained as bytes"},
    "ecg": {"base": "https://physionet.org/files/ptbdb/1.0.0/",
        "page": "https://physionet.org/content/ptbdb/1.0.0/",
        "files": {"patient001/s0010_re.dat": (921600, "4e26a62c96e50eebd0eca7a11a4ad62ac8d7654e4de47acf2e0ce64be9565f20"),
                  "patient001/s0010_re.xyz": (230400, "0caffd208e17c5c597fb39c8416f85ce55726f3e8e9d5486a6331c9ec4451265"),
                  "patient001/s0010_re.hea": (2687, "30d2d5db5b7b735f7dc39e5cf3e60a433a868b53d24587c9820cf51aa1729b87")},
        "scope": "One original PTB record s0010_re, 12-lead dat, 3-lead xyz and unchanged header; not all PTBDB",
        "layout": "WFDB format16 little-endian int16, multiplexed channels; 15 channels x 38400 samples; original header retained"}}


def fetch(root, dataset):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    spec = SPECS[dataset]
    output = root / dataset
    if not output.exists():
        with tempfile.TemporaryDirectory(prefix=".numeric-", dir=root) as temp:
            stage = Path(temp) / "source"
            stage.mkdir()
            for name, (size, sha) in spec["files"].items():
                with urlopen(spec["base"] + name, timeout=60) as stream:
                    raw = stream.read((16 << 20) + 1)
                if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha:
                    raise ValueError("Pinned numeric file bytes/SHA mismatch")
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(raw)
            if not stage.resolve().is_relative_to(root) or not output.resolve().is_relative_to(root):
                raise ValueError("Invalid staged numeric source")
            stage.rename(output)
    files = inventory(output)
    if {f["path"]: (f["bytes"], f["sha256"]) for f in files} != spec["files"]:
        raise ValueError("Existing numeric input differs from the pinned original")
    return {"dataset": dataset, "source": str(output), "source_page": spec["page"],
        "file_urls": {name: spec["base"] + name for name in spec["files"]}, "files": files,
        "license": "Open Data Commons Attribution License v1.0",
        "scope": spec["scope"], "layout": spec["layout"], "original_paths_and_bytes": True,
        "conversion": "None: no float/int conversion, filtering, resampling, channel transpose or numeric normalization"}


def noise(root):
    raw = random.Random(20261015).randbytes(262147)
    output = Path(root).resolve() / "noise"
    output.mkdir(parents=True, exist_ok=True)
    path = output / "seeded-noise.bin"
    if not path.exists():
        with path.open("xb") as stream:
            stream.write(raw)
    files = inventory(output)
    expected = [{"path": path.name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}]
    if files != expected:
        raise ValueError("Synthetic negative control changed")
    return {"dataset": "noise", "source": str(output), "files": files,
        "scope": "Seeded random-byte negative control for the tested codecs, not an independent scientific corpus",
        "generator": "random.Random(20261015).randbytes(262147)", "license": "Project-generated test bytes"}
