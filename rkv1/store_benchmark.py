"""Real-version independent archives / isolated CAS / shared CAS controls."""
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time

from .benchmark import peak_rss, summary
from .controlled import implementation_checksums, inventory
from .core import assert_tree_equal, pack, unpack as archive_unpack
from .read_benchmark import aggregate_trials, file_digest, round_seed, timestamp
from .store import Store, OBJECT, _allocated, unpack as store_unpack


def matrix():
    return [{"name": f"archive-fixed-{size//1024}", "kind": "archive", "chunker": "fixed", "chunk_size": size, "compression": "zstd"}
            for size in (65536, 1048576)] + [
        {"name": f"{kind}-{mode}-{size//1024}", "kind": kind, "chunker": mode, "chunk_size": size, "compression": "zstd"}
        for kind in ("isolated", "shared") for mode, size in (("fixed", 65536), ("fixed", 1048576), ("gear-v1", 65536))]


def cas_touched_bytes(reader, request):
    entry = reader.files[request["path"]]
    offsets = reader.offsets[request["path"]]
    start, end = request["offset"], request["offset"] + request["length"]
    i = bisect_right(offsets, start) - 1
    refs = []
    while request["length"] and i < len(entry["chunks"]) and offsets[i] < end:
        refs.append(entry["chunks"][i]); i += 1
    return {"requested_bytes": request["length"], "chunk_decodes": len(refs),
            "decoded_raw_bytes": sum(r["size"] for r in refs),
            "stored_payload_bytes": sum(reader.store.object_path(r["id"]).stat().st_size - OBJECT.size for r in refs),
            "object_header_bytes": len(refs) * OBJECT.size}


def _tree_stats(root):
    files = list(Path(root).rglob("*")); files = [p for p in files if p.is_file()]
    allocations = [_allocated(p) for p in files]
    return {"logical_file_bytes": sum(p.stat().st_size for p in files), "files": len(files),
            "allocated_file_data_bytes": sum(allocations) if all(a is not None for a in allocations) else None,
            "filesystem_directory_metadata_journal_unmeasured": True}


def sequence_worker(sources, root, config, round_index):
    root = Path(root)
    rows = []
    shared = root / "shared"
    setup = 0
    if config["kind"] == "shared":
        start = time.perf_counter()
        Store.create(shared, compression=config["compression"], chunker=config["chunker"], chunk_size=config["chunk_size"])
        setup = time.perf_counter() - start
    for index, source in enumerate(map(Path, sources)):
        start, cpu = time.perf_counter(), time.process_time()
        if config["kind"] == "archive":
            target = root / f"{index}.rkv"
            stats = pack(source, target, config["chunk_size"], compression=config["compression"])
            kind, snapshot_id = "archive", None
        else:
            target = shared if config["kind"] == "shared" else root / f"cas-{index}"
            if config["kind"] == "isolated":
                Store.create(target, compression=config["compression"], chunker=config["chunker"], chunk_size=config["chunk_size"])
            stats = Store(target).add(source, label=source.name,
                                     chunker_backend=config.get("chunker_backend", "python"),
                                     native_library=config.get("native_library"))
            kind, snapshot_id = "cas", stats["snapshot_id"]
        add = {"wall_s": time.perf_counter() - start, "cpu_s": time.process_time() - cpu, "stats": stats}
        # Tree/allocation scans are a separate untimed ledger, not add CPU time.
        storage = _tree_stats(root)
        previous = rows[-1]["cumulative_storage"]["logical_file_bytes"] if rows else 0
        expected_growth = (stats["stored_bytes"] if kind == "archive" else stats["new_written_bytes"])
        if config["kind"] == "isolated" or (config["kind"] == "shared" and index == 0):
            expected_growth += (target / "config.rkvc").stat().st_size
        if storage["logical_file_bytes"] - previous != expected_growth:
            raise ValueError("Version ledger excludes or double counts stored files")
        rows.append({"version_index": index, "source": str(source), "storage_kind": kind,
                     "snapshot_id": snapshot_id, "target": str(target), "add": add,
                     "cumulative_storage": storage})
    encoding_rss = peak_rss()
    # Persist references only after completing the chronological add sequence.
    return {"round": round_index, "setup_s": setup, "versions": rows,
            "encode_peak_rss_bytes": encoding_rss, "bytewise_source_hashed": True}


