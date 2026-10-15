"""Independent ledger/journal audit and frozen engineering gate for v0.14."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from rkv1.controlled import implementation_checksums,inventory
from rkv1.crossdomain_benchmark import matrix
from rkv1.crossdomain_data import SPECS
from rkv1.read_benchmark import fingerprint
from scripts.run_crossdomain import DATASETS,resource
from scripts.run_units import save
from scripts.summarize_numeric import paired
from scripts.summarize_units import p95,table


def label(row):
    c=row["configuration"];return f"{c['compression']}/{c['chunk_size']//1024}KiB/{c['transform']}"


def analyze(root,test_log):
    read=lambda name:json.loads((root/name).read_text("utf-8"))
    checks=read("source-checksums.json");assert checks==implementation_checksums()
    cost=read("numeric-resource.json");assert cost==resource()
    result={"resource":cost,"datasets":{},"primary_new_scientific_gate":[],"totals":{}}
    totals={k:0 for k in ("formal_roundtrips","warmup_roundtrips","formal_range_reads","warmup_range_reads","formal_file_syncs","formal_publish_retries")}
    text="""# v0.14.0 跨领域字节重排与代码/数学对照

本轮复用既有算法：SAC地震样例、DCD分子动力学样例；Python源码、LaTeX数学文档为
非数值对照；已见ECG/固定噪声为连续性/回退对照。不是新语义编码或严格盲测。
完整原字节/路径/头/记录标志/署名保留，不解析后重写。DCD原头声明500帧但实际
保存98完整帧，该差异不修复。各新领域只有一个公开样例，不能代替大样本泛化。

每组8条件：Zlib6/Zstd3×64KiB/1MiB×none/字节重排，同v4容器；ECG字宽2，其余4。
五轮正式、一次完整预热，新进程分阶段测wall/CPU/RSS；恢复全部显式files，含文件
SHA/flush/fsync/close/目录发布及其重试，未测目录/卷或掉电持久性。温OS缓存，
工作区E卷scratch，计时外逐字节比较/删除输出/追加审计日志，不与历史close批次算加速。

归档含全部清单/路径/块/文件SHA/索引/标识/payload；重排另计整个numeric.py一次。
公共Python/core/Zstd/pyc未全额分配，不是完整部署占用；无新DLL/模型/字典。
联合门槛按协议冻结：同codec/块候选计源后不增大，完整恢复/常驻p95/重开p95配对
中位>=1且各至少4/5轮更快；编码独立披露，不称全流程支配。范围门槛使用byte_weighted。
四类范围请求按实际非空类别计，跨块以64KiB网格定位，不一定跨1MiB块。

