"""Summarize matched Gear backend measurements and full native resource cost."""
import argparse
import json
from pathlib import Path

from scripts.run_units import save
from scripts.summarize_units import table
from scripts.summarize_versions import p95, total_restore


def generate(root):
    report = json.loads((root / "qasper-gear.json").read_text("utf-8"))
    native = report["native_provenance"]
    rounds = report["protocol"]["rounds"]
    resource = native["bytes"] + native["metadata_bytes"]
    rows = {r["configuration"]["name"]: r for r in report["results"]}
    counts = {"configurations": len(rows), "versions": len(report["files_by_version"]),
              "measured_roundtrips": sum(t["round"] >= 0 for r in rows.values() for v in r["versions"] for t in v["restore_trials"]),
              "warmup_roundtrips": sum(t["round"] < 0 for r in rows.values() for v in r["versions"] for t in v["restore_trials"]),
              "verified_range_reads": sum(g["verified_requests"] for r in rows.values() for v in r["versions"] for t in v["range_trials"] for g in t["groups"].values()),
              "verified_warmup_range_reads": sum(g["verified_warmup_requests"] for r in rows.values() for v in r["versions"] for t in v["range_trials"] for g in t["groups"].values())}
    derived = {"counts": counts, "conditions": {}, "native_resource_bytes": resource,
               "backend_comparisons": report["backend_encoding_equivalence"]}
    text = f"""# v0.8.0 热点剖析与精确 Rust Gear 边界扫描

QASPER 原始 train/dev 三次发布，总原文 {report['raw_bytes_all_versions']:,} bytes。
{counts['configurations']} 个条件、{rounds}轮本机温缓存；{counts['measured_roundtrips']} 次正式完整恢复、
{counts['verified_range_reads']:,} 次正式范围读取全部逐字节一致；另有
{counts['warmup_roundtrips']} 次恢复预热、{counts['verified_warmup_range_reads']:,} 次查询预热。
全部 Zstd3，无CSV/模型/字典。Rust只替换Gear循环，递推、表、切点与流状态保持一致。
同方式Python/Rust的每轮完整存储树、所有快照ID和新增对象账本相同。

## 不带剖析器的主实验

提交为三个版本耗时之和（包含共享初始化），每轮新进程，再取中位。
恢复为三个独立恢复进程耗时之和的中位。读取为最后版本byte_weighted组每轮p95的中位。
对象84byte头、双摘要、全部配置/快照/未引用对象计入logical；allocated取正式第0轮。
本表不将原生资源混入存储树，下一节全额单列。原始逐轮wall/CPU/RSS均保留。

"""
    tab = []
    for name in sorted(rows):
        r = rows[name]
        item = {**r["storage"], "sequence_add_s": r["sequence_add_s"],
                "three_snapshot_restore_s": total_restore(r),
                "last_snapshot_open_reader_p95_s": p95(r["versions"][-1], "open_reader"),
                "last_snapshot_open_and_read_p95_s": p95(r["versions"][-1], "open_and_read"),
                "encode_peak_rss_bytes": r["encode_peak_rss_bytes"]}
        derived["conditions"][name] = item
        tab.append([name, item["logical_file_bytes"], item["allocated_file_data_bytes"], item["files"],
                    f'{item["sequence_add_s"]["median"]:.3f}', f'{item["three_snapshot_restore_s"]["median"]:.3f}',
                    f'{item["last_snapshot_open_reader_p95_s"]*1000:.3f}', f'{item["last_snapshot_open_and_read_p95_s"]*1000:.3f}'])
    text += table(["条件", "logical bytes", "allocated数据 bytes", "文件数", "三版提交 s", "三版恢复 s", "常驻p95 ms", "重开p95 ms"], tab)
    text += "\n## 同表示、同完整性规则的提交配对\n\n仅边界扫描后端不同，包含FFI、复制、首次DLL身份检查/加载，压缩与全部旧对象验证照常。\n\n"
    text += table(["存储方式", "提交配对加速中位", "逐轮加速范围", "Rust更快轮数", "每轮完整树相同"],
                  [[c["kind"], f'{c["paired_submission_speedup_median"]:.2f}×',
                    f'{min(c["paired_submission_speedup_samples"]):.2f}–{max(c["paired_submission_speedup_samples"]):.2f}×',
                    f'{c["rust_faster_rounds"]}/{c["rounds"]}', c["identical_complete_tree"]]
                   for c in report["backend_encoding_equivalence"]])
    text += "\n逐轮范围只描述观测波动，不是置信区间。原生提交wall仍受文件发布等阶段影响，原始CPU/wall均保留。\n"
    shared = derived["conditions"]["shared-gear-v1-64-rust"]
    base = derived["conditions"]["archive-fixed-1024"]
    total = shared["logical_file_bytes"] + resource
    comparison = {"shared_gear_logical_bytes": shared["logical_file_bytes"],
                  "dll_and_metadata_bytes": resource, "shared_gear_plus_full_native_bytes": total,
                  "archive_1MiB_logical_bytes": base["logical_file_bytes"],
                  "logical_saving_vs_archive_pct": 100*(1-shared["logical_file_bytes"]/base["logical_file_bytes"]),
                  "saving_with_full_native_vs_archive_pct": 100*(1-total/base["logical_file_bytes"]),
                  "submission_median_ratio_vs_archive": shared["sequence_add_s"]["median"]/base["sequence_add_s"]["median"],
                  "restore_median_ratio_vs_archive": shared["three_snapshot_restore_s"]["median"]/base["three_snapshot_restore_s"]["median"],
                  "reopen_p95_median_ratio_vs_archive": shared["last_snapshot_open_and_read_p95_s"]/base["last_snapshot_open_and_read_p95_s"]}
    derived["complete_incremental_resource_comparison"] = comparison
    text += f"""
## 原生资源与旧归档对照

冻结 Windows DLL {native['bytes']:,} bytes + native.json {native['metadata_bytes']:,} bytes，
全额共享原生资源 **{resource:,} bytes**。虽然同时包含CSV符号，本实验未使用CSV，仍计整份库。
共享Gear存储树 {shared['logical_file_bytes']:,} bytes，加一次全额原生资源
**{total:,} bytes**，对旧独立1MiB归档 {base['logical_file_bytes']:,} bytes 减少
**{comparison['saving_with_full_native_vs_archive_pct']:.3f}%**。
公共Python/codec/OS/链接依赖未完整分配，不称为完整部署或物理卷成本。

按本轮中位耗时比较，Rust共享Gear提交仍为旧1MiB归档的
**{comparison['submission_median_ratio_vs_archive']:.2f}倍**；完整恢复
**{comparison['restore_median_ratio_vs_archive']:.2f}倍**，重开p95
**{comparison['reopen_p95_median_ratio_vs_archive']:.2f}倍**。
Rust未改变读取/解码路径，Python/Rust条件之间恢复/读取时序波动不能解释成Rust解码收益。

## 诊断剖析

profiling-baseline.json 的全部Python模块指纹与v0.7.0相同；一轮不带剖析器，
随后一轮cProfile，每轮新建共享Gear。每个版本add独立剖析，验证/树审计不计时。
cProfile会放大per-byte append/len成本；下面inclusive时间互相重叠，不是CPU采样百分比，
也不能用诊断轮与主实验或旧版本时序相除来宣称加速。

"""
    profile_rows = []
    for filename in ("profiling-baseline.json", "profiling-native.json"):
        if not (root / filename).exists():
            continue
        prof = json.loads((root / filename).read_text("utf-8"))
        for trial in prof["trials"]:
            if not trial["profiled"]:
                continue
            for version in trial["versions"]:
                f = next(x for x in version["functions_by_exclusive_time"] if x["file"] == "chunking.py" and x["function"] == "chunks")
                profile_rows.append([prof.get("chunker_backend", "python"), version["version"],
                                     f'{version["wall_s"]:.3f}', f'{f["inclusive_s"]:.3f}',
                                     f'{100*f["inclusive_s"]/version["wall_s"]:.1f}%'])
    text += table(["诊断后端", "版本", "instrumented add s", "chunks inclusive s", "占instrumented wall"], profile_rows)
    text += """
## 边界与后续

Gear scale64KiB仍为同一冻结单mask profile，实测平均约87.4KiB，不是FastCDC。
输入仍全量扫描/哈希，旧对象仍逐一解压验证；没有依靠跳过校验获得加速。
底层仍为一对象一文件，914文件的目录/MFT/日志未完整计入；RSS含存储审计，
范围RSS包含真值、预读清单和账本，不当作生产内存。新增原生库没有修改CAS格式，
Python仍为默认，可用v0.7 Python读取Rust产生的同字节存储树。
一个语料家族三版、五轮描述统计，不做显著性或全局最优结论；冷缓存、跨机器、
跨日、推理质量均未测。后续按剩余热点评估对象发布/访问，再补独立版本家族与E2类型。
"""
    with (root / "SUMMARY.md").open("x", encoding="utf-8", newline="\n") as f:
        f.write(text)
    save(root / "derived-metrics.json", derived)
    return rows, derived


