"""Complete-cost unit results, matched against whole and ordinary small blocks."""
import argparse
import json
from pathlib import Path

from rkv1.benchmark import summary


def table(columns, rows):
    return ("| " + " | ".join(columns) + " |\n|" + "|".join("---" for _ in columns) + "|\n"
            + "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in rows) + "\n")


def pick(report, layout, codec="zstd", transform="none"):
    return next(r for r in report["results"] if r["configuration"]["layout"] == layout
                and r["configuration"]["compression"] == codec and r["configuration"]["transform"] == transform)


def group(row, mode="open_reader", category="byte_weighted"):
    return row["range_aggregate"][mode]["groups"][category]


def p95(row, mode="open_reader"):
    return group(row, mode)["round_p95_s"]["median"]


def compare(base, candidate, mode):
    old = {(t["round"], t["mode"]): t["groups"]["byte_weighted"] for t in base["range_trials"]}
    ratios = []
    for trial in candidate["range_trials"]:
        if trial["mode"] != mode:
            continue
        left = old[(trial["round"], mode)]
        right = trial["groups"]["byte_weighted"]
        if left["request_sha256"] != right["request_sha256"]:
            raise ValueError("Unit comparison request mismatch")
        ratios.append(left["latency_s"]["p95"] / right["latency_s"]["p95"])
    return {"paired_p95_speedup": summary(ratios), "faster_rounds": sum(r > 1 for r in ratios), "rounds": len(ratios)}


def generate(root):
    reports = {name: json.loads((root / f"{name}.json").read_text("utf-8"))
               for name in ("wine", "superconductivity", "qasper", "htru2") if (root / f"{name}.json").exists()}
    if not reports:
        raise ValueError("No unit reports")
    rows_all = [row for r in reports.values() for row in r["results"]]
    measured = sum(r["verified_measured_roundtrips"] for r in rows_all)
    warmups = sum(r["verified_warmup_roundtrips"] for r in rows_all)
    reads = sum(g["verified_requests"] for r in rows_all for t in r["range_trials"] for g in t["groups"].values())
    warm_reads = sum(g["verified_warmup_requests"] for r in rows_all for t in r["range_trials"] for g in t["groups"].values())
    text = f"""# v0.5.0 独立单元与完整索引成本

{len(reports)} 组原始科学输入、**{len(rows_all)} 个条件**；**{measured} 次正式完整恢复 + {warmups} 次预热恢复**，
**{reads:,} 次正式范围读取 + {warm_reads:,} 次查询预热**全部逐字节一致。
每次编码归档相同；实验前后源文件、递归源码和归档哈希一致。

默认仍写 v2。显式 unit_size 才写 v3：父块 1 MiB，单元 16/64 KiB，索引含每个
单元的原始 SHA-256、大小与编码标志。部分读校验索引/触及单元，完整恢复继续校验
父块与文件。不是通过跳过校验或丢弃原文获得速度。

下表体积包含全部 prefix、JSON、二进制索引和 payload。延迟是各轮 p95 的中位数，
不是置信区间；历史协议不同，以下均用本轮同源码、匹配请求对照。

## 超导材料 CSV：整块、直接小块与两层单元

"""
    rows = []
    if "superconductivity" in reports:
        report = reports["superconductivity"]
        for codec in ("zlib", "zstd"):
            for layout in ("flat-1024", "flat-64", "flat-16", "units-64", "units-16"):
                row = pick(report, layout, codec, "csv-columns-v1")
                storage = row["storage"]
                rows.append([codec, layout, storage["stored_bytes"], storage.get("unit_index_bytes", 0),
                             f'{row["encode_s"]["median"] * 1000:.1f}', f'{row["decode_s"]["median"] * 1000:.1f}',
                             f'{p95(row) * 1000:.3f}', f'{p95(row, "open_and_read") * 1000:.3f}',
                             f'{group(row)["decode_amplification"]["median"]:.1f}×'])
    text += table(["codec", "布局", "总 bytes", "其中单元索引 bytes", "编码 ms", "完整恢复 ms", "常驻 p95 ms", "重开 p95 ms", "逻辑解码放大"], rows)
    derived = []
    text += "\n## 两层单元相对直接小块\n\n同 codec/transform、同单元/扁平块大小；变换接受阈值的元数据成本可能不同。\n\n"
    rows = []
    for name, report in reports.items():
        codecs = ("zlib", "zstd") if name in ("wine", "superconductivity") else ("zstd",)
        transforms = ("none",) if name == "qasper" else ("none", "csv-columns-v1")
        sizes = (64,) if name == "htru2" else (64, 16)
        for codec in codecs:
            for transform in transforms:
                for size in sizes:
                    flat = pick(report, f"flat-{size}", codec, transform)
                    candidate = pick(report, f"units-{size}", codec, transform)
                    record = {"dataset": name, "codec": codec, "transform": transform, "unit_kib": size,
                              "archive_saving_vs_flat_same_size_pct": (1 - candidate["storage"]["stored_bytes"] / flat["storage"]["stored_bytes"]) * 100,
                              "baseline": f"flat-{size}", "candidate": f"units-{size}",
                              "open_reader": compare(flat, candidate, "open_reader"),
                              "open_and_read": compare(flat, candidate, "open_and_read")}
                    derived.append(record)
                    rows.append([name, codec, transform, size, f'{record["archive_saving_vs_flat_same_size_pct"]:.3f}%',
                                 f'{record["open_reader"]["paired_p95_speedup"]["median"]:.2f}×',
                                 f'{record["open_and_read"]["paired_p95_speedup"]["median"]:.2f}×',
                                 f'{record["open_and_read"]["faster_rounds"]}/{record["open_and_read"]["rounds"]}'])
    text += table(["数据", "codec", "变换", "单元 KiB", "对直接小块节省", "常驻 p95 加速", "重开 p95 加速", "重开更快轮数"], rows)
    text += "\n## 同时看普通编码\n\n超导材料/Zstd，避免只拿最慢的整块 CSV 作参照。\n\n"
    rows = []
    if "superconductivity" in reports:
        for transform in ("none", "csv-columns-v1"):
            for layout in ("flat-1024", "flat-64", "units-64", "units-16"):
                row = pick(reports["superconductivity"], layout, "zstd", transform)
                rows.append([transform, layout, row["storage"]["stored_bytes"], f'{row["decode_s"]["median"]*1000:.1f}',
                             f'{p95(row)*1000:.3f}', f'{p95(row,"open_and_read")*1000:.3f}',
                             f'{row["decode_peak_rss_bytes"]["median"]/1048576:.2f}'])
    text += table(["变换", "布局", "总 bytes", "完整恢复 ms", "常驻 p95 ms", "重开 p95 ms", "恢复峰值 MiB"], rows)
    text += "\n## 科学文本与缓存消融\n\nQASPER/Zstd/none；缓存设置仅改变范围读取，完整恢复用默认读取器。\n\n"
    rows = []
    if "qasper" in reports:
        for layout in ("flat-1024", "flat-64", "flat-16", "units-64", "units-16", "units-64-no-cache"):
            row = pick(reports["qasper"], layout)
            rows.append([layout, row["storage"]["stored_bytes"], row["storage"]["metadata_bytes"],
                         row["storage"].get("unit_index_bytes", 0), f'{p95(row)*1000:.3f}',
                         f'{p95(row,"open_and_read")*1000:.3f}'])
    text += table(["布局", "总 bytes", "prefix+JSON bytes", "单元索引 bytes", "常驻 p95 ms", "重开 p95 ms"], rows)
    text += """

## 解释与范围

独立单元减少整块反变换，二进制索引减少顶层 JSON 条目；这两项收益须分别和普通
小块对照。单元变小可能增加压缩损失，完整恢复仍读所有单元并多做索引/父块校验。
负结果必须保留。HTRU2 CR-only 仍回退，不将其当成 CSV 算法成功。

缓存是已校验的索引，预算计费不是硬 RSS；没有缓存恢复内容。未触及单元损坏可
不影响合法局部读取，完整 verify 则必须失败。单元摘要尚未用于跨父块去重/增量
共享，父块仍是复用粒度。本版不是追加式多版本 CAS，也没有 Rust 加速或推理数据。

范围 RSS 包含真值与独立工作账本读取器，不能当作生产读取器内存；完整恢复 RSS
单独记录。referenced_index_bytes 不是物理 IO 或实际索引未命中数量。单机温缓存，
五轮默认样本，不做显著性或全局最优结论；冷缓存/跨机器/跨日仍未测。
协议见 [UNITS.md](../../docs/UNITS.md)，格式见 [FORMAT.md](../../docs/FORMAT.md)。
"""
    (root / "SUMMARY.md").write_text(text, encoding="utf-8", newline="\n")
    (root / "derived-metrics.json").write_text(json.dumps(derived, indent=2) + "\n", encoding="utf-8", newline="\n")
    return reports, {"configurations": len(rows_all), "measured_roundtrips": measured, "warmup_roundtrips": warmups,
                     "verified_range_reads": reads, "verified_warmup_range_reads": warm_reads}


def plot(root, reports):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), layout="constrained")
    for ax, name, transform in ((axes[0], "superconductivity", "csv-columns-v1"), (axes[1], "qasper", "none")):
        if name not in reports:
            continue
        for family, layouts, color in (("Flat blocks", ("flat-16", "flat-64", "flat-1024"), "#b45309"),
                                       ("Two-level units", ("units-16", "units-64"), "#2563eb")):
            points = [pick(reports[name], layout, "zstd", transform) for layout in layouts]
            x = [r["storage"]["stored_bytes"]/1e6 for r in points]
            y = [p95(r,"open_and_read")*1000 for r in points]
            ax.plot(x,y,"o-",color=color,label=family)
            for px,py,layout in zip(x,y,layouts):
                ax.annotate(layout.replace("flat-", "F").replace("units-", "U"), (px,py), xytext=(4,6), textcoords="offset points",fontsize=9)
        ax.set_title(name.upper() + (" | CSV" if transform != "none" else " | Plain"))
        ax.set_xlabel("Complete archive (MB), indexes included")
        ax.set_ylabel("Reopen per request: round p95 median (ms)")
        ax.grid(alpha=0.2); ax.legend()
        ax.margins(x=0.2,y=0.2)
        ax.set_ylim(bottom=0)
    fig.suptitle("RKV-1 v0.5.0 | Zstd 3 | Warm cache | F=flat block KiB, U=unit KiB")
    fig.savefig(root/"unit-tradeoffs.png",dpi=160)
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
