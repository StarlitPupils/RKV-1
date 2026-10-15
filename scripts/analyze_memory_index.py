"""Audit the frozen index ablation without model calls or tuning."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from scripts.run_memory import inputs
from scripts.run_memory_index import PROFILES,STAGES,queries
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root,test_log):
    read=lambda n:json.loads((root/n).read_text("utf-8"))
    checks=read("source-checksums.json");assert checks==implementation_checksums()
    trial=read("trials.json");rows=[json.loads(line) for line in (root/"trials.jsonl").read_text("utf-8").splitlines()]
    assert rows==trial["trials"] and trial["rounds"]==3 and len(rows)==9 and trial["generation_calls"]==0
    lookup={(r["round"],r["profile"]):r for r in rows};assert len(lookup)==9
    _,claims=inputs();claim_map={str(c["id"]):c for c in claims};source=read("index-resource.json")
    raw=Path(source["path"]).read_bytes();assert len(raw)==source["bytes"] and hashlib.sha256(raw).hexdigest()==source["sha256"]
    historical=json.loads(Path("results/v0.15.0/retrieval.json").read_text("utf-8"))
    old_keys={str(q["claim_id"]):q["keys"] for q in historical["trials"]}
    old_api=json.loads(Path("results/v0.15.0/model-eval.json").read_text("utf-8"))
    old_prompts={r["claim_id"]:r["record"]["prompt_sha256"] for r in old_api["records"] if r["record"]["retrieval_enabled"]}
    count=old_count=offline=0
    for r in rows:
        assert r["generation_calls"]==0 and [s["stage"] for s in r["stages"]]==list(STAGES)
        baseline=lookup[r["round"],"full-v1"]
        for s,b in zip(r["stages"],baseline["stages"]):
            stage=s["stage"];xs=s["query"]["queries"];ys=b["query"]["queries"]
            assert s["full_source_bytes_verified"] and s["query"]["generation_calls"]==0
            assert [q["claim_id"] for q in xs]==[cid for cid,_ in queries(stage,claims)]
            assert len(xs)==len(ys) and s["build"]["snapshot_id"]==b["build"]["snapshot_id"]
            for x,y,(_,q) in zip(xs,ys,queries(stage,claims)):
                assert x["question_sha256"]==hashlib.sha256(q.encode()).hexdigest()
                assert x["keys"]==y["keys"] and x["evidence_sha256"]==y["evidence_sha256"]
                assert len(x["ranks"])==len(y["ranks"]) and all(abs(a-b)<=1e-10 for a,b in zip(x["ranks"],y["ranks"]))
                assert x["all_source_bytes_verified"]
                if stage=="original":assert x["keys"]==old_keys[x["claim_id"]]
                count+=1
            assert s["old_snapshot_keys"]==b["old_snapshot_keys"] and not s["old_snapshot_keys"][-1]
            old_count+=len(s["old_snapshot_keys"])
            ps=s["query"]["offline_v015_request_checks"]
            if stage=="original":assert {p["claim_id"]:p["prompt_sha256"] for p in ps}==old_prompts
            else:assert not ps
            offline+=len(ps)
    assert count==4275 and old_count==1764 and offline==108
    result={"stages":{},"generation_calls":0,"unique_scientific_claims":188,"formal_queries":count,"old_snapshot_queries":old_count,
            "offline_existing_request_checks":offline,"offline_unique_existing_requests":12,"dedicated_index_source":source,
            "global_BM25_keys_and_source_identity_match":True,"BM25_absolute_tolerance":1e-10,"original_rankings_match_v015":True,
            "cold_cache":None,"cross_machine":None,"new_model_quality":None}
    for stage in STAGES:
        result["stages"][stage]={}
        for selected in PROFILES:
            ss=[next(s for s in lookup[n,selected]["stages"] if s["stage"]==stage) for n in range(3)]
            storage=[s["storage"]["logical_file_bytes"] for s in ss];assert len(set(storage))==1
            baselines=[next(s for s in lookup[n,"full-v1"]["stages"] if s["stage"]==stage) for n in range(3)]
            dedicated=source["bytes"] if selected!="full-v1" else 0
            latency=summary([q["wall_s"] for s in ss for q in s["query"]["queries"]])
            # Pair the same question in the same round, then summarize ratios.
            ratios=[bq["wall_s"]/q["wall_s"] for s,b in zip(ss,baselines) for q,bq in zip(s["query"]["queries"],b["query"]["queries"])]
            view={"logical_file_bytes":storage[0],"dedicated_source_bytes_once":dedicated,"counted_bytes":storage[0]+dedicated,
                "net_saving_vs_full_v1":1-(storage[0]+dedicated)/baselines[0]["storage"]["logical_file_bytes"],
                "by_directory_bytes":ss[0]["storage"]["by_directory_bytes"],"head_bytes":ss[0]["storage"]["head_bytes"],
                "latency_s":latency,"paired_query_speedup":summary(ratios),"build_wall_s":summary([s["build_wall_s"] for s in ss]),
                "build_cpu_s":summary([s["build_cpu_s"] for s in ss]),"query_worker_peak_RSS_bytes":summary([s["query"]["peak_rss_bytes"] for s in ss]),
                "query_process_wall_including_startup_s":summary([s["query_process_wall_including_startup_s"] for s in ss]),
                "new_index_bytes":[s["build"].get("new_index_bytes",s["build"]["index_bytes"]) for s in ss],
                "delta_depth":[s["build"].get("delta_depth",0) for s in ss]}
            result["stages"][stage][selected]=view
    gold_recall={}
    original=lookup[0,"full-v1"]["stages"][0]["query"]["queries"]
    for k in (1,5,10):
        scores=[]
        for q in original:
            expected={"doc:"+str(key) for key in claim_map[q["claim_id"]]["evidence"]}
            scores.append(len(expected&set(q["keys"][:k]))/len(expected))
        gold_recall[str(k)]=sum(scores)/188
    result["original_macro_gold_document_recall"]=gold_recall
    log=test_log.read_bytes();text=log.decode("utf-8-sig");ran=re.search(r"Ran (\d+) tests",text);ok=re.search(r"^OK(?: \(skipped=(\d+)\))?\r?$",text,re.M)
    assert ran and ok and "FAILED (" not in text
    validation={"measured_Python_modules":len(checks),"formal_queries_audited":count,"old_snapshot_queries_audited":old_count,
         "all_global_BM25_rankings_and_source_identities_match_full_v1":True,"original_queries_match_v015_records":True,
         "offline_existing_model_input_and_citation_checks":offline,"new_model_generation_calls":0,
         "tests":{"run":int(ran[1]),"passed":int(ran[1])-int(ok[1] or 0),"skipped":int(ok[1] or 0),"failed":0,"log_sha256":hashlib.sha256(log).hexdigest()}}
    text="""# v0.16 记忆索引成本对照