def plot(root, rows, derived):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = ["archive-fixed-1024", "shared-fixed-64", "isolated-gear-v1-64-python",
             "isolated-gear-v1-64-rust", "shared-gear-v1-64-python", "shared-gear-v1-64-rust"]
    labels = ["RKV 1MiB", "Shared fixed64", "Isolated Gear Py", "Isolated Gear Rust", "Shared Gear Py", "Shared Gear Rust"]
    colors = ["#64748b", "#a8a29e", "#a3bffa", "#4361b8", "#82d1ae", "#147d58"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4), layout="constrained")
    times = [rows[n]["sequence_add_s"]["median"] for n in names]
    bars = axes[0].bar(labels, times, color=colors)
    axes[0].set_yscale("log"); axes[0].set_ylim(min(times)*.65, max(times)*2)
    axes[0].bar_label(bars, labels=[f"{v:.3f}s" for v in times], padding=5)
    axes[0].set_ylabel("Three-version submission seconds (median, log scale)")
    axes[0].set_title("Same Gear bytes; only scanner backend changes")
    volumes = [rows[n]["storage"]["logical_file_bytes"]/1e6 for n in names]
    bars = axes[1].bar(labels, volumes, color=colors)
    resources = [derived["native_resource_bytes"]/1e6 if n.endswith("-rust") else 0 for n in names]
    axes[1].bar(labels, resources, bottom=volumes, color="#f59e0b", label="Full DLL + metadata, once")
    axes[1].bar_label(bars, labels=[f"{v:.2f}" for v in volumes], padding=7)
    axes[1].set_ylabel("Logical storage MB (decimal)"); axes[1].set_ylim(0,max(volumes)*1.17)
    axes[1].set_title("Storage unchanged by the native scanner"); axes[1].legend(fontsize=8)
    for ax in axes:
        ax.tick_params(axis="x",labelrotation=27,labelsize=8)
        ax.grid(axis="y",alpha=.18); ax.set_axisbelow(True)
    fig.suptitle("QASPER original releases 0.1 / 0.2 / 0.3 - local warm-cache, five rounds")
    output = root / "gear-tradeoffs.png"
    if output.exists():
        raise ValueError("Plot already exists")
    fig.savefig(output, dpi=160); plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    root = parser.parse_args().root
    rows, derived = generate(root)
    plot(root, rows, derived)
