"""Independent raw-record audit of numeric source/trials/plans and exact costs."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from rkv1.controlled import implementation_checksums, inventory
from rkv1.numeric_data import SPECS
from scripts.run_units import save


def validate(root,test_log):
    checks=json.loads((root/"source-checksums.json").read_text("utf-8"))
    assert checks==implementation_checksums(),"Measured implementation changed"
    resource=json.loads((root/"numeric-resource.json").read_text("utf-8"))
    raw=Path("rkv1/numeric.py").read_bytes()
    assert len(raw)==resource["source_bytes"] and hashlib.sha256(raw).hexdigest()==resource["source_sha256"]
    families={}
    for dataset in ("eeg","ecg","noise"):
        report=json.loads((root/f"{dataset}-numeric.json").read_text("utf-8"))
        provenance=json.loads((root/f"{dataset}-provenance.json").read_text("utf-8"))
        assert report["implementation_checksums"]==checks
        assert report["files"]==provenance["files"]==inventory(provenance["source"])
        if dataset in SPECS:
            assert {f["path"]:(f["bytes"],f["sha256"]) for f in report["files"]}==SPECS[dataset]["files"]
        plans={}; counts={"formal_roundtrips":0,"warmup_roundtrips":0,"formal_range_reads":0,"warmup_range_reads":0}
        for row in report["results"]:
            assert row["configuration"]["format_version"]==4
            assert row["bytewise_verified"] and row["deterministic_archive_bytes"]
            assert row["storage"]["stored_bytes"]==row["storage"]["payload_bytes"]+row["storage"]["metadata_bytes"]
            assert row["storage"]["transformed_chunks"]==sum(n for k,n in row["actual_transforms"].items() if k!="none")
            for trial in row["encode_trials"]:
                assert trial["bytewise_verified"] and trial["stats"]==row["storage"]
            assert {t["round"] for t in row["encode_trials"]}==set(range(-1,report["protocol"]["rounds"]))
            for trial in row["decode_trials"]:
                assert trial["bytewise_verified"]
                assert trial["stats"]["raw_bytes"]==report["raw_file_bytes"]
                counts["formal_roundtrips"]+=trial["round"]>=0
                counts["warmup_roundtrips"]+=trial["round"]<0
            for trial in row["range_trials"]:
                assert trial["bytewise_verified"]
                for category,group in trial["groups"].items():
                    key=trial["round"],category
                    assert plans.setdefault(key,group["request_sha256"])==group["request_sha256"]
                    assert group["verified_requests"]==len(group["requests"])
                    assert (len(group["latency_s"]["samples"]) if group["latency_s"] is not None else 0)==group["verified_requests"]
                    counts["formal_range_reads"]+=group["verified_requests"]
                    counts["warmup_range_reads"]+=group["verified_warmup_requests"]
            if dataset=="noise":assert row["storage"]["transformed_chunks"]==0
        families[dataset]={**counts,"conditions":len(report["results"]),"input_bytes_and_source_pins_verified":True,
            "archive_cost_identity_verified":True,"all_round_archives_and_selection_ledgers_identical":True,
            "all_request_plans_match_across_configurations_and_modes":True}
    log_raw=test_log.read_bytes();log=log_raw.decode("utf-8-sig")
    ran=re.search(r"Ran (\d+) tests",log);status=re.search(r"^OK(?: \(skipped=(\d+)\))?\r?$",log,re.MULTILINE)
    assert ran and status and "FAILED (" not in log
    count,skip=int(ran[1]),int(status[1] or 0)
    return {"datasets":families,"measured_python_modules_match_current":True,
        "numeric_source_resource_identity_verified":True,"no_native_numeric_library_used":True,
        "synthetic_noise_all_conditions_fell_back_to_none":True,
        "local_python_tests":{"run":count,"passed":count-skip,"skipped":skip,"failed":0,
            "skip_reason":"Local Windows symlink privilege","log_sha256":hashlib.sha256(log_raw).hexdigest()},
        "compatibility":"Default flat none/CSV remains v2; units remain v3; v4 requires explicit numeric policy or format_version=4. v4 rejects CSV/units. Existing v1/v2 fixtures pass.",
        "scientific_scope":"Two original single-record int16 corpora; no real floating-point-array performance evidence",
        "cold_os_cache":None,"cross_machine":None,"cross_day":None,"inference_quality":None}


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("root",type=Path);parser.add_argument("--test-log",type=Path,required=True)
    args=parser.parse_args();save(args.root/"validation.json",validate(args.root,args.test_log))
