"""Frozen fixed/Gear and v2/v3 multi-version ablation; no model requests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import sqlite3
import subprocess
import sys
import time

from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import files_in
from rkv1.memory import Memory
from rkv1.native import load_native_gear
from scripts.run_memory import inputs,append
from scripts.run_units import save

CASES={"fixed-v2":("fixed","compact-delta-v2","python"),
       "gear-python-v2":("gear-v1","compact-delta-v2","python"),
       "fixed-v3":("fixed","compact-base-v3","python"),
       "gear-python-v3":("gear-v1","compact-base-v3","python"),
       "gear-rust-v3":("gear-v1","compact-base-v3","rust")}
STAGES=("original","append-1","equal-1","insert-1","undo-insert","append-2","equal-2","insert-2","delete-note","delete-record","append-3")
MARKERS=(" RKV17EDITQ9."," RKV17SECONDINSERTQ9.")
PROBES=(("probe-note","RKV17NOTE01Q9"),("probe-insert-1","RKV17EDITQ9"),("probe-insert-2","RKV17SECONDINSERTQ9"))


def jobs(stage,claims,old=False):
    eligible=sorted((c for c in claims if c["evidence"]),key=lambda c:c["id"])
    selected=eligible[:8] if old else eligible if stage==0 else eligible[:32]
    return [(str(c["id"]),c["claim"]) for c in selected]+(list(PROBES) if old or stage else [])


def tree(memory):
    entries={name:{"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()} for path,name in files_in(memory.root)}
    return hashlib.sha256(json.dumps(entries,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def query(args):
    _,claims=inputs();m=Memory(args.memory);selected=jobs(args.stage,claims)
    m.search(selected[0][1],top_k=10);records=[];started=time.perf_counter();cpu=time.process_time()
    for cid,q in selected:
        found=m.search(q,top_k=10);hits=found["hits"]
        # Snapshot IDs identify each storage representation; raw evidence identity
        # is compared independently across fixed and Gear stores.
        evidence=[{"key":h["key"],"title":h["title"],"sentences":h["sentences"],
                   "locator":{k:v for k,v in h["locator"].items() if k!="snapshot_id"}} for h in hits]
        records.append({"claim_id":cid,"question_sha256":hashlib.sha256(q.encode()).hexdigest(),"keys":[h["key"] for h in hits],
              "ranks":[h["rank"] for h in hits],"evidence_sha256":hashlib.sha256(json.dumps(evidence,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
              "wall_s":found["wall_s"],"all_original_records_verified":all(h["source_bytes_verified"] for h in hits)})
    save(args.result,{"queries":records,"wall_s":time.perf_counter()-started,"cpu_s":time.process_time()-cpu,"peak_rss_bytes":peak_rss(),"generation_calls":0})


def mutation(source,lines,n):
    if n in (1,5,10):
        number={1:1,5:2,10:3}[n]
        note=f"RKV17NOTE0{number}Q9 calibration code: JADE-8842.\r\n证据层测试，非真实科学结论。\r\n".encode()
        assert len(note)==88;(source/f"note-{number}.txt").write_bytes(note)
    elif n in (2,6):
        obj=json.loads(lines[-1]);obj["title"]=("X" if n==2 else "Y")+obj["title"][1:]
        changed=json.dumps(obj,ensure_ascii=True).encode()+b"\n";assert len(changed)==len(lines[-1]);lines[-1]=changed
    elif n in (3,4,7):
        obj=json.loads(lines[0]);old_len=len(lines[0])
        if n==4:
            assert obj["abstract"][0].endswith(MARKERS[0]);obj["abstract"][0]=obj["abstract"][0][:-len(MARKERS[0])]
        else:obj["abstract"][0]+=MARKERS[0 if n==3 else 1]
        changed=json.dumps(obj,ensure_ascii=True).encode()+b"\n"
        assert len(changed)-old_len==(-len(MARKERS[0]) if n==4 else len(MARKERS[0 if n==3 else 1]))
        lines[0]=changed
    elif n==8:(source/"note-1.txt").unlink()
    elif n==9:lines.pop(0)
    if n in (2,3,4,6,7,9):(source/"corpus.jsonl").write_bytes(b"".join(lines))


def clean_env():
    return {k:v for k,v in os.environ.items() if not k.startswith("RKV_LLM_")}


def worker(args):
    args.work.mkdir();source=args.work/"source";source.mkdir()
    raw=Path("data/scifact/corpus.jsonl").read_bytes();lines=raw.splitlines(keepends=True);(source/"corpus.jsonl").write_bytes(raw)
    chunker,index,backend=CASES[args.case];m=Memory.create(args.work/"memory",index_profile=index,chunker=chunker)
    stages=[];history=[];_,claims=inputs();first=None
    for n,name in enumerate(STAGES):
        if n:mutation(source,lines,n)
        truth={p:{"bytes":f.stat().st_size,"sha256":hashlib.sha256(f.read_bytes()).hexdigest()} for f,p in files_in(source)}
        started=time.perf_counter();cpu=time.process_time()
        built=m.add(source,label="scifact-corpus-only" if n==0 else f"v017-{n:02d}-{name}",chunker_backend=backend,
                    native_library=args.native_library if backend=="rust" else None)
        build_wall=time.perf_counter()-started;build_cpu=time.process_time()-cpu;sid=built["snapshot_id"]
        if first is None:first=sid
        history.append((sid,truth))
        with m.store.snapshot(sid) as snap:
            assert set(snap.files)==set(truth)
            for p in snap.files:assert snap.read_range(p)==(source/p).read_bytes()
        inventory=tree(m);stats=m.stats();query_file=args.work/(str(n)+"-queries.json");started=time.perf_counter()
        subprocess.run([sys.executable,"-m","scripts.run_memory_updates","--query","--memory",str(m.root),"--stage",str(n),"--result",str(query_file)],env=clean_env(),check=True)
        query_process_wall=time.perf_counter()-started;result=json.loads(query_file.read_text("utf-8"))
        old=[m.search(q,snapshot=first,top_k=10) for _,q in jobs(n,claims,old=True)]
        assert all(not x["hits"] for x in old[-3:])
        assert inventory==tree(m) and stats==m.stats()
        stages.append({"stage":name,"index":n,"build":built,"build_wall_s":build_wall,"build_cpu_s":build_cpu,
            "storage":stats,"tree_sha256":inventory,"source_truth":truth,"full_source_bytewise_verified":True,
            "query":result,"query_process_wall_including_startup_s":query_process_wall,
            "old_snapshot_keys":[[h["key"] for h in r["hits"]] for r in old]})
        print(args.case,args.round,n,name,stats["logical_file_bytes"],built["new_objects"],built.get("new_index_bytes"),flush=True)
    for sid,truth in history:
        with m.store.snapshot(sid) as snap:
            assert set(snap.files)==set(truth)
            for p,expected in truth.items():
                raw=snap.read_range(p);assert len(raw)==expected["bytes"] and hashlib.sha256(raw).hexdigest()==expected["sha256"]
    save(args.result,{"case":args.case,"round":args.round,"stages":stages,"all_11_historical_snapshots_reopened_and_full_source_hash_verified":True,"generation_calls":0})


def main(args):
    inputs();checks=implementation_checksums();args.out.mkdir();args.work.mkdir()
    library=args.native_library.resolve();load_native_gear(str(library))
    metadata=library.with_name("native.json");native={"library":str(library),"bytes":library.stat().st_size,
       "sha256":hashlib.sha256(library.read_bytes()).hexdigest(),"metadata_bytes":metadata.stat().st_size,
       "metadata_sha256":hashlib.sha256(metadata.read_bytes()).hexdigest(),"metadata":json.loads(metadata.read_text("utf-8")),
       "scope":"Existing measured Gear scan only; not a new native codec or query engine"}
    save(args.out/"native-resource.json",native)
    sources={p:{"bytes":Path(p).stat().st_size,"sha256":hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in ("rkv1/memory.py","rkv1/memory_index.py","rkv1/chunking.py")}
    save(args.out/"source-resource.json",{"files":sources,"total_bytes":sum(x["bytes"] for x in sources.values()),"allocation":"Whole three source files once for each condition; common Store/core/Python/SQLite/OS excluded"})
    save(args.out/"source-checksums.json",checks)
    save(args.out/"environment.json",{"python":platform.python_version(),"sqlite":sqlite3.sqlite_version,"platform":platform.platform(),"logical_cpus":os.cpu_count(),
        "work":str(args.work.resolve()),"generation_calls":0,"scope":"One local Windows host, warm cache; new query subprocess per stage; RSS includes interpreter/input loading"})
    trials=[]
    for n in range(3):
        order=list(CASES);random.Random(20261020+n).shuffle(order)
        for case in order:
            work=args.work/(str(n)+"-"+case);result=args.work/(str(n)+"-"+case+".json")
            subprocess.run([sys.executable,"-m","scripts.run_memory_updates","--worker","--work",str(work),"--case",case,"--round",str(n),
                            "--native-library",str(library),"--result",str(result)],env=clean_env(),check=True)
            trial=json.loads(result.read_text("utf-8"));trials.append(trial);append(args.out/"trials.jsonl",trial)
    assert checks==implementation_checksums()
    assert hashlib.sha256(library.read_bytes()).hexdigest()==native["sha256"] and hashlib.sha256(metadata.read_bytes()).hexdigest()==native["metadata_sha256"]
    save(args.out/"trials.json",{"trials":trials,"rounds":3,"generation_calls":0})


if __name__=="__main__":
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,"reconfigure"):stream.reconfigure(encoding="utf-8")
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path);p.add_argument("--work",type=Path);p.add_argument("--native-library",type=Path)
    p.add_argument("--query",action="store_true");p.add_argument("--worker",action="store_true");p.add_argument("--memory",type=Path)
    p.add_argument("--case",choices=CASES);p.add_argument("--round",type=int);p.add_argument("--stage",type=int);p.add_argument("--result",type=Path)
    a=p.parse_args()
    if a.query:query(a)
    elif a.worker:worker(a)
    else:main(a)
