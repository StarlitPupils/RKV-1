"""Recompute only historical analytical work ledgers; never replace timings."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from rkv1.controlled import implementation_checksums,inventory
from rkv1.core import Archive,pack,verify
from rkv1.read_benchmark import touched_bytes,fingerprint
from scripts.run_units import save


def linear_work(header,request):
    """Independent overlap scan, rather than the reader's prefix/bisect lookup."""
    file=next(f for f in header["files"] if f["path"]==request["path"])
    result={"requested_bytes":request["length"],"chunk_decodes":0,"decoded_raw_bytes":0,"stored_payload_bytes":0}
    cursor=0
    for key in file["chunks"]:
        b=header["blocks"][key];end=cursor+b["raw_size"]
        if request["length"] and cursor<request["offset"]+request["length"] and end>request["offset"]:
            result["chunk_decodes"]+=1;result["decoded_raw_bytes"]+=b["raw_size"];result["stored_payload_bytes"]+=b["stored_size"]
        cursor=end
    return result


def correct(old_root,scratch):
    checks=implementation_checksums();datasets={};total_requests=0;archives=0
    roots={"spitzer32":"data/scientific/spitzer32","m13_64":"data/layout/m13_64","rosat32":"data/layout/rosat32",
           "ecg":"data/numeric/ecg","noise":"data/numeric/noise"}
    with tempfile.TemporaryDirectory(prefix="rkv-work-correction-",dir=Path(scratch).resolve()) as temp:
        path=Path(temp)/"control.rkv"
        for d,source in roots.items():
            original=(old_root/(d+"-layout.json")).read_bytes();report=json.loads(original)
            assert inventory(source)==report["files"]
            records=[]
            for row in report["results"]:
                c=row["configuration"]
                stats=pack(source,path,c["chunk_size"],overwrite=True,compression=c["compression"],deduplicate=c["deduplicate"],
                           transform=c["transform"],format_version=6,layout=c["file_layout"])
                assert stats==row["storage"],"Re-encoded historical archive differs"
                verify(path);archives+=1;changes=[]
                with Archive(path) as reader:
                    for trial in row["range_trials"]:
                        for name,group in trial["groups"].items():
                            assert fingerprint(group["requests"])==group["request_sha256"]
                            total={k:0 for k in group["work"]}
                            for request in group["requests"]:
                                work=touched_bytes(reader.header,request,reader)
                                assert work==linear_work(reader.header,request)
                                for k,v in work.items():total[k]+=v
                                total_requests+=1
                            assert total["requested_bytes"]==group["work"]["requested_bytes"]
                            if total!=group["work"]:
                                changes.append({"round":trial["round"],"mode":trial["mode"],"group":name,
                                    "request_sha256":group["request_sha256"],"original_work":group["work"],"corrected_work":total,
                                    "original_decode_amplification":group["decode_amplification"],
                                    "corrected_decode_amplification":total["decoded_raw_bytes"]/total["requested_bytes"] if total["requested_bytes"] else None})
                if c["file_layout"]=="fixed":assert not changes,"Fixed-layout ledger unexpectedly changed"
                records.append({"configuration":c,"archive_sha256":stats["archive_sha256"],"changed_groups":changes})
            datasets[d]={"original_report_sha256":hashlib.sha256(original).hexdigest(),"records":records}
            print("historical work audited",d,flush=True)
    assert checks==implementation_checksums()
    return {"original_tag":"v0.12.0","datasets":datasets,"implementation_checksums":checks,
            "historical_archives_reencoded_byte_identically":archives,"formal_requests_recomputed":total_requests,
            "prefix_ledger_agrees_with_independent_linear_overlap_scan":True,"fixed_layout_work_unchanged":True,
            "timing_samples_or_requests_replaced":False,"new_read_performance_measurements":False,
            "scope":"Only segmented v6 analytical work/amplification was wrong. Original byte comparisons, archive sizes and timed latency fields remain unchanged. v0.12 acceptance used bytes/latencies, not this work ledger."}


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    p.add_argument("--old-root",type=Path,default=Path("results/v0.12.0"));p.add_argument("--scratch",type=Path,default=Path(".tools/sync-scratch"))
    args=p.parse_args();args.scratch.mkdir(parents=True,exist_ok=True)
    save(args.out,correct(args.old_root,args.scratch))
