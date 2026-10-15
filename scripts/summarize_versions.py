"""Separate representation, physical object sharing, CDC, and access costs."""
import argparse
import json
from pathlib import Path

from rkv1.benchmark import summary
from scripts.summarize_units import table


def p95(version, mode):
    return version["range_aggregate"][mode]["groups"]["byte_weighted"]["round_p95_s"]["median"]


def total_restore(row):
    by_round = {}
    for version in row["versions"]:
        for trial in version["restore_trials"]:
            if trial["round"] >= 0:
                by_round[trial["round"]] = by_round.get(trial["round"], 0) + trial["wall_s"]
    return summary(list(by_round.values()))


def generate(root):
    report = json.loads((root / "qasper-versions.json").read_text("utf-8"))
    rows = {r["configuration"]["name"]: r for r in report["results"]}
    measured = sum(sum(t["round"] >= 0 for t in v["restore_trials"]) for r in rows.values() for v in r["versions"])
    warmups = sum(sum(t["round"] < 0 for t in v["restore_trials"]) for r in rows.values() for v in r["versions"])
    reads = sum(g["verified_requests"] for r in rows.values() for v in r["versions"] for t in v["range_trials"] for g in t["groups"].values())
    warm_reads = sum(g["verified_warmup_requests"] for r in rows.values() for v in r["versions"] for t in v["range_trials"] for g in t["groups"].values())
    counts = {"configurations": len(rows), "versions": len(report["files_by_version"]),
              "measured_roundtrips": measured, "warmup_roundtrips": warmups,
              "verified_range_reads": reads, "verified_warmup_range_reads": warm_reads}
    derived = {"counts": counts, "conditions": {}, "sharing_comparisons": [], "cdc_comparisons": []}
    text = f"""# v0.7.0 原始版本序列、共享 CAS 与 Gear CDC

QASPER 官方 train/dev v0.1→v0.2→v0.3，三次原始发布、同一语料家族。
原文件名/原文字节均保留，不重序列化 JSON；合计原文 **{report['raw_bytes_all_versions']:,} bytes**。
**{len(rows)} 个条件、{measured} 次正式完整恢复 + {warmups} 次预热恢复，
{reads:,} 次正式范围读取 + {warm_reads:,} 次查询预热全部逐字节一致**。
每轮全存储树字节指纹一致；输入/源码/读取前后存储树哈希一致。

全部 Zstd3、无 CSV/原生后端/模型/字典。fixed为固定边界；gear-v1 的64KiB是mask
scale，不是实际平均长度，也不是FastCDC复现。独立/共享 CAS 同边界下对象文件
字节的并集相同、快照ID相同，分离“新格式”和“跨版本共享”的影响。

## 三个版本的总成本

logical计入每个对象84byte头/双摘要/payload、全部快照/config及未引用对象。
allocated为文件数据分配空间，不含完整目录/MFT/日志成本；文件数一并报告。
提交为三版总耗时，含共享初始化；恢复为三个独立进程恢复耗时之和，再取轮次中位。
范围为最后版本的各轮p95中位数。存储扫描/分配空间统计不计入提交wall。
logical/file count每轮一致；allocated表内取第0正式轮审计值，各轮原始值保留。

"""
    table_rows = []
    for name in sorted(rows):
        row = rows[name]; storage = row["storage"]
        logical, allocated = storage["logical_file_bytes"], storage["allocated_file_data_bytes"]
        restoration = total_restore(row)
        item = {"logical_file_bytes": logical, "allocated_file_data_bytes": allocated, "files": storage["files"],
                "sequence_add_s": row["sequence_add_s"], "three_snapshot_restore_s": restoration,
                "last_snapshot_open_reader_p95_s": p95(row["versions"][-1], "open_reader"),
                "last_snapshot_open_and_read_p95_s": p95(row["versions"][-1], "open_and_read")}
        derived["conditions"][name] = item
        table_rows.append([name, logical, allocated, storage["files"], f'{row["sequence_add_s"]["median"]:.3f}',
                           f'{restoration["median"]:.3f}', f'{item["last_snapshot_open_reader_p95_s"]*1000:.3f}',
                           f'{item["last_snapshot_open_and_read_p95_s"]*1000:.3f}'])
    text += table(["条件", "总logical bytes", "allocated数据 bytes", "文件数", "三版提交 s", "三版恢复 s", "v0.3常驻p95 ms", "v0.3重开p95 ms"], table_rows)
    text += "\n## 同格式的跨版本共享收益\n\n相同分块/profile，同编码对象字节；累计共享收益包含少写两份config，原始成本也完整列出。\n\n"
    table_rows = []
    for suffix in ("fixed-64", "fixed-1024", "gear-v1-64"):
        isolated, shared = rows["isolated-" + suffix], rows["shared-" + suffix]
        a, b = isolated["storage"], shared["storage"]
        record = {"profile": suffix, "isolated_logical_bytes": a["logical_file_bytes"], "shared_logical_bytes": b["logical_file_bytes"],
                  "logical_saving_bytes": a["logical_file_bytes"] - b["logical_file_bytes"],
                  "logical_saving_pct": 100 * (1 - b["logical_file_bytes"] / a["logical_file_bytes"]),
                  "allocated_saving_pct": 100 * (1 - b["allocated_file_data_bytes"] / a["allocated_file_data_bytes"])
                  if a["allocated_file_data_bytes"] and b["allocated_file_data_bytes"] is not None else None}
        derived["sharing_comparisons"].append(record)
        table_rows.append([suffix, record["isolated_logical_bytes"], record["shared_logical_bytes"], record["logical_saving_bytes"],
                           f'{record["logical_saving_pct"]:.3f}%', f'{record["allocated_saving_pct"]:.3f}%' if record["allocated_saving_pct"] is not None else "未测"])
    text += table(["边界", "独立CAS bytes", "共享CAS bytes", "节省 bytes", "logical节省", "allocated数据节省"], table_rows)
    text += "\n## 每版新增写入与严格跨版本复用\n\n下表复用为“本版独特对象中已存在于更早版本的比例”，由同表示的独立CAS对照计算，排除本版内部重复。\n\n"
    table_rows = []
    for suffix in ("fixed-64", "fixed-1024", "gear-v1-64"):
        isolated, shared = rows["isolated-" + suffix], rows["shared-" + suffix]
        for v, version in enumerate(shared["versions"]):
            current, alone = version["stats"], isolated["versions"][v]["stats"]
            reuse = 100 * (1 - current["new_objects"] / alone["new_objects"]) if alone["new_objects"] else 0
            reuse_raw = 100 * (1 - current["new_raw_bytes"] / alone["new_raw_bytes"]) if alone["new_raw_bytes"] else 0
            record = {"profile": suffix, "version": ["0.1", "0.2", "0.3"][v], "new_objects": current["new_objects"],
                      "new_written_bytes": current["new_written_bytes"], "unique_objects_reused_from_previous_pct": reuse,
                      "unique_raw_bytes_reused_from_previous_pct": reuse_raw, "observed_chunk_sizes": summary(current["chunk_sizes"])}
            derived["sharing_comparisons"][next(i for i,x in enumerate(derived["sharing_comparisons"]) if x["profile"] == suffix)].setdefault("versions", []).append(record)
            table_rows.append([suffix, record["version"], current["new_objects"], current["new_written_bytes"],
                               f'{reuse:.2f}%', f'{reuse_raw:.2f}%',
                               f'{sum(current["chunk_sizes"])/len(current["chunk_sizes"]):.0f}' if current["chunk_sizes"] else 0])
    text += table(["边界", "版本", "新增对象", "新增对象+快照 bytes", "跨版对象复用", "跨版独特原文复用", "实际平均块 bytes"], table_rows)
    text += "\n## CDC 相对固定边界\n\n相同CAS格式与共享方式；nominal64KiB不等于实际平均一致，不能将全部差异归于单一边界因素。\n\n"
    table_rows = []
    for kind in ("isolated", "shared"):
        fixed, gear = rows[kind + "-fixed-64"], rows[kind + "-gear-v1-64"]
        record = {"kind": kind, "logical_saving_vs_fixed64_pct": 100 * (1 - gear["storage"]["logical_file_bytes"] / fixed["storage"]["logical_file_bytes"]),
                  "sequence_add_time_ratio_gear_over_fixed": gear["sequence_add_s"]["median"] / fixed["sequence_add_s"]["median"],
                  "three_restore_time_ratio_gear_over_fixed": total_restore(gear)["median"] / total_restore(fixed)["median"]}
        derived["cdc_comparisons"].append(record)
        table_rows.append([kind, f'{record["logical_saving_vs_fixed64_pct"]:.3f}%', f'{record["sequence_add_time_ratio_gear_over_fixed"]:.2f}×',
                           f'{record["three_restore_time_ratio_gear_over_fixed"]:.2f}×'])
    text += table(["方式", "Gear logical节省", "Gear/固定提交耗时", "Gear/固定恢复耗时"], table_rows)
    text += """

## 解释与范围

只有共享CAS对独立同格式CAS的差异可直接归于复用/共享配置成本。旧RKV和CAS
布局/对象校验/文件数不同；CAS结果不能单独说明编码器或hash本身更快。
所有来源仍全量扫描/哈希，复用旧对象前验证；新写入少不保证提交更快。
Gear Python循环、更多小文件与对象校验均可能增加CPU/IO成本，保留负结果。

分配空间仅测文件数据extent，目录/MFT resident/日志/公共运行时未全额分配。
本机温缓存、五轮描述统计；一个语料家族的三版，不声称显著性或通用CDC最优。
CAS无GC、失败提交可留计费的orphan、没有断电耐久性证明。范围RSS包含真值、
预读对象清单/元数据和工作账本，编码RSS含未计时存储审计，不当作生产RSS。
冷缓存/跨机器/跨日、神经预测和科学推理质量未测。

原始结果 qasper-versions.json，数据固定指纹 dataset-provenance.json；协议见
[STORE.md](../../docs/STORE.md)，旧格式及默认归档行为保持兼容。
"""
    (root / "SUMMARY.md").write_text(text, encoding="utf-8", newline="\n")
    (root / "derived-metrics.json").write_text(json.dumps(derived, indent=2) + "\n", encoding="utf-8", newline="\n")
    return rows, counts


