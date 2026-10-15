"""Matched flat/small-block/two-level storage controls, including index cost."""
from __future__ import annotations

import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile

from .controlled import implementation_checksums, inventory, measure
from .core import pack, verify
from .read_benchmark import aggregate_trials, file_digest, round_seed, timestamp


def matrix(dataset):
    layouts = (("flat-1024", 1048576, None), ("flat-64", 65536, None), ("flat-16", 16384, None),
               ("units-64", 1048576, 65536), ("units-16", 1048576, 16384))
    codecs = ("zlib", "zstd") if dataset in ("wine", "superconductivity") else ("zstd",)
    transforms = ("none", "csv-columns-v1") if dataset != "qasper" else ("none",)
    if dataset == "htru2":
        layouts = tuple(layout for layout in layouts if layout[0] in ("flat-1024", "flat-64", "units-64"))
    configs = [{"layout": layout, "compression": codec, "chunk_size": chunk, "unit_size": unit,
                "deduplicate": True, "transform": transform, "index_cache_bytes": 1 << 20}
               for layout, chunk, unit in layouts for codec in codecs for transform in transforms]
    if dataset in ("qasper", "superconductivity"):
        selected_transform = "none" if dataset == "qasper" else "csv-columns-v1"
        row = next(c for c in configs if c["layout"] == "units-64" and c["compression"] == "zstd"
                   and c["transform"] == selected_transform)
        configs.append({**row, "layout": "units-64-no-cache", "index_cache_bytes": 0})
    return configs


def unit_benchmark(source, *, configs=None, rounds=5, queries=64, warmup_queries=4, seed=20261014):
    if (any(type(v) is not int for v in (rounds, queries, warmup_queries, seed))
            or not 1 <= rounds <= 100 or not 1 <= queries <= 10000 or not 0 <= warmup_queries <= 128):
        raise ValueError("Invalid unit benchmark counts")
    source = Path(source).resolve()
    files = inventory(source)
    if not any(f["bytes"] for f in files):
        raise ValueError("Unit benchmark needs nonempty input")
    checksums = implementation_checksums()
    configs = list(matrix(source.name) if configs is None else configs)
    if not configs:
        raise ValueError("No unit benchmark configurations")
    random.Random(seed).shuffle(configs)
    started = timestamp()
    rows = []
    with tempfile.TemporaryDirectory(prefix="rkv-unit-controls-") as temp:
        root = Path(temp)
        for index, config in enumerate(configs):
            print(f"{source.name} encode/restore {index + 1}/{len(configs)} {config}", file=sys.stderr, flush=True)
            config = {**config, "queries": queries, "seed": seed}
            result = measure(source, config, repeats=rounds, warmups=1, ranges=False)
            archive = root / f"{index}.rkv"
            stats = pack(source, archive, config["chunk_size"], compression=config["compression"],
                         transform=config["transform"], deduplicate=config["deduplicate"], unit_size=config["unit_size"],
                         format_version=config.get("format_version"))
            verify(archive)
            if stats["archive_sha256"] != result["storage"]["archive_sha256"]:
                raise ValueError("Reading archive differs from measured encoding bytes")
            result.update({"range_trials": [], "full_archive_verified": True})
            rows.append(result)
        jobs = [(index, round_index, mode) for index in range(len(rows)) for round_index in range(rounds)
                for mode in ("open_reader", "open_and_read")]
        random.Random(seed ^ 0x554E4954).shuffle(jobs)
        for position, (index, round_index, mode) in enumerate(jobs):
            row = rows[index]
            settings = {**row["configuration"], "session": 0, "round": round_index, "mode": mode,
                        "queries": queries, "warmup_queries": warmup_queries,
                        "query_seed": round_seed(seed, 0, round_index), "query_boundary_size": 65536,
                        "boundary_group": "cross_unit"}
            print(f"{source.name} ranges {position + 1}/{len(jobs)} "
                  f'{settings["layout"]} {settings["compression"]} {settings["transform"]} {mode}', file=sys.stderr, flush=True)
            child = subprocess.run([sys.executable, "-m", "rkv1.read_benchmark", str(source), str(root / f"{index}.rkv"),
                                    json.dumps(settings)], capture_output=True, text=True, encoding="utf-8")
            if child.returncode:
                raise ValueError(f"Unit range worker failed: {child.stderr[-4000:]}")
            trial = json.loads(child.stdout)
            trial["execution_index"] = position
            row["range_trials"].append(trial)
        plans = {}
        for index, row in enumerate(rows):
            row["range_trials"].sort(key=lambda t: (t["round"], t["mode"]))
            row["range_aggregate"] = aggregate_trials(row["range_trials"])
            for trial in row["range_trials"]:
                for group, result in trial["groups"].items():
                    key = (trial["round"], group)
                    plans.setdefault(key, result["request_sha256"])
                    if plans[key] != result["request_sha256"]:
                        raise ValueError("Unmatched unit benchmark requests")
            if file_digest(root / f"{index}.rkv") != row["storage"]["archive_sha256"]:
                raise ValueError("Unit archive changed during measurement")
    if checksums != implementation_checksums() or files != inventory(source):
        raise ValueError("Input or implementation changed during unit measurement")
    from . import __version__
    return {"schema_version": 5, "rkv1_version": __version__, "dataset": source.name,
            "started_utc": started, "finished_utc": timestamp(), "files": files,
            "raw_file_bytes": sum(f["bytes"] for f in files), "implementation_checksums": checksums,
            "protocol": {"rounds": rounds, "queries_per_group": queries, "warmup_queries_per_group": warmup_queries,
                         "seed": seed, "range_order": "all layouts/codecs/transforms/rounds/modes interleaved and shuffled",
                         "encode_order": "configurations shuffled, one warmup and five default encode/restore trials per condition",
                         "cache": "full archive pre-read; warm OS cache; independent phase processes",
                         "matching": "all actual requests identical across all configurations and modes for a round",
                         "cross_unit": "4096-byte window centered at a fixed 64 KiB grid boundary; may not cross a 1 MiB parent",
                         "integrity": "v2 touched block hashes; v3 authenticated unit indexes and touched unit hashes; full restore verifies parent/file hashes",
                         "cost": "complete archive bytes include prefix, JSON, fixed 48-byte unit entries, hashes and encoded payload",
                         "work": "unit-aware analytical decoded/encoded bytes; referenced_index_bytes is not cache-miss or physical-IO count",
                         "rss": "separate encode/restore/range workers; range includes truth and an unmeasured ledger reader/cache"},
            "range_execution_order": [list(job) for job in jobs], "results": rows,
            "unmeasured": {"cold_os_cache": None, "cross_machine": None, "cross_day": None,
                           "rust_speedup": None, "inference_quality": None},
            "limits": ["single host, warm cache, uncontrolled background load; no significance claim",
                       "unit indexes cached with a charged budget and at most 128 parents; budget is not a hard RSS limit",
                       "v3 deduplicates outer parents only; no cross-parent unit CAS or append-only version store",
                       "CSV acceptance can differ because unit entry flags have fixed cost while v2 uses JSON transform labels"]}
