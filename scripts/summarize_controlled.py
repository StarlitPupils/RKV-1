"""Summarize raw controlled JSON records; optionally render a scientific plot."""
import argparse
import json
from pathlib import Path


def load(root, name):
    return json.loads((root / f"{name}.json").read_text("utf-8"))


def select(report, codec="zstd", chunk=1048576, transform="none", dedup=True):
    return next(row for row in report["results"] if row["configuration"]["compression"] == codec
                and row["configuration"]["chunk_size"] == chunk and row["configuration"]["transform"] == transform
                and row["configuration"]["deduplicate"] == dedup)


def p95(row, group="byte_weighted"):
    sample = row["range_reads"]["ranges"]["open_reader"][group]["latency_s"]
    return sample["p95"] * 1000 if sample else None


def table(columns, rows):
    return "| " + " | ".join(columns) + " |\n|" + "|".join("---" for _ in columns) + "|\n" + "\n".join(
        "| " + " | ".join(str(value) for value in row) + " |" for row in rows) + "\n"


def generate(root):
    reports = {name: load(root, name) for name in ("uci", "scifact", "qasper", "wine", "synthetic-duplicates")}
    incremental = load(root, "incremental")
    derived = []
    for name, report in reports.items():
        for row in report["results"]:
            raw = report["raw_file_bytes"]
            derived.append({"dataset": name, "configuration": row["configuration"],
                            "stored_bits": row["storage"]["stored_bytes"] * 8,
                            "compression_ratio": raw / row["storage"]["stored_bytes"],
                            "encode_mib_s": raw / 1048576 / row["encode_s"]["median"],
                            "decode_mib_s": raw / 1048576 / row["decode_s"]["median"],
                            "basis": f"{name}.json medians; calculated, not additional measurements"})
    (root / "derived-metrics.json").write_text(json.dumps(derived, indent=2) + "\n", encoding="utf-8", newline="\n")
    configs = sum(len(report["results"]) for report in reports.values())
    measured = sum(r["verified_measured_roundtrips"] for report in reports.values() for r in report["results"])
    warmups = sum(r["verified_warmup_roundtrips"] for report in reports.values() for r in report["results"])
    measured += sum(r["verified_measured_roundtrips"] for case in incremental["results"] for r in case["runs"].values())
    warmups += sum(r["verified_warmup_roundtrips"] for case in incremental["results"] for r in case["runs"].values())
    ranges = sum(group["verified_requests"] for report in reports.values() for row in report["results"]
                 for groups in row["range_reads"]["ranges"].values() for group in groups.values())
    env = reports["scifact"]["environment"]
    protocol = reports["scifact"]["protocol"]
    version = reports["scifact"]["rkv1_version"]
    text = f"""# v0.2.0 受控实验与 E2 CSV 试验

环境：{env['platform']}；{env['processor']}；Python {env['python']}。
记录版本 {version}；详细主机信息见 environment.json（如提供）。
四组真实输入（UCI、SciFact、QASPER、Wine）和一组合成重复输入；UCI/Wine 共享 red CSV，
不能视为四个完全独立数据源。QASPER 原始 JSON 合计 {reports['qasper']['raw_file_bytes']:,} bytes。

共 **{configs} 个配置**；**{measured} 次记录恢复 + {warmups} 次预热恢复**，
**{ranges:,} 次范围读取**全部逐字节验证通过。每配置记录 {protocol['repeats']} 次完整运行；
每个可用查询类别 {protocol['queries_per_available_group']} 次，并分别记录已打开清单与每次重新打开两种模式。

所有方法使用相同 RKV v2 容器、校验与 flush/fsync/原子发布流程。三个阶段独立进程
记录内存。全部输入哈希、样本、参数和各查询类别见 JSON；[协议](../../docs/EXPERIMENTS.md)。
总存储位数、压缩倍率和编码/恢复 MiB/s 由原始记录计算，见 [derived-metrics.json](derived-metrics.json)。

## 同容器主对照

1 MiB 分块、去重开启、无可逆变换。归档总 bytes 含全部元数据；延迟为温 OS 缓存下
按输入文件字节数加权的请求。编码/恢复为 {protocol['repeats']} 次中位数；内存为恢复进程峰值的中位数。

"""
    rows = []
    for name in ("uci", "scifact", "qasper", "wine"):
        report = reports[name]
        for codec in ("zlib", "zstd"):
            row = select(report, codec)
            rows.append([name, codec, row["storage"]["stored_bytes"],
                         round(report["raw_file_bytes"] / row["storage"]["stored_bytes"], 3),
                         round(row["encode_s"]["median"] * 1000, 3), round(row["decode_s"]["median"] * 1000, 3),
                         round(p95(row), 4), round(row["decode_peak_rss_bytes"]["median"] / 1048576, 2)])
    text += table(["输入", "codec", "归档 bytes", "倍率", "编码 ms", "恢复 ms", "随机读 p95 ms", "恢复峰值 MiB"], rows)
    for name in ("scifact", "qasper"):
        a, b = select(reports[name], "zlib"), select(reports[name], "zstd")
        saving = (1 - b["storage"]["stored_bytes"] / a["storage"]["stored_bytes"]) * 100
        memory_saving = (1 - b["decode_peak_rss_bytes"]["median"] / a["decode_peak_rss_bytes"]["median"]) * 100
        text += f"\n{name}：同条件 Zstd 的归档节省 {saving:.2f}%；编码加速 {a['encode_s']['median'] / b['encode_s']['median']:.2f}×；恢复加速 {a['decode_s']['median'] / b['decode_s']['median']:.2f}×；恢复进程峰值减少 {memory_saving:.2f}%。\n"
    text += "不同语料与 codec 的结果须分别判断。v0.1.0 与整流 TAR 的内存差距受持有完整缓冲和流式布局影响，不能归于 Zstd 算法固有内存。\n"
    text += "\n## 分块取舍\n\nZstd、去重开启、无变换。小块降低解码放大，但增加压缩损失和索引开销。\n\n"
    rows = []
    for name in ("scifact", "qasper"):
        report = reports[name]
        base = select(report)
        for chunk in (65536, 262144, 1048576):
            row = select(report, chunk=chunk)
            rows.append([name, chunk // 1024, row["storage"]["stored_bytes"],
                         round((row["storage"]["stored_bytes"] / base["storage"]["stored_bytes"] - 1) * 100, 2),
                         round(p95(row), 4), round(p95(row, "cross_chunk"), 4)])
    text += table(["输入", "块 KiB", "归档 bytes", "较 1 MiB 增大 %", "加权读 p95 ms", "跨块读 p95 ms"], rows)
    text += "\n小块/大块的选择须结合实际查询工作负载；本版保留参数，不将某个配置宣称为全局最优。\n"
    text += "\n## E2：CSV 可逆列重排\n\n同 codec、同 1 MiB 分块，与 transform=none 比较。保存数值原文、表头和换行。\n\n"
    rows = []
    for name in ("uci", "wine"):
        report = reports[name]
        for codec in ("zlib", "zstd"):
            base, row = select(report, codec), select(report, codec, transform="csv-columns-v1")
            rows.append([name, codec, base["storage"]["stored_bytes"], row["storage"]["stored_bytes"],
                         round((1 - row["storage"]["stored_bytes"] / base["storage"]["stored_bytes"]) * 100, 3),
                         round(row["encode_s"]["median"] / base["encode_s"]["median"], 2),
                         round(row["decode_s"]["median"] / base["decode_s"]["median"], 2),
                         round(p95(row) / p95(base), 2)])
    text += table(["输入", "codec", "普通 bytes", "列重排 bytes", "总字节节省 %", "编码耗时倍数", "恢复耗时倍数", "随机读 p95 倍数"], rows)
    text += "\n上表同时记录完整归档节省与执行代价；应以全部指标决定是否启用。策略保持可选，未列为默认综合优化。\n"
    text += "每块也会尝试普通编码，收益不够时回退；完整容器成本已计入，模型/外部字典/语义索引均未引入。\n"
    text += "所有 v2 对照部署同一份 RKV/transform 源码，源码成本在该条件下共有；与删掉变换功能的最小部署比较时仍需单独核算。\n"
    text += "[runtime-footprint.json](runtime-footprint.json) 记录本机 RKV 源码、变换模块与可选 Zstd 安装占用；归档字节不是完整部署大小。\n"
    footprint_path = root / "runtime-footprint.json"
    if footprint_path.exists():
        import math
        footprint = json.loads(footprint_path.read_text("utf-8"))
        if footprint["zstandard"]:
            extra = footprint["zstandard"]["installed_distribution_bytes"]
            text += f"\n本机额外 Zstd distribution 占 {extra:,} bytes。若它专门为本项目安装、共享一次，且每对象独立写完整归档，\n"
            counts = []
            for name in ("scifact", "qasper"):
                saving = select(reports[name], "zlib")["storage"]["stored_bytes"] - select(reports[name], "zstd")["storage"]["stored_bytes"]
                counts.append(f"{name} 约 {math.floor(extra / saving) + 1} 个对象")
            text += "按本次体积差需至少 " + "、".join(counts) + " 才抵消该安装占用。这是条件成本计算，不是新增压缩实测，\n"
            text += "也不包含 Python/所有共享原生依赖；若 Zstd 已因其他用途存在，则新增安装边际成本可为零。\n"
    text += f"\n## 增量复用\n\nSciFact、Zstd、1 MiB；每种模式 {incremental['warmups']} 次预热 + {incremental['repeats']} 次记录，中位数如下。\n\n"
    rows = []
    for case in incremental["results"]:
        full, reuse = case["runs"]["full"], case["runs"]["reuse"]
        rows.append([case["case"], f'{reuse["storage"]["reused_chunks"]}/{reuse["storage"]["unique_chunks"]}',
                     round(full["encode_s"]["median"] * 1000, 3), round(reuse["encode_s"]["median"] * 1000, 3),
                     round(full["encode_s"]["median"] / reuse["encode_s"]["median"], 3), reuse["storage"]["stored_bytes"]])
    text += table(["改动", "复用块", "完整编码 ms", "复用编码 ms", "加速倍数", "新快照 bytes"], rows)
    factors = [case["runs"]["full"]["encode_s"]["median"] / case["runs"]["reuse"]["encode_s"]["median"] for case in incremental["results"]]
    text += f"\n本次复用加速范围 {min(factors):.2f}–{max(factors):.2f}×。各场景复用比例与耗时应独立判断，不能由旧版单次小文件探针外推。\n"
    text += "所有模式都读取源文件并写完整独立快照，尚未实现追加式多版本存储。\n"
    text += "\n## 去重与边界\n\n"
    natural_duplicates = sum(r["storage"]["chunk_references"] - r["storage"]["unique_chunks"]
                             for name in ("uci", "scifact", "qasper", "wine") for r in reports[name]["results"]
                             if r["configuration"]["deduplicate"] and r["configuration"]["transform"] == "none")
    text += f"真实输入各无变换/去重配置的重复块引用合计 {natural_duplicates} 次（按配置累计）。合成对照必须与无去重的同容器条件比较；\n"
    text += "没有重复块时，开关差异主要来自 block id 元数据。\n"
    text += "单机、温缓存、后台负载未隔离；重新打开清单不等于冷磁盘。没有神经压缩、问答、检索或推理质量结果。\n"
    text += "E2 当前仅数值 CSV 原型；科学数组、代码、数学文本仍待开展。旧版数据/Release 不覆盖。\n"
    (root / "SUMMARY.md").write_text(text, encoding="utf-8", newline="\n")
    return reports


