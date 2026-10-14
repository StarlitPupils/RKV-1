"""Derived matched-backend metrics and deployment-aware scientific figure."""
import argparse
import json
import math
from pathlib import Path

from rkv1.benchmark import summary
from scripts.summarize_units import compare, p95, table


def pick(report, layout, codec, transform, backend):
    return next(r for r in report["results"] if r["configuration"]["layout"] == layout
                and r["configuration"]["compression"] == codec and r["configuration"]["transform"] == transform
                and r["configuration"]["decoder_backend"] == backend)


def restoration_compare(base, candidate):
    left = {t["round"]: t for t in base["restore_trials"] if t["round"] >= 0}
    ratios = [left[t["round"]]["wall_s"] / t["wall_s"] for t in candidate["restore_trials"] if t["round"] >= 0]
    return {"paired_wall_speedup": summary(ratios), "faster_rounds": sum(r > 1 for r in ratios), "rounds": len(ratios)}


def generate(root):
    reports = {name: json.loads((root / f"{name}.json").read_text("utf-8"))
               for name in ("wine", "superconductivity", "htru2") if (root / f"{name}.json").exists()}
    if not reports:
        raise ValueError("No native reports")
    all_rows = [row for report in reports.values() for row in report["results"]]
    provenance = next(iter(reports.values()))["native_provenance"]
    cost = provenance["bytes"] + provenance["metadata_bytes"]
    if any(report["native_provenance"] != provenance for report in reports.values()):
        raise ValueError("Unmatched native binaries")
    counts = {"configurations": len(all_rows), "archives": len(all_rows) // 2,
              "measured_roundtrips": sum(r["verified_measured_roundtrips"] for r in all_rows),
              "warmup_roundtrips": sum(r["verified_warmup_roundtrips"] for r in all_rows),
              "verified_range_reads": sum(g["verified_requests"] for r in all_rows for t in r["range_trials"] for g in t["groups"].values()),
              "verified_warmup_range_reads": sum(g["verified_warmup_requests"] for r in all_rows for t in r["range_trials"] for g in t["groups"].values())}
    text = f"""# v0.6.0 Rust 精确反变换：同归档后端对照

{len(reports)} 组原始科学输入、{counts['archives']} 份归档、**{counts['configurations']} 个读取条件**。
**{counts['measured_roundtrips']} 次正式完整恢复 + {counts['warmup_roundtrips']} 次预热恢复**，
**{counts['verified_range_reads']:,} 次正式范围读取 + {counts['verified_warmup_range_reads']:,} 次查询预热**全部逐字节一致。
同一个归档用于两个后端；编码两次确定性一致。输入/递归 Python 源码/归档/DLL/元数据
前后哈希一致。Rust 只替换 CSV 反变换，完整性校验保持相同。

本机 CPU、温缓存、五次默认重复。表内延迟是每轮 p95 的中位数；配对加速为对应
轮次比值的中位数，两者不是同一统计量。不构造置信区间或显著性结论。
完整恢复含库身份检查/加载、FFI 和复制；预热范围请求不含进程首次加载。

## CSV：Python → Rust

"""
    backend_rows, derived = [], []
    for name, report in reports.items():
        csv_python = [r for r in report["results"] if r["configuration"]["transform"] == "csv-columns-v1"
                      and r["configuration"]["decoder_backend"] == "python"]
        csv_python.sort(key=lambda r: (r["configuration"]["compression"], r["configuration"]["layout"]))
        for python in csv_python:
            config = python["configuration"]
            rust = pick(report, config["layout"], config["compression"], config["transform"], "rust")
            plain = pick(report, config["layout"], config["compression"], "none", "python")
            if python["storage"] != rust["storage"]:
                raise ValueError("Different archive bytes between backends")
            saving = plain["storage"]["stored_bytes"] - rust["storage"]["stored_bytes"]
            record = {"dataset": name, "codec": config["compression"], "layout": config["layout"],
                      "archive_bytes": rust["storage"]["stored_bytes"], "archive_sha256": rust["storage"]["archive_sha256"],
                      "transformed_chunks": rust["storage"]["transformed_chunks"],
                      "transformed_units": rust["storage"].get("transformed_units"),
                      "csv_archive_saving_vs_plain_bytes": saving,
                      "csv_archive_saving_vs_plain_pct": 100 * saving / plain["storage"]["stored_bytes"],
                      "native_incremental_deployment_bytes": cost,
                      "one_archive_net_saving_vs_plain_bytes": saving - cost,
                      "same_size_archives_to_strict_net_saving": math.floor(cost / saving) + 1 if saving > 0 else None,
                      "csv_python_to_rust_restore": restoration_compare(python, rust),
                      "csv_python_to_rust_open_reader": compare(python, rust, "open_reader"),
                      "csv_python_to_rust_open_and_read": compare(python, rust, "open_and_read"),
                      "plain_python_to_csv_rust_restore": restoration_compare(plain, rust),
                      "plain_python_to_csv_rust_open_reader": compare(plain, rust, "open_reader"),
                      "plain_python_to_csv_rust_open_and_read": compare(plain, rust, "open_and_read")}
            derived.append(record)
            backend_rows.append([name, config["compression"], config["layout"],
                                 f'{python["decode_s"]["median"]*1000:.2f} → {rust["decode_s"]["median"]*1000:.2f}',
                                 f'{record["csv_python_to_rust_restore"]["paired_wall_speedup"]["median"]:.2f}×',
                                 f'{p95(python)*1000:.3f} → {p95(rust)*1000:.3f}',
                                 f'{p95(python,"open_and_read")*1000:.3f} → {p95(rust,"open_and_read")*1000:.3f}',
                                 f'{python["decode_peak_rss_bytes"]["median"]/1048576:.2f} → {rust["decode_peak_rss_bytes"]["median"]/1048576:.2f}'])
    text += table(["数据", "codec", "布局", "完整恢复 ms", "恢复配对加速", "常驻 p95 ms", "重开 p95 ms", "恢复峰值 MiB"], backend_rows)
    text += "\n## 保留普通编码与部署成本对照\n\n下面 none 为 Python，CSV 为 Rust。包含全归档；尚未分摊原生库。\n\n"
    rows = []
    for record in derived:
        report = reports[record["dataset"]]
        plain = pick(report, record["layout"], record["codec"], "none", "python")
        rust = pick(report, record["layout"], record["codec"], "csv-columns-v1", "rust")
        rows.append([record["dataset"], record["codec"], record["layout"], plain["storage"]["stored_bytes"],
                     record["archive_bytes"], f'{record["csv_archive_saving_vs_plain_pct"]:.3f}%',
                     f'{plain["decode_s"]["median"]*1000:.2f} / {rust["decode_s"]["median"]*1000:.2f}',
                     f'{p95(plain,"open_and_read")*1000:.3f} / {p95(rust,"open_and_read")*1000:.3f}',
                     record["one_archive_net_saving_vs_plain_bytes"], record["same_size_archives_to_strict_net_saving"]])
    text += table(["数据", "codec", "布局", "none bytes", "CSV bytes", "归档节省", "恢复 none/CSV ms", "重开 none/CSV ms", "单份计入原生库后节省 bytes", "严格净节省所需同等归档数"], rows)
    text += "\n## 跨 codec 的最小普通归档对照\n\n不能只引用相同 Zlib 的空间收益；在本轮候选集合中分别挑体积最小的 none/Python 与 CSV/Rust。\n\n"
    rows = []
    for name, report in reports.items():
        plain = min((r for r in report["results"] if r["configuration"]["transform"] == "none"
                     and r["configuration"]["decoder_backend"] == "python"), key=lambda r: r["storage"]["stored_bytes"])
        csv = min((r for r in report["results"] if r["configuration"]["transform"] == "csv-columns-v1"
                   and r["configuration"]["decoder_backend"] == "rust"), key=lambda r: r["storage"]["stored_bytes"])
        saving = plain["storage"]["stored_bytes"] - csv["storage"]["stored_bytes"]
        rows.append([name, plain["configuration"]["compression"], csv["configuration"]["compression"],
                     plain["storage"]["stored_bytes"], csv["storage"]["stored_bytes"], saving - cost,
                     f'{plain["decode_s"]["median"]*1000:.2f} / {csv["decode_s"]["median"]*1000:.2f}',
                     f'{p95(plain,"open_and_read")*1000:.3f} / {p95(csv,"open_and_read")*1000:.3f}'])
    text += table(["数据", "最小 none codec", "最小 CSV codec", "none bytes", "CSV bytes", "单份计入原生库后节省 bytes", "恢复 none/CSV ms", "重开 none/CSV ms"], rows)
    text += f"""

DLL **{provenance['bytes']:,} bytes** + native.json **{provenance['metadata_bytes']:,} bytes**，
额外共享部署资源合计 **{cost:,} bytes**。摊销数假设每份归档有相同的归档节省，
是成本情景计算，不是跨版本 CAS 或新增独立数据的观测。公共 Python/操作系统/
链接依赖未完整计入，不称为完整部署大小。HTRU2 没有实际 CSV 变换，回退结果保留。

## 无变换后端负对照

即使没有 CSV 单元，显式 Rust 后端仍检查/加载库；对普通恢复可能增加启动成本。
不能将这种计时差异当成 codec 加速或归档变化。

"""
    rows = []
    for name, report in reports.items():
        for python in sorted((r for r in report["results"] if r["configuration"]["transform"] == "none"
                              and r["configuration"]["decoder_backend"] == "python"),
                             key=lambda r: (r["configuration"]["compression"], r["configuration"]["layout"])):
            config = python["configuration"]
            rust = pick(report, config["layout"], config["compression"], "none", "rust")
            if rust["storage"] != python["storage"]:
                raise ValueError("Unmatched negative-control archives")
            rows.append([name, config["compression"], config["layout"],
                         f'{python["decode_s"]["median"]*1000:.2f} / {rust["decode_s"]["median"]*1000:.2f}',
                         f'{p95(python,"open_and_read")*1000:.3f} / {p95(rust,"open_and_read")*1000:.3f}'])
    text += table(["数据", "codec", "布局", "none 恢复 Python/Rust ms", "none 重开 Python/Rust p95 ms"], rows)
    text += """

协议见 [NATIVE.md](../../docs/NATIVE.md)，冻结构建与源码见 native-provenance.json 和
source-checksums.json。已发表 v0.5 时序均为 Python；本轮与历史数字协议/执行日期
不同，结论使用本轮内部对照。默认策略未改；冷缓存/跨机器/跨日和推理质量未测。
Rust 范围结果已经包含 Python 调用、复制、原有 codec/哈希与索引校验。
"""
    (root / "SUMMARY.md").write_text(text, encoding="utf-8", newline="\n")
    (root / "derived-metrics.json").write_text(json.dumps(derived, indent=2) + "\n", encoding="utf-8", newline="\n")
    return reports, counts


