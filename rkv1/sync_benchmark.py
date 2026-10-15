"""Same-archive restore-only close/files paired measurements on one volume."""
from pathlib import Path
import random
import shutil
import tempfile

from .benchmark import summary
from .controlled import _child,implementation_checksums,inventory
from .core import pack,assert_tree_equal,_file_digest
from .read_benchmark import timestamp


def measure(cases,scratch,*,rounds=10,seed=20261016):
    if type(rounds) is not int or not 1<=rounds<=100:raise ValueError("Invalid restore rounds")
    scratch=Path(scratch).resolve();scratch.mkdir(parents=True,exist_ok=True)
    checks=implementation_checksums();started=timestamp();records=[]
    with tempfile.TemporaryDirectory(prefix="rkv-sync-",dir=scratch) as temp:
        root=Path(temp);prepared=[]
        for i,case in enumerate(cases):
            source=Path(case["source"]).resolve();files=inventory(source);archive=root/f"{i}.rkv"
            storage=pack(source,archive,**case["pack"])
            prepared.append({"case":case["name"],"source":str(source),"files":files,"pack":case["pack"],
                             "storage":storage,"archive":archive,"trials":[]})
        warmups=[(i,p,-1) for i in range(len(cases)) for p in ("close","files")]
        jobs=[(i,p,r) for i in range(len(cases)) for p in ("close","files") for r in range(rounds)]
        random.Random(seed).shuffle(warmups);random.Random(seed^0x55).shuffle(jobs)
        for order,(i,policy,r) in enumerate(warmups+jobs):
            row=prepared[i];archive=row["archive"];destination=root/"restored"
            assert _file_digest(archive)==row["storage"]["archive_sha256"]
            print(f"restore {order+1}/{len(warmups+jobs)} {row['case']} {policy} round {r}",flush=True)
            try:
                trial=_child("decode",row["source"],archive,destination,{"restore_sync":policy})
            except ValueError as error:
                complete=destination.exists()
                if complete:assert_tree_equal(row["source"],destination)
                row["trials"].append({"policy":policy,"round":r,"execution_index":order,"success":False,
                    "error":str(error),"target_present":complete,"target_bytewise_verified":complete,
                    "archive_sha256":_file_digest(archive)})
                assert _file_digest(archive)==row["storage"]["archive_sha256"]
                if complete:
                    if not destination.resolve().is_relative_to(root.resolve()):raise ValueError("Invalid failed output")
                    shutil.rmtree(destination)
                continue  # Never retry/relabel an entire failed restore as a timing success.
            assert_tree_equal(row["source"],destination)
            assert trial["stats"]["sync_policy"]==policy
            assert trial["stats"]["files_synced"]==(len(row["files"]) if policy=="files" else 0)
            assert _file_digest(archive)==row["storage"]["archive_sha256"]
            trial.update(policy=policy,round=r,execution_index=order,bytewise_verified=True,success=True,
                         archive_sha256=row["storage"]["archive_sha256"])
            row["trials"].append(trial)
            if not destination.resolve().is_relative_to(root.resolve()):raise ValueError("Invalid benchmark output")
            shutil.rmtree(destination)
        for row in prepared:
            assert row["files"]==inventory(row["source"])
            row.pop("archive");row["trials"].sort(key=lambda t:(t["policy"],t["round"]))
            row["summaries"]={p:{metric:summary([t[metric] for t in row["trials"] if t["policy"]==p and t["round"]>=0 and t["success"]])
                                   for metric in ("wall_s","cpu_s","peak_rss_bytes")} for p in ("close","files")}
            records.append(row)
        volume=root.anchor
    assert checks==implementation_checksums()
    return {"schema_version":13,"started_utc":started,"finished_utc":timestamp(),"cases":records,
            "implementation_checksums":checks,"execution_order":[list(x) for x in warmups+jobs],
            "protocol":{"rounds":rounds,"warmups_per_case_policy":1,"seed":seed,"scratch_volume":volume,
                "same_archive":"One frozen archive per case, same SHA for both policies and every restore",
                "timing":"Fresh phase process; excludes Python startup and external byte comparison. Includes unpack/verification/file sync/publish (including bounded Windows rename retries)/temp cleanup.",
                "failures":"All failed jobs retained; no whole-restore retries. Timing summaries use successful jobs only; paired statistics require both policies succeed in the round.",
                "ordering":"All case/policy/round jobs shuffled after shuffled warmups; independent staging directory per restore",
                "cache":"Archive hash pre-read outside timing, warm OS cache; no device cache eviction or background-load isolation",
                "persistence":"files: file SHA, flush, fsync, close, all-files-complete then directory rename. close: file SHA then close; same remaining path.",
                "limits":"File sync requests are not a directory/volume/controller power-loss proof. No directory fsync or automatic orphan recovery."},
            "cold_os_cache":None,"cross_machine":None,"power_failure":None,"inference_quality":None}
