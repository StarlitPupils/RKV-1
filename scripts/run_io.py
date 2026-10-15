"""Two independent real-release families, same-byte CAS IO ablations."""
import argparse
import os
from pathlib import Path
import platform

from rkv1.controlled import implementation_checksums, runtime_footprint
from rkv1.evidence_versions import fetch_versions as fetch_evidence
from rkv1.io_benchmark import io_benchmark
from rkv1.native import load_native_gear
from rkv1.read_benchmark import timestamp
from rkv1.version_data import fetch_versions as fetch_qasper
from scripts.run_units import save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-library", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--datasets", nargs="+", choices=("qasper", "evidence"), default=["qasper", "evidence"])
    parser.add_argument("--rounds", type=int, default=5); parser.add_argument("--queries", type=int, default=64)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    checksums = implementation_checksums()
    provenance = load_native_gear(str(args.native_library.resolve())).provenance
    save(args.out / "environment.json", {"python": platform.python_version(), "platform": platform.platform(),
                                         "logical_cpus": os.cpu_count(), "recorded_utc": timestamp()})
    save(args.out / "native-provenance.json", provenance)
    for dataset in args.datasets:
        fetch, folder = (fetch_qasper, "qasper-versions") if dataset == "qasper" else (fetch_evidence, "evidence-versions")
        records = fetch(args.data / folder)
        save(args.out / f"{dataset}-provenance.json", records)
        save(args.out / f"{dataset}-io.json", io_benchmark([r["source"] for r in records], args.native_library,
              dataset=dataset, rounds=args.rounds, queries=args.queries))
    if checksums != implementation_checksums():
        raise ValueError("Source changed during IO campaign")
    save(args.out / "source-checksums.json", checksums)
    save(args.out / "runtime-footprint.json", {**runtime_footprint(), "native": provenance})


if __name__ == "__main__":
    main()