def restore_worker(source, target, destination, kind, snapshot_id):
    start, cpu = time.perf_counter(), time.process_time()
    stats = (store_unpack(target, snapshot_id, destination) if kind == "cas" else archive_unpack(target, destination))
    return {"wall_s": time.perf_counter() - start, "cpu_s": time.process_time() - cpu,
            "peak_rss_bytes": peak_rss(), "stats": stats}


def _child(phase, args):
    child = subprocess.run([sys.executable, "-m", "rkv1.store_benchmark", phase, json.dumps(args)],
                           capture_output=True, text=True, encoding="utf-8")
    if child.returncode:
        raise ValueError(f"Version worker {phase} failed: {child.stderr[-4000:]}")
    return json.loads(child.stdout)


def _fingerprint(root):
    return {p.relative_to(root).as_posix(): file_digest(p) for p in sorted(root.rglob("*")) if p.is_file()}


def version_benchmark(sources, *, configs=None, rounds=5, queries=64, warmup_queries=4, seed=20261015):
    if (any(type(x) is not int for x in (rounds, queries, warmup_queries, seed)) or not 1 <= rounds <= 100
            or not 1 <= queries <= 10000 or not 0 <= warmup_queries <= 128):
        raise ValueError("Invalid version experiment counts")
    sources = [str(Path(s).resolve()) for s in sources]
    if len(sources) < 2:
        raise ValueError("Version sequence needs at least two snapshots")
    files, checksums = [inventory(s) for s in sources], implementation_checksums()
    configs = list(matrix() if configs is None else configs)
    random.Random(seed).shuffle(configs)
    if not configs:
        raise ValueError("No version configurations")
    rows = [{"configuration": c, "sequence_trials": [], "versions": [{"restore_trials": [], "range_trials": []} for _ in sources]} for c in configs]
    started = timestamp()
    with tempfile.TemporaryDirectory(prefix="rkv-version-controls-") as temp:
        root = Path(temp)
        warm = [(i, -1) for i in range(len(rows))]
        formal = [(i, r) for i in range(len(rows)) for r in range(rounds)]
        random.Random(seed ^ 0x5741524D).shuffle(warm); random.Random(seed ^ 0x56455253).shuffle(formal)
        jobs = warm + formal
        fingerprints = {}
        reading_targets = {}
        for position, (index, r) in enumerate(jobs):
            config = rows[index]["configuration"]
            print(f"sequence {position + 1}/{len(jobs)} round {r} {config['name']}", file=sys.stderr, flush=True)
            trial_root = root / f"{index}-{r}"; trial_root.mkdir()
            trial = _child("sequence", {"sources": sources, "root": str(trial_root), "config": config, "round_index": r})
            trial["execution_index"] = position
            # Each restore has its own process and memory peak, as in prior milestones.
            for version_index, record in enumerate(trial["versions"]):
                destination = root / "restored"
                restored = _child("restore", {"source": sources[version_index], "target": record["target"],
                                              "destination": str(destination), "kind": record["storage_kind"], "snapshot_id": record["snapshot_id"]})
                assert_tree_equal(sources[version_index], destination)
                if not destination.resolve().is_relative_to(root.resolve()):
                    raise ValueError("Invalid temporary restored path")
                shutil.rmtree(destination)
                rows[index]["versions"][version_index]["restore_trials"].append(
                    {**restored, "round": r, "bytewise_verified": True, "execution_index": position})
            # Restored outputs are outside the stored corpus and never counted.
            fingerprint = _fingerprint(trial_root)
            if fingerprints.setdefault(index, fingerprint) != fingerprint:
                raise ValueError("Non-deterministic version store/archive bytes")
            trial["deterministic_files_sha256"] = digest_map(fingerprint)
            rows[index]["sequence_trials"].append(trial)
            if r == 0:
                reading_targets[index] = trial
            else:
                if not trial_root.resolve().is_relative_to(root.resolve()):
                    raise ValueError("Invalid temporary trial path")
                shutil.rmtree(trial_root)
        range_jobs = [(i, v, r, mode) for i in range(len(rows)) for v in range(len(sources)) for r in range(rounds)
                      for mode in ("open_reader", "open_and_read")]
        random.Random(seed ^ 0x43415352).shuffle(range_jobs)
        # Isolate sharing from format/encoding effects: union of isolated object
        # bytes must exactly equal the shared store, with identical snapshot IDs.
        equivalence = []
        for index, row in enumerate(rows):
            config = row["configuration"]
            if config["kind"] != "shared":
                continue
            paired = next((j for j, other in enumerate(rows) if other["configuration"]["kind"] == "isolated"
                           and all(other["configuration"][key] == config[key] for key in ("compression", "chunker", "chunk_size"))), None)
            if paired is None:
                continue
            shared_objects = _fingerprint(Path(reading_targets[index]["versions"][0]["target"]) / "objects")
            union = {}
            for a, b in zip(reading_targets[index]["versions"], reading_targets[paired]["versions"]):
                if a["snapshot_id"] != b["snapshot_id"]:
                    raise ValueError("Isolated/shared snapshot representations differ")
                for key, checksum in _fingerprint(Path(b["target"]) / "objects").items():
                    if union.setdefault(key, checksum) != checksum:
                        raise ValueError("CAS encoder differs between isolated versions")
            if union != shared_objects:
                raise ValueError("Shared CAS bytes differ from isolated object union")
            equivalence.append({"shared": config["name"], "isolated": rows[paired]["configuration"]["name"],
                                "identical_snapshot_ids": True, "identical_object_union": True, "unique_objects": len(union)})
        plans = {}
        for position, (index, version_index, r, mode) in enumerate(range_jobs):
            config = rows[index]["configuration"]
            record = reading_targets[index]["versions"][version_index]
            print(f"ranges {position + 1}/{len(range_jobs)} v{version_index} {config['name']} {mode}", file=sys.stderr, flush=True)
            settings = {**config, "session": version_index, "round": r, "mode": mode, "queries": queries,
                        "warmup_queries": warmup_queries, "query_seed": round_seed(seed, version_index, r),
                        "query_boundary_size": 65536, "boundary_group": "cross_unit",
                        "storage_kind": record["storage_kind"], "snapshot_id": record["snapshot_id"]}
            child = subprocess.run([sys.executable, "-m", "rkv1.read_benchmark", sources[version_index], record["target"], json.dumps(settings)],
                                   capture_output=True, text=True, encoding="utf-8")
            if child.returncode:
                raise ValueError(f"Version range worker failed: {child.stderr[-4000:]}")
            trial = json.loads(child.stdout)
            for category, group in trial["groups"].items():
                key = (version_index, r, category)
                if plans.setdefault(key, group["request_sha256"]) != group["request_sha256"]:
                    raise ValueError("Unmatched requests between version conditions")
            rows[index]["versions"][version_index]["range_trials"].append({**trial, "execution_index": position})
        for index, row in enumerate(rows):
            row["sequence_trials"].sort(key=lambda t: t["round"])
            formal_trials = [t for t in row["sequence_trials"] if t["round"] >= 0]
            row["sequence_add_s"] = summary([t["setup_s"] + sum(v["add"]["wall_s"] for v in t["versions"]) for t in formal_trials])
            row["encode_peak_rss_bytes"] = summary([t["encode_peak_rss_bytes"] for t in formal_trials])
            row["storage"] = formal_trials[0]["versions"][-1]["cumulative_storage"]
            for v, item in enumerate(row["versions"]):
                item["restore_trials"].sort(key=lambda t: t["round"])
                item["range_trials"].sort(key=lambda t: (t["round"], t["mode"]))
                formal_restore = [t for t in item["restore_trials"] if t["round"] >= 0]
                item.update({"decode_s": summary([t["wall_s"] for t in formal_restore]),
                             "decode_peak_rss_bytes": summary([t["peak_rss_bytes"] for t in formal_restore]),
                             "add_s": summary([t["versions"][v]["add"]["wall_s"] for t in formal_trials]),
                             "range_aggregate": aggregate_trials(item["range_trials"]),
                             "storage_after_version": formal_trials[0]["versions"][v]["cumulative_storage"],
                             "stats": formal_trials[0]["versions"][v]["add"]["stats"]})
            kept = root / f"{index}-0"
            if _fingerprint(kept) != fingerprints[index]:
                raise ValueError("Stored version bytes changed during reads")
        # Equal-size CAS objects must use identical encoded payloads in isolated/shared controls.
        # Whole-tree repeat fingerprints above include all object headers/manifests/configs.
    if files != [inventory(s) for s in sources] or checksums != implementation_checksums():
        raise ValueError("Version input or implementation changed during experiment")
    from . import __version__
    return {"schema_version": 7, "rkv1_version": __version__, "dataset": "qasper-original-versions",
            "started_utc": started, "finished_utc": timestamp(), "files_by_version": files,
            "raw_bytes_all_versions": sum(f["bytes"] for fs in files for f in fs),
            "implementation_checksums": checksums, "results": rows,
            "cas_encoding_equivalence": equivalence,
            "sequence_execution_order": jobs, "range_execution_order": range_jobs,
            "protocol": {"rounds": rounds, "queries_per_group": queries, "warmup_queries_per_group": warmup_queries, "seed": seed,
                         "chronology": "versions always added in release order; conditions/replicate jobs shuffled; warmups precede formal jobs",
                         "controls": "legacy independent RKV, same-format isolated CAS, shared CAS; fixed 64KiB/1MiB and simple gear-v1 scale64KiB",
                         "integrity": "all restoration paths/bytes compared; CAS config/snapshot/stored/raw/file hashes; archive original checks",
                         "cost": "all logical files, object headers, snapshot/config records, orphans; allocated data extents separately, directory/MFT/journal not counted",
                         "cache": "pre-read selected snapshot records/referenced objects or full archive; warm OS cache; no decoded-data cache",
                         "matching": "actual request fingerprints match all conditions within version/round/category; fixed 64KiB cross-window grid",
                         "timing": "add includes compression, verification/reuse, object/snapshot fsync/publish; allocation/tree audit untimed; shared setup separate but included in sequence total",
                         "rss": "sequence encoding separate worker, includes untimed storage ledger; each restoration separate worker; range includes truth and metadata ledger"},
            "unmeasured": {"cold_os_cache": None, "cross_machine": None, "cross_day": None, "inference_quality": None},
            "limits": ["one scientific corpus family, three real releases; no universal deduplication/CDC result",
                       "gear-v1 is a simple single-mask profile, not a reproduction or speed claim for FastCDC",
                       "shared immutable CAS; failed adds can leave counted orphan objects; no garbage collection or power-loss guarantee",
                       "all sources still read/hashed; CAS adds do not skip source scanning; no neural prediction or semantic reasoning result"]}


def digest_map(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


if __name__ == "__main__":
    phase, arguments = sys.argv[1:]
    args = json.loads(arguments)
    result = sequence_worker(**args) if phase == "sequence" else restore_worker(**args)
    print(json.dumps(result))
