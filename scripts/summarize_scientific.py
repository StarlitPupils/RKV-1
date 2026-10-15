"""Derive full archive and explicitly allocated dependency costs from raw trials."""
import argparse
import json
from pathlib import Path

from scripts.run_units import save
from scripts.summarize_numeric import label, paired
from scripts.summarize_units import p95, table

DATASETS=("spitzer32","bolocam32","msx64","ecg","noise")


def policy(row):
    c=row["configuration"]
    if c["compression"].startswith("blosc-"):
        return "blosc-"+c["compression"].split("-")[2]
    return "ordinary" if c["transform"]=="none" else "xor" if c["transform"].startswith("xor-") else "shuffle"


def generate(root):
    resources=json.loads((root/"dependency-provenance.json").read_text("utf-8"))
    sources={r["name"]:r["bytes"] for r in resources["dedicated_sources"]}
    charges={"ordinary":0,"shuffle":sources["numeric.py"],"xor":sources["numeric.py"]}
    charges.update({"blosc-"+f:resources["total_recorded_dependency_bytes"]+sources["blosc_codec.py"]
                    for f in ("none","shuffle","bitshuffle")})
    result={"resource_provenance":resources,"allocated_once_bytes":charges,"datasets":{}}
    totals={k:0 for k in ("formal_roundtrips","warmup_roundtrips","formal_range_reads","warmup_range_reads")}
    text="""# v0.11.0 原始浮点 FITS 与专业字节压缩对照

三份完整公开 FITS 示例（两个 float32、一个 float64），前版 ECG int16，以及固定随机字节负对照。
全部源字节保留，FITS 头/填充/NaN payload 不变，不转换数值或端序。
每组 18 条件：64KiB/1MiB ×（Zlib6/Zstd3 ×普通/字节重排/XOR重排，加 Blosc-Zstd 无过滤/字节重排/位重排）。
全部同 v5 容器；专业库 python-blosc 1.11.4 / C-Blosc，单线程，clevel3，内部块 64KiB。
Blosc clevel 与内嵌 Zstd 版本不同于直接 Zstd3，跨后端差异不是单一过滤器的因果收益。
只在 Blosc 相同块/宽度/后端下的过滤器消融隔离过滤选择。未测试 Blosc2、NDArray 子块读取或所有科学压缩器。

每条件完整预热后五轮正式编码/恢复，条件与轮次打乱；两个读取器生命周期五轮范围读取，
各条件/模式共享原始请求。完整编码和首个实际 Blosc 块的恢复计入首次导入/设置；
正式范围读排除查询预热中的首次加载，均为本机温 OS 缓存。整块解码/校验，未减少真值检查。

完整归档含全部容器/块头/路径/SHA。分别报告依赖已安装情景（仅归档增量），和一次全额
分配整个已安装 Blosc 发行包+适配源文件的情景；Python 变换计整个 numeric.py 一次。
后者仍不包括公共 Python/core/Zstd 与外部 OS 运行时全部成本，不称完整部署大小。
没有按单算法裁剪库。NumPy 是否被导入及分配由实测环境记录，不把未加载的可选依赖计入或移出计时。

"""
    for dataset in DATASETS:
        report=json.loads((root/f"{dataset}-scientific.json").read_text("utf-8"))
        provenance=json.loads((root/f"{dataset}-provenance.json").read_text("utf-8"))
        rows=report["results"]
        counts={"formal_roundtrips":sum(t["round"]>=0 for r in rows for t in r["decode_trials"]),
                "warmup_roundtrips":sum(t["round"]<0 for r in rows for t in r["decode_trials"]),
                "formal_range_reads":sum(g["verified_requests"] for r in rows for t in r["range_trials"] for g in t["groups"].values()),
                "warmup_range_reads":sum(g["verified_warmup_requests"] for r in rows for t in r["range_trials"] for g in t["groups"].values())}
        for key in totals:totals[key]+=counts[key]
        record={"raw_bytes":report["raw_file_bytes"],"counts":counts,"layout":provenance.get("layout") if isinstance(provenance.get("layout"),dict) else None,
                "conditions":{},"matched_comparisons":[],"minimum_archive_comparisons":[]}
        result["datasets"][dataset]=record
        text+=f"## {dataset}\n\n原始 {report['raw_file_bytes']:,} bytes；18 条件、五轮。\n\n"
        if record["layout"]:
            x=record["layout"]
            text+=f"BITPIX {x['bitpix']}，FITS 轴 {x['fits_axes']}，大端；头 {x['header_bytes']:,}、图像 {x['image_bytes']:,}、填充 {x['padding_bytes']:,} bytes。图像 {x['image_words']:,} 字，NaN {x['nan_words']:,}（{100*x['nan_words']/x['image_words']:.4f}%），Inf {x['infinite_words']}，正/负零 {x['positive_zero_words']}/{x['negative_zero_words']}。此分布不能代表一般科学数组。\n\n"
        tab=[]
        for row in rows:
            name=label(row);charge=charges[policy(row)]
            record["conditions"][name]={"configuration":row["configuration"],"storage":row["storage"],
                "actual_transforms":row["actual_transforms"],"actual_codecs":row["actual_codecs"],
                "allocated_once_bytes":charge,"archive_plus_allocated_bytes":row["storage"]["stored_bytes"]+charge,
                **{k:row[k] for k in ("encode_s","decode_s","encode_cpu_s","decode_cpu_s","encode_peak_rss_bytes","decode_peak_rss_bytes")},
                "resident_p95_s":p95(row,"open_reader"),"reopen_p95_s":p95(row,"open_and_read")}
            tab.append([name,row["storage"]["stored_bytes"],charge,
                        f"{row['encode_s']['median']*1000:.3f}",f"{row['decode_s']['median']*1000:.3f}",
                        f"{p95(row,'open_reader')*1000:.3f}",f"{p95(row,'open_and_read')*1000:.3f}"])
        text+=table(["codec/块/策略","完整归档 B","另分配一次 B","编码 ms","恢复 ms","常驻 p95 ms","重开 p95 ms"],tab)
        text+="\n### 相同后端/块/宽度消融\n\n倍率为逐轮 baseline/candidate 的中位数，大于 1 更快，括号为更快轮数；不是两组中位之比。依赖成本在同 Blosc 对照内抵消。\n\n"
        tab=[]
        for candidate in rows:
            c=candidate["configuration"];p=policy(candidate)
            if p in ("ordinary","blosc-none"):continue
            base=next(r for r in rows if r["configuration"]["chunk_size"]==c["chunk_size"] and
                ((policy(r)=="blosc-none") if p.startswith("blosc-") else
                 (policy(r)=="ordinary" and r["configuration"]["compression"]==c["compression"])))
            old,new=base["storage"]["stored_bytes"],candidate["storage"]["stored_bytes"]
            comparisons={m:paired(base,candidate,m) for m in ("encode","decode","open_reader","open_and_read")}
            record["matched_comparisons"].append({"baseline":label(base),"candidate":label(candidate),
                "archive_saving_pct":100*(1-new/old),"paired":comparisons})
            def ratio(m):
                x=comparisons[m];return f"{x['speedup_median']:.3f}× ({x['candidate_faster_rounds']}/{x['rounds']})"
            tab.append([label(candidate),f"{100*(1-new/old):.3f}%",*(ratio(m) for m in comparisons)])
        text+=table(["候选","归档节省","编码配对","恢复配对","常驻配对","重开配对"],tab)
        baseline=min((r for r in rows if policy(r)=="ordinary"),key=lambda r:r["storage"]["stored_bytes"])
        old=baseline["storage"]["stored_bytes"]
        text+="\n### 本次候选内分别按最小归档选参\n\n限本次有限矩阵，不是全局最优，也不是按速度优化的配置。跨后端/块差异包含多种因素。\n\n"
        tab=[]
        for p in charges:
            candidate=min((r for r in rows if policy(r)==p),key=lambda r:r["storage"]["stored_bytes"])
            new=candidate["storage"]["stored_bytes"];charge=charges[p]
            item={"policy":p,"baseline":label(baseline),"candidate":label(candidate),"ordinary_bytes":old,
                "candidate_bytes":new,"allocated_once_bytes":charge,"archive_saving_pct":100*(1-new/old),
                "net_saved_bytes_with_allocation_once":old-new-charge,"net_saving_pct_with_allocation_once":100*(1-(new+charge)/old),
                "encode_median_s":candidate["encode_s"]["median"],"decode_median_s":candidate["decode_s"]["median"],
                "paired":{m:paired(baseline,candidate,m) for m in ("encode","decode","open_reader","open_and_read")}}
            record["minimum_archive_comparisons"].append(item)
            tab.append([p,label(candidate),new,f"{item['archive_saving_pct']:.3f}%",new+charge,
                        f"{item['net_saving_pct_with_allocation_once']:.3f}%",f"{item['decode_median_s']*1000:.3f}"])
        text+=table(["策略","最小归档配置","归档 B","已安装情景节省","归档+一次分配 B","分配后净省","恢复 ms"],tab)+"\n"
    aggregate=[]
    for p,charge in charges.items():
        selected=[next(x for x in result["datasets"][d]["minimum_archive_comparisons"] if x["policy"]==p) for d in DATASETS if d!="noise"]
        old=sum(x["ordinary_bytes"] for x in selected);new=sum(x["candidate_bytes"] for x in selected)
        aggregate.append({"policy":p,"ordinary_bytes":old,"candidate_bytes":new,"allocated_once_bytes":charge,
                          "archive_saving_pct":100*(1-new/old),"net_saving_pct_with_allocation_once":100*(1-(new+charge)/old)})
    result["four_scientific_groups_shared_dependency"]=aggregate;result["totals"]=totals
    text+="## 四组科学输入合计，依赖共用一次\n\n三个 FITS 加 ECG，不含噪声；只累加独立归档，不引入 CAS、不叠加其他版本节省比例。每组独立按体积选参，不按时延选。\n\n"
    text+=table(["策略","合计归档 B","已安装节省","共享分配一次 B","分配后净省"],
                [[x["policy"],x["candidate_bytes"],f"{x['archive_saving_pct']:.3f}%",x["allocated_once_bytes"],
                  f"{x['net_saving_pct_with_allocation_once']:.3f}%"] for x in aggregate])
    text+=f"\n## 完整性与限制\n\n共 {totals['formal_roundtrips']} 次正式恢复、{totals['formal_range_reads']:,} 次正式范围读取，另 {totals['warmup_roundtrips']} 次恢复预热、{totals['warmup_range_reads']:,} 次查询预热，全部逐字节一致。源/实现/依赖身份冻结、各轮归档确定性及请求一致性见 validation.json。\n\n"
    text+="五轮为描述统计，不能称置信区间或稳定跨机器收益。三个天文示例来自同一托管项目，不是三个独立科学领域；float64 样本尤其小。未测试真实无穷值/有符号零的性能，位模式仅在测试中覆盖。完整恢复含首次导入，暖范围不含；不可将其差异解释为纯解码内核差异。峰值 RSS 为进程口径，包含输入/真值/记账对象，不是生产常驻服务的纯增量。\n\n没有冷缓存/跨机器/跨日、数值 Rust 内核、CAS+数值组合、模型推理质量或无限上下文结果。默认 none/v2 保持不变；v5 与 Blosc 都须显式选择。E2 仍在验证，代码/数学类型与 E3/E4 待开展。\n"
    with (root/"SUMMARY.md").open("x",encoding="utf-8",newline="\n") as stream:stream.write(text)
    save(root/"derived-metrics.json",result)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout="constrained")
    science=result["four_scientific_groups_shared_dependency"]
    labels=[x["policy"] for x in science];sizes=[x["candidate_bytes"]/1048576 for x in science]
    charges=[x["allocated_once_bytes"]/1048576 for x in science]
    axes[0].bar(labels,sizes,color="#188567",label="Complete archives")
    axes[0].bar(labels,charges,bottom=sizes,color="#d7a246",label="Dependency + source once")
    axes[0].set_ylabel("MiB, four scientific groups");axes[0].set_title("Storage with dependency allocation");axes[0].legend(fontsize=8)
    for d,record in result["datasets"].items():
        if d=="noise":continue
        items=record["minimum_archive_comparisons"]
        axes[1].plot(labels,[x["decode_median_s"]*1000 for x in items],marker="o",label=d)
    axes[1].set_ylabel("ms, median of 5 full restores");axes[1].set_title("Each policy's minimum archive configuration");axes[1].legend(fontsize=8)
    for ax in axes:
        ax.tick_params(axis="x",rotation=35,labelsize=8);ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True)
    fig.suptitle("v0.11: original float/int bytes; first Blosc load charged in full restore")
    path=root/"scientific-costs.png"
    if path.exists():raise ValueError("Plot exists")
    fig.savefig(path,dpi=160);plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("root",type=Path);args=parser.parse_args()
    plot(args.root,generate(args.root))
