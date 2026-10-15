"""Independently audit raw IO records, historical bytes, requests and provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from rkv1.controlled import implementation_checksums
from scripts.run_units import save


def validate(root, library, test_log):
    checks = json.loads((root / "source-checksums.json").read_text("utf-8"))
    assert checks == implementation_checksums(), "Measured Python source changed"
    frozen = subprocess.check_output(["git", "show", "v0.8.0:rkv1/store.py"])
    assert frozen == Path("rkv1/store_v0_8.py").read_bytes()
    native = json.loads((root / "native-provenance.json").read_text("utf-8"))
    assert hashlib.sha256(library.read_bytes()).hexdigest() == native["sha256"]
    assert hashlib.sha256(library.with_name("native.json").read_bytes()).hexdigest() == native["metadata_sha256"]
    kernels = {}
    for path in sorted(Path("rust/src").rglob("*.rs")):
        original = subprocess.check_output(["git", "show", native["source_commit"] + ":" + path.as_posix()])
        assert path.read_bytes() == original, path
        kernels[path.as_posix()] = hashlib.sha256(original).hexdigest()
    old = json.loads(Path("results/v0.8.0/qasper-gear.json").read_text("utf-8"))
    historical = {r["configuration"]["name"]: r for r in old["results"]}
    families = {}
    for dataset in ("qasper", "evidence"):
        report = json.loads((root / f"{dataset}-io.json").read_text("utf-8"))
        assert report["implementation_checksums"] == checks
        assert report["native_provenance"] == native
        assert report["unmeasured"]["inference_quality"] is None
        if dataset == "qasper":
            assert report["files_by_version"] == old["files_by_version"]
        trees, plans = {}, {}
        measured = warmups = reads = warm_reads = 0
        rows = {r["configuration"]["name"]: r for r in report["results"]}
        base = rows["shared-gear-reference"]
        for name, row in rows.items():
            config = row["configuration"]
            key = (config["kind"], config["chunker"], config["chunk_size"], config["compression"])
            for trial in row["sequence_trials"]:
                tree = trial["deterministic_files_sha256"]
                assert trees.setdefault(key, tree) == tree
                if dataset == "qasper":
                    old_name = ("archive-fixed-1024" if config["kind"] == "archive" else
                                "shared-fixed-64" if config["chunker"] == "fixed" else
                                config["kind"] + "-gear-v1-64-rust")
                    assert tree == historical[old_name]["sequence_trials"][0]["deterministic_files_sha256"]
            if key[0] == "shared" and key[1] == "gear-v1":
                left = {t["round"]: t for t in base["sequence_trials"]}
                for trial in row["sequence_trials"]:
                    assert [v["add"]["stats"] for v in trial["versions"]] == [v["add"]["stats"] for v in left[trial["round"]]["versions"]]
            for version, data in enumerate(row["versions"]):
                for trial in data["restore_trials"]:
                    assert trial["bytewise_verified"]
                    measured += trial["round"] >= 0
                    warmups += trial["round"] < 0
                for trial in data["range_trials"]:
                    assert trial["bytewise_verified"]
                    for category, group in trial["groups"].items():
                        key = (version, trial["round"], category)
                        assert plans.setdefault(key, group["request_sha256"]) == group["request_sha256"]
                        assert group["verified_requests"] == len(group["requests"])
                        reads += group["verified_requests"]
                        warm_reads += group["verified_warmup_requests"]
        families[dataset] = {"conditions": len(rows), "measured_roundtrips": measured,
            "warmup_roundtrips": warmups, "verified_range_reads": reads,
            "verified_warmup_range_reads": warm_reads,
            "same_representation_trees_and_ledgers_identical": True,
            "requests_match_across_all_conditions_and_lifecycle_modes": True,
            "all_qasper_trees_match_v0_8": True if dataset == "qasper" else None}
    raw_log = test_log.read_bytes()
    log = raw_log.decode("utf-8-sig")
    ran = re.search(r"Ran (\d+) tests", log)
    status = re.search(r"^OK(?: \(skipped=(\d+)\))?\r?$", log, re.MULTILINE)
    assert ran and status and "FAILED (" not in log
    count, skipped = int(ran[1]), int(status[1] or 0)
    return {"datasets": families, "all_measured_python_modules_match_current": True,
        "frozen_v0_8_store_byte_identical_to_tag": True,
        "frozen_native_binary_and_metadata_verified": True,
        "rust_kernel_sources_match_measured_build_commit": kernels,
        "native_build_source_commit": native["source_commit"],
        "local_python_tests": {"run": count, "passed": count-skipped, "skipped": skipped,
            "failed": 0, "skip_reason": "Local Windows symlink permission",
            "log_sha256": hashlib.sha256(raw_log).hexdigest()},
        "defaults": {"io_backend": "reference", "publisher": "link"},
        "cold_os_cache": None, "cross_machine": None, "cross_day": None,
        "power_loss_durability": None, "inference_quality": None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--native-library", type=Path, required=True)
    parser.add_argument("--test-log", type=Path, required=True)
    args = parser.parse_args()
    save(args.root / "validation.json", validate(args.root, args.native_library, args.test_log))
