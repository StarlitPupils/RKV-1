"""Reproduce v0.2 controlled benchmarks without replacing prior results."""
import argparse
import json
from pathlib import Path
import random
import tempfile

from rkv1.controlled import controlled_benchmark, incremental_matrix, runtime_footprint
from rkv1.datasets import fetch_public


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("results/local-controlled"))
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--queries", type=int, default=128)
    parser.add_argument("--datasets", nargs="+", choices=("uci", "scifact", "qasper", "wine"), default=["uci", "scifact", "qasper", "wine"])
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for dataset in args.datasets:
        source = args.data / dataset
        fetch_public(source, dataset)
        save(args.out / f"{dataset}.json", controlled_benchmark(source, repeats=args.repeats, queries=args.queries,
                                                             csv_trials=dataset in ("uci", "wine")))
    if "scifact" in args.datasets:
        save(args.out / "incremental.json", incremental_matrix(args.data / "scifact", repeats=args.repeats))
    with tempfile.TemporaryDirectory(prefix="rkv-dedup-") as temp:
        source = Path(temp) / "synthetic-duplicates"
        source.mkdir()
        block = random.Random(20261014).randbytes(1 << 20)
        for i in range(4):
            (source / f"copy-{i}.bin").write_bytes(block)
        report = controlled_benchmark(source, repeats=args.repeats, queries=args.queries)
        report["synthetic"] = {"generator": "random.Random(20261014).randbytes(1 << 20), four copies",
                               "purpose": "deduplication control; not a natural scientific corpus"}
        save(args.out / "synthetic-duplicates.json", report)
    save(args.out / "runtime-footprint.json", runtime_footprint())


if __name__ == "__main__":
    main()
