"""Reproduce independent E2 corpora, decoder profiles and paired exact trials."""
import argparse
import json
import os
from pathlib import Path
import platform

from rkv1.controlled import implementation_checksums, runtime_footprint
from rkv1.csv_benchmark import csv_benchmark
from rkv1.datasets import fetch_public
from rkv1.read_benchmark import timestamp


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("results/local-csv"))
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--queries", type=int, default=32)
    parser.add_argument("--datasets", nargs="+", choices=("wine", "htru2", "superconductivity"),
                        default=["wine", "htru2", "superconductivity"])
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    save(args.out / "environment.json", {"python": platform.python_version(), "platform": platform.platform(),
                                         "processor": platform.processor(), "logical_cpus": os.cpu_count(),
                                         "recorded_utc": timestamp()})
    checksums = implementation_checksums()
    for dataset in args.datasets:
        source = args.data / dataset
        fetch_public(source, dataset)
        save(args.out / f"{dataset}.json", csv_benchmark(source, rounds=args.rounds, queries=args.queries))
    if checksums != implementation_checksums():
        raise ValueError("Implementation changed during CSV campaign")
    save(args.out / "source-checksums.json", checksums)
    save(args.out / "runtime-footprint.json", runtime_footprint())


if __name__ == "__main__":
    main()
