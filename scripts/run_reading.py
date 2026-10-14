"""Reproduce the v0.3 repeated reading campaign; never overwrite an old campaign."""
import argparse
import json
from pathlib import Path

from rkv1.controlled import implementation_checksums, runtime_footprint
from rkv1.datasets import fetch_public
from rkv1.read_benchmark import read_benchmark


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("results/local-reading"))
    parser.add_argument("--sessions", type=int, default=2)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--queries", type=int, default=128)
    parser.add_argument("--warmup-queries", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20261014)
    parser.add_argument("--datasets", nargs="+", choices=("scifact", "qasper"), default=["scifact", "qasper"])
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    checksums = implementation_checksums()
    for dataset in args.datasets:
        source = args.data / dataset
        fetch_public(source, dataset)
        report = read_benchmark(source, sessions=args.sessions, rounds=args.rounds, queries=args.queries,
                                warmup_queries=args.warmup_queries, seed=args.seed)
        save(args.out / f"{dataset}.json", report)
    if checksums != implementation_checksums():
        raise ValueError("Implementation changed during the campaign")
    save(args.out / "source-checksums.json", checksums)
    save(args.out / "runtime-footprint.json", runtime_footprint())


if __name__ == "__main__":
    main()
