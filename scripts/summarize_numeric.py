"""Numeric prototype: complete archive costs, matched timings and negative controls."""
import argparse
import json
from pathlib import Path
import statistics

from scripts.run_units import save
from scripts.summarize_units import p95, table


def label(row):
    c = row["configuration"]
    return f"{c['compression']}/{c['chunk_size']//1024}KiB/{c['transform']}"


def paired(base, candidate, metric):
    if metric in ("encode", "decode"):
        def values(row):
            return {t["round"]: t["wall_s"] for t in row[metric+"_trials"] if t["round"] >= 0}
    else:
        def values(row):
            return {t["round"]: t["groups"]["byte_weighted"]["latency_s"]["p95"]
                    for t in row["range_trials"] if t["mode"] == metric}
    a,b=values(base),values(candidate)
    assert set(a)==set(b)
    ratios=[a[i]/b[i] for i in sorted(a)]
    return {"metric":metric,"speedup_samples":ratios,"speedup_median":statistics.median(ratios),
            "min":min(ratios),"max":max(ratios),"candidate_faster_rounds":sum(v>1 for v in ratios),"rounds":len(ratios)}


def generate(root):
    resource=json.loads((root/"numeric-resource.json").read_text("utf-8"))
    source_cost=resource["source_bytes"]
    result={"numeric_resource":resource,"datasets":{}}
    totals={"formal_roundtrips":0,"warmup_roundtrips":0,"formal_range_reads":0,"warmup_range_reads":0}
    text="""# v0.10.0 精确数值字节原型

EEG/ECG各一个原始记录，另有随机字节负对照。真实信号为int16，本轮不测真实浮点
科学数组；4/8字节宽度、NaN/Inf/signed-zero等仅作位模式正确性测试。
所有条件同v4平块容器：Zlib6/Zstd3 ×64KiB/1MiB ×none/byte-shuffle2/xor-shuffle2。
全部原始文件/头/注释保留，无数值转换。每条件完整预热后五轮正式，条件/轮次打乱；
范围读五轮、常驻/重开分别测，使用相同原始请求。均为本机温OS缓存。

完整归档包括prefix、manifest、路径、文件/块SHA、变换标识和payload；不以payload
大小冒充净成本。无专用DLL/权重/字典；另列整个numeric.py源文件全额计一次的
保守成本情景，不等于完整编译或部署成本。普通Python/core/codec未全额分配。

"""
    for dataset in ("eeg","ecg","noise"):
        report=json.loads((root/f"{dataset}-numeric.json").read_text("utf-8"))
        rows=report["results"]
        counts={"configurations":len(rows),
            "formal_roundtrips":sum(t["round"]>=0 for r in rows for t in r["decode_trials"]),
            "warmup_roundtrips":sum(t["round"]<0 for r in rows for t in r["decode_trials"]),
            "formal_range_reads":sum(g["verified_requests"] for r in rows for t in r["range_trials"] for g in t["groups"].values()),
            "warmup_range_reads":sum(g["verified_warmup_requests"] for r in rows for t in r["range_trials"] for g in t["groups"].values())}
        for key in totals:totals[key]+=counts[key]
        record={"raw_bytes":report["raw_file_bytes"],"counts":counts,"conditions":{},"matched_comparisons":[],"minimum_archive_comparisons":[]}
        result["datasets"][dataset]=record
        text+=f"## {dataset}\n\n原始{report['raw_file_bytes']:,}bytes；{counts['configurations']}条件、{report['protocol']['rounds']}轮。\n\n"
        tab=[]
        for row in rows:
            name=label(row)
            record["conditions"][name]={"configuration":row["configuration"],"storage":row["storage"],
                "actual_transforms":row["actual_transforms"],"encode_s":row["encode_s"],"decode_s":row["decode_s"],
                "encode_cpu_s":row["encode_cpu_s"],"decode_cpu_s":row["decode_cpu_s"],
                "encode_peak_rss_bytes":row["encode_peak_rss_bytes"],"decode_peak_rss_bytes":row["decode_peak_rss_bytes"],
                "resident_p95_s":p95(row,"open_reader"),"reopen_p95_s":p95(row,"open_and_read")}
            tab.append([name,row["storage"]["stored_bytes"],row["storage"]["transformed_chunks"],
                f"{row['encode_s']['median']*1000:.3f}",f"{row['decode_s']['median']*1000:.3f}",
                f"{p95(row,'open_reader')*1000:.3f}",f"{p95(row,'open_and_read')*1000:.3f}"])
        text+=table(["codec/块/策略","完整bytes","变换块数","编码ms","恢复ms","常驻p95 ms","重开p95 ms"],tab)
        text+="\n### 同codec/块大小对照\n\n倍率为逐轮none/candidate再取中位；大于1更快，括号为更快轮数。\n\n"
        tab=[]
        for candidate in rows:
            c=candidate["configuration"]
            if c["transform"]=="none":continue
            base=next(r for r in rows if r["configuration"]["transform"]=="none"
                and r["configuration"]["chunk_size"]==c["chunk_size"] and r["configuration"]["compression"]==c["compression"])
            old,new=base["storage"]["stored_bytes"],candidate["storage"]["stored_bytes"]
            comparisons={metric:paired(base,candidate,metric) for metric in ("encode","decode","open_reader","open_and_read")}
            record["matched_comparisons"].append({"baseline":label(base),"candidate":label(candidate),
                "archive_saving_pct":100*(1-new/old),"net_saved_bytes_with_source_once":old-new-source_cost,
                "paired":comparisons})
            def ratio(metric):
                p=comparisons[metric]
                return f"{p['speedup_median']:.3f}× ({p['candidate_faster_rounds']}/{p['rounds']})"
            tab.append([label(candidate),f"{100*(1-new/old):.3f}%",old-new-source_cost,
                        ratio("encode"),ratio("decode"),ratio("open_reader"),ratio("open_and_read")])
        text+=table(["候选","归档节省","加源模块净省bytes","编码配对","恢复配对","常驻配对","重开配对"],tab)
        text+="\n### 本次候选集合内各自最小归档\n\n按完整归档体积选参数，不按速度选；限本次两个codec、两个块大小，无全局最优含义。\n\n"
        ordinary=min((r for r in rows if r["configuration"]["transform"]=="none"),key=lambda r:r["storage"]["stored_bytes"])
        tab=[]
        for policy in ("byte-shuffle-2-v1","xor-shuffle-2-v1"):
            candidate=min((r for r in rows if r["configuration"]["transform"]==policy),key=lambda r:r["storage"]["stored_bytes"])
            old,new=ordinary["storage"]["stored_bytes"],candidate["storage"]["stored_bytes"]
            derived={"ordinary":label(ordinary),"candidate":label(candidate),"ordinary_bytes":old,"candidate_bytes":new,
                "source_bytes_once":source_cost,"net_saved_bytes_with_source_once":old-new-source_cost,
                "net_saving_pct_with_source_once":100*(1-(new+source_cost)/old),
                "archive_saving_pct":100*(1-new/old),
                "ordinary_restore_s":ordinary["decode_s"]["median"],"candidate_restore_s":candidate["decode_s"]["median"],
                "restore_medians_ratio":candidate["decode_s"]["median"]/ordinary["decode_s"]["median"],
                "ordinary_reopen_p95_s":p95(ordinary,"open_and_read"),"candidate_reopen_p95_s":p95(candidate,"open_and_read")}
            record["minimum_archive_comparisons"].append(derived)
            tab.append([label(ordinary),label(candidate),old,new,old-new-source_cost,
                f"{derived['net_saving_pct_with_source_once']:.3f}%",
                f"{ordinary['decode_s']['median']*1000:.3f}/{candidate['decode_s']['median']*1000:.3f}"])
        text+=table(["最小普通","最小策略","普通bytes","策略bytes","计源净省bytes","计源净省%","恢复普通/策略ms"],tab)
        text+="\n"
    result["totals"]={**totals,"scientific_families":2,"synthetic_controls":1}
    text+=f"""## 验证与限制

三组共{totals['formal_roundtrips']}次正式完整恢复、{totals['formal_range_reads']:,}次正式范围读取，
另{totals['warmup_roundtrips']}次完整预热、{totals['warmup_range_reads']:,}次查询预热，全部逐字节一致。
完整归档各轮确定性一致，源/源码/读前后归档SHA及请求指纹一致。
专用numeric.py原始源文件{source_cost:,}bytes；同版本安装已含它，上表仍保守地给每组
候选单独全额计一次。额外原生库、模型、字典均0；公共运行时、pyc及物理目录成本未全额计入。

信号样本量有限且同为int16，不能外推所有科学数组。ECG相邻字可能属于不同通道；
EDF头和注释同样参与变换，未做语义拆分。噪声是测试回退和成本的合成负对照。
每块仍整块反变换/校验，不能从压缩率推断局部读取加速。噪声回退后的读取时序波动
不解释为变换解码收益。没有数值Rust或推理收益。
五轮只作描述统计，波动范围不是置信区间；冷缓存、跨机器、跨日、真实浮点数据、
专业科学压缩器广泛对照和推理质量未测。默认none/v2不变，v4须显式选择。
"""
    with (root/"SUMMARY.md").open("x",encoding="utf-8",newline="\n") as stream:stream.write(text)
    save(root/"derived-metrics.json",result)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(13,4.6),layout="constrained")
    for ax,(dataset,record) in zip(axes,result["datasets"].items()):
        pairs=record["minimum_archive_comparisons"]
        sizes=[pairs[0]["ordinary_bytes"],pairs[0]["candidate_bytes"],pairs[1]["candidate_bytes"]]
        charges=[0,pairs[0]["source_bytes_once"],pairs[1]["source_bytes_once"]]
        labels=["Ordinary","Shuffle2","XOR+shuffle2"]
        bars=ax.bar(labels,[v/1024 for v in sizes],color=["#64748b","#188567","#4f87c6"])
        ax.bar(labels,[v/1024 for v in charges],bottom=[v/1024 for v in sizes],color="#d7a246",label="Full numeric.py source")
        ax.bar_label(bars,labels=[f"{(a+b)/1024:.1f}" for a,b in zip(sizes,charges)],padding=5)
        ax.set_ylim(0,max(a+b for a,b in zip(sizes,charges))/1024*1.16)
        ax.set_title(dataset);ax.set_ylabel("KiB, minimum archive per policy + source")
        ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True);ax.tick_params(axis="x",labelsize=9)
    fig.suptitle("Original bytes, no numeric conversion - size selection among Zlib/Zstd and 64KiB/1MiB")
    axes[0].legend(fontsize=8,loc="upper right")
    path=root/"numeric-costs.png"
    if path.exists():raise ValueError("Plot exists")
    fig.savefig(path,dpi=160);plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("root",type=Path);args=parser.parse_args()
    plot(args.root,generate(args.root))