"""
    for name in DATASETS:
        report=read(name+"-crossdomain.json");prov=read(name+"-provenance.json");rows=report["results"]
        assert report["schema_version"]==14 and report["protocol"]["rounds"]==5
        assert report["implementation_checksums"]==checks and report["files"]==prov["files"]==inventory(prov["source"])
        if name in SPECS:
            assert report["files"]==[{k:SPECS[name][k] for k in ("path","bytes","sha256")}]
        assert [{k:v for k,v in r["configuration"].items() if k not in ("queries","seed")} for r in rows]==matrix(2 if name=="ecg" else 4)
        assert sorted(map(tuple,report["full_execution_order"]))==[(i,r) for i in range(8) for r in range(-1,5)]
        assert sorted(map(tuple,report["range_execution_order"]))==sorted((i,r,m) for i in range(8) for r in range(5) for m in ("open_reader","open_and_read"))
        raw_journal=(root/(name+"-journal.jsonl")).read_bytes()
        journal=[json.loads(line) for line in raw_journal.decode("utf-8").splitlines()]
        assert journal[0]["event"]=="started" and journal[-1]["event"]=="completed"
        assert journal[0]["implementation_checksums"]==checks and journal[0]["files"]==report["files"]
        assert not any(e["event"].endswith("failed") for e in journal)
        workers={(label({"configuration":e["configuration"]}),e["round"],e["phase"]):e for e in journal if e["event"]=="worker_returned"}
        ranges={(label({"configuration":e["configuration"]}),e["round"],e["mode"]):e for e in journal if e["event"]=="range_returned"}
        verified={(label({"configuration":e["configuration"]}),e["round"]) for e in journal if e["event"]=="roundtrip_verified"}
        assert len(workers)==96 and len(ranges)==80 and len(verified)==48 and len(journal)==226
        rec={"raw_bytes":report["raw_file_bytes"],"partition":prov["partition"],"conditions":{},"comparisons":[],"minimum_archives":[],
             "journal_sha256":hashlib.sha256(raw_journal).hexdigest(),"journal_events":len(journal)}
        result["datasets"][name]=rec;plans={};tab=[]
        assert rec["raw_bytes"]==sum(f["bytes"] for f in report["files"])
        text+=f"## {name}\n\n{prov['partition']}；完整原文件 {rec['raw_bytes']:,} B。\n\n"
        for r in rows:
            key=label(r);s=r["storage"];assert s["stored_bytes"]==s["metadata_bytes"]+s["payload_bytes"]
            assert r["bytewise_verified"] and r["deterministic_archive_bytes"]
            for phase in ("encode","decode"):
                ts=r[phase+"_trials"];assert [t["round"] for t in ts]==list(range(-1,5))
                for t in ts:
                    logged=workers[(key,t["round"],phase)]["result"]
                    assert {k:t[k] for k in logged}==logged and t["bytewise_verified"]
                    if phase=="encode":assert t["stats"]==s
                    else:
                        assert t["stats"]["sync_policy"]=="files" and t["stats"]["files_synced"]==len(report["files"])
                        assert t["stats"]["verified_files"]==len(report["files"]) and t["stats"]["raw_bytes"]==rec["raw_bytes"]
                        assert (key,t["round"]) in verified
                        totals["formal_roundtrips" if t["round"]>=0 else "warmup_roundtrips"]+=1
                        if t["round"]>=0:
                            totals["formal_file_syncs"]+=t["stats"]["files_synced"]
                            totals["formal_publish_retries"]+=t["stats"]["publish_attempts"]-1
            for t in r["range_trials"]:
                logged=ranges[(key,t["round"],t["mode"])]["result"];assert {k:t[k] for k in logged}==logged
                assert t["bytewise_verified"]
                for category,g in t["groups"].items():
                    assert fingerprint(g["requests"])==g["request_sha256"]
                    assert plans.setdefault((t["round"],category),g["request_sha256"])==g["request_sha256"]
                    assert g["verified_requests"]==len(g["requests"])
                    assert (len(g["latency_s"]["samples"]) if g["latency_s"] else 0)==g["verified_requests"]
                    totals["formal_range_reads"]+=g["verified_requests"];totals["warmup_range_reads"]+=g["verified_warmup_requests"]
            rec["conditions"][key]={"configuration":r["configuration"],"storage":s,"actual_transforms":r["actual_transforms"],
                 "encode_s":r["encode_s"],"decode_s":r["decode_s"],"resident_p95_s":p95(r,"open_reader"),"reopen_p95_s":p95(r,"open_and_read")}
            tab.append([key,s["stored_bytes"],s["transformed_chunks"],f"{r['encode_s']['median']*1000:.3f}",f"{r['decode_s']['median']*1000:.3f}",f"{p95(r,'open_reader')*1000:.3f}",f"{p95(r,'open_and_read')*1000:.3f}"])
        text+=table(["配置","完整归档 B","重排块","编码 ms","同步恢复 ms","常驻p95 ms","重开p95 ms"],tab)+"\n"
        tab=[]
        for r in rows:
            c=r["configuration"]
            if c["transform"]=="none":continue
            base=next(b for b in rows if b["configuration"]["transform"]=="none" and b["configuration"]["compression"]==c["compression"] and b["configuration"]["chunk_size"]==c["chunk_size"])
            allocated=r["storage"]["stored_bytes"]+cost["bytes"]
            comparisons={m:paired(base,r,m) for m in ("encode","decode","open_reader","open_and_read")}
            a={t["round"]:t for t in base["decode_trials"] if t["round"]>=0}
            b={t["round"]:t for t in r["decode_trials"] if t["round"]>=0}
            first=[i for i in sorted(a) if a[i]["stats"]["publish_attempts"]==b[i]["stats"]["publish_attempts"]==1]
            ratios=[a[i]["wall_s"]/b[i]["wall_s"] for i in first]
            from rkv1.benchmark import summary
            secondary={"rounds":first,"decode_speedup":summary(ratios),"candidate_faster_rounds":sum(v>1 for v in ratios),
                       "scope":"Post-hoc diagnostic subset only; all original samples retained in primary gate"}
            passed=allocated<=base["storage"]["stored_bytes"] and all(comparisons[m]["speedup_median"]>=1 and comparisons[m]["candidate_faster_rounds"]>=4 for m in ("decode","open_reader","open_and_read"))
            x={"candidate":label(r),"ordinary":label(base),"net_saving_pct":100*(1-allocated/base["storage"]["stored_bytes"]),"comparisons":comparisons,"gate_pass":passed,
               "secondary_decode_both_first_publish_attempt":secondary,
               "ordinary_formal_decode_retry_rounds":[i for i in a if a[i]["stats"]["publish_attempts"]>1],
               "candidate_formal_decode_retry_rounds":[i for i in b if b[i]["stats"]["publish_attempts"]>1]}
            rec["comparisons"].append(x)
            if name in ("seismic","molecular"):result["primary_new_scientific_gate"].append({"dataset":name,**x})
            def speed(m):
                v=comparisons[m];return f"{v['speedup_median']:.3f}× ({v['candidate_faster_rounds']}/5)"
            tab.append([label(r),f"{x['net_saving_pct']:.3f}%",speed("encode"),speed("decode"),speed("open_reader"),speed("open_and_read"),passed])
        text+="同codec/块配对，大于1更快；括号为更快轮数，非置信区间。\n\n"+table(["候选","计源净省","编码","同步恢复","常驻p95","重开p95","联合通过"],tab)+"\n"
        text+="发布重试敏感性：以下只看两策略均首次发布成功的配对作事后诊断，不替代主验收或增加正式轮数。\n\n"
        text+=table(["候选","普通重试轮","候选重试轮","诊断配对轮","诊断恢复加速"],
            [[x["candidate"],x["ordinary_formal_decode_retry_rounds"],x["candidate_formal_decode_retry_rounds"],
              x["secondary_decode_both_first_publish_attempt"]["rounds"],
              f"{x['secondary_decode_both_first_publish_attempt']['decode_speedup']['median']:.3f}×" if x["secondary_decode_both_first_publish_attempt"]["rounds"] else "无配对"] for x in rec["comparisons"]])+"\n"
        old=min((r for r in rows if r["configuration"]["transform"]=="none"),key=lambda r:r["storage"]["stored_bytes"])
        new=min((r for r in rows if r["configuration"]["transform"]!="none"),key=lambda r:r["storage"]["stored_bytes"])
        rec["minimum_archives"]={"ordinary":label(old),"ordinary_bytes":old["storage"]["stored_bytes"],"shuffle":label(new),"shuffle_bytes":new["storage"]["stored_bytes"],
          "allocated_once_bytes":cost["bytes"],"net_saving_pct":100*(1-(new["storage"]["stored_bytes"]+cost["bytes"])/old["storage"]["stored_bytes"]),
          "ordinary_decode_ms":old["decode_s"]["median"]*1000,"shuffle_decode_ms":new["decode_s"]["median"]*1000}
        x=rec["minimum_archives"];text+=f"事后各自最小归档：普通 {x['ordinary_bytes']:,} B，重排 {x['shuffle_bytes']:,} B，加专用源 {cost['bytes']:,} B后净省 {x['net_saving_pct']:.3f}%。不是预先固定部署策略或速度最优。\n\n"
    primary=result["primary_new_scientific_gate"];assert len(primary)==8
    xs=[result["datasets"][d]["minimum_archives"] for d in ("seismic","molecular")]
    old=sum(x["ordinary_bytes"] for x in xs);new=sum(x["shuffle_bytes"] for x in xs)
    result["new_scientific_minimum_archives_shared_source"]={"ordinary_bytes":old,"shuffle_bytes":new,"source_bytes_once":cost["bytes"],"net_saving_pct":100*(1-(new+cost["bytes"])/old)}
    result["totals"]=totals
    text+=f"## 新领域合计与验收\n\n两个新科学样例主验收 {sum(x['gate_pass'] for x in primary)}/8 通过。各自事后最小归档加总：普通 {old:,} B，重排 {new:,} B，共用源 {cost['bytes']:,} B一次，净省 {100*(1-(new+cost['bytes'])/old):.3f}%。体积合计受较大DCD主导，不包括文本、已见ECG或噪声。\n\n"
    text+=f"正式完整恢复 {totals['formal_roundtrips']} 次、范围读取 {totals['formal_range_reads']:,} 次；另恢复预热 {totals['warmup_roundtrips']} 次、查询预热 {totals['warmup_range_reads']:,} 次，全部逐字节一致。正式文件fsync请求 {totals['formal_file_syncs']} 次，正式发布重试 {totals['formal_publish_retries']} 次，等待保留在计时内。\n\n"
    text+="数据/规则/算法在正式结果前冻结，非自动路由或代码/数学语义压缩。源、资源、归档确定性和追加日志均核对；单机温缓存五轮只作描述统计。目录持久性、真实掉电、冷缓存、跨机器、数值Rust、CAS组合及推理质量未测；默认编码不因少量样例自动切换。\n"
    raw=test_log.read_bytes();log=raw.decode("utf-8-sig");ran=re.search(r"Ran (\d+) tests",log);ok=re.search(r"^OK(?: \(skipped=(\d+)\))?\r?$",log,re.M)
    assert ran and ok and "FAILED (" not in log
    count=int(ran[1]);skip=int(ok[1] or 0)
    validation={"frozen_source_and_resources_verified":True,"original_files_sha_verified":True,"matched_requests_verified":True,
       "all_roundtrips_and_ranges_bytewise_verified":True,"append_only_journals_match_final_records":True,
       "formal_sync_policy_files_every_trial":True,"primary_gate_passes":sum(x["gate_pass"] for x in primary),"primary_gate_total":8,
       "totals":totals,"tests":{"run":count,"passed":count-skip,"skipped":skip,"failed":0,"log_sha256":hashlib.sha256(raw).hexdigest()},
       "cold_os_cache":None,"cross_machine_performance":None,"inference_quality":None,"power_failure":None}
    save(root/"derived-metrics.json",result);save(root/"validation.json",validation)
    with (root/"SUMMARY.md").open("x",encoding="utf-8",newline="\n") as f:f.write(text)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names=list(DATASETS);fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout="constrained")
    for ax,selected in zip(axes,(names[:2],names[2:])):
        for off,key,color in ((-.18,"ordinary_bytes","#64748b"),(.18,"shuffle_bytes","#188567")):
            values=[(result["datasets"][d]["minimum_archives"][key]+(result["resource"]["bytes"] if key=="shuffle_bytes" else 0))/result["datasets"][d]["minimum_archives"]["ordinary_bytes"]*100 for d in selected]
            bars=ax.bar([i+off for i in range(len(selected))],values,width=.34,label="ordinary" if key=="ordinary_bytes" else "shuffle + dedicated source",color=color)
            ax.bar_label(bars,fmt="%.1f",padding=3,fontsize=9)
        ax.set_xticks(range(len(selected)),selected);ax.set_ylabel("% of minimum ordinary archive (lower is smaller)")
        ax.set_ylim(0,ax.get_ylim()[1]*1.12);ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True)
    axes[0].set_title("Two new scientific examples");axes[1].set_title("Text, prior ECG and synthetic controls")
    axes[0].legend(loc="lower left",fontsize=8)
    fig.suptitle("v0.14 existing byte shuffle: each method's smallest archive\nWhole numeric.py charged once per dataset; common runtime incomplete")
    target=root/"crossdomain-costs.png"
    if target.exists():raise ValueError("Plot exists")
    fig.savefig(target,dpi=160);plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("root",type=Path);p.add_argument("--test-log",type=Path,required=True);p.add_argument("--plot",action="store_true")
    args=p.parse_args();result=analyze(args.root,args.test_log)
    if args.plot:plot(args.root,result)
