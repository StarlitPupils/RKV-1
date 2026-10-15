"""Audit the multi-version update experiment without calls or tuning."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from scripts.run_memory import inputs
from scripts.run_memory_updates import CASES,STAGES,jobs
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root,test_log):
    read=lambda name:json.loads((root/name).read_text("utf-8"))
    checks=read("source-checksums.json");assert checks==implementation_checksums()
    trial=read("trials.json");rows=[json.loads(s) for s in (root/"trials.jsonl").read_text("utf-8").splitlines()]
    assert rows==trial["trials"] and len(rows)==15 and trial["rounds"]==3 and trial["generation_calls"]==0
    lookup={(r["round"],r["case"]):r for r in rows};assert len(lookup)==15
    source=read("source-resource.json");native=read("native-resource.json")
    assert sum(v["bytes"] for v in source["files"].values())==source["total_bytes"]
    for name,v in source["files"].items():
        raw=Path(name).read_bytes();assert len(raw)==v["bytes"] and hashlib.sha256(raw).hexdigest()==v["sha256"]
    raw=Path(native["library"]).read_bytes();meta=Path(native["library"]).with_name("native.json").read_bytes()
    assert len(raw)==native["bytes"] and hashlib.sha256(raw).hexdigest()==native["sha256"]
    assert len(meta)==native["metadata_bytes"] and hashlib.sha256(meta).hexdigest()==native["metadata_sha256"]
    old=json.loads(Path("results/v0.16.0/trials.json").read_text("utf-8"))
    original=next(r for r in old["trials"] if r["profile"]=="full-v1")["stages"][0]["query"]["queries"]
    old_keys={q["claim_id"]:q["keys"] for q in original}
    _,claims=inputs();claim_map={str(c["id"]):c for c in claims}
    count=old_count=histories=0
    for r in rows:
        assert r["generation_calls"]==0 and r["all_11_historical_snapshots_reopened_and_full_source_hash_verified"]
        assert [s["stage"] for s in r["stages"]]==list(STAGES)
        baseline=lookup[r["round"],"fixed-v2"]
        for n,(s,b) in enumerate(zip(r["stages"],baseline["stages"])):
            assert s["source_truth"]==b["source_truth"] and s["full_source_bytewise_verified"]
            assert s["query"]["generation_calls"]==0 and s["old_snapshot_keys"]==b["old_snapshot_keys"]
            xs=s["query"]["queries"];ys=b["query"]["queries"];expected=jobs(n,claims)
            assert len(xs)==len(ys)==len(expected)
            for x,y,(cid,q) in zip(xs,ys,expected):
                assert x["claim_id"]==cid and x["question_sha256"]==hashlib.sha256(q.encode()).hexdigest()
                assert x["keys"]==y["keys"] and x["evidence_sha256"]==y["evidence_sha256"] and x["all_original_records_verified"]
                assert len(x["ranks"])==len(y["ranks"]) and all(abs(a-b)<=1e-10 for a,b in zip(x["ranks"],y["ranks"]))
                if n==0:assert x["keys"]==old_keys[cid]
                count+=1
            assert len(s["old_snapshot_keys"])==11 and all(not k for k in s["old_snapshot_keys"][-3:])
            old_count+=11;histories+=1
            if r["case"]=="gear-rust-v3":
                py=lookup[r["round"],"gear-python-v3"]["stages"][n]
                assert s["tree_sha256"]==py["tree_sha256"] and s["storage"]==py["storage"]
            peer="gear-python-v3" if CASES[r["case"]][0]=="gear-v1" else "fixed-v3"
            assert s["build"]["snapshot_id"]==lookup[r["round"],peer]["stages"][n]["build"]["snapshot_id"]
    assert count==8070 and old_count==1815 and histories==165
    result={"stages":{},"totals":{},"generation_calls":0,"formal_queries":count,"old_snapshot_queries":old_count,
            "historical_snapshots_fully_reopened":histories,"unique_scientific_claims":188,
            "source_resource":source,"native_resource":native,"all_rankings_and_original_record_identities_match_fixed_v2":True,
            "all_Gear_Python_Rust_storage_trees_byte_identical":True,"BM25_absolute_tolerance":1e-10,
            "cold_cache":None,"cross_machine":None,"new_model_quality":None}
    for n,stage in enumerate(STAGES):
        result["stages"][stage]={}
        for case in CASES:
            ss=[lookup[i,case]["stages"][n] for i in range(3)];bs=[lookup[i,"fixed-v2"]["stages"][n] for i in range(3)]
            files=[s["storage"]["logical_file_bytes"] for s in ss];assert len(set(files))==1
            native_bytes=native["bytes"]+native["metadata_bytes"] if CASES[case][2]=="rust" else 0
            counted=files[0]+source["total_bytes"]+native_bytes
            pairs=[bq["wall_s"]/q["wall_s"] for s,b in zip(ss,bs) for q,bq in zip(s["query"]["queries"],b["query"]["queries"])]
            view={"logical_file_bytes":files[0],"source_bytes_once":source["total_bytes"],"native_bytes_once":native_bytes,"counted_bytes":counted,
                  "net_saving_vs_fixed_v2":1-counted/(bs[0]["storage"]["logical_file_bytes"]+source["total_bytes"]),
                  "by_directory_bytes":ss[0]["storage"]["by_directory_bytes"],"head_bytes":ss[0]["storage"]["head_bytes"],
                  "source_raw_bytes":ss[0]["build"]["raw_bytes"],"new_objects":[s["build"]["new_objects"] for s in ss],
                  "new_object_bytes":[s["build"]["new_object_bytes"] for s in ss],"reused_references":[s["build"]["reused_references"] for s in ss],
                  "new_index_bytes":[s["build"]["new_index_bytes"] for s in ss],"delta_depth":[s["build"]["delta_depth"] for s in ss],
                  "relocation_ranges":[s["build"].get("relocation_ranges",0) for s in ss],"overlay_upserts":[s["build"].get("overlay_upserts",0) for s in ss],
                  "latency_s":summary([q["wall_s"] for s in ss for q in s["query"]["queries"]]),"paired_query_speedup_vs_fixed_v2":summary(pairs),
                  "build_wall_s":summary([s["build_wall_s"] for s in ss]),"build_cpu_s":summary([s["build_cpu_s"] for s in ss]),
                  "paired_build_speedup_vs_fixed_v2":summary([b["build_wall_s"]/s["build_wall_s"] for s,b in zip(ss,bs)]),
                  "query_process_peak_RSS_bytes":summary([s["query"]["peak_rss_bytes"] for s in ss]),
                  "query_process_wall_including_startup_s":summary([s["query_process_wall_including_startup_s"] for s in ss])}
            result["stages"][stage][case]=view
    for case in CASES:
        totals=[sum(s["build_wall_s"] for s in lookup[n,case]["stages"]) for n in range(3)]
        checkpoints=[sum(s["build"]["new_index_bytes"]>1<<20 for s in lookup[n,case]["stages"]) for n in range(3)]
        result["totals"][case]={"all_11_commits_wall_s":summary(totals),"full_base_writes_including_initial":checkpoints,
                               "final_counted_bytes":result["stages"][STAGES[-1]][case]["counted_bytes"]}
    scores={}
    for k in (1,5,10):
        values=[]
        for q in lookup[0,"fixed-v2"]["stages"][0]["query"]["queries"]:
            gold={"doc:"+str(x) for x in claim_map[q["claim_id"]]["evidence"]};values.append(len(gold&set(q["keys"][:k]))/len(gold))
        scores[str(k)]=sum(values)/188
    result["original_macro_gold_document_recall"]=scores
    log=test_log.read_bytes();text=log.decode("utf-8-sig");ran=re.search(r"Ran (\d+) tests",text);ok=re.search(r"^OK(?: \(skipped=(\d+)\))?\r?$",text,re.M)
    assert ran and ok and "FAILED (" not in text
    validation={"measured_Python_modules":len(checks),"formal_queries_audited":count,"old_snapshot_queries_audited":old_count,
       "historical_snapshots_fully_reopened":histories,"all_cases_rankings_and_original_evidence_identity_match":True,
       "all_Gear_Python_Rust_persistent_trees_identical":True,"original_rankings_match_v016":True,"generation_calls":0,
       "tests":{"run":int(ran[1]),"passed":int(ran[1])-int(ok[1] or 0),"skipped":int(ok[1] or 0),"failed":0,"log_sha256":hashlib.sha256(log).hexdigest()}}
    text="""# v0.17 多版本更新放大对照

