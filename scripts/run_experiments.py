"""Run the frozen E0/E1 suite; all outputs are measured, no invented scores."""
import argparse
import json
from pathlib import Path
import random
import tempfile

from rkv1.benchmark import benchmark, incremental_experiment
from rkv1.datasets import fetch_public


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("results/local"))
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for dataset in ("uci", "scifact"):
        source = args.data / dataset
        fetch_public(source, dataset)
        result = benchmark(source, repeats=args.repeats)
        result["incremental"] = incremental_experiment(source)
        (args.out / f"{dataset}.json").write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    with tempfile.TemporaryDirectory(prefix="rkv-dedup-") as temp:
        source = Path(temp) / "synthetic-duplicates"
        source.mkdir()
        block = random.Random(20261014).randbytes(1 << 20)
        for i in range(4):
            (source / f"copy-{i}.bin").write_bytes(block)
        result = benchmark(source, repeats=args.repeats)
        result["synthetic"] = {"purpose": "cross-file deduplication control, NOT a real scientific corpus",
                               "generator": "random.Random(20261014).randbytes(1 << 20), four identical files"}
        (args.out / "synthetic-duplicates.json").write_text(json.dumps(result, indent=2) + "\n", "utf-8")


if __name__ == "__main__":
    main()
