"""Audit pinned byte truth, dependency identity, all trials and shared request plans."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from rkv1.controlled import implementation_checksums, inventory
from rkv1.numeric_data import SPECS as NUMERIC_SPECS
from rkv1.scientific_benchmark import matrix
from rkv1.scientific_data import SPECS, COMMIT, primary_layout
from rkv1.scientific_resources import resources
from scripts.run_units import save


def validate(root,test_log):
    checks=json.loads((root/"source-checksums.json").read_text("utf-8"))
    assert checks==implementation_checksums(),"Measured implementation changed"
    dependency=json.loads((root/"dependency-provenance.json").read_text("utf-8"))
    assert dependency==resources(),"Measured installed dependency identity changed"
    assert dependency["threads"]==1 and dependency["numpy_imported"] is False
    datasets={}
    for dataset in ("spitzer32","bolocam32","msx64","ecg","noise"):
        report=json.loads((root/f"{dataset}-scientific.json").read_text("utf-8"))
        provenance=json.loads((root/f"{dataset}-provenance.json").read_text("utf-8"))
        assert report["implementation_checksums"]==checks
        assert report["schema_version"]==11 and report["rkv1_version"]=="0.11.0"
        assert report["files"]==provenance["files"]==inventory(provenance["source"])
        assert report["raw_file_bytes"]==sum(f["bytes"] for f in report["files"])
        if dataset in SPECS:
            path,size,sha,bitpix,axes=SPECS[dataset]
            assert report["files"]==[{"path":Path(path).name,"bytes":size,"sha256":sha}]
            assert provenance["source_commit"]==COMMIT
            assert provenance["layout"]==primary_layout((Path(provenance["source"])/Path(path).name).read_bytes())
            assert provenance["layout"]["bitpix"]==bitpix and tuple(provenance["layout"]["fits_axes"])==axes
        elif dataset=="ecg":
            assert {f["path"]:(f["bytes"],f["sha256"]) for f in report["files"]}==NUMERIC_SPECS[dataset]["files"]
        configs=[{k:v for k,v in r["configuration"].items() if k not in ("queries","seed")} for r in report["results"]]
        assert configs==matrix(report["word_bytes"])
        rounds=report["protocol"]["rounds"];assert rounds==5
        assert sorted(map(tuple,report["full_execution_order"]))==[(i,r) for i in range(18) for r in range(-1,rounds)]
        assert sorted(map(tuple,report["range_execution_order"]))==sorted((i,r,m) for i in range(18) for r in range(rounds) for m in ("open_reader","open_and_read"))
        plans={};counts={k:0 for k in ("formal_roundtrips","warmup_roundtrips","formal_range_reads","warmup_range_reads")}
        for row in report["results"]:
            assert row["bytewise_verified"] and row["deterministic_archive_bytes"]
            assert row["storage"]["stored_bytes"]==row["storage"]["payload_bytes"]+row["storage"]["metadata_bytes"]
            assert row["storage"]["transformed_chunks"]==sum(v for k,v in row["actual_transforms"].items() if k!="none")
            for phase in ("encode","decode"):
                trials=row[phase+"_trials"]
                assert [t["round"] for t in trials]==list(range(-1,rounds))
                assert all(t["bytewise_verified"] for t in trials)
                if phase=="encode":assert all(t["stats"]==row["storage"] for t in trials)
                else:
                    assert all(t["stats"]["raw_bytes"]==report["raw_file_bytes"] for t in trials)
                    counts["formal_roundtrips"]+=rounds;counts["warmup_roundtrips"]+=1
            assert {(t["round"],t["mode"]) for t in row["range_trials"]}=={(r,m) for r in range(rounds) for m in ("open_reader","open_and_read")}
            for trial in row["range_trials"]:
                assert trial["bytewise_verified"]
                for category,group in trial["groups"].items():
                    assert plans.setdefault((trial["round"],category),group["request_sha256"])==group["request_sha256"]
                    assert group["verified_requests"]==len(group["requests"])
                    assert (len(group["latency_s"]["samples"]) if group["latency_s"] is not None else 0)==group["verified_requests"]
                    counts["formal_range_reads"]+=group["verified_requests"]
                    counts["warmup_range_reads"]+=group["verified_warmup_requests"]
            if dataset=="noise":
                assert row["storage"]["transformed_chunks"]==0
                assert set(row["actual_codecs"])=={"raw"}
        datasets[dataset]={**counts,"conditions":18,"input_pins_and_layout_verified":True,
            "deterministic_archive_and_complete_cost_verified":True,"all_request_plans_identical_across_conditions_and_modes":True}
    raw=test_log.read_bytes();log=raw.decode("utf-8-sig")
    ran=re.search(r"Ran (\d+) tests",log);status=re.search(r"^OK(?: \(skipped=(\d+)\))?\r?$",log,re.MULTILINE)
    assert ran and status and "FAILED (" not in log
    count,skip=int(ran[1]),int(status[1] or 0)
    return {"datasets":datasets,"measured_implementation_and_entire_installed_dependency_identity_verified":True,
        "blosc_threads":1,"numpy_imported":False,"no_RKV_numeric_Rust_library":True,
        "local_python_tests":{"run":count,"passed":count-skip,"skipped":skip,"failed":0,"log_sha256":hashlib.sha256(raw).hexdigest(),"skip_reason":"Windows symlink privilege"},
        "compatibility":"Defaults remain v2, units v3, numeric v4; v5 explicit or professional codec; older released reader rejects v5. Local wheel compatibility verified separately.",
        "cold_os_cache":None,"cross_machine":None,"cross_day":None,"inference_quality":None,"CAS_numeric_integration":None}


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("root",type=Path);parser.add_argument("--test-log",type=Path,required=True)
    args=parser.parse_args();save(args.root/"validation.json",validate(args.root,args.test_log))
