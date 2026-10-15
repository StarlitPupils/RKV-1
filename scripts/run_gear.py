"""Reproduce the frozen Gear boundary backend experiment without overwriting records."""
import argparse
import os
from pathlib import Path
import platform

from rkv1.controlled import implementation_checksums, runtime_footprint
from rkv1.gear_benchmark import gear_benchmark
from rkv1.native import load_native_gear
from rkv1.read_benchmark import timestamp
from rkv1.version_data import fetch_versions
from scripts.run_units import save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-library", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("data/qasper-versions"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--queries", type=int, default=64)
    args = parser.parse_args()
    planned = ("environment.json", "dataset-provenance.json", "native-provenance.json",
               "qasper-gear.json", "source-checksums.json", "runtime-footprint.json")
    if any((args.out / name).exists() for name in planned):
        raise ValueError("Gear campaign report already exists; choose a fresh output path")
    args.out.mkdir(parents=True, exist_ok=True)  # permits a separately frozen baseline profile
    records = fetch_versions(args.data)
    provenance = load_native_gear(str(args.native_library.resolve())).provenance
    checksums = implementation_checksums()
    save(args.out / "environment.json", {"python": platform.python_version(), "platform": platform.platform(),
                                         "processor": platform.processor(), "logical_cpus": os.cpu_count(), "recorded_utc": timestamp()})
    save(args.out / "dataset-provenance.json", records)
    save(args.out / "native-provenance.json", provenance)
    save(args.out / "qasper-gear.json", gear_benchmark([r["source"] for r in records], args.native_library,
                                                       rounds=args.rounds, queries=args.queries))
    if checksums != implementation_checksums():
        raise ValueError("Source changed during Gear campaign")
    save(args.out / "source-checksums.json", checksums)
    save(args.out / "runtime-footprint.json", {**runtime_footprint(), "native": provenance})


if __name__ == "__main__":
    main()
