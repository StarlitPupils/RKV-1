"""Frozen-binary local CPU experiment; never overwrite a previous result directory."""
import argparse
import hashlib
import os
from pathlib import Path
import platform

from rkv1.controlled import implementation_checksums, runtime_footprint
from rkv1.datasets import fetch_public
from rkv1.native import load_native
from rkv1.native_benchmark import native_benchmark
from rkv1.read_benchmark import timestamp
from scripts.run_units import save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-library", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("results/local-native"))
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--queries", type=int, default=64)
    parser.add_argument("--datasets", nargs="+", choices=("wine", "superconductivity", "htru2"),
                        default=["wine", "superconductivity", "htru2"])
    args = parser.parse_args()
    library = args.native_library.resolve()
    provenance = load_native(str(library)).provenance
    checksums = implementation_checksums()
    args.out.mkdir(parents=True, exist_ok=False)
    save(args.out / "environment.json", {"python": platform.python_version(), "platform": platform.platform(),
                                         "processor": platform.processor(), "logical_cpus": os.cpu_count(), "recorded_utc": timestamp()})
    save(args.out / "native-provenance.json", provenance)
    for dataset in args.datasets:
        source = args.data / dataset
        fetch_public(source, dataset)
        save(args.out / f"{dataset}.json", native_benchmark(source, library, rounds=args.rounds, queries=args.queries))
    if (checksums != implementation_checksums() or hashlib.sha256(library.read_bytes()).hexdigest() != provenance["sha256"]
            or hashlib.sha256(library.with_name("native.json").read_bytes()).hexdigest() != provenance["metadata_sha256"]):
        raise ValueError("Implementation or native binary changed during campaign")
    save(args.out / "source-checksums.json", checksums)
    save(args.out / "runtime-footprint.json", {**runtime_footprint(), "native": provenance})


if __name__ == "__main__":
    main()
