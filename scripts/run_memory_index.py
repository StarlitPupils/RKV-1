"""Frozen local-only memory-index ablation; never calls a model service."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import sqlite3
import subprocess
import sys
import time

from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.memory import Memory
from rkv1.memory_index import PROFILES
from rkv1.memory_model import messages,exposed_hits,validate_answer
from scripts.run_memory import inputs,append
from scripts.run_units import save

STAGES=("original","append","relocate","delete")
NOTE="RKV15BEACONQ9 calibration code: JADE-8842.\r\n证据层测试，非真实科学结论。\r\n".encode()


def queries(stage,claims):
    eligible=sorted((c for c in claims if c["evidence"]),key=lambda c:c["id"])
    selected=eligible if stage in ("original","append") else eligible[:48]
    result=[(str(c["id"]),c["claim"]) for c in selected]
    if stage!="original":result.append(("note-probe","RKV15BEACONQ9"))
    return result


def query_worker(args):
    _,claims=inputs();m=Memory(args.memory);jobs=queries(args.stage,claims);m.search(jobs[0][1],top_k=10)
    records=[];prompts=[];started=time.perf_counter();cpu=time.process_time()
    for cid,q in jobs:
        result=m.search(q,top_k=10,snapshot=args.snapshot)
        compact=[{k:h[k] for k in ("key","title","sentences","locator","source_bytes_verified")} for h in result["hits"]]
        records.append({"claim_id":cid,"question_sha256":hashlib.sha256(q.encode()).hexdigest(),"keys":[h["key"] for h in result["hits"]],
                        "ranks":[h["rank"] for h in result["hits"]],"evidence_sha256":hashlib.sha256(json.dumps(compact,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
                        "wall_s":result["wall_s"],"all_source_bytes_verified":all(h["source_bytes_verified"] for h in result["hits"])})
    if args.stage=="original":
        old=json.loads(Path("results/v0.15.0/model-eval.json").read_text("utf-8"))
        for r in old["records"]:
            record=r["record"]
            if not record["retrieval_enabled"]:continue
            found=m.search(record["question"],snapshot=args.snapshot,top_k=5);visible=exposed_hits(found["hits"])
            payload={"model":record["model"],"messages":messages(record["question"],visible),"temperature":0,"max_tokens":256,**record["request_extra_body"]}
            raw=json.dumps(payload,ensure_ascii=False,separators=(",",":")).encode()
            assert hashlib.sha256(raw).hexdigest()==record["prompt_sha256"]
            assert validate_answer(record["raw_model_content"],visible)==record["answer"]
            prompts.append({"claim_id":r["claim_id"],"prompt_sha256":record["prompt_sha256"]})
    save(args.result,{"queries":records,"offline_v015_request_checks":prompts,"process_wall_s":time.perf_counter()-started,
                      "process_cpu_s":time.process_time()-cpu,"peak_rss_bytes":peak_rss(),"generation_calls":0})


def worker(args):
    root=args.work;root.mkdir(parents=True);source=root/"source";source.mkdir()
    (source/"corpus.jsonl").write_bytes(Path("data/scifact/corpus.jsonl").read_bytes())
    memory=Memory.create(root/"memory",index_profile=args.profile);stages=[];original=None
    original_raw=(source/"corpus.jsonl").read_bytes()
    lines=original_raw.splitlines(keepends=True);obj=json.loads(lines[0]);obj["abstract"][0]+=" RKV16EDITQ9."
    changed=json.dumps(obj,ensure_ascii=True).encode()+b"\n";modified=changed+b"".join(lines[1:])
    for stage in STAGES:
        if stage=="append":(source/"memory-update.txt").write_bytes(NOTE)
        elif stage=="relocate":(source/"corpus.jsonl").write_bytes(modified)
        elif stage=="delete":
            (source/"memory-update.txt").unlink();(source/"corpus.jsonl").write_bytes(b"".join(lines[1:]))
        started=time.perf_counter();cpu=time.process_time()
        built=memory.add(source,label="scifact-corpus-only" if stage=="original" else "v016-"+stage)
        build_wall=time.perf_counter()-started;build_cpu=time.process_time()-cpu;sid=built["snapshot_id"]
        if original is None:original=sid
        with memory.store.snapshot(sid) as snap:
            for name in snap.files:assert snap.read_range(name)==(source/name).read_bytes()
        query_file=root/(stage+"-queries.json")
        started=time.perf_counter()
        subprocess.run([sys.executable,"-m","scripts.run_memory_index","--query","--memory",str(memory.root),"--stage",stage,
                        "--snapshot",sid,"--result",str(query_file)],check=True)
        query_process_wall=time.perf_counter()-started
        query=json.loads(query_file.read_text("utf-8"));before=memory.stats()
        # Old view is independently reopened after every update. No stored file may change.
        old=[memory.search(q,snapshot=original,top_k=10) for _,q in queries("relocate",inputs()[1])]
        assert not old[-1]["hits"]
        assert memory.stats()==before
        stages.append({"stage":stage,"build":built,"build_wall_s":build_wall,"build_cpu_s":build_cpu,
             "storage":before,"query_process_wall_including_startup_s":query_process_wall,"query":query,
             "old_snapshot_keys":[[h["key"] for h in r["hits"]] for r in old],"full_source_bytes_verified":True})
        print(args.profile,args.round,stage,before["logical_file_bytes"],flush=True)
    save(args.result,{"profile":args.profile,"round":args.round,"stages":stages,"generation_calls":0})


def main(args):
    checks=implementation_checksums();inputs();args.out.mkdir(parents=True);args.work.mkdir(parents=True)
    if list(args.out.iterdir()) or list(args.work.iterdir()):raise ValueError("Use fresh output/work directories")
    save(args.out/"source-checksums.json",checks)
    old_sha=subprocess.check_output(["git","rev-parse","v0.15.0^{commit}"],text=True).strip()
    save(args.out/"environment.json",{"python":platform.python_version(),"sqlite":sqlite3.sqlite_version,"platform":platform.platform(),
         "logical_cpus":os.cpu_count(),"work":str(args.work.resolve()),"old_release_commit":old_sha,"generation_calls":0,
         "scope":"One local Windows host, warm OS cache; fresh query subprocess per stage; peak RSS includes interpreter and whole query worker"})
    save(args.out/"index-resource.json",{"path":"rkv1/memory_index.py","bytes":Path("rkv1/memory_index.py").stat().st_size,
         "sha256":hashlib.sha256(Path("rkv1/memory_index.py").read_bytes()).hexdigest(),"allocation":"Whole dedicated source once; common Python/SQLite/core runtime excluded"})
    trials=[]
    for n in range(3):
        order=list(PROFILES);random.Random(20261019+n).shuffle(order)
        for selected in order:
            work=args.work/(str(n)+"-"+selected);result=work.parent/(work.name+".json")
            subprocess.run([sys.executable,"-m","scripts.run_memory_index","--worker","--work",str(work),"--profile",selected,"--round",str(n),"--result",str(result)],check=True)
            trial=json.loads(result.read_text("utf-8"));trials.append(trial);append(args.out/"trials.jsonl",trial)
    if checks!=implementation_checksums():raise ValueError("Source changed during formal experiment")
    save(args.out/"trials.json",{"trials":trials,"rounds":3,"generation_calls":0})


if __name__=="__main__":
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,"reconfigure"):stream.reconfigure(encoding="utf-8")
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path);p.add_argument("--work",type=Path)
    p.add_argument("--worker",action="store_true");p.add_argument("--query",action="store_true");p.add_argument("--memory",type=Path)
    p.add_argument("--profile",choices=PROFILES);p.add_argument("--round",type=int);p.add_argument("--stage",choices=STAGES)
    p.add_argument("--snapshot");p.add_argument("--result",type=Path);a=p.parse_args()
    if a.query:query_worker(a)
    elif a.worker:worker(a)
    else:main(a)
