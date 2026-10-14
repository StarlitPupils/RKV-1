"""Matched archive bytes with interleaved Python/Rust inverse-decoder trials."""
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile

from .benchmark import summary
from .controlled import _child, implementation_checksums, inventory
from .core import assert_tree_equal, pack, verify
from .native import load_native
from .read_benchmark import aggregate_trials, file_digest, round_seed, timestamp


def matrix(dataset):
    layouts = (("flat-1024", 1048576, None), ("units-64", 1048576, 65536), ("units-16", 1048576, 16384))
    if dataset == "htru2":
        layouts = layouts[:1]
    codecs = ("zstd",) if dataset == "htru2" else ("zlib", "zstd")
    return [{"layout": layout, "chunk_size": chunk, "unit_size": unit, "compression": codec,
             "transform": transform, "deduplicate": True, "index_cache_bytes": 1 << 20}
            for layout, chunk, unit in layouts for codec in codecs for transform in ("none", "csv-columns-v1")]


def native_benchmark(source, library, *, configs=None, rounds=5, queries=64, warmup_queries=4, seed=20261015):
    if (any(type(v) is not int for v in (rounds, queries, warmup_queries, seed))
            or not 1 <= rounds <= 100 or not 1 <= queries <= 10000 or not 0 <= warmup_queries <= 128):
        raise ValueError("Invalid native benchmark counts")
    source, library = Path(source).resolve(), Path(library).resolve()
    provenance = load_native(str(library)).provenance
    files, checksums = inventory(source), implementation_checksums()
    if not any(f["bytes"] for f in files):
        raise ValueError("Native benchmark needs nonempty input")
    configs = list(matrix(source.name) if configs is None else configs)
    if not configs:
        raise ValueError("No native benchmark configurations")
    random.Random(seed).shuffle(configs)
    rows, started = [], timestamp()
    with tempfile.TemporaryDirectory(prefix="rkv-native-controls-") as temp:
        root = Path(temp)
        for index, config in enumerate(configs):
            print(f"{source.name} archive {index + 1}/{len(configs)} {config}", file=sys.stderr, flush=True)
            archive = root / f"{index}.rkv"
            storage = pack(source, archive, config["chunk_size"], compression=config["compression"],
                           transform=config["transform"], unit_size=config["unit_size"], deduplicate=config["deduplicate"])
            repeated = pack(source, root / "repeat.rkv", config["chunk_size"], overwrite=True,
                            compression=config["compression"], transform=config["transform"],
                            unit_size=config["unit_size"], deduplicate=config["deduplicate"])
            if repeated["archive_sha256"] != storage["archive_sha256"]:
                raise ValueError("Non-deterministic native campaign archive")
            verify(archive)
            for backend in ("python", "rust"):
                settings = {**config, "decoder_backend": backend, "queries": queries, "seed": seed}
                if backend == "rust":
                    settings["native_library"] = str(library)
                rows.append({"configuration": settings, "archive_index": index, "storage": storage,
                             "restore_trials": [], "range_trials": [], "deterministic_archive_bytes": True,
                             "full_archive_verified": True})
        # Every restoration starts a new process, including library identity check/load.
        # A labelled warmup per condition is excluded; all formal condition/round jobs shuffle.
        warmup_jobs = [(index, -1) for index in range(len(rows))]
        restore_jobs = [(index, r) for index in range(len(rows)) for r in range(rounds)]
        random.Random(seed ^ 0x5741524D).shuffle(warmup_jobs)
        random.Random(seed ^ 0x52455354).shuffle(restore_jobs)
        restore_jobs = warmup_jobs + restore_jobs
        for position, (index, r) in enumerate(restore_jobs):
            row = rows[index]
            config = row["configuration"]
            print(f"{source.name} restore {position + 1}/{len(restore_jobs)} {config['decoder_backend']}",
                  file=sys.stderr, flush=True)
            destination = root / "restored"
            trial = _child("decode", source, root / f"{row['archive_index']}.rkv", destination, config)
            assert_tree_equal(source, destination)
            if not destination.resolve().is_relative_to(root.resolve()):
                raise ValueError("Invalid temporary restore path")
            shutil.rmtree(destination)
            row["restore_trials"].append({**trial, "round": r, "execution_index": position, "bytewise_verified": True})
        jobs = [(index, r, mode) for index in range(len(rows)) for r in range(rounds)
                for mode in ("open_reader", "open_and_read")]
        random.Random(seed ^ 0x4E415449).shuffle(jobs)
        for position, (index, r, mode) in enumerate(jobs):
            row = rows[index]
            settings = {**row["configuration"], "session": 0, "round": r, "mode": mode,
                        "warmup_queries": warmup_queries, "query_seed": round_seed(seed, 0, r),
                        "query_boundary_size": 65536, "boundary_group": "cross_unit"}
            print(f"{source.name} ranges {position + 1}/{len(jobs)} {settings['layout']} "
                  f"{settings['transform']} {settings['decoder_backend']} {mode}", file=sys.stderr, flush=True)
            child = subprocess.run([sys.executable, "-m", "rkv1.read_benchmark", str(source),
                                    str(root / f"{row['archive_index']}.rkv"), json.dumps(settings)],
                                   capture_output=True, text=True, encoding="utf-8")
            if child.returncode:
                raise ValueError(f"Native range worker failed: {child.stderr[-4000:]}")
            trial = json.loads(child.stdout)
            row["range_trials"].append({**trial, "execution_index": position})
        plans = {}
        for row in rows:
            formal = [t for t in row["restore_trials"] if t["round"] >= 0]
            row.update({"decode_s": summary([t["wall_s"] for t in formal]),
                        "decode_cpu_s": summary([t["cpu_s"] for t in formal]),
                        "decode_peak_rss_bytes": summary([t["peak_rss_bytes"] for t in formal]),
                        "verified_measured_roundtrips": rounds, "verified_warmup_roundtrips": 1,
                        "bytewise_verified": True})
            row["restore_trials"].sort(key=lambda t: t["round"])
            row["range_trials"].sort(key=lambda t: (t["round"], t["mode"]))
            row["range_aggregate"] = aggregate_trials(row["range_trials"])
            for trial in row["range_trials"]:
                for category, group in trial["groups"].items():
                    key = (trial["round"], category)
                    plans.setdefault(key, group["request_sha256"])
                    if plans[key] != group["request_sha256"]:
                        raise ValueError("Unmatched native campaign requests")
            if file_digest(root / f"{row['archive_index']}.rkv") != row["storage"]["archive_sha256"]:
                raise ValueError("Native campaign archive changed")
    if (checksums != implementation_checksums() or files != inventory(source)
            or hashlib.sha256(library.read_bytes()).hexdigest() != provenance["sha256"]
            or hashlib.sha256(library.with_name("native.json").read_bytes()).hexdigest() != provenance["metadata_sha256"]):
        raise ValueError("Input, implementation or native binary changed during campaign")
    from . import __version__
    return {"schema_version": 6, "rkv1_version": __version__, "dataset": source.name,
            "started_utc": started, "finished_utc": timestamp(), "files": files,
            "raw_file_bytes": sum(f["bytes"] for f in files), "implementation_checksums": checksums,
            "native_provenance": provenance, "results": rows,
            "restore_execution_order": restore_jobs, "range_execution_order": jobs,
            "protocol": {"rounds": rounds, "queries_per_group": queries, "warmup_queries_per_group": warmup_queries,
                         "seed": seed, "archives": "two deterministic encodings; same archive file for both backends",
                         "restore": "one labelled warmup and five default formal fresh-process restores per condition; all jobs shuffled; hash/load/FFI/copies/codec/integrity included",
                         "ranges": "all conditions, rounds and modes shuffled; actual requests matched across conditions",
                         "cache": "pre-read archive; warm OS cache; process initialization excluded from warmed range queries",
                         "rust_scope": "exact CSV v1 inverse only; encoding/codecs/SHA/file IO remain Python or existing libraries",
                         "cost": "complete archive plus separately reported DLL and metadata deployment cost",
                         "rss": "full restoration in separate workers; range includes truth and analytical ledger reader"},
            "unmeasured": {"cold_os_cache": None, "cross_machine": None, "cross_day": None, "inference_quality": None},
            "limits": ["single host, warm cache, background load uncontrolled; no significance or universal optimum claim",
                       "process-level load cache requires immutable trusted library; shared/system dependencies not fully measured",
                       "native archive bytes unchanged; no Rust codec, hash, encoder or append-only CAS result"]}
