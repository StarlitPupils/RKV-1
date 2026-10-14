"""Reproduce immutable real-release multi-version storage controls."""
import argparse
import os
from pathlib import Path
import platform

from rkv1.controlled import implementation_checksums, runtime_footprint
from rkv1.read_benchmark import timestamp
from rkv1.store_benchmark import version_benchmark
from rkv1.version_data import fetch_versions
from scripts.run_units import save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/qasper-versions"))
    parser.add_argument("--out", type=Path, default=Path("results/local-versions"))
    parser.add_argument("--rounds", type=int, default=5); parser.add_argument("--queries", type=int, default=64)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    records = fetch_versions(args.data)
    checksums = implementation_checksums()
    save(args.out / "environment.json", {"python": platform.python_version(), "platform": platform.platform(),
                                         "processor": platform.processor(), "logical_cpus": os.cpu_count(), "recorded_utc": timestamp()})
    save(args.out / "dataset-provenance.json", records)
    save(args.out / "qasper-versions.json", version_benchmark([r["source"] for r in records], rounds=args.rounds, queries=args.queries))
    if checksums != implementation_checksums():
        raise ValueError("Implementation changed during version campaign")
    save(args.out / "source-checksums.json", checksums)
    save(args.out / "runtime-footprint.json", runtime_footprint())


if __name__ == "__main__":
    main()