def plot(root, reports):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), layout="constrained")
    for ax, name in zip(axes, ("wine", "superconductivity")):
        if name not in reports:
            continue
        for transform, backend, label, color in (("none", "python", "Plain / Python", "#475569"),
                                                ("csv-columns-v1", "python", "CSV / Python", "#b45309"),
                                                ("csv-columns-v1", "rust", "CSV / Rust", "#2563eb")):
            layouts = ("flat-1024", "units-64", "units-16")
            rows = [pick(reports[name], layout, "zstd", transform, backend) for layout in layouts]
            x = [r["storage"]["stored_bytes"] / 1e6 for r in rows]
            y = [p95(r, "open_and_read") * 1000 for r in rows]
            ax.plot(x, y, "o-", label=label, color=color)
            for px, py, layout in zip(x, y, layouts):
                ax.annotate(layout.replace("flat-", "F").replace("units-", "U"), (px, py), xytext=(4, 5), textcoords="offset points", fontsize=8)
        ax.set_title(name.upper()); ax.set_xlabel("Complete archive size (decimal MB)")
        ax.set_ylabel("Reopen per request: round p95 median (ms)")
        ax.set_ylim(bottom=0); ax.margins(x=0.2, y=0.2); ax.grid(alpha=0.2); ax.legend()
    fig.suptitle("RKV-1 v0.6.0 | Zstd 3 | Warm cache | Native deployment cost reported separately")
    fig.savefig(root / "native-tradeoffs.png", dpi=160)
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
