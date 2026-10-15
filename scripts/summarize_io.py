"""Generate complete-cost tables, per-round IO comparisons and scientific figures."""
import argparse
import json
from pathlib import Path
import statistics

from scripts.run_units import save
from scripts.summarize_units import table
from scripts.summarize_versions import p95, total_restore


def paired(rows, left, right, metric):
    def values(row):
        if metric == "add":
            return {t["round"]: t["setup_s"] + sum(v["add"]["wall_s"] for v in t["versions"])
                    for t in row["sequence_trials"] if t["round"] >= 0}
        if metric == "restore":
            rounds = {}
            for v in row["versions"]:
                for t in v["restore_trials"]:
                    if t["round"] >= 0: rounds[t["round"]] = rounds.get(t["round"], 0) + t["wall_s"]
            return rounds
        return {t["round"]: t["groups"]["byte_weighted"]["latency_s"]["p95"]
                for t in row["versions"][-1]["range_trials"] if t["mode"] == metric}
    a, b = values(rows[left]), values(rows[right])
    ratios = [a[i]/b[i] for i in sorted(a)]
    return {"reference": left, "candidate": right, "metric": metric,
            "speedup_samples": ratios, "speedup_median": statistics.median(ratios),
            "min": min(ratios), "max": max(ratios),
            "candidate_faster_rounds": sum(b[i] < a[i] for i in a), "rounds": len(a)}


