"""Derive round-level comparisons and a plot from the v0.3 reading records."""
import argparse
import json
from pathlib import Path

from rkv1.benchmark import summary


def table(columns, rows):
    return ("| " + " | ".join(columns) + " |\n|" + "|".join("---" for _ in columns) + "|\n"
            + "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in rows) + "\n")


def select(report, codec, chunk):
    return next(r for r in report["results"] if r["configuration"]["compression"] == codec
                and r["configuration"]["chunk_size"] == chunk)


def group(row, mode, category="byte_weighted"):
    return row["aggregate"][mode]["groups"][category]


def paired_comparison(base, candidate, mode, category="byte_weighted"):
    originals = {(t["session"], t["round"]): t["groups"][category]
                 for t in base["trials"] if t["mode"] == mode}
    speedups = []
    for trial in candidate["trials"]:
        if trial["mode"] != mode:
            continue
        current = trial["groups"][category]
        old = originals[(trial["session"], trial["round"])]
        if current["latency_s"] is None:
            continue
        if category != "cross_chunk" and old["request_sha256"] != current["request_sha256"]:
            raise ValueError("Unmatched query plans in paired comparison")
        speedups.append(old["latency_s"]["p95"] / current["latency_s"]["p95"])
    return {"p95_speedup": summary(speedups), "faster_rounds": sum(s > 1 for s in speedups),
            "compared_rounds": len(speedups), "queries_identical": category != "cross_chunk"}


def generate(root):
    reports = {p.stem: json.loads(p.read_text("utf-8")) for p in sorted(root.glob("*.json"))
               if p.stem in ("scifact", "qasper")}
    if not reports:
        raise ValueError("No reading reports")
    trials = sum(len(row["trials"]) for report in reports.values() for row in report["results"])
    verified = sum(g["verified_requests"] for report in reports.values() for row in report["results"]
                   for trial in row["trials"] for g in trial["groups"].values())
    warmups = sum(g["verified_warmup_requests"] for report in reports.values() for row in report["results"]
                  for trial in row["trials"] for g in trial["groups"].values())
    configs = sum(len(r["results"]) for r in reports.values())
    protocol = next(iter(reports.values()))["protocol"]
    rounds = protocol["sessions"] * protocol["rounds_per_session"]
    queries = protocol["queries_per_available_group_per_round"]
    query_warmups = protocol["warmup_queries_per_group"]
    for report in reports.values():
        if report["protocol"] != protocol:
            raise ValueError("Summary requires one common reading protocol")
    text = f"""# v0.3.0 多轮读取评测

本轮推进 E0 读取协议，未改变 RKV v2 格式、codec 默认值或 E2 变换。
共 {len(reports)} 组科学文本、**{configs} 个配置、{trials} 个独立 worker**；
**{verified:,} 次正式范围读取 + {warmups:,} 次预热读取**全部逐字节一致。
每个归档先完整校验，实验前后核对输入、实现指纹与归档哈希。

每配置 {protocol['sessions']} 个连续批次，每批 {protocol['rounds_per_session']} 个不同查询种子；同一轮的非跨块请求在 codec、块大小和
打开模式之间完全相同。每个可用类别 {queries} 次正式请求和 {query_warmups} 次查询预热；执行顺序交错
打乱，每轮/模式独立进程，计时前预读完整归档。具体参数以各 JSON protocol 为准。
本机温缓存；冷缓存、跨机器、跨日、成熟 seekable 系统和推理质量均未测，记录为 null。

下表延迟是 **{rounds} 轮各自 p95 的中位数**，括号是这 {rounds} 个 p95 的最小–最大值；
不是置信区间，也不是将全部请求合并后的 p95。旧版只有单批查询，不能直接把两版
延迟变化归为代码优化。归档格式/数据未变，体积应与旧版对应条件一致。

## Zstd 分块与读取器生命周期

"""
    rows = []
    derived = []
    for name, report in reports.items():
        base = select(report, "zstd", 1048576)
        for chunk in (65536, 262144, 1048576):
            row = select(report, "zstd", chunk)
            values = []
            for mode in ("open_reader", "open_and_read"):
                stats = group(row, mode)["round_p95_s"]
                values.append(f'{stats["median"] * 1000:.3f} ({stats["min"] * 1000:.3f}–{stats["max"] * 1000:.3f})')
                derived.append({"dataset": name, "codec": "zstd", "chunk_size": chunk, "mode": mode,
                                "archive_increase_pct": (row["storage"]["stored_bytes"] / base["storage"]["stored_bytes"] - 1) * 100,
                                "baseline_chunk_size": 1048576,
                                **paired_comparison(base, row, mode)})
            rows.append([name, chunk // 1024, row["storage"]["stored_bytes"],
                         f'{(row["storage"]["stored_bytes"] / base["storage"]["stored_bytes"] - 1) * 100:.2f}%', *values])
    text += table(["数据", "块 KiB", "归档 bytes", "比 1 MiB 增大", "常驻 p95 ms 中位数（范围）", "每次重开 p95 ms 中位数（范围）"], rows)
    text += "\n同种子逐轮比较（倍率 >1 为候选更快；不做显著性判定）：\n\n"
    text += table(["数据", "块 KiB", "模式", "对 1 MiB p95 加速中位数", "更快轮数/总轮数"],
                  [[r["dataset"], r["chunk_size"] // 1024, r["mode"],
                    f'{r["p95_speedup"]["median"]:.2f}×', f'{r["faster_rounds"]}/{r["compared_rounds"]}']
                   for r in derived if r["chunk_size"] != 1048576])
    text += "\n## 同容器 codec 对照\n\n1 MiB，无变换，包含相同块校验。\n\n"
    rows = []
    for name, report in reports.items():
        for codec in ("raw", "zlib", "zstd"):
            row = select(report, codec, 1048576)
            rows.append([name, codec, row["storage"]["stored_bytes"],
                         f'{group(row, "open_reader")["round_p95_s"]["median"] * 1000:.3f}',
                         f'{group(row, "open_and_read")["round_p95_s"]["median"] * 1000:.3f}'])
    text += table(["数据", "codec", "归档 bytes", "常驻 p95 ms", "重开 p95 ms"], rows)
    text += "\n## 打开成本与解码放大\n\n"
    rows = []
    for name, report in reports.items():
        for chunk in (65536, 262144, 1048576):
            row = select(report, "zstd", chunk)
            stats = group(row, "open_and_read")
            rows.append([name, chunk // 1024, row["storage"]["metadata_bytes"],
                         f'{stats["round_open_median_s"]["median"] * 1000:.3f}',
                         f'{stats["round_read_median_s"]["median"] * 1000:.3f}',
                         f'{stats["decode_amplification"]["median"]:.1f}×'])
    text += table(["数据", "块 KiB", "容器元数据 bytes", "每次打开中位 ms", "范围读阶段中位 ms", "逻辑解码字节/请求字节"], rows)
    text += """
打开阶段包括文件打开、清单读取/哈希/解析/结构检查以及路径索引建立；并非只测 JSON。
工作账本按触及的块原始/压缩字节计算，不能解释成物理磁盘读取量；进程内存包含
解释器、codec、预先准备的查询真值和临时块，不与旧版完整恢复进程 RSS 直接比较。

## 本轮可以支持的决策

块大小必须结合读取器生命周期与空间预算判断。报告逐轮稳定性，不根据单次 p95
改默认策略。冷缓存/跨机器保持未测；本轮不宣布通用最优或推理质量提升。
下一步仍为 E2：独立数值数据、反变换与块内访问性能分析；Rust 迁移须有热点证据。
完整脚本和协议见 [READING.md](../../docs/READING.md)，旧结果保留。
"""
    (root / "SUMMARY.md").write_text(text, encoding="utf-8", newline="\n")
    (root / "derived-metrics.json").write_text(json.dumps(derived, indent=2) + "\n", encoding="utf-8", newline="\n")
    return reports, {"configurations": configs, "worker_trials": trials,
                     "verified_measured_range_reads": verified, "verified_warmup_range_reads": warmups}


def plot(root, reports):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(reports), figsize=(7 * len(reports), 4.8), squeeze=False, layout="constrained")
    for ax, (name, report) in zip(axes[0], reports.items()):
        chunks = (65536, 262144, 1048576)
        for mode, label, color in (("open_reader", "Persistent reader", "#2563eb"),
                                   ("open_and_read", "Reopen per request", "#b45309")):
            stats = [group(select(report, "zstd", chunk), mode)["round_p95_s"] for chunk in chunks]
            y = [s["median"] * 1000 for s in stats]
            errors = [[(s["median"] - s["min"]) * 1000 for s in stats],
                      [(s["max"] - s["median"]) * 1000 for s in stats]]
            ax.errorbar(range(3), y, yerr=errors, label=label, color=color, marker="o", capsize=5)
        ax.set_xticks(range(3), ["64 KiB", "256 KiB", "1 MiB"])
        ax.set_title(name.upper() + " | Zstd 3")
        ax.set_ylabel("Round p95 (ms): median and min-max")
        ax.set_xlabel("Block size")
        ax.grid(alpha=0.2)
        ax.legend()
        ax.set_ylim(bottom=0)
    protocol = next(iter(reports.values()))["protocol"]
    rounds = protocol["sessions"] * protocol["rounds_per_session"]
    fig.suptitle(f"RKV-1 v0.3.0 | Warm archive | {rounds} rounds | Ranges are not confidence intervals")
    fig.savefig(root / "reading.png", dpi=160)
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