def plot(root, reports):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.6), layout="constrained")
    for ax, name in zip(axes[:2], ("scifact", "qasper")):
        points = [select(reports[name], chunk=chunk) for chunk in (65536, 262144, 1048576)]
        x = [r["storage"]["stored_bytes"] / 1e6 for r in points]
        y = [p95(r) for r in points]
        ax.plot(x, y, "o-", color="#2563eb", linewidth=2, markersize=7)
        for px, py, size in zip(x, y, ("64 KiB", "256 KiB", "1 MiB")):
            ax.annotate(size, (px, py), xytext=(5, 8), textcoords="offset points", fontsize=10)
        ax.set_title(f"{name.upper()}: Zstd block sizes", fontweight="bold")
        ax.set_xlabel("Complete archive (MB)")
        ax.set_ylabel("Warm weighted-read p95 (ms)")
        ax.grid(alpha=0.2)
        ax.margins(x=0.2, y=0.25)
    labels, savings, slowdown = [], [], []
    for name in ("uci", "wine"):
        for codec in ("zlib", "zstd"):
            a, b = select(reports[name], codec), select(reports[name], codec, transform="csv-columns-v1")
            labels.append(name.upper() + "\n" + codec)
            savings.append((1 - b["storage"]["stored_bytes"] / a["storage"]["stored_bytes"]) * 100)
            slowdown.append(b["decode_s"]["median"] / a["decode_s"]["median"])
    axes[2].bar(labels, savings, color="#0f766e", width=0.62)
    for index, (saving, factor) in enumerate(zip(savings, slowdown)):
        axes[2].text(index, saving + 0.15, f"{saving:.2f}%\ndecode {factor:.1f}x", ha="center", fontsize=9, color="#92400e")
    axes[2].set_title("CSV: size gain vs decode cost", fontweight="bold")
    axes[2].set_ylabel("Complete archive saving (%)")
    axes[2].set_ylim(0, 6.4)
    axes[2].grid(axis="y", alpha=0.2)
    fig.suptitle("RKV-1 v0.2.0 | Same container, checksums and fsync | CPU measurements", fontsize=12)
    fig.savefig(root / "tradeoffs.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    reports = generate(args.directory)
    if args.plot:
        plot(args.directory, reports)