def generate(root):
    native = json.loads((root / "native-provenance.json").read_text("utf-8"))
    resource = native["bytes"] + native["metadata_bytes"]
    derived = {"native_resource_bytes": resource, "datasets": {}}
    totals = {"measured_roundtrips": 0, "warmup_roundtrips": 0,
              "verified_range_reads": 0, "verified_warmup_range_reads": 0}
    text = """# v0.9.0 同格式CAS对象IO消融与独立版本家族

分别测QASPER三个原始发布和Evidence Inference三个官方发布的两张原始主CSV表。
全部Zstd3，Gear使用相同冻结v0.8 Rust库；无CSV变换/模型。默认reference/link保持不变。
八条件包括旧独立1MiB、共享固定64KiB、独立/共享冻结v0.8 Gear、当前reference/link、
bounded/link、reference/Windows rename及组合。逐新文件flush/fsync、全部复用验证保留。

logical计全部对象84-byte头/双摘要/payload、配置/快照及未引用对象；本表原生库另计。
allocated为正式第0轮文件数据extent，不含完整目录/MFT/日志。提交含初始化、库首次
身份检查/加载、全量扫描、压缩、旧对象验证与发布。恢复为三次独立进程耗时之和，
再取轮次中位。范围为最后版本byte_weighted组各轮p95的中位。原始wall/CPU/RSS均保留。
所有同kind/profile条件完整存储树、快照和对象账本相同，读取前后存储树不变。

"""
    for dataset in ("qasper", "evidence"):
        report = json.loads((root / f"{dataset}-io.json").read_text("utf-8"))
        rows = {r["configuration"]["name"]: r for r in report["results"]}
        counts = {"configurations": len(rows), "versions": len(report["files_by_version"]),
                  "measured_roundtrips": sum(t["round"] >= 0 for r in rows.values() for v in r["versions"] for t in v["restore_trials"]),
                  "warmup_roundtrips": sum(t["round"] < 0 for r in rows.values() for v in r["versions"] for t in v["restore_trials"]),
                  "verified_range_reads": sum(g["verified_requests"] for r in rows.values() for v in r["versions"] for t in v["range_trials"] for g in t["groups"].values()),
                  "verified_warmup_range_reads": sum(g["verified_warmup_requests"] for r in rows.values() for v in r["versions"] for t in v["range_trials"] for g in t["groups"].values())}
        for key in totals: totals[key] += counts[key]
        result = {"counts": counts, "raw_bytes_all_versions": report["raw_bytes_all_versions"], "conditions": {}, "paired": []}
        derived["datasets"][dataset] = result
        text += f"## {dataset}\n\n原文合计{report['raw_bytes_all_versions']:,} bytes，{counts['configurations']}条件、{report['protocol']['rounds']}轮。\n\n"
        tab = []
        for name in sorted(rows):
            r = rows[name]
            c = {**r["storage"], "sequence_add_s": r["sequence_add_s"], "three_snapshot_restore_s": total_restore(r),
                 "last_snapshot_open_reader_p95_s": p95(r["versions"][-1], "open_reader"),
                 "last_snapshot_open_and_read_p95_s": p95(r["versions"][-1], "open_and_read")}
            result["conditions"][name] = c
            tab.append([name,c["logical_file_bytes"],c["allocated_file_data_bytes"],c["files"],
                        f'{c["sequence_add_s"]["median"]:.3f}',f'{c["three_snapshot_restore_s"]["median"]:.3f}',
                        f'{1000*c["last_snapshot_open_reader_p95_s"]:.3f}',f'{1000*c["last_snapshot_open_and_read_p95_s"]:.3f}'])
        text += table(["条件","logical bytes","allocated数据 bytes","文件数","提交 s","恢复 s","常驻p95 ms","重开p95 ms"],tab)
        text += "\n### 相同框架的配对\n\n倍率=reference/candidate，每轮比值后取中位；范围是描述统计，不是置信区间。\n\n"
        comparisons = [("shared-gear-reference", "shared-gear-v08", "add"),
                       ("shared-gear-reference", "shared-gear-bounded", "add"),
                       ("shared-gear-reference", "shared-gear-rename", "add"),
                       ("shared-gear-reference", "shared-gear-combined", "add"),
                       ("shared-gear-reference", "shared-gear-bounded", "restore"),
                       ("shared-gear-reference", "shared-gear-bounded", "open_reader"),
                       ("shared-gear-reference", "shared-gear-bounded", "open_and_read"),
                       ("shared-gear-rename", "shared-gear-combined", "restore"),
                       ("shared-gear-rename", "shared-gear-combined", "open_reader"),
                       ("shared-gear-rename", "shared-gear-combined", "open_and_read")]
        tab=[]
        for left,right,metric in comparisons:
            if right not in rows or left not in rows: continue
            c=paired(rows,left,right,metric);result["paired"].append(c)
            tab.append([left.removeprefix("shared-gear-"),right.removeprefix("shared-gear-"),metric,
                        f'{c["speedup_median"]:.3f}×',f'{c["min"]:.3f}–{c["max"]:.3f}×',
                        f'{c["candidate_faster_rounds"]}/{c["rounds"]}'])
        text+=table(["reference","candidate","指标","配对加速中位","逐轮范围","candidate更快轮数"],tab)
        combined = next(c for c in result["paired"] if c["candidate"] == "shared-gear-combined" and c["metric"] == "add")
        text += (f"\n组合提交配对中位{combined['speedup_median']:.3f}×，"
                 f"{combined['candidate_faster_rounds']}/{combined['rounds']}轮更快。"
                 "逐轮波动跨过1；不从两个耗时中位之比推算配对收益。\n")
        shared=rows["shared-gear-combined"]["storage"]["logical_file_bytes"]
        isolated=rows["isolated-gear-v08"]["storage"]["logical_file_bytes"]
        archive=rows["archive-fixed-1024"]["storage"]["logical_file_bytes"]
        result["cost"]={"shared_gear_bytes":shared,"isolated_gear_bytes":isolated,"archive_1MiB_bytes":archive,
                        "native_resource_bytes_once":resource,"shared_plus_full_native_bytes":shared+resource,
                        "shared_saving_vs_isolated_pct":100*(1-shared/isolated),
                        "saving_with_native_vs_archive_pct":100*(1-(shared+resource)/archive)}
        text+=f"\n同表示共享节省{result['cost']['shared_saving_vs_isolated_pct']:.3f}%；本家族单独部署加整份库后{shared+resource:,}bytes，对独立1MiB减少{result['cost']['saving_with_native_vs_archive_pct']:.3f}%。\n"
        # File identity is distinct from chunk reuse: expose unchanged input files.
        inventories=report["files_by_version"]
        file_reuse=[]
        for index,files in enumerate(inventories):
            previous={f["sha256"] for old in inventories[:index] for f in old}
            same=sum(f["bytes"] for f in files if f["sha256"] in previous)
            file_reuse.append({"version_index":index,"unchanged_whole_file_raw_bytes":same,
                               "raw_bytes":sum(f["bytes"] for f in files)})
        result["whole_file_reuse_context"]=file_reuse
        text+="\n原文件整文件复用背景（不等同于块复用）："+", ".join(f"v{i+1} {r['unchanged_whole_file_raw_bytes']:,}/{r['raw_bytes']:,}原文字节来自早期相同文件" for i,r in enumerate(file_reuse))+"。\n\n"
    derived["totals"]={**totals,"dataset_families":len(derived["datasets"])}
    shared=sum(d["cost"]["shared_gear_bytes"] for d in derived["datasets"].values())
    archive=sum(d["cost"]["archive_1MiB_bytes"] for d in derived["datasets"].values())
    derived["two_independent_stores_one_native_library"]={"shared_store_bytes_sum":shared,"native_bytes_once":resource,
        "total_bytes":shared+resource,"independent_archive_bytes_sum":archive,"saving_pct":100*(1-(shared+resource)/archive)}
    text+=f"""## 验证、资源与范围

两家族共{totals['measured_roundtrips']}次正式完整恢复、{totals['verified_range_reads']:,}次正式范围读取，
另{totals['warmup_roundtrips']}次恢复预热、{totals['verified_warmup_range_reads']:,}次查询预热，全部逐字节一致。
DLL {native['bytes']:,}bytes + 原始元数据{native['metadata_bytes']:,}bytes = {resource:,}bytes，
每家族单独部署上表全额加一次。两个独立仓库共用同一份库时，总逻辑成本
{shared+resource:,}bytes，对各自独立归档之和{archive:,}bytes减少
{100*(1-(shared+resource)/archive):.3f}%；这是资源摊销情景，未做跨家族CAS去重。

候选不改编码，默认reference/link不变。rename只有Windows发布路径变化，read路径
与reference相同；不把其读取波动解释为rename解码加速。bounded仍检查对象路径和
完整EOF、全部SHA与受限解压。每个新文件仍flush/fsync，不以减少同步次数换速度。
Gear scale64KiB不保证实际均值一致，不是FastCDC。本机温缓存五轮，不做统计显著
或全局最优结论；冷缓存、跨机器、跨日和推理质量未测。范围RSS含真值和账本，
编码RSS含树审计，不当作生产内存。无GC或断电耐久性证明。

Evidence Inference只测两张官方原始主表，prompts三版完全相同；不能把此家族较高
共享收益推广至论文全文或独立科学数据。来源范围、固定commit/SHA见DATASETS/IO协议。
"""
    with (root/"SUMMARY.md").open("x",encoding="utf-8",newline="\n") as f:f.write(text)
    save(root/"derived-metrics.json",derived)
    return derived


