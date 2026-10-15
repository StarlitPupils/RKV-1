"""Frozen SciFact lexical retrieval, bounded paired API calls and update mechanics."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import sqlite3
import time

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from rkv1.datasets import SCIFACT
from rkv1.memory import Memory,digest
from rkv1.memory_model import answer,configuration
from scripts.run_units import save

SEED=20261018


def inputs():
    root=Path("data/scifact")
    for name in ("corpus.jsonl","claims_dev.jsonl"):
        if digest((root/name).read_bytes())!=SCIFACT[name]:raise ValueError("Pinned SciFact input differs")
    claims=[json.loads(x) for x in (root/"claims_dev.jsonl").read_bytes().splitlines()]
    return root,claims


def gold(claim):
    labels={r["label"] for rs in claim["evidence"].values() for r in rs}
    if len(labels)>1:raise ValueError("Mixed-label claim excluded by frozen protocol")
    return next(iter(labels)) if labels else "INSUFFICIENT"


def api_plan(claims):
    selected=[]
    for label in ("SUPPORT","CONTRADICT","INSUFFICIENT"):
        selected.extend(sorted((c for c in claims if gold(c)==label),key=lambda c:c["id"])[:4])
    if len(selected)!=12:raise ValueError("Insufficient balanced fixed claims")
    jobs=[(c,enabled) for c in selected for enabled in (False,True)]
    random.Random(SEED).shuffle(jobs)
    return jobs


def append(path,value):
    with path.open("a",encoding="utf-8",newline="\n") as f:
        f.write(json.dumps(value,ensure_ascii=False)+"\n");f.flush();os.fsync(f.fileno())


def score(c,record):
    expected=gold(c);a=record["answer"] if record["accepted"] else None
    verdict=bool(a and a["verdict"]==expected)
    pairs={(x["key"].removeprefix("doc:"),x["sentence"]) for x in a["evidence"]} if a else set()
    rationale=any({(str(doc),i) for i in r["sentences"]}<=pairs for doc,rs in c["evidence"].items() for r in rs)
    return {"gold_verdict":expected,"verdict_correct":verdict,"complete_gold_rationale_cited":rationale,
            "grounded_correct":verdict and (rationale or expected=="INSUFFICIENT")}


def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    p.add_argument("--work",type=Path,default=Path(".tools/memory-v015-demo"));p.add_argument("--api",action="store_true")
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False);args.work.mkdir(parents=True,exist_ok=False)
    checks=implementation_checksums();root,claims=inputs();source=args.work/"source";source.mkdir()
    (source/"corpus.jsonl").write_bytes((root/"corpus.jsonl").read_bytes())
    save(args.out/"dataset-provenance.json",{"source":"SciFact original pinned corpus/dev", "files":{n:SCIFACT[n] for n in ("corpus.jsonl","claims_dev.jsonl")},
         "corpus_records":5183,"dev_claims":300,"index_contains_only":"corpus.jsonl; no claims or gold labels",
         "licenses":{"claims_and_annotations":"CC-BY-4.0","abstracts":"ODC-By-1.0"},"license_source":"https://github.com/allenai/scifact/blob/master/LICENSE.md"})
    save(args.out/"environment.json",{"python":platform.python_version(),"platform":platform.platform(),"sqlite":sqlite3.sqlite_version,"logical_cpus":os.cpu_count(),
         "work":str(args.work.resolve()),"model_compute":"Remote user-selected API if enabled; local CPU for storage/retrieval"})
    m=Memory.create(args.work/"memory");build=m.add(source,label="scifact-corpus-only");sid=build["snapshot_id"]
    snap=m.store.snapshot(sid);assert set(snap.files)=={"corpus.jsonl"}
    assert snap.read_range("corpus.jsonl")== (root/"corpus.jsonl").read_bytes()
    assert build["indexed_records"]==5183
    save(args.out/"build.json",{"build":build,"full_original_bytes_verified":True,"storage_before_queries":m.stats()})
    eligible=sorted((c for c in claims if c["evidence"]),key=lambda c:c["id"]);assert len(eligible)==188
    m.search(eligible[0]["claim"],top_k=10)  # one explicit uncounted warmup
    trials=[]
    for round_index in range(3):
        jobs=list(eligible);random.Random(SEED+round_index).shuffle(jobs)
        for index,c in enumerate(jobs):
            j=m.search(c["claim"],top_k=10);keys=[h["key"] for h in j["hits"]];expected={"doc:"+str(k) for k in c["evidence"]}
            rec={"round":round_index,"claim_id":c["id"],"question_sha256":digest(c["claim"].encode()),"keys":keys,"gold_keys":sorted(expected),
                 "wall_s":j["wall_s"],"locators":[h["locator"] for h in j["hits"]],"source_bytes_verified":all(h["source_bytes_verified"] for h in j["hits"]),
                 "metrics":{str(k):{"gold_document_recall":len(expected&set(keys[:k]))/len(expected),"any_gold_hit":bool(expected&set(keys[:k]))} for k in (1,5,10)}}
            trials.append(rec);append(args.out/"retrieval-journal.jsonl",rec)
            if index%40==0:print("retrieval",round_index,index+1,"/",len(jobs),flush=True)
    first=[r for r in trials if r["round"]==0]
    retrieval={"unique_annotated_claims":188,"formal_queries":len(trials),"rounds":3,"trials":trials,"wall_s":summary([r["wall_s"] for r in trials]),
        "metrics":{str(k):{"macro_gold_document_recall":sum(r["metrics"][str(k)]["gold_document_recall"] for r in first)/len(first),
                           "claims_with_any_gold":sum(r["metrics"][str(k)]["any_gold_hit"] for r in first)} for k in (1,5,10)},
        "scope":"Lexical BM25 over original abstracts; dev annotated-document recall, not semantic retrieval, complete relevance precision, independent samples, or inference quality"}
    save(args.out/"retrieval.json",retrieval)
    plan=api_plan(claims);save(args.out/"api-plan.json",{"seed":SEED,"max_generation_calls":24,"max_output_tokens_per_call":256,
         "jobs":[{"claim_id":c["id"],"retrieval_enabled":enabled,"gold_verdict":gold(c)} for c,enabled in plan],
         "baseline":"Same evidence-only responder with empty evidence; not unconstrained closed-book model or mature RAG comparison"})
    records=[]
    if args.api:
        config=configuration()
        for order,(c,enabled) in enumerate(plan):
            print("model",order+1,"/24 claim",c["id"],"retrieval",enabled,flush=True)
            r=answer(m,c["claim"],top_k=5,snapshot=sid,config=config,use_retrieval=enabled)
            rec={"order":order,"claim_id":c["id"],"record":r,"score":score(c,r)}
            records.append(rec);append(args.out/"api-journal.jsonl",rec)
            # Do not spend the remaining allowance on a broken service or auth.
            if r.get("error_type") in ("HTTPError","URLError","TimeoutError"):break
    model={"enabled":args.api,"planned_generation_calls":24,"completed_generation_calls":len(records),"complete":len(records)==24,"records":records,
           "scope":"12 balanced dev claims, one API sample per condition; annotation correctness and citation byte binding are distinct; no automatic entailment proof"}
    save(args.out/"model-eval.json",model)
    note="RKV15BEACONQ9 calibration code: JADE-8842.\r\n证据层测试，非真实科学结论。\r\n".encode()
    (source/"memory-update.txt").write_bytes(note);updated=m.add(source,label="synthetic-memory-update")
    reopened=Memory(args.work/"memory");new=reopened.search("RKV15BEACONQ9");old=reopened.search("RKV15BEACONQ9",snapshot=sid)
    assert new["hits"][0]["key"]=="file:memory-update.txt" and not old["hits"]
    assert reopened.store.snapshot(updated["snapshot_id"]).read_range("memory-update.txt")==note
    derived=m.remember({"producer":"synthetic-mechanics-test-not-a-model-call","text":"RKV15DERIVEDONLYQ9"})
    assert not reopened.search("RKV15DERIVEDONLYQ9")["hits"]
    save(args.out/"mechanics.json",{"old_snapshot":sid,"updated_snapshot":updated["snapshot_id"],"new_note_bytewise_verified":True,
         "fresh_process_object_reopen_retrieves_update":True,"old_snapshot_excludes_future_note":True,"derived_output_not_primary_or_retrievable":True,
         "synthetic_derived_probe":derived,"update":updated,"scope":"Controlled storage/index update checks, not autonomous long-conversation learning"})
    save(args.out/"resources.json",{"all_retained_after_update":m.stats(),"build":build,"new_documents":5183,
        "model_weights_and_remote_runtime_bytes":None,"vector_index_bytes":0,"embedding_model_bytes":0,"common_local_runtime_allocation_complete":False,
        "note":"Whole SQLite indexes for both retained snapshots count in full. No total deployment net-space-saving claim."})
    if checks!=implementation_checksums():raise ValueError("Memory implementation changed during evaluation")
    save(args.out/"source-checksums.json",checks)


if __name__=="__main__":main()
