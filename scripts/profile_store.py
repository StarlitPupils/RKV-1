"""Diagnostic cProfile campaign; its perturbed timings are not benchmark results."""
import argparse
import cProfile
import json
from pathlib import Path
import platform
import pstats
import tempfile
import time

from rkv1.controlled import implementation_checksums, inventory
from rkv1.read_benchmark import timestamp
from rkv1.store import Store
from rkv1.store_benchmark import _fingerprint, digest_map
from scripts.run_units import save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/qasper-versions"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--backend", choices=("python", "rust"), default="python")
    parser.add_argument("--native-library", type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Profile report already exists")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sources = [args.data / f"v0.{i}" for i in (1, 2, 3)]
    inputs, checksums = [inventory(s) for s in sources], implementation_checksums()
    rows, trees = [], []
    with tempfile.TemporaryDirectory(prefix="rkv-cas-profile-") as temp:
        for profiled in (False, True):
            store = Store.create(Path(temp) / str(profiled), chunker="gear-v1")
            trial = []
            for source in sources:
                profiler = cProfile.Profile()
                start, cpu = time.perf_counter(), time.process_time()
                if profiled:
                    profiler.enable()
                stats = store.add(source, label=source.name, chunker_backend=args.backend,
                                  native_library=args.native_library)
                if profiled:
                    profiler.disable()
                wall, used_cpu = time.perf_counter() - start, time.process_time() - cpu
                functions = []
                if profiled:
                    for (filename, line, name), (primitive, calls, own, cumulative, _) in pstats.Stats(profiler).stats.items():
                        functions.append({"file": Path(filename).name, "line": line, "function": name,
                                          "primitive_calls": primitive, "calls": calls,
                                          "exclusive_s": own, "inclusive_s": cumulative})
                    functions.sort(key=lambda f: f["exclusive_s"], reverse=True)
                trial.append({"version": source.name, "wall_s": wall, "cpu_s": used_cpu,
                              "stats": stats, "functions_by_exclusive_time": functions})
                print(f"profiled={profiled} {source.name}: {wall:.3f}s", flush=True)
                store.snapshot(stats["snapshot_id"]).process()
            rows.append({"profiled": profiled, "versions": trial})
            trees.append(_fingerprint(store.root))
        if trees[0] != trees[1]:
            raise ValueError("Profiling changed stored bytes")
    if inputs != [inventory(s) for s in sources] or checksums != implementation_checksums():
        raise ValueError("Input/source changed during profile")
    native = None
    if args.backend == "rust":
        import hashlib
        from rkv1.native import load_native_gear
        native = load_native_gear(str(args.native_library.resolve())).provenance
        if (hashlib.sha256(args.native_library.read_bytes()).hexdigest() != native["sha256"]
                or hashlib.sha256(args.native_library.with_name("native.json").read_bytes()).hexdigest() != native["metadata_sha256"]):
            raise ValueError("Native files changed during profile")
    save(args.out, {"schema_version": 1, "recorded_utc": timestamp(), "python": platform.python_version(),
                    "chunker_backend": args.backend, "native_provenance": native,
                    "implementation_checksums": checksums, "inputs": inputs, "trials": rows,
                    "identical_store_tree_sha256": digest_map(trees[0]), "all_snapshots_verified": True,
                    "protocol": "Unprofiled sequence followed by cProfile sequence, each fresh shared Gear CAS; add only profiled. Verification/tree audit untimed.",
                    "limitations": "One diagnostic pass; cProfile perturbs especially per-byte Python calls. Exclusive times partition the instrumented run; inclusive times overlap. Not an optimization speed claim."})


if __name__ == "__main__":
    main()
