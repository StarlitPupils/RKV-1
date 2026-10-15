"""CAS IO ablations: frozen reference, bounded reads, and Windows no-replace rename."""
import hashlib
import os
from pathlib import Path
import statistics

from .native import load_native_gear
from .store_benchmark import version_benchmark


def matrix(library=None, *, compression="zstd", scale=65536):
    common = {"chunker": "gear-v1", "chunk_size": scale, "compression": compression,
              "chunker_backend": "rust" if library is not None else "python"}
    if library is not None:
        common["native_library"] = str(Path(library).resolve())
    configs = [{"name": "archive-fixed-1024", "kind": "archive", "chunker": "fixed",
                "chunk_size": 1048576, "compression": compression},
               {"name": "shared-fixed-v08", "kind": "shared", "chunker": "fixed",
                "chunk_size": scale, "compression": compression, "store_implementation": "v0.8"},
               {**common, "name": "isolated-gear-v08", "kind": "isolated", "store_implementation": "v0.8"},
               {**common, "name": "shared-gear-v08", "kind": "shared", "store_implementation": "v0.8"}]
    policies = [("reference", "reference", "link"), ("bounded", "bounded", "link")]
    if os.name == "nt":
        policies += [("rename", "reference", "rename"), ("combined", "bounded", "rename")]
    configs += [{**common, "name": "shared-gear-" + name, "kind": "shared",
                 "store_implementation": "current", "io_backend": io, "publisher": publisher}
                for name, io, publisher in policies]
    return configs


def io_benchmark(sources, library=None, *, dataset, configs=None, rounds=5, queries=64, warmup_queries=4):
    provenance = load_native_gear(str(Path(library).resolve())).provenance if library is not None else None
    result = version_benchmark(sources, configs=matrix(library) if configs is None else configs,
                               rounds=rounds, queries=queries, warmup_queries=warmup_queries)
    rows = {r["configuration"]["name"]: r for r in result["results"]}
    groups = {}
    for name, row in rows.items():
        config = row["configuration"]
        key = (config["kind"], config["chunker"], config["chunk_size"], config["compression"])
        fingerprint = row["sequence_trials"][0]["deterministic_files_sha256"]
        if any(t["deterministic_files_sha256"] != fingerprint for t in row["sequence_trials"]):
            raise ValueError("Nonidentical IO policy repeat tree")
        if groups.setdefault(key, fingerprint) != fingerprint:
            raise ValueError("IO policies alter stored bytes")
    paired = []
    baseline = rows["shared-gear-reference"]
    for name in ("shared-gear-v08", "shared-gear-bounded", "shared-gear-rename", "shared-gear-combined"):
        if name not in rows:
            continue
        target = rows[name]
        def times(row):
            return {t["round"]: t["setup_s"] + sum(v["add"]["wall_s"] for v in t["versions"])
                    for t in row["sequence_trials"] if t["round"] >= 0}
        left, right = times(baseline), times(target)
        ratios = [left[i]/right[i] for i in sorted(left)]
        for a, b in zip(baseline["sequence_trials"], target["sequence_trials"]):
            if any(x["add"]["stats"] != y["add"]["stats"] for x,y in zip(a["versions"],b["versions"])):
                raise ValueError("IO policies alter object/publication ledgers")
        paired.append({"reference": "shared-gear-reference", "candidate": name,
                       "submission_speedup_samples": ratios, "submission_speedup_median": statistics.median(ratios),
                       "candidate_faster_rounds": sum(right[i]<left[i] for i in left), "rounds": rounds,
                       "identical_complete_trees_and_ledgers": True})
    if provenance is not None and (hashlib.sha256(Path(library).read_bytes()).hexdigest() != provenance["sha256"]
            or hashlib.sha256(Path(library).with_name("native.json").read_bytes()).hexdigest() != provenance["metadata_sha256"]):
        raise ValueError("Frozen native identity changed during IO campaign")
    result.update({"schema_version": 9, "dataset": dataset, "native_provenance": provenance,
                   "io_submission_comparisons": paired,
                   "identical_encoding_groups": [{"kind": key[0], "chunker": key[1], "scale": key[2],
                                                    "compression": key[3], "tree_sha256": value} for key,value in groups.items()]})
    result["protocol"]["controls"] = "Frozen v0.8 store; current reference/link scaffold; bounded read/mkdir only; Windows rename only; combined. Legacy 1MiB and shared fixed64 controls. All Gear uses the same frozen Rust scanner."
    result["protocol"]["publication"] = "Each new file is flushed/fsynced before no-replace link or Windows same-directory rename. All objects precede snapshot. No skipped old-object decompression or SHA checks. IO flags are instance-only and never serialized."
    result["protocol"]["reading"] = "Restore/range use the selected read policy. Rename changes publication only; its read timing differences are repeated observations, not a separate decoder."
    result["protocol"]["native"] = ("Full frozen v0.8 DLL and original metadata charged once; no new native IO implementation or model."
                                    if provenance else "Python-only protocol smoke; no native speed claim.")
    result["limits"][0] = f"one scientific corpus family, {len(sources)} real releases per report; aggregate campaigns are separate families"
    return result
