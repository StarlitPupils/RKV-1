"""Repeated warm-cache range trials; reader lifetime and query seeds are explicit.

This module changes the measurement protocol, not the RKV archive format. Each
trial uses a fresh process. Reopening a file does not evict the OS page cache.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import tempfile
import time

from .benchmark import peak_rss, summary
from .controlled import implementation_checksums, inventory, request_groups
from .core import Archive, files_in, pack, verify
from .units import ENTRY

MODES = ("open_reader", "open_and_read")


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def round_seed(seed, session, round_index):
    encoded = f"RKV-read-v3:{seed}:{session}:{round_index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "little")


def fingerprint(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while data := stream.read(1 << 20):
            result.update(data)
    return result.hexdigest()


def touched_bytes(header, request, reader=None):
    """Logical decode/IO work, not physical disk traffic or hardware cache hits."""
    entry = next(f for f in header["files"] if f["path"] == request["path"])
    chunk = header["chunk_size"]
    first = request["offset"] // chunk
    last = (request["offset"] + request["length"] + chunk - 1) // chunk
    keys = entry["chunks"][first:last] if request["length"] else []
    blocks = [header["blocks"][key] for key in keys]
    if header.get("version", 2) == 3:
        if reader is None:
            raise ValueError("Unit work ledger needs an unmeasured index reader")
        raw_bytes = stored_bytes = unit_count = index_bytes = 0
        unit = header["unit_size"]
        for parent, key in enumerate(keys, start=first):
            meta = header["blocks"][key]
            index, _, _ = reader.unit_index(key)
            index_bytes += len(index)
            start = max(0, request["offset"] - parent * chunk)
            end = min(meta["raw_size"], request["offset"] + request["length"] - parent * chunk)
            for i in range(start // unit, (end + unit - 1) // unit):
                raw, stored, *_ = ENTRY.unpack_from(index, i * ENTRY.size)
                raw_bytes += raw
                stored_bytes += stored
                unit_count += 1
        return {"requested_bytes": request["length"], "chunk_decodes": 0, "unit_decodes": unit_count,
                "parent_chunks_touched": len(keys), "decoded_raw_bytes": raw_bytes,
                "stored_payload_bytes": stored_bytes, "referenced_index_bytes": index_bytes}
    return {"requested_bytes": request["length"], "chunk_decodes": len(blocks),
            "decoded_raw_bytes": sum(b["raw_size"] for b in blocks),
            "stored_payload_bytes": sum(b["stored_size"] for b in blocks)}


def range_trial(source, archive, settings):
    from .experiments.decoder_policy import select_csv_decoder
    select_csv_decoder(settings.get("csv_decoder", "current"))
    mode = settings["mode"]
    cas = settings.get("storage_kind", "archive") == "cas"
    if settings.get("storage_kind", "archive") not in ("archive", "cas"):
        raise ValueError("Unknown range storage kind")
    if cas:
        from .store import Store, OBJECT
        from .store_policy import open_store
    if mode not in MODES:
        raise ValueError("Invalid range-reader mode")
    files = [{"path": rel, "bytes": path.stat().st_size} for path, rel in files_in(source)]
    warmups, queries = settings["warmup_queries"], settings["queries"]
    plans = request_groups(files, settings.get("query_boundary_size", settings["chunk_size"]),
                          queries + warmups, settings["query_seed"])
    if settings.get("boundary_group") == "cross_unit":
        plans["cross_unit"] = plans.pop("cross_chunk")
    # Prepare truth before warming the archive, and outside every timed request.
    expected = {}
    for group, requests in plans.items():
        values = []
        for request in requests:
            with (Path(source) / request["path"]).open("rb") as stream:
                stream.seek(request["offset"])
                values.append(stream.read(request["length"]))
        expected[group] = values
    warmed = 0
    if cas:
        selected = open_store(archive, settings).snapshot(settings["snapshot_id"])
        keys = {r["id"] for e in selected.files.values() for r in e["chunks"]}
        paths = [selected.store.root / "config.rkvc", selected.store.root / "snapshots" / (selected.snapshot_id + ".rkvs")]
        paths.extend(selected.store.object_path(key) for key in sorted(keys))
    else:
        paths = [Path(archive)]
    for path in paths:
        with path.open("rb") as stream:
            while data := stream.read(1 << 20):
                warmed += len(data)
    started = timestamp()
    opened_at = time.perf_counter()
    cache_bytes = settings.get("index_cache_bytes", 1 << 20)
    reader_options = {"index_cache_bytes": cache_bytes, "decoder_backend": settings.get("decoder_backend", "python"),
                      "native_library": settings.get("native_library")}
    def open_reader():
        return open_store(archive, settings).snapshot(settings["snapshot_id"]) if cas else Archive(archive, **reader_options)
    persistent = open_reader() if mode == "open_reader" else None
    initial_open_s = time.perf_counter() - opened_at if persistent is not None else None
    # Use a separate unmeasured reader for the analytical block-work ledger.
    metadata = open_store(archive, settings).snapshot(settings["snapshot_id"]) if cas else Archive(archive)
    header = metadata.header
    group_order = list(plans)
    random.Random(settings["query_seed"] ^ 0x726B76).shuffle(group_order)
    groups = {}
    try:
        for group in group_order:
            latencies, open_times, read_times, close_times = [], [], [], []
            ledger = {k: 0 for k in ("requested_bytes", "chunk_decodes", "decoded_raw_bytes", "stored_payload_bytes")}
            for index, request in enumerate(plans[group]):
                start = time.perf_counter()
                reader = persistent if persistent is not None else open_reader()
                after_open = time.perf_counter()
                try:
                    actual = reader.read_range(request["path"], request["offset"], request["length"])
                    after_read = time.perf_counter()
                finally:
                    if persistent is None:
                        reader.close()
                end = time.perf_counter()
                if actual != expected[group][index]:
                    raise ValueError("Repeated byte-range mismatch")
                if index < warmups:
                    continue
                latencies.append(end - start)
                read_times.append(after_read - after_open)
                if persistent is None:
                    open_times.append(after_open - start)
                    close_times.append(end - after_read)
                if cas:
                    from .store_benchmark import cas_touched_bytes
                    work = cas_touched_bytes(metadata, request)
                else:
                    work = touched_bytes(header, request, metadata)
                for key, value in work.items():
                    ledger[key] = ledger.get(key, 0) + value
            measured = plans[group][warmups:]
            groups[group] = {"requests": measured, "request_sha256": fingerprint(measured),
                             "latency_s": summary(latencies), "open_s": summary(open_times),
                             "read_s": summary(read_times), "close_s": summary(close_times),
                             "verified_requests": len(latencies),
                             "verified_warmup_requests": min(warmups, len(plans[group])),
                             "work": ledger,
                             "decode_amplification": ledger["decoded_raw_bytes"] / ledger["requested_bytes"]
                             if ledger["requested_bytes"] else None}
    finally:
        if persistent is not None:
            persistent.close()
        metadata.close()
    return {"session": settings["session"], "round": settings["round"], "query_seed": settings["query_seed"],
            "mode": mode, "started_utc": started, "finished_utc": timestamp(),
            "group_order": group_order, "initial_open_s": initial_open_s,
            "cache": {"condition": "warm_archive", "pre_read_bytes": warmed,
                      "os_cache_evicted": False, "physical_disk_reads_measured": False},
            "peak_rss_bytes": peak_rss(), "groups": groups, "bytewise_verified": True}


def aggregate_trials(trials):
    output = {}
    for mode in MODES:
        rows = [r for r in trials if r["mode"] == mode]
        groups = {}
        categories = ("byte_weighted", "small_file", "large_file", "cross_chunk")
        if any("cross_unit" in r["groups"] for r in rows):
            categories += ("cross_unit",)
        for name in categories:
            available = [r["groups"][name] for r in rows
                         if name in r["groups"] and r["groups"][name]["latency_s"] is not None]
            if not available:
                groups[name] = None
                continue
            groups[name] = {
                "round_p95_s": summary([r["latency_s"]["p95"] for r in available]),
                "round_median_s": summary([r["latency_s"]["median"] for r in available]),
                "round_open_median_s": summary([r["open_s"]["median"] for r in available]) if mode == "open_and_read" else None,
                "round_read_median_s": summary([r["read_s"]["median"] for r in available]),
                "decode_amplification": summary([r["decode_amplification"] for r in available]),
                "verified_requests": sum(r["verified_requests"] for r in available),
                "rounds": len(available),
            }
        output[mode] = {"groups": groups, "peak_rss_bytes": summary([r["peak_rss_bytes"] for r in rows])}
    return output


def read_benchmark(source, *, sessions=2, rounds=5, queries=128, warmup_queries=8,
                   seed=20261014, codecs=("raw", "zlib", "zstd"), chunks=(65536, 262144, 1048576)):
    if (any(type(v) is not int for v in (sessions, rounds, queries, warmup_queries, seed))
            or not 1 <= sessions <= 10 or not 1 <= rounds <= 100 or not 1 <= queries <= 10000
            or not 0 <= warmup_queries <= 128 or type(seed) is not int):
        raise ValueError("Invalid repeated reading benchmark counts")
    if (not codecs or len(set(codecs)) != len(codecs) or any(c not in ("raw", "zlib", "zstd") for c in codecs)
            or not chunks or len(set(chunks)) != len(chunks) or any(type(c) is not int or not 1 <= c <= 8 << 20 for c in chunks)):
        raise ValueError("Invalid reading codec/chunk matrix")
    source = Path(source).resolve()
    files = inventory(source)
    if not any(f["bytes"] for f in files):
        raise ValueError("Reading benchmark needs a nonempty file")
    checksums = implementation_checksums()
    started = timestamp()
    results, session_records = [], []
    with tempfile.TemporaryDirectory(prefix="rkv-read-matrix-") as temp:
        root = Path(temp)
        for codec in codecs:
            for chunk in chunks:
                archive = root / f"{codec}-{chunk}.rkv"
                stats = pack(source, archive, chunk, compression=codec)
                verify(archive)
                results.append({"configuration": {"compression": codec, "chunk_size": chunk,
                                                   "deduplicate": True, "transform": "none"},
                                "storage": stats, "full_archive_verified": True, "trials": []})
        for session in range(sessions):
            began = timestamp()
            jobs = [(index, round_index, mode) for index in range(len(results))
                    for round_index in range(rounds) for mode in MODES]
            random.Random(round_seed(seed, session, -1)).shuffle(jobs)
            for position, (index, round_index, mode) in enumerate(jobs):
                row = results[index]
                config = row["configuration"]
                archive = root / f'{config["compression"]}-{config["chunk_size"]}.rkv'
                settings = {**config, "mode": mode, "queries": queries, "warmup_queries": warmup_queries,
                            "query_seed": round_seed(seed, session, round_index),
                            "session": session, "round": round_index}
                print(f"{source.name} session {session + 1}/{sessions} trial {position + 1}/{len(jobs)} "
                      f'{config["compression"]}/{config["chunk_size"]} {mode}', file=sys.stderr, flush=True)
                child = subprocess.run([sys.executable, "-m", "rkv1.read_benchmark", str(source),
                                        str(archive), json.dumps(settings)], capture_output=True, text=True, encoding="utf-8")
                if child.returncode:
                    raise ValueError(f"Reading worker failed: {child.stderr[-4000:]}")
                trial = json.loads(child.stdout)
                trial["execution_index"] = position
                row["trials"].append(trial)
            session_records.append({"session": session, "started_utc": began, "finished_utc": timestamp(),
                                    "execution_order": [list(job) for job in jobs]})
        for row in results:
            row["trials"].sort(key=lambda t: (t["session"], t["round"], t["mode"]))
            row["aggregate"] = aggregate_trials(row["trials"])
            config = row["configuration"]
            if file_digest(root / f'{config["compression"]}-{config["chunk_size"]}.rkv') != row["storage"]["archive_sha256"]:
                raise ValueError("Archive changed during reading trials")
    if checksums != implementation_checksums() or files != inventory(source):
        raise ValueError("Implementation or input changed during reading measurement")
    from . import __version__
    try:
        zstd_version = importlib.metadata.version("zstandard")
    except importlib.metadata.PackageNotFoundError:
        zstd_version = None
    return {"schema_version": 3, "rkv1_version": __version__, "dataset": source.name,
            "started_utc": started, "finished_utc": timestamp(), "files": files,
            "raw_file_bytes": sum(f["bytes"] for f in files), "implementation_checksums": checksums,
            "environment": {"python": platform.python_version(), "platform": platform.platform(),
                            "processor": platform.processor(), "logical_cpus": os.cpu_count(), "zstandard": zstd_version},
            "protocol": {"sessions": sessions, "rounds_per_session": rounds, "queries_per_available_group_per_round": queries,
                         "warmup_queries_per_group": warmup_queries, "master_seed": seed,
                         "query_seed": "SHA-256(RKV-read-v3:master:session:round), first eight bytes little-endian",
                         "matching": "same queries across codecs, chunks and modes for non-crossing groups; cross_chunk depends on block size",
                         "order": "configurations/rounds/modes interleaved and shuffled per session; query categories shuffled per round",
                         "cache": "full archive pre-read before each trial; OS warm cache, fresh Python worker per mode/round",
                         "timing": "request total; separate open/read/close spans; truth reads and byte comparison excluded; worker startup excluded",
                         "summary": "median and range of per-round nearest-rank p95, not a confidence interval or pooled p95",
                         "storage": "same RKV v2 container, dedup on, transform none; raw/Zlib 6/Zstd 3",
                         "work": "analytical touched raw/stored payload bytes, not physical disk IO"},
            "sessions": session_records, "results": results,
            "unmeasured": {"cold_os_cache": None, "cross_machine": None, "cross_day": None,
                           "mature_seekable_comparison": None, "inference_quality": None},
            "limits": ["single host, uncontrolled background load", "sessions are consecutive within one campaign",
                       "no OS cache eviction; warm results cannot predict cold disk latency",
                       "query-level dependencies and only a few rounds; no statistical significance claim",
                       "decoder RSS includes prepared truth bytes and runtime; not comparable to v0.2 restore RSS"]}


if __name__ == "__main__":
    source, archive, settings = sys.argv[1:]
    print(json.dumps(range_trial(source, archive, json.loads(settings))))
