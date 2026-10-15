"""Run fixed original-byte numeric-word controls, without overwriting reports."""
import argparse
import hashlib
import os
from pathlib import Path
import platform

from rkv1.controlled import implementation_checksums, runtime_footprint
from rkv1.numeric_data import fetch, noise
from rkv1.numeric_benchmark import numeric_benchmark
from rkv1.read_benchmark import timestamp
from scripts.run_units import save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/numeric"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--queries", type=int, default=32)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    checks = implementation_checksums()
    save(args.out / "environment.json", {"python": platform.python_version(), "platform": platform.platform(),
        "logical_cpus": os.cpu_count(), "recorded_utc": timestamp()})
    import rkv1.numeric
    module = Path(rkv1.numeric.__file__)
    save(args.out / "numeric-resource.json", {"source_module": "rkv1/numeric.py",
        "source_bytes": module.stat().st_size, "source_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
        "native_library_bytes": 0, "model_bytes": 0, "dictionary_bytes": 0,
        "scope": "Same-install archive cost plus a conservative separate scenario charging the entire dedicated numeric.py source once to candidate; not compiled module or full deployment cost. Python/codec/core shared allocation incomplete."})
    for dataset in ("eeg", "ecg", "noise"):
        provenance = noise(args.data) if dataset == "noise" else fetch(args.data, dataset)
        save(args.out / f"{dataset}-provenance.json", provenance)
        save(args.out / f"{dataset}-numeric.json", numeric_benchmark(provenance["source"], rounds=args.rounds, queries=args.queries))
    if checks != implementation_checksums():
        raise ValueError("Source changed across numeric campaigns")
    save(args.out / "source-checksums.json", checks)
    save(args.out / "runtime-footprint.json", runtime_footprint())


if __name__ == "__main__":
    main()
