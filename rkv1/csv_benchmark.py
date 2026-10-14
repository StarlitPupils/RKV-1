"""E2 paired decoder trials, retaining byte-identical v0.3 archives/validation."""
from __future__ import annotations

import cProfile
import hashlib
import json
from pathlib import Path
import pstats
import random
import shutil
import subprocess
import sys
import tempfile

from .benchmark import summary
from .codecs import decompress
from .controlled import _child, implementation_checksums, inventory
from .core import Archive, assert_tree_equal, pack, verify
from .read_benchmark import aggregate_trials, file_digest, round_seed, timestamp

BASELINE_SHA256 = "3a50f14a7e6998bf35fa475e2f0e8394e0c34912fade5baaa90c383cb7292ad6"


def decoder_profiles(archive):
    from .transforms import csv_columns_decode as current
    from .experiments.csv_v0_3 import csv_columns_decode as legacy
    with Archive(archive) as reader:
        selected = next(((key, meta) for key, meta in reader.header["blocks"].items()
                         if meta.get("transform") == "csv-columns-v1"), None)
        if selected is None:
            return None
        key, meta = selected
        expected = reader.block(key)
        reader.stream.seek(reader.body_start + meta["offset"])
        coded = decompress(reader.stream.read(meta["stored_size"]), meta["codec"], meta["coded_size"])
    output = {}
    for name, decoder in (("v0.3.0", legacy), ("current", current)):
        profiler = cProfile.Profile()
        profiler.enable()
        for _ in range(3):
            assert decoder(coded, meta["raw_size"]) == expected
        profiler.disable()
        stats = pstats.Stats(profiler)
        functions = []
        for (filename, line, function), (primitive, calls, own, cumulative, _) in stats.stats.items():
            functions.append({"file": Path(filename).name, "line": line, "function": function,
                              "calls": calls, "primitive_calls": primitive,
                              "own_s": own, "cumulative_s": cumulative})
        output[name] = {"calls": 3, "total_profiled_s": stats.total_tt,
                        "functions": sorted(functions, key=lambda f: f["cumulative_s"], reverse=True)}
    return {"block_hash": key, "raw_bytes": meta["raw_size"], "coded_bytes": len(coded),
            "basis": "three cProfile calls on one transformed block; diagnostic, not a wall-time benchmark; cumulative times overlap",
            "profiles": output}


