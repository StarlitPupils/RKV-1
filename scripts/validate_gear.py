"""Independent raw-record audit, including exact storage bytes versus released v0.7."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from rkv1.controlled import implementation_checksums
from scripts.run_units import save


def validate(root, reference, library, test_log=None):
    report = json.loads((root / "qasper-gear.json").read_text("utf-8"))
    old = json.loads((reference / "qasper-versions.json").read_text("utf-8"))
    rows = {r["configuration"]["name"]: r for r in report["results"]}
    originals = {r["configuration"]["name"]: r for r in old["results"]}
    checksums = json.loads((root / "source-checksums.json").read_text("utf-8"))
    if checksums != implementation_checksums() or report["files_by_version"] != old["files_by_version"]:
        raise ValueError("Current source or raw input differs from recorded campaign")
    provenance = report["native_provenance"]
    if (hashlib.sha256(library.read_bytes()).hexdigest() != provenance["sha256"]
            or hashlib.sha256(library.with_name("native.json").read_bytes()).hexdigest() != provenance["metadata_sha256"]):
        raise ValueError("Frozen native identity differs")
    historical = []
    plans = {}
    measured = warmups = reads = warm_reads = 0
    for name, row in rows.items():
        previous = originals[name.removesuffix("-python").removesuffix("-rust")]
        old_tree = previous["sequence_trials"][0]["deterministic_files_sha256"]
        if any(t["deterministic_files_sha256"] != old_tree for t in row["sequence_trials"]):
            raise ValueError(f"{name} complete stored bytes differ from v0.7")
        for a, b in zip(row["versions"], previous["versions"]):
            if a["stats"] != b["stats"]:
                raise ValueError("Historical object or archive ledger differs")
        historical.append({"condition": name, "reference": previous["configuration"]["name"],
                           "all_rounds_complete_tree_bytes_identical": True, "tree_sha256": old_tree})
        for version, v in enumerate(row["versions"]):
            for t in v["restore_trials"]:
                if not t["bytewise_verified"]:
                    raise ValueError("Incomplete full restoration")
                measured += t["round"] >= 0; warmups += t["round"] < 0
            for trial in v["range_trials"]:
                for category, group in trial["groups"].items():
                    key = (version, trial["round"], category)
                    if plans.setdefault(key, group["request_sha256"]) != group["request_sha256"]:
                        raise ValueError("Range requests differ between conditions or lifecycle modes")
                    reads += group["verified_requests"]; warm_reads += group["verified_warmup_requests"]
    baseline = json.loads((root / "profiling-baseline.json").read_text("utf-8"))
    if baseline["implementation_checksums"] != old["implementation_checksums"]:
        raise ValueError("Diagnostic baseline is not frozen v0.7 code")
    native_profile = json.loads((root / "profiling-native.json").read_text("utf-8"))
    if baseline["identical_store_tree_sha256"] != native_profile["identical_store_tree_sha256"]:
        raise ValueError("Diagnostic backend storage trees differ")
    tests = None
    if test_log is not None:
        raw_log = test_log.read_bytes()
        text = raw_log.decode("utf-8-sig")
        total = re.search(r"Ran (\d+) tests", text)
        status = re.search(r"^OK(?: \(skipped=(\d+)\))?\r?$", text, re.MULTILINE)
        if not total or not status or "FAILED (" in text:
            raise ValueError("Local unittest log does not show a successful full run")
        run, skipped = int(total[1]), int(status[1] or 0)
        tests = {"run": run, "passed": run-skipped, "skipped": skipped, "failed": 0,
                 "log_sha256": hashlib.sha256(raw_log).hexdigest(),
                 "skip_reason": "See unittest log; local Windows symlink permission"}
    return {"configurations": len(rows), "versions": len(report["files_by_version"]),
            "measured_roundtrips": measured, "warmup_roundtrips": warmups,
            "verified_range_reads": reads, "verified_warmup_range_reads": warm_reads,
            "measurement_python_source_matches_current_release": True,
            "inputs_identical_to_v0_7": True, "historical_encoding_compatibility": historical,
            "actual_requests_match_all_conditions_and_modes": True,
            "frozen_native_library_and_metadata_identity_verified": True,
            "diagnostic_storage_trees_identical": True,
            "all_backend_storage_trees_and_add_ledgers_identical": True,
            "integrity": "Source scanning, raw/stored/object/file SHA and reuse verification retained; corruption tests include existing-object reuse.",
            "native_scope": "Gear submission scan only; all restores/ranges use Python. No native CAS decoder speed result.",
            "cost": "All logical store files and full measured DLL+metadata once. Allocated file data extents only; directories/MFT/journal/common runtime unallocated.",
            "local_python_tests": tests,
            "native_build_source_commit": provenance["source_commit"],
            "cross_platform_ci": "Recorded separately in native-source-verification.json; this raw-record audit does not rerun CI.",
            "cold_os_cache": None, "cross_machine": None, "cross_day": None,
            "rust_cas_decoder_speedup": None, "inference_quality": None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--reference", type=Path, default=Path("results/v0.7.0"))
    parser.add_argument("--native-library", type=Path, required=True)
    parser.add_argument("--test-log", type=Path)
    args = parser.parse_args()
    save(args.root / "validation.json", validate(args.root, args.reference, args.native_library, args.test_log))