def plot(root,derived):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names=["shared-gear-v08","shared-gear-reference","shared-gear-bounded","shared-gear-rename","shared-gear-combined"]
    labels=["Frozen v0.8","Current ref","Bounded","Rename","Combined"]
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout="constrained")
    for ax,(dataset,data) in zip(axes,derived["datasets"].items()):
        wall=[data["conditions"][n]["sequence_add_s"]["median"] for n in names]
        samples=[data["conditions"][n]["sequence_add_s"]["samples"] for n in names]
        bars=ax.bar(labels,wall,color=["#64748b","#a8a29e","#4f87c6","#d7a246","#188567"])
        ax.bar_label(bars,labels=[f"{v:.3f}s" for v in wall],label_type="center",color="white",fontweight="bold")
        for index, values in enumerate(samples):
            ax.scatter([index + (i-2)*.065 for i in range(len(values))],values,
                       color="#111827",s=16,zorder=3,alpha=.7)
        ax.set_ylim(0,max(max(v) for v in samples)*1.16);ax.set_ylabel("Three-release submission seconds")
        ax.set_title(dataset);ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True)
    fig.suptitle("Same stored bytes and per-file fsync - local Windows\nBars: medians; dots: five round observations")
    path=root/"io-ablation.png"
    if path.exists():raise ValueError("Plot already exists")
    fig.savefig(path,dpi=160);plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("root",type=Path);root=parser.parse_args().root
    plot(root,generate(root))