def csv_benchmark(source, *, rounds=5, queries=32, warmup_queries=4, seed=20261014):
    if (any(type(v) is not int for v in (rounds, queries, warmup_queries, seed))
            or not 1 <= rounds <= 100 or not 1 <= queries <= 10000 or not 0 <= warmup_queries <= 128):
        raise ValueError("Invalid CSV benchmark counts")
    source = Path(source).resolve()
    files = inventory(source)
    if not any(f["bytes"] for f in files):
        raise ValueError("CSV benchmark needs nonempty input")
    baseline = Path(__file__).parent / "experiments/csv_v0_3.py"
    if hashlib.sha256(baseline.read_bytes()).hexdigest() != BASELINE_SHA256:
        raise ValueError("Frozen v0.3 CSV baseline changed")
    checksums = implementation_checksums()
    started = timestamp()
    rows = []
    with tempfile.TemporaryDirectory(prefix="rkv-csv-paired-") as temp:
        root = Path(temp)
        archives, profiles = {}, {}
        for codec in ("zlib", "zstd"):
            for transform in ("none", "csv-columns-v1"):
                path = root / f"{codec}-{transform}.rkv"
                stats = pack(source, path, 1048576, compression=codec, transform=transform)
                verify(path)
                archives[(codec, transform)] = (path, stats)
            profiles[codec] = decoder_profiles(archives[(codec, "csv-columns-v1")][0])
            for name, transform, decoder in (("plain", "none", "current"),
                                              ("legacy_csv", "csv-columns-v1", "v0.3.0"),
                                              ("current_csv", "csv-columns-v1", "current")):
                rows.append({"configuration": {"compression": codec, "chunk_size": 1048576,
                                               "deduplicate": True, "transform": transform, "csv_decoder": decoder},
                             "variant": name, "storage": archives[(codec, transform)][1],
                             "full_archive_verified": True, "decode_trials": [], "range_trials": []})

        def decode(index, round_index, warmup=False):
            row = rows[index]
            archive = archives[(row["configuration"]["compression"], row["configuration"]["transform"])][0]
            destination = root / "restored"
            result = _child("decode", source, archive, destination, row["configuration"])
            assert_tree_equal(source, destination)
            if not destination.resolve().is_relative_to(root.resolve()):
                raise ValueError("Invalid CSV restoration temporary path")
            shutil.rmtree(destination)
            result.update({"round": round_index, "bytewise_verified": True})
            if not warmup:
                row["decode_trials"].append(result)

        for index in range(len(rows)):
            decode(index, -1, warmup=True)
        jobs = [(index, round_index, phase) for index in range(len(rows)) for round_index in range(rounds)
                for phase in ("decode", "open_reader", "open_and_read")]
        random.Random(seed ^ 0x435356).shuffle(jobs)
        for position, (index, round_index, phase) in enumerate(jobs):
            row = rows[index]
            print(f"{source.name} CSV trial {position + 1}/{len(jobs)} "
                  f'{row["configuration"]["compression"]} {row["variant"]} {phase}', file=sys.stderr, flush=True)
            if phase == "decode":
                decode(index, round_index)
            else:
                archive = archives[(row["configuration"]["compression"], row["configuration"]["transform"])][0]
                settings = {**row["configuration"], "mode": phase, "queries": queries, "warmup_queries": warmup_queries,
                            "query_seed": round_seed(seed, 0, round_index), "session": 0, "round": round_index}
                child = subprocess.run([sys.executable, "-m", "rkv1.read_benchmark", str(source), str(archive),
                                        json.dumps(settings)], capture_output=True, text=True, encoding="utf-8")
                if child.returncode:
                    raise ValueError(f"CSV range worker failed: {child.stderr[-4000:]}")
                trial = json.loads(child.stdout)
                trial["execution_index"] = position
                row["range_trials"].append(trial)
        for row in rows:
            row["decode_trials"].sort(key=lambda r: r["round"])
            row["range_trials"].sort(key=lambda r: (r["round"], r["mode"]))
            row["decode_s"] = summary([r["wall_s"] for r in row["decode_trials"]])
            row["decode_cpu_s"] = summary([r["cpu_s"] for r in row["decode_trials"]])
            row["decode_peak_rss_bytes"] = summary([r["peak_rss_bytes"] for r in row["decode_trials"]])
            row["range_aggregate"] = aggregate_trials(row["range_trials"])
        for path, stats in archives.values():
            if file_digest(path) != stats["archive_sha256"]:
                raise ValueError("CSV archive changed during paired trials")
    if checksums != implementation_checksums() or files != inventory(source):
        raise ValueError("Implementation or source changed during CSV trials")
    from . import __version__
    return {"schema_version": 4, "rkv1_version": __version__, "dataset": source.name,
            "started_utc": started, "finished_utc": timestamp(), "files": files,
            "raw_file_bytes": sum(f["bytes"] for f in files), "implementation_checksums": checksums,
            "baseline": {"tag": "v0.3.0", "path": "rkv1/transforms.py", "sha256": BASELINE_SHA256,
                         "scope": "only CSV inverse transform replaced inside isolated legacy worker; all other v0.4 code shared"},
            "protocol": {"rounds": rounds, "queries_per_group": queries, "warmup_queries_per_group": warmup_queries,
                         "seed": seed, "cache": "full archive pre-read; warm OS cache; independent workers",
                         "timing": "restore includes internal hashes and file IO, external byte comparison excluded; range total and open/read/close spans",
                         "matching": "same CSV archive for old/new decoder; all request groups paired across variants/codecs at fixed 1 MiB",
                         "order": "restore/read jobs interleaved and shuffled; one restore warmup per condition",
                         "profiles": "diagnostic cProfile separately before timed jobs; not used to claim speedup",
                         "memory": "restore and range workers separate; legacy worker also imports frozen decoder module"},
            "execution_order": [list(job) for job in jobs], "results": rows, "decoder_profiles": profiles,
            "verified_measured_roundtrips": len(rows) * rounds, "verified_warmup_roundtrips": len(rows),
            "full_archives_verified": len(archives), "inference_quality": None,
            "limits": ["single host, one campaign, few rounds; no confidence interval or significance claim",
                       "only 32 range queries per group in default E2 trials; not a replacement for the v0.3 reading matrix",
                       "CSV v1 supports numeric LF/CRLF only; unsupported CR-only/mixed cells fall back exactly",
                       "pack executed once per profile; no new encode-speed claim",
                       "frozen legacy inverse transform is a benchmark control, not full v0.3 application timing"]}
