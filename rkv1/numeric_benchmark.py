"""Interleaved full-cost numeric-word controls with exact original-byte truth."""
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile

from .benchmark import summary
from .controlled import _child, implementation_checksums, inventory
from .core import Archive, assert_tree_equal, verify
from .numeric import POLICIES as NUMERIC_POLICIES
from .read_benchmark import aggregate_trials, file_digest, round_seed, timestamp


def matrix():
    return [{"layout": f"flat-{size//1024}", "chunk_size": size, "unit_size": None,
             "compression": codec, "transform": transform, "deduplicate": True,
             "format_version": 4, "index_cache_bytes": 0}
            for size in (65536, 1048576) for codec in ("zlib", "zstd")
            for transform in ("none", "byte-shuffle-2-v1", "xor-shuffle-2-v1")]


def numeric_benchmark(source, *, configs=None, rounds=5, queries=32, warmup_queries=4, seed=20261015):
    if (any(type(v) is not int for v in (rounds, queries, warmup_queries, seed))
            or not 1 <= rounds <= 100 or not 1 <= queries <= 10000 or not 0 <= warmup_queries <= 128):
        raise ValueError("Invalid numeric benchmark counts")
    source = Path(source).resolve()
    files, checksums = inventory(source), implementation_checksums()
    configs = list(matrix() if configs is None else configs)
    if not configs or not any(f["bytes"] for f in files):
        raise ValueError("Numeric benchmark needs configurations and nonempty input")
    started = timestamp()
    warmups = [(i, -1) for i in range(len(configs))]
    jobs = [(i, r) for i in range(len(configs)) for r in range(rounds)]
    random.Random(seed).shuffle(warmups)
    random.Random(seed ^ 0x110).shuffle(jobs)
    rows = [{"configuration": {**c, "queries": queries, "seed": seed},
             "encode_trials": [], "decode_trials": [], "range_trials": []} for c in configs]
    with tempfile.TemporaryDirectory(prefix="rkv-numeric-") as temp:
        root = Path(temp)
        for order, (index, round_index) in enumerate(warmups + jobs):
            row = rows[index]
            archive, destination = root / f"{index}.rkv", root / "restored"
            print(f"{source.name} full {order+1}/{len(warmups+jobs)} round {round_index} {row['configuration']}", file=sys.stderr, flush=True)
            encoded = _child("encode", source, archive, destination, row["configuration"])
            decoded = _child("decode", source, archive, destination, row["configuration"])
            assert_tree_equal(source, destination)
            if not destination.resolve().is_relative_to(root.resolve()):
                raise ValueError("Invalid restored numeric path")
            shutil.rmtree(destination)
            for trial in (encoded, decoded):
                trial.update({"round": round_index, "execution_index": order, "bytewise_verified": True})
            row["encode_trials"].append(encoded)
            row["decode_trials"].append(decoded)
            if "storage" in row and encoded["stats"] != row["storage"]:
                raise ValueError("Numeric archive/selection is nondeterministic")
            row["storage"] = encoded["stats"]
        for index, row in enumerate(rows):
            archive = root / f"{index}.rkv"
            verify(archive)
            with Archive(archive) as reader:
                if reader.header["version"] != row["configuration"].get("format_version", 4):
                    raise ValueError("Numeric matrix format differs from its declared control")
                row["actual_transforms"] = {name: sum(m["transform"] == name for m in reader.header["blocks"].values())
                                             for name in ("none", *NUMERIC_POLICIES)}
                row["actual_codecs"] = {name: sum(m["codec"] == name for m in reader.header["blocks"].values())
                                        for name in sorted({m["codec"] for m in reader.header["blocks"].values()})}
            for phase in ("encode", "decode"):
                row[f"{phase}_trials"].sort(key=lambda t: t["round"])
                formal = [t for t in row[f"{phase}_trials"] if t["round"] >= 0]
                for field in ("wall_s", "cpu_s", "peak_rss_bytes"):
                    output = f"{phase}_s" if field == "wall_s" else f"{phase}_{field}"
                    row[output] = summary([t[field] for t in formal])
            row.update({"bytewise_verified": True, "verified_measured_roundtrips": rounds,
                        "verified_warmup_roundtrips": 1, "deterministic_archive_bytes": True})
        range_jobs = [(i, r, mode) for i in range(len(rows)) for r in range(rounds)
                      for mode in ("open_reader", "open_and_read")]
        random.Random(seed ^ 0x220).shuffle(range_jobs)
        plans = {}
        for order, (index, r, mode) in enumerate(range_jobs):
            row = rows[index]
            settings = {**row["configuration"], "session": 0, "round": r, "mode": mode,
                "warmup_queries": warmup_queries, "query_seed": round_seed(seed, 0, r),
                "query_boundary_size": 65536, "boundary_group": "cross_chunk"}
            print(f"{source.name} ranges {order+1}/{len(range_jobs)} {index} round {r} {mode}", file=sys.stderr, flush=True)
            child = subprocess.run([sys.executable, "-m", "rkv1.read_benchmark", str(source),
                str(root / f"{index}.rkv"), json.dumps(settings)], capture_output=True, text=True, encoding="utf-8")
            if child.returncode:
                raise ValueError(f"Numeric range worker failed: {child.stderr[-4000:]}")
            trial = json.loads(child.stdout)
            trial["execution_index"] = order
            row["range_trials"].append(trial)
            for category, group in trial["groups"].items():
                key = (r, category)
                if plans.setdefault(key, group["request_sha256"]) != group["request_sha256"]:
                    raise ValueError("Numeric request plans differ")
        for index, row in enumerate(rows):
            row["range_trials"].sort(key=lambda t: (t["round"], t["mode"]))
            row["range_aggregate"] = aggregate_trials(row["range_trials"])
            if file_digest(root / f"{index}.rkv") != row["storage"]["archive_sha256"]:
                raise ValueError("Numeric archive changed during reads")
    if checksums != implementation_checksums() or files != inventory(source):
        raise ValueError("Numeric input/source changed during campaign")
    from . import __version__
    return {"schema_version": 10, "rkv1_version": __version__, "dataset": source.name,
        "started_utc": started, "finished_utc": timestamp(), "files": files,
        "raw_file_bytes": sum(f["bytes"] for f in files), "implementation_checksums": checksums,
        "results": rows, "full_execution_order": [list(j) for j in warmups+jobs],
        "range_execution_order": [list(j) for j in range_jobs],
        "protocol": {"rounds": rounds, "queries_per_group": queries, "warmup_queries_per_group": warmup_queries,
            "seed": seed, "container": "v4 flat blocks for all conditions, including none",
            "ordering": "One full warmup/config, then shuffled condition/round jobs; encode followed by fresh-process restore. All range jobs shuffled separately.",
            "transforms": "Explicit 2-byte word grid resets each block; tail literal. No int/float parsing, channel separation or sample prediction semantics.",
            "selection": "Ordinary codec first, then selected transform+same codec; use only if payload gain exceeds local label cost. Full metadata cost reported; policy may still lose overall.",
            "integrity": "Unchanged bounded decompression, manifest/block/file SHA and external bytewise restore/range truth; deterministic archives each round.",
            "persistence": "Temporary file, flush/fsync, atomic replace and full archive digest, identical across methods.",
            "ranges": "Same original byte requests per round across every configuration/mode. 64KiB-grid cross_chunk windows may not cross a 1MiB block.",
            "cache": "Full archive pre-read; warm OS cache; no decoded-block cache; fresh process per phase/range trial.",
            "cost": "Entire archive including prefix, JSON, file paths/hashes, block metadata and payload. No native library/model/dictionary; shared Python/codec not fully allocated.",
            "rss": "Fresh phase processes; range includes truth and metadata ledger, not production RSS"},
        "unmeasured": {"cold_os_cache": None, "cross_machine": None, "cross_day": None,
            "rust_numeric_speedup": None, "inference_quality": None},
        "limits": ["single host; five default rounds are descriptive, not confidence intervals",
            "one EEG and one ECG record, not full databases or floating-point-array evaluation",
            "byte-word transforms cover original embedded text/annotation bytes too; no semantic field parser",
            "synthetic noise is a fallback/cost control, not a third scientific dataset",
            "no claim against all specialist scientific compressors or optimal word/stride layouts"]}
