"""Same-container E0 controls and E2 trials with independent phase processes."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import tempfile
import time

from .benchmark import peak_rss, summary
from .core import Archive, MAX_OUTPUT, assert_tree_equal, files_in, pack, unpack


def implementation_checksums():
    root = Path(__file__).parent
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*.py"))}


def runtime_footprint():
    root = Path(__file__).parent
    zstd_info = None
    try:
        distribution = importlib.metadata.distribution("zstandard")
        files = [distribution.locate_file(p) for p in distribution.files or []]
        existing = [p for p in files if p.is_file()]
        from .codecs import zstd_module
        zstd_info = {"package_version": distribution.version,
                     "native_library_version": list(zstd_module().ZSTD_VERSION),
                     "installed_distribution_bytes": sum(p.stat().st_size for p in existing),
                     "recorded_files": len(existing),
                     "basis": "installed distribution files; includes metadata/backends; may exclude linked dependencies"}
    except importlib.metadata.PackageNotFoundError:
        pass
    return {"zstandard": zstd_info, "rkv_source_bytes": sum(p.stat().st_size for p in root.rglob("*.py")),
            "transform_module_source_bytes": (root / "transforms.py").stat().st_size,
            "experiment_source_bytes": sum(p.stat().st_size for p in (root / "experiments").glob("*.py")),
            "accounting": "RKV/transform source shared by all v2 conditions; Python/shared native dependencies not assigned per archive; optional Zstd distribution is a deployment cost",
            "not_a_complete_deployment_size": True}


def inventory(source):
    files = list(files_in(source))
    if sum(p.stat().st_size for p, _ in files) > MAX_OUTPUT:
        raise ValueError("Controlled benchmark limited to 2 GiB input")
    result = []
    for path, rel in files:
        h = hashlib.sha256()
        with path.open("rb") as stream:
            while data := stream.read(1 << 20):
                h.update(data)
        result.append({"path": rel, "bytes": path.stat().st_size, "sha256": h.hexdigest()})
    return result


def request_groups(files, chunk_size, queries, seed):
    """Uniform bytes across eligible files; explicitly separate cross-block reads."""
    rng = random.Random(seed)
    groups = {}
    filters = {
        "byte_weighted": lambda n: n > 0,
        "small_file": lambda n: 0 < n < 1 << 20,
        "large_file": lambda n: n >= 1 << 20,
        "cross_chunk": lambda n: n > chunk_size,
    }
    for name, predicate in filters.items():
        candidates = [f for f in files if predicate(f["bytes"])]
        requests = []
        if candidates:
            weights = [f["bytes"] for f in candidates]
            for _ in range(queries):
                entry = rng.choices(candidates, weights=weights, k=1)[0]
                size = entry["bytes"]
                if name == "cross_chunk":
                    boundary = rng.randint(1, (size - 1) // chunk_size) * chunk_size
                    start = max(0, boundary - 2048)
                    length = min(4096, size - start)
                else:
                    length = min(4096, size)
                    start = rng.randrange(size - length + 1)
                requests.append({"path": entry["path"], "offset": start, "length": length})
        groups[name] = requests
    return groups


def _range_worker(source, archive, config):
    files = [{"path": rel, "bytes": path.stat().st_size} for path, rel in files_in(source)]
    requests = request_groups(files, config["chunk_size"], config["queries"], config["seed"])
    output = {}
    for mode in ("open_reader", "open_and_read"):
        groups = {}
        reader = Archive(archive) if mode == "open_reader" else None
        try:
            for name, ranges in requests.items():
                times = []
                for request in ranges:
                    with (Path(source) / request["path"]).open("rb") as stream:
                        stream.seek(request["offset"])
                        expected = stream.read(request["length"])
                    start = time.perf_counter()
                    if reader:
                        actual = reader.read_range(request["path"], request["offset"], request["length"])
                    else:
                        with Archive(archive) as opened:
                            actual = opened.read_range(request["path"], request["offset"], request["length"])
                    times.append(time.perf_counter() - start)
                    if actual != expected:
                        raise ValueError("Controlled byte range mismatch")
                groups[name] = {"latency_s": summary(times), "verified_requests": len(times)}
            output[mode] = groups
        finally:
            if reader:
                reader.close()
    return {"ranges": output, "peak_rss_bytes": peak_rss(), "verified": True}


def worker(phase, source, archive, destination, config):
    from .experiments.decoder_policy import select_csv_decoder
    select_csv_decoder(config.get("csv_decoder", "current"))
    if phase == "ranges":
        return _range_worker(source, archive, config)
    start, cpu = time.perf_counter(), time.process_time()
    if phase == "encode":
        stats = pack(source, archive, config["chunk_size"], overwrite=True,
                     compression=config["compression"], deduplicate=config["deduplicate"],
                     transform=config["transform"], base=config.get("base"), unit_size=config.get("unit_size"),
                     format_version=config.get("format_version"))
    elif phase == "decode":
        stats = unpack(archive, destination, decoder_backend=config.get("decoder_backend", "python"),
                       native_library=config.get("native_library"))
    else:
        raise ValueError("Unknown phase")
    return {"wall_s": time.perf_counter() - start, "cpu_s": time.process_time() - cpu,
            "peak_rss_bytes": peak_rss(), "stats": stats}


def _child(phase, source, archive, destination, config):
    result = subprocess.run([sys.executable, "-m", "rkv1.controlled", phase, str(source), str(archive),
                             str(destination), json.dumps(config)], capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise ValueError(f"{phase} worker failed: {result.stderr[-4000:]}")
    return json.loads(result.stdout)


def configuration(compression="zstd", chunk_size=1 << 20, deduplicate=True, transform="none", queries=128, seed=20261014):
    return {"compression": compression, "chunk_size": chunk_size, "deduplicate": deduplicate,
            "transform": transform, "queries": queries, "seed": seed}


def measure(source, config, *, repeats=5, warmups=1, ranges=True):
    if not 1 <= repeats <= 100 or not 0 <= warmups <= 10 or not 0 <= config["queries"] <= 10000:
        raise ValueError("Invalid controlled benchmark counts")
    checksums = implementation_checksums()
    encoded, decoded, hashes = [], [], set()
    with tempfile.TemporaryDirectory(prefix="rkv-controlled-") as temp:
        root = Path(temp)
        archive = root / "snapshot.rkv"
        for i in range(warmups + repeats):
            destination = root / f"restored-{i}"
            enc = _child("encode", source, archive, destination, config)
            dec = _child("decode", source, archive, destination, config)
            assert_tree_equal(source, destination)
            # This directory is a known child of this private temporary root.
            if not destination.resolve().is_relative_to(root.resolve()):
                raise ValueError("Invalid temporary restoration path")
            shutil.rmtree(destination)
            if i >= warmups:
                encoded.append(enc)
                decoded.append(dec)
                hashes.add(enc["stats"]["archive_sha256"])
        if len(hashes) != 1:
            raise ValueError("Non-deterministic archive bytes")
        reads = _child("ranges", source, archive, root / "unused", config) if ranges else None
    if implementation_checksums() != checksums:
        raise ValueError("Implementation files changed during measurement; repeat with fixed source")
    return {"configuration": {k: v for k, v in config.items() if k != "base"}, "implementation_checksums": checksums,
            "encode_s": summary([r["wall_s"] for r in encoded]), "decode_s": summary([r["wall_s"] for r in decoded]),
            "encode_cpu_s": summary([r["cpu_s"] for r in encoded]), "decode_cpu_s": summary([r["cpu_s"] for r in decoded]),
            "encode_peak_rss_bytes": summary([r["peak_rss_bytes"] for r in encoded]),
            "decode_peak_rss_bytes": summary([r["peak_rss_bytes"] for r in decoded]),
            "storage": encoded[-1]["stats"], "range_reads": reads,
            "bytewise_verified": True, "verified_measured_roundtrips": repeats,
            "verified_warmup_roundtrips": warmups, "deterministic_archive_bytes": True}


def controlled_benchmark(source, *, configs=None, repeats=5, warmups=1, queries=128, csv_trials=False):
    source = Path(source).resolve()
    files = inventory(source)
    if configs is None:
        configs = [configuration(codec, chunk, dedup, queries=queries)
                   for chunk in (65536, 262144, 1048576) for codec in ("raw", "zlib", "zstd") for dedup in (False, True)]
        if csv_trials:
            configs.extend(configuration(codec, chunk, True, "csv-columns-v1", queries)
                           for chunk in (65536, 262144, 1048576) for codec in ("zlib", "zstd"))
    # Shuffle execution order reproducibly to reduce fixed-order bias.
    configs = list(configs)
    random.Random(20261014).shuffle(configs)
    rows = []
    for index, config in enumerate(configs):
        print(f"{source.name}: {index + 1}/{len(configs)} {config}", file=sys.stderr, flush=True)
        rows.append(measure(source, config, repeats=repeats, warmups=warmups))
    from . import __version__
    return {"schema_version": 2, "rkv1_version": __version__, "dataset": source.name, "files": files,
            "raw_file_bytes": sum(f["bytes"] for f in files),
            "environment": {"python": platform.python_version(), "platform": platform.platform(), "processor": platform.processor(),
                            "logical_cpus": os.cpu_count(), "zstandard": importlib.metadata.version("zstandard")},
            "protocol": {"repeats": repeats, "warmups": warmups, "queries_per_available_group": queries,
                         "container": "RKV1 v2 for every method", "verification": "SHA-256 manifest/chunks/files; external bytewise comparison",
                         "persistence": "same pack: temporary file, flush, fsync, atomic replace, archive digest",
                         "memory": "encode/decode/range phases in separate fresh processes; RSS includes runtime and buffers",
                         "range_cache": "OS cache warm; open_reader excludes manifest open; open_and_read includes open/close; no OS cache eviction",
                         "sampling": "file probabilities proportional to raw bytes; separate small/large/cross-chunk groups",
                         "order": "configuration order shuffled with seed 20261014"},
            "results": rows, "inference_quality": None,
            "limits": ["single host, uncontrolled background load", "OS warm cache; reopen is not a cold-disk measurement", "RKV container controls only, not a claim against all seekable storage systems"]}


def incremental_matrix(source, *, repeats=5, warmups=1):
    """Largest-file edits and metadata-only changes, matched full/reuse trials."""
    source = Path(source).resolve()
    original = inventory(source)
    if not original:
        raise ValueError("Incremental matrix needs files")
    largest = max(original, key=lambda f: f["bytes"])["path"]
    smallest = min(original, key=lambda f: f["bytes"])["path"]
    probe = b"\nRKV1-controlled-incremental-probe\n"
    results = []
    with tempfile.TemporaryDirectory(prefix="rkv-updates-") as temp:
        root = Path(temp)
        base = root / "base.rkv"
        config = configuration(queries=0)
        pack(source, base, config["chunk_size"], compression=config["compression"])
        for case in ("append_largest", "insert_middle_largest", "replace_equal_length_largest", "rename_largest", "delete_smallest"):
            snapshot = root / case
            shutil.copytree(source, snapshot)
            target = snapshot / largest
            if case == "append_largest":
                with target.open("ab") as stream:
                    stream.write(probe)
            elif case in ("insert_middle_largest", "replace_equal_length_largest"):
                raw = target.read_bytes()
                middle = len(raw) // 2
                advance = len(probe) if case == "replace_equal_length_largest" else 0
                target.write_bytes(raw[:middle] + probe + raw[middle + advance:])
            elif case == "rename_largest":
                target.rename(target.with_name("renamed-" + target.name))
            else:
                (snapshot / smallest).unlink()
            pair = {}
            # Reuse/full order alternates across cases.
            modes = ("full", "reuse") if len(results) % 2 == 0 else ("reuse", "full")
            for mode in modes:
                print(f"incremental {source.name}: {case} {mode}", file=sys.stderr, flush=True)
                settings = {**config, **({"base": str(base)} if mode == "reuse" else {})}
                pair[mode] = measure(snapshot, settings, repeats=repeats, warmups=warmups, ranges=False)
            results.append({"case": case, "files": inventory(snapshot), "runs": pair})
    return {"dataset": source.name, "original_files": original, "largest_file": largest, "smallest_file": smallest,
            "repeats": repeats, "warmups": warmups, "results": results,
            "limitation": "fixed chunks; every mode reads/hashes source and writes a complete independent archive"}


if __name__ == "__main__":
    phase, source, archive, destination, settings = sys.argv[1:]
    print(json.dumps(worker(phase, source, archive, destination, json.loads(settings))))