5条件×3轮，各11个连续快照：初始、追加、等长改写、短插入/撤销、再追加/改写、不同
长度插入、删除note、删除首记录、追加note。全部原文/历史/索引保留，无GC。
8070正式查询、1815旧快照查询的排序和来源身份全部匹配同轮fixed-v2，BM25误差
<=1e-10；165个历史快照最终全部重开核对整文件SHA/大小。188个独立科学主张，
控制探针/重复轮次不算新样本。初始排名匹配v0.16；本轮0次模型生成，无新推理结论。

所有条件计完整memory.py/memory_index.py/chunking.py一次，Rust再计整个实测库与
元数据一次；公共Python/SQLite/Store/core/OS和文件系统元数据未完整分配。固定与
Gear的CAS快照ID可以不同，原始来源/位置/SHA必须一致；Gear Python/Rust整个持久
树逐字节相同。引用基于各自实际快照校验，不以跨表示snapshot_id相等为门槛。

## 全历史成本与提交

"""
    text+=table(["条件","最终保留文件B","统一源码B","原生B","最终计费B","对fixed-v2净省","11次提交wall中位s","完整基础索引写入（三轮）"],
       [[c,result["stages"][STAGES[-1]][c]["logical_file_bytes"],source["total_bytes"],result["stages"][STAGES[-1]][c]["native_bytes_once"],v["final_counted_bytes"],
         f"{100*result['stages'][STAGES[-1]][c]['net_saving_vs_fixed_v2']:.2f}%",f"{v['all_11_commits_wall_s']['median']:.3f}",str(v["full_base_writes_including_initial"])] for c,v in result["totals"].items()])
    text+="\n## 逐阶段成本/新写放大\n\n"
    text+=table(["阶段","条件","全部保留文件B","CAS新对象（三轮）","新写对象B（三轮）","新写索引B（三轮）","增量层数"],
       [[stage,c,v["logical_file_bytes"],str(v["new_objects"]),str(v["new_object_bytes"]),str(v["new_index_bytes"]),str(v["delta_depth"])] for stage,ps in result["stages"].items() for c,v in ps.items()])
    text+="\n## 查询与提交成本\n\n"
    text+=table(["阶段","条件","查询中位ms","p95 ms","配对查询加速","提交中位ms","配对提交加速","查询进程峰值MiB"],
       [[stage,c,f"{v['latency_s']['median']*1000:.2f}",f"{v['latency_s']['p95']*1000:.2f}",f"{v['paired_query_speedup_vs_fixed_v2']['median']:.3f}×",f"{v['build_wall_s']['median']*1000:.2f}",f"{v['paired_build_speedup_vs_fixed_v2']['median']:.3f}×",f"{v['query_process_peak_RSS_bytes']['median']/1048576:.2f}"] for stage,ps in result["stages"].items() for c,v in ps.items()])
    text+="\n比值先按同问题/同轮配对再取中位，不是两组中位之比；RSS含完整新查询进程及输入加载。提交仍全量扫描/哈希/校验，查询仍全SHA校验，启动时间另列。没有新缓存、跳过校验或把历史删除排除在账本外。\n\n"
    text+="v3以单份基础相对overlay和偏移区间处理位置变化，避免将位置变化计作全部记录改写；累计非位置变更超过25%或区间超过256仍建检查点。v2维持8层/25%旧策略。细粒度边界、长期真实更新和热查询缓存策略仍待测，不把本组合成变化泛化到任意更新。\n\n"
    text+="新v3应用清单需v0.17，v1/v2库保持旧策略；归档v1–v6/CAS1不变。Gear为可选，默认固定分块不切换。Rust数据只适用于记录的实测二进制，不代指CI新库或完整解码器。无自动迁移/GC、目录/卷/掉电验证、冷缓存/跨机器、E3、长期对话、多跳或形式化证明。不同版本的语料/阶段/资源口径不直接相加。\n"
    save(root/"derived-metrics.json",result);save(root/"validation.json",validation)
    with (root/"SUMMARY.md").open("x",encoding="utf-8",newline="\n") as f:f.write(text)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels=list(CASES);colors=["#64748b","#c38d3f","#238066","#4a93b0","#8a62a4"]
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout="constrained")
    for c,color in zip(labels,colors):
        axes[0].plot(range(11),[result["stages"][s][c]["counted_bytes"]/1e6 for s in STAGES],marker="o",markersize=3,color=color,label=c)
    axes[0].set_xlabel("Snapshot (all versions retained)");axes[0].set_ylabel("Files + allocated source/native (MB)");axes[0].set_title("Retained storage growth");axes[0].legend(fontsize=8)
    values=[result["totals"][c]["all_11_commits_wall_s"]["median"] for c in labels]
    bars=axes[1].bar(range(5),values,color=colors);axes[1].bar_label(bars,fmt="%.2f",padding=3)
    axes[1].set_xticks(range(5),["fixed\nv2","Gear Py\nv2","fixed\nv3","Gear Py\nv3","Gear Rust\nv3"])
    axes[1].set_ylabel("Median total commit wall time (s)");axes[1].set_title("11 commits, including full source scans");axes[1].set_ylim(0,max(values)*1.15)
    for ax in axes:ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True)
    fig.suptitle("v0.17 update amplification ablation\nSame global BM25 and exact sources; warm cache, one host; common runtime excluded")
    path=root/"update-costs.png"
    if path.exists():raise ValueError("Plot exists")
    fig.savefig(path,dpi=160);plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("root",type=Path);p.add_argument("--test-log",type=Path,required=True);p.add_argument("--plot",action="store_true")
    a=p.parse_args();r=analyze(a.root,a.test_log)
    if a.plot:plot(a.root,r)
