"""Report exact CSV space/restore/read tradeoffs; retain negative controls."""
import argparse
import json
from pathlib import Path

from rkv1.benchmark import summary


def table(columns, rows):
    return ("| " + " | ".join(columns) + " |\n|" + "|".join("---" for _ in columns) + "|\n"
            + "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in rows) + "\n")


def pick(report, codec, variant):
    return next(r for r in report["results"] if r["configuration"]["compression"] == codec and r["variant"] == variant)


def paired_restore(legacy, current):
    old = {r["round"]: r["wall_s"] for r in legacy["decode_trials"]}
    factors = [old[r["round"]] / r["wall_s"] for r in current["decode_trials"]]
    return {"speedup": summary(factors), "faster_rounds": sum(f > 1 for f in factors), "rounds": len(factors)}


def p95(row, mode="open_reader"):
    return row["range_aggregate"][mode]["groups"]["byte_weighted"]["round_p95_s"]["median"]


def generate(root):
    names = ("wine", "htru2", "superconductivity")
    reports = {n: json.loads((root / f"{n}.json").read_text("utf-8")) for n in names if (root / f"{n}.json").exists()}
    if not reports:
        raise ValueError("No CSV reports")
    configs = sum(len(r["results"]) for r in reports.values())
    restores = sum(r["verified_measured_roundtrips"] for r in reports.values())
    warm_restores = sum(r["verified_warmup_roundtrips"] for r in reports.values())
    verified = sum(g["verified_requests"] for report in reports.values() for row in report["results"]
                   for trial in row["range_trials"] for g in trial["groups"].values())
    warm_reads = sum(g["verified_warmup_requests"] for report in reports.values() for row in report["results"]
                     for trial in row["range_trials"] for g in trial["groups"].values())
    text = f"""# v0.4.0 E2 独立数值数据与 CSV 反变换优化

{len(reports)} 组语料、{configs} 个条件；**{restores} 次正式完整恢复 + {warm_restores} 次预热恢复**，
**{verified:,} 次正式范围读取 + {warm_reads:,} 次预热范围读取**全部逐字节一致。
同一 CSV 归档在旧/新反变换条件间复用，原文数值、换行和文件哈希保持一致。

增加 HTRU2 脉冲星候选与 Superconductivity 两个原始公开数据集；Wine 作为已有对照。
HTRU2 使用 CR-only 换行，当前 CSV v1 不适用，必须回退且不规范化。Superconductivity
保留 train.csv 与含化学式的 unique_m.csv，混合非数值数据也可回退；不筛选只报正结果。

优化只把按单元索引的 Python 生成器替换为列切片 + zip 重建，保留词法、维度、长度
和最终块 SHA-256 校验。无格式变化、无新模型或字典，默认 CSV 仍关闭。

## 空间与完整恢复

同 codec、1 MiB；耗时为记录轮次中位数。旧基线是冻结的 v0.3 CSV 反变换，其余代码
共享本版实现，因此不是把两次历史整机运行直接比较。

"""
    rows, derived = [], []
    for name, report in reports.items():
        for codec in ("zlib", "zstd"):
            plain, legacy, current = (pick(report, codec, variant) for variant in ("plain", "legacy_csv", "current_csv"))
            if legacy["storage"]["archive_sha256"] != current["storage"]["archive_sha256"]:
                raise ValueError("Decoder comparison uses different archive bytes")
            paired = paired_restore(legacy, current)
            saving = (1 - current["storage"]["stored_bytes"] / plain["storage"]["stored_bytes"]) * 100
            record = {"dataset": name, "codec": codec, "csv_saving_pct": saving,
                      "csv_saving_bytes": plain["storage"]["stored_bytes"] - current["storage"]["stored_bytes"],
                      "transformed_chunks": current["storage"]["transformed_chunks"],
                      "inverse_transform_used": current["storage"]["transformed_chunks"] > 0,
                      "total_chunks": current["storage"]["unique_chunks"],
                      "restore_speedup_ratio_of_medians": legacy["decode_s"]["median"] / current["decode_s"]["median"],
                      "current_csv_restore_time_vs_plain": current["decode_s"]["median"] / plain["decode_s"]["median"],
                      "current_csv_read_p95_vs_plain": p95(current) / p95(plain), "paired_restore": paired,
                      "basis": "calculated from raw v0.4 samples; no additional measurements"}
            derived.append(record)
            rows.append([name, codec, plain["storage"]["stored_bytes"], current["storage"]["stored_bytes"],
                         f'{saving:.3f}%', f'{record["transformed_chunks"]}/{record["total_chunks"]}',
                         f'{legacy["decode_s"]["median"] * 1000:.3f}', f'{current["decode_s"]["median"] * 1000:.3f}',
                         f'{record["restore_speedup_ratio_of_medians"]:.2f}×' if record["inverse_transform_used"] else "无变换",
                         f'{paired["faster_rounds"]}/{paired["rounds"]}' if record["inverse_transform_used"] else "—",
                         f'{record["current_csv_restore_time_vs_plain"]:.2f}×'])
    text += table(["数据", "codec", "普通 bytes", "CSV bytes", "空间节省", "变换块/全部块", "旧 CSV 恢复 ms", "新 CSV 恢复 ms", "旧/新耗时", "更快轮数", "新 CSV/普通耗时"], rows)
    text += "\nHTRU2 的回退没有 CSV 算法收益；微小时间差属于对照波动。启用策略的头部会有少量固定成本。\n"
    text += "\n## 跨 codec 的体积对照\n\n仅在本轮 Zlib/Zstd 中，分别选择普通与 CSV 条件的最小归档；不代表全部成熟方法的最优。\n\n"
    rows = []
    for name, report in reports.items():
        plain = min((r for r in report["results"] if r["variant"] == "plain"), key=lambda r: r["storage"]["stored_bytes"])
        current = min((r for r in report["results"] if r["variant"] == "current_csv"), key=lambda r: r["storage"]["stored_bytes"])
        rows.append([name, plain["configuration"]["compression"], plain["storage"]["stored_bytes"],
                     f'{plain["decode_s"]["median"] * 1000:.3f}', current["configuration"]["compression"],
                     current["storage"]["stored_bytes"], f'{current["decode_s"]["median"] * 1000:.3f}',
                     f'{(1-current["storage"]["stored_bytes"]/plain["storage"]["stored_bytes"])*100:.3f}%',
                     f'{current["decode_s"]["median"]/plain["decode_s"]["median"]:.2f}×'])
    text += table(["数据", "普通最小体积 codec", "普通 bytes", "普通恢复 ms", "CSV 最小体积 codec", "CSV bytes", "CSV 恢复 ms", "净空间节省", "CSV/普通恢复耗时"], rows)
    text += "\n## 加权范围读取与内存\n\n延迟为各轮 p95 中位数；每轮每类别请求数见 protocol，样本量较小，不替代 v0.3 读取矩阵。\n\n"
    rows = []
    for name, report in reports.items():
        for codec in ("zlib", "zstd"):
            for variant in ("plain", "legacy_csv", "current_csv"):
                row = pick(report, codec, variant)
                rows.append([name, codec, variant, f'{p95(row) * 1000:.3f}', f'{p95(row, "open_and_read") * 1000:.3f}',
                             f'{row["decode_peak_rss_bytes"]["median"] / 1048576:.2f}'])
    text += table(["数据", "codec", "条件", "常驻 p95 ms", "重开 p95 ms", "恢复峰值 MiB"], rows)
    text += "\n## 诊断与解释边界\n\n"
    for name, report in reports.items():
        for codec, profile in report["decoder_profiles"].items():
            if profile is None:
                text += f"- {name}/{codec}：没有实际变换块，反变换 profile=null。\n"
            else:
                text += f'- {name}/{codec}：取一个 {profile["raw_bytes"]:,} bytes 的变换块，分别诊断旧/新反变换三次；全部函数计数/时间在 JSON。\n'
    text += """

cProfile 的累计时间有嵌套重叠且受 instrumentation 影响；不能相加成总 CPU 占比，
也不能用它替代独立 worker 的耗时对照。列切片会增加引用存储，必须同时看 RSS。
词法正则验证仍保留，是后续 Rust/解析优化候选；本版没有 Rust 加速结果。

范围读取仍重建完整变换块，局部循环优化不能保证随机访问的综合收益。体积和耗时
应分别验收；保持可选策略。单机、温缓存、五轮默认样本，不声称通用最优或显著性。
归档字节包含所有元数据，运行时账本另记实验源码；冻结旧解码器是共享实验资源，
不是每个归档的模型/字典。完整 Python/共享原生依赖仍未全额分摊。

下一步：依据诊断结果改善类型表示和块内访问，再开展真实版本序列/共享块存储；
数组、代码、数学文本和 E3/E4 尚待推进。见 [CSV-TRIALS.md](../../docs/CSV-TRIALS.md)。
"""
    (root / "SUMMARY.md").write_text(text, encoding="utf-8", newline="\n")
    (root / "derived-metrics.json").write_text(json.dumps(derived, indent=2) + "\n", encoding="utf-8", newline="\n")
    return reports, {"configurations": configs, "measured_roundtrips": restores, "warmup_roundtrips": warm_restores,
                     "verified_range_reads": verified, "verified_warmup_range_reads": warm_reads}


def plot(root, reports):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels, savings, speedups, costs = [], [], [], []
    for name, report in reports.items():
        for codec in ("zlib", "zstd"):
            plain, old, current = (pick(report, codec, v) for v in ("plain", "legacy_csv", "current_csv"))
            if not current["storage"]["transformed_chunks"]:
                continue
            label = "SUPERCON." if name == "superconductivity" else name.upper()
            labels.append(label + "\n" + codec)
            savings.append((1 - current["storage"]["stored_bytes"] / plain["storage"]["stored_bytes"]) * 100)
            speedups.append(old["decode_s"]["median"] / current["decode_s"]["median"])
            costs.append(current["decode_s"]["median"] / plain["decode_s"]["median"])
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), layout="constrained")
    axes[0].bar(labels, savings, color="#0f766e")
    for i, value in enumerate(savings):
        axes[0].text(i, value + 0.15, f"{value:.2f}%", ha="center")
    axes[0].set_ylabel("Complete archive saving (%)")
    axes[0].set_title("Column transform: space gain")
    axes[0].set_ylim(0, max(savings) * 1.2)
    axes[1].bar(labels, costs, color="#b45309")
    for i, (cost, speedup) in enumerate(zip(costs, speedups)):
        axes[1].text(i, cost + 0.12, f"old/new {speedup:.2f}x", ha="center", fontsize=10)
    axes[1].set_ylabel("New CSV / plain restore time (ratio)")
    axes[1].set_title("After optimization: restore cost remains")
    axes[1].axhline(1, color="#111827", linestyle="--", label="Same time as plain")
    axes[1].set_ylim(0, max(costs) * 1.25)
    axes[1].legend()
    for ax in axes:
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle("RKV-1 v0.4.0 | Five-run medians | HTRU2: no transformed blocks; fallback retained")
    fig.savefig(root / "csv-tradeoffs.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    reports, counts = generate(args.directory)
    print(json.dumps(counts))
    if args.plot:
        plot(args.directory, reports)
