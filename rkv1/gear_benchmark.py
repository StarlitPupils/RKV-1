"""Same-profile, byte-identical Python/Rust Gear submission controls."""
import hashlib
from pathlib import Path
import statistics

from .native import load_native_gear
from .store_benchmark import version_benchmark


def gear_benchmark(sources, library, *, rounds=5, queries=64, warmup_queries=4,
                   include_controls=True, compression="zstd", scale=65536):
    library = Path(library).resolve()
    provenance = load_native_gear(str(library)).provenance
    rust_sources = Path(__file__).resolve().parent.parent / "rust"
    kernel_hashes = {p.relative_to(rust_sources).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(rust_sources.rglob("*.rs")) if "target" not in p.parts}
    configs = []
    if include_controls:
        configs += [{"name": "archive-fixed-1024", "kind": "archive", "chunker": "fixed",
                     "chunk_size": 1048576, "compression": compression},
                    {"name": "shared-fixed-64", "kind": "shared", "chunker": "fixed",
                     "chunk_size": scale, "compression": compression}]
    kinds = ("isolated", "shared") if include_controls else ("shared",)
    for kind in kinds:
        for backend in ("python", "rust"):
            config = {"name": f"{kind}-gear-v1-{scale//1024}-{backend}", "kind": kind,
                      "chunker": "gear-v1", "chunk_size": scale, "compression": compression,
                      "chunker_backend": backend}
            if backend == "rust":
                config["native_library"] = str(library)
            configs.append(config)
    result = version_benchmark(sources, configs=configs, rounds=rounds, queries=queries, warmup_queries=warmup_queries)
    comparisons = []
    for kind in kinds:
        paired = {r["configuration"]["chunker_backend"]: r for r in result["results"]
                  if r["configuration"]["kind"] == kind and r["configuration"]["chunker"] == "gear-v1"}
        left, right = paired["python"], paired["rust"]
        if left["storage"]["logical_file_bytes"] != right["storage"]["logical_file_bytes"]:
            raise ValueError("Gear backends differ in stored size")
        for a, b in zip(left["sequence_trials"], right["sequence_trials"]):
            if a["round"] != b["round"] or a["deterministic_files_sha256"] != b["deterministic_files_sha256"]:
                raise ValueError("Gear backends differ in complete tree bytes")
            if any(x["add"]["stats"] != y["add"]["stats"] for x, y in zip(a["versions"], b["versions"])):
                raise ValueError("Gear backends differ in object/reference ledgers")
        def times(row):
            return {t["round"]: t["setup_s"] + sum(v["add"]["wall_s"] for v in t["versions"])
                    for t in row["sequence_trials"] if t["round"] >= 0}
        py, rs = times(left), times(right)
        samples = [py[i] / rs[i] for i in sorted(py)]
        comparisons.append({"kind": kind, "python": left["configuration"]["name"], "rust": right["configuration"]["name"],
                            "identical_complete_tree": True, "identical_all_add_ledgers": True,
                            "complete_tree_sha256": left["sequence_trials"][0]["deterministic_files_sha256"],
                            "paired_submission_speedup_samples": samples,
                            "paired_submission_speedup_median": statistics.median(samples),
                            "rust_faster_rounds": sum(rs[i] < py[i] for i in py), "rounds": rounds})
    if (hashlib.sha256(library.read_bytes()).hexdigest() != provenance["sha256"]
            or hashlib.sha256(library.with_name("native.json").read_bytes()).hexdigest() != provenance["metadata_sha256"]
            or kernel_hashes != {p.relative_to(rust_sources).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(rust_sources.rglob("*.rs")) if "target" not in p.parts}):
        raise ValueError("Native binary, metadata or kernel source changed during campaign")
    result.update({"schema_version": 8, "native_provenance": provenance,
                   "rust_source_checksums": kernel_hashes, "backend_encoding_equivalence": comparisons})
    result["protocol"]["controls"] = "Same Python pipeline/profile: only boundary scan switches Python/Rust; legacy 1MiB archive and shared fixed CAS controls. No transform or model."
    result["protocol"]["native"] = "Explicit frozen CI binary; first add includes hash/provenance checking and CDLL load. Python still assembles chunks, hashes, verifies, compresses, fsyncs and publishes. Restores/reads use identical Python CAS readers; timing differences there are not Rust decoder gains."
    result["protocol"]["native_cost"] = "Full DLL+native.json reported once separately, then added to shared logical cost for a single deployment; common Python/codec/OS costs unallocated."
    return result