三策略、三轮、本机温缓存。保留原文、全部旧快照/索引/增量和SHA校验；本轮0次模型
生成，不产生新推理质量结论。完整正文索引full-v1为同轮同来源基线；compact-full
隔离去正文副本收益，compact-delta再隔离基础索引复用。原语料8,307,875B。

4275次正式查询、1764次旧快照检查的排序及原文身份全部匹配full-v1，BM25绝对误差
<=1e-10。独立科学主张仍为188条；控制探针和重复轮次不增加独立样本量。初始排名
与v0.15一致；原有12次检索请求的正文SHA及原模型响应引用核对108次，无新API。

"""
    text+=table(["阶段","策略","全部保留文件B","另计专用源B","计源相对full-v1净省","查询中位ms","p95 ms","配对查询加速中位","查询进程峰值MiB"],
         [[stage,p,v["logical_file_bytes"],v["dedicated_source_bytes_once"],f"{100*v['net_saving_vs_full_v1']:.2f}%",f"{v['latency_s']['median']*1000:.2f}",f"{v['latency_s']['p95']*1000:.2f}",f"{v['paired_query_speedup']['median']:.3f}×",f"{v['query_worker_peak_RSS_bytes']['median']/1048576:.2f}"] for stage,ps in result["stages"].items() for p,v in ps.items()])
    text+="\n配对比值逐问题/轮计算后取中位，不是两组中位之比；峰值RSS是整个新查询进程峰值，含解释器/输入加载，不是单条请求或纯索引内存。进程启动另计；构建与完整CAS提交的wall/CPU见JSON。\n\n"
    text+=table(["阶段","策略","构建wall中位ms","新写索引B（三轮）","增量深度（三轮）"],[[stage,p,f"{v['build_wall_s']['median']*1000:.2f}",str(v['new_index_bytes']),str(v['delta_depth'])] for stage,ps in result["stages"].items() for p,v in ps.items()])
    text+="\nappend仅新增88B合成记录；relocate/delete修改的是原始语料的独立工作副本，只验机制，不代表新科学输入或推理收益。大范围定位变化会按冻结25%门槛重建紧凑检查点；原CAS/基础索引仍保留，所以大幅改写依然增长。8层增量检查点另由单元测试覆盖。\n\n"
    a=result["stages"]["original"]["compact-delta-v2"];b=result["stages"]["append"]["compact-delta-v2"]
    text+=f"紧凑增量库初始计源{a['counted_bytes']:,}B，是原文{a['counted_bytes']/8307875:.3f}倍；追加后计源{b['counted_bytes']:,}B。公共Python/SQLite/core、文件系统元数据/日志未全额分配，不能称完整部署净压缩。与v0.15含24个回答的正式库不直接计算配对节省。\n\n"
    text+="新建库使用v2应用清单，旧v1库仍读写原策略；v0.15不能读取新v2清单，归档v1–v6/CAS1未改。专用源只计完整memory_index.py一次；既有共享框架和公共运行时成本未分配。没有自动GC、目录/卷/真实掉电、冷缓存/跨机器、长期对话、多跳或E3神经压缩结论。空间和速度分别判断，不以空间变小宣称全流程支配。\n"
    save(root/"derived-metrics.json",result);save(root/"validation.json",validation)
    with (root/"SUMMARY.md").open("x",encoding="utf-8",newline="\n") as f:f.write(text)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.4),layout="constrained")
    labels=["Full v1","Compact full","Compact delta"];colors=["#64748b","#4a93b0","#238066"]
    for ax,stage in zip(axes,("original","append")):
        values=[result["stages"][stage][p]["counted_bytes"]/1e6 for p in PROFILES]
        bars=ax.bar(labels,values,color=colors);ax.bar_label(bars,fmt="%.2f",padding=3)
        ax.axhline(8307875/1e6,color="#9a4235",linestyle="--",label="Original source bytes")
        ax.set_title("Initial corpus" if stage=="original" else "After 88-byte note; both snapshots retained")
        ax.set_ylabel("Retained files + dedicated source (MB)");ax.set_ylim(0,max(values)*1.16);ax.legend();ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True)
    fig.suptitle("v0.16 memory-index ablation\nSame global BM25 rankings; common runtime excluded; no new model calls")
    target=root/"index-costs.png"
    if target.exists():raise ValueError("Plot exists")
    fig.savefig(target,dpi=160);plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("root",type=Path);p.add_argument("--test-log",type=Path,required=True);p.add_argument("--plot",action="store_true")
    a=p.parse_args();r=analyze(a.root,a.test_log)
    if a.plot:plot(a.root,r)