def plot(root, rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = sorted(rows)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    x = list(range(len(names)))
    axes[0].bar([n-.18 for n in x], [rows[n]["storage"]["logical_file_bytes"]/1e6 for n in names], width=.36, label="Logical file bytes")
    if all(rows[n]["storage"]["allocated_file_data_bytes"] is not None for n in names):
        axes[0].bar([n+.18 for n in x], [rows[n]["storage"]["allocated_file_data_bytes"]/1e6 for n in names], width=.36, label="Allocated data extents")
    labels = [n.replace("archive-fixed-", "RKV F").replace("isolated-fixed-", "Isolated F")
              .replace("shared-fixed-", "Shared F").replace("isolated-gear-v1-", "Isolated Gear")
              .replace("shared-gear-v1-", "Shared Gear") for n in names]
    axes[0].set_xticks(x, labels, rotation=35, ha="right")
    axes[0].set_ylabel("Three versions total (decimal MB)"); axes[0].legend(); axes[0].grid(axis="y", alpha=.2)
    for suffix, label in (("fixed-1024", "Fixed 1 MiB"), ("fixed-64", "Fixed 64 KiB"), ("gear-v1-64", "Gear scale 64 KiB")):
        row = rows["shared-"+suffix]
        axes[1].plot([1,2,3],[v["storage_after_version"]["logical_file_bytes"]/1e6 for v in row["versions"]], "o-",label=label)
    axes[1].set_xticks([1,2,3], ["v0.1", "v0.2", "v0.3"]); axes[1].set_ylabel("Shared CAS cumulative logical bytes (MB)")
    axes[1].set_ylim(bottom=0); axes[1].legend(); axes[1].grid(alpha=.2)
    fig.suptitle("RKV-1 v0.7.0 | QASPER original releases | Zstd 3 | Filesystem metadata not fully counted")
    fig.savefig(root/"version-storage.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("directory", type=Path); parser.add_argument("--plot", action="store_true")
    args = parser.parse_args(); rows, counts = generate(args.directory); print(json.dumps(counts))
    if args.plot: plot(args.directory, rows)
