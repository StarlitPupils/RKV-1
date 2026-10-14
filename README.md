# RKV-1 — Reversible Knowledge Vault

面向科学知识与推理的可逆记忆研究项目。原始证据逐字节保存；未来的摘要、图谱、
语义索引和神经记忆只作为辅助表示，最终结论能够回到精确来源。

[![tests](https://github.com/StarlitPupils/RKV-1/actions/workflows/ci.yml/badge.svg)](https://github.com/StarlitPupils/RKV-1/actions/workflows/ci.yml)
[版本发布](https://github.com/StarlitPupils/RKV-1/releases) · [实验路线](docs/ROADMAP.md) · [格式规范](docs/FORMAT.md)

## 当前版本：v0.1.0 · E0/E1

已实现 Python 无损目录归档：固定分块、SHA-256 内容寻址、跨文件去重、Zlib/原样
存储选择、完整性检查、原子发布、随机范围读取、旧快照压缩块复用。
增量模式会重读源数据并写出独立完整快照，不依赖旧归档。

E0 同时测量 Zstd、Brotli、LZMA、Zlib、原始 TAR 和 RKV；保存体积、吞吐、
编码/恢复时间、随机读延迟、进程峰值内存、数据来源及固定哈希。每次恢复都做逐字节比较。
Rust 已提供格式前缀和块范围计算的测试骨架，尚未接入 Python 性能路径。

## 本机实测

2026-10-14，i5-14600KF，Windows，Python 3.13.12；1 次预热 + 3 次记录。
SciFact 原始文件共 **8,582,267 bytes**；下表体积含容器开销，耗时为中位数。

| 方法 | 归档 bytes | 压缩倍率 | 编码 ms | 恢复 ms | 随机读 p95 ms |
|---|---:|---:|---:|---:|---:|
| TAR + Zlib 6 | 2,848,963 | 3.01× | 310.76 | 30.97 | 25.36 |
| TAR + LZMA 6 | 1,967,480 | 4.36× | 3756.99 | 79.32 | 78.85 |
| TAR + Zstd 3 | 2,670,268 | 3.21× | 43.29 | 16.80 | 9.43 |
| TAR + Brotli 5 | 2,402,133 | 3.57× | 206.34 | 23.91 | 17.86 |
| RKV1 + Zlib/去重 | 2,862,790 | 3.00× | 335.69 | 37.69 | 3.35 |

**没有观察到 RKV 全面胜过成熟压缩器。** 当前收益在按块读取、完整性检查和复用机制。
RKV 随机读保留已打开的清单，整流 TAR 每次解码；尚未比较 seekable Zstd。
真实 UCI/SciFact 在默认分块下没有重复块。合成重复数据验证了 4 个块引用只存 1 份，
但这不代表真实语料的压缩率。所有已运行恢复和范围读取比较通过。

[完整结果与局限](results/v0.1.0/SUMMARY.md) · [原始 SciFact 样本](results/v0.1.0/scifact.json) ·
[实验方法与复现](docs/EXPERIMENTS.md) · [数据署名与许可](docs/DATASETS.md)

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[bench]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m rkv1 fetch data/uci
.\.venv\Scripts\python.exe -m rkv1 pack data/uci data/uci.rkv
.\.venv\Scripts\python.exe -m rkv1 verify data/uci.rkv
.\.venv\Scripts\python.exe -m rkv1 unpack data/uci.rkv data/restored
.\.venv\Scripts\python.exe -m rkv1 compare data/uci data/restored
.\.venv\Scripts\python.exe scripts/run_experiments.py --out results/local
```

需要 Python 3.10+。Linux/macOS 使用 `.venv/bin/python`；只使用归档核心时可
安装 `pip install -e .`，不需要外部 Python 依赖。已有目标默认拒绝覆盖。

## 路线与边界

| 阶段 | 状态 |
|---|---|
| E0 基准 | 公开数据 + 合成去重对照已实测 |
| E1 无损核心 | Python 原型完成；Rust 骨架待性能迁移 |
| E2 类型感知可逆压缩 | 下一阶段 |
| E3 神经预测 + 熵编码 + 精确残差 | 后续，必须计入模型与解码成本 |
| E4 科学记忆、检索与可验证推理 | 后续，尚无推理质量结果 |

当前格式为 Draft 0.1，仅恢复普通文件路径与内容，不保留权限、时间戳、空子目录、
符号链接；最多 2 GiB 恢复数据。SHA-256 检查完整性，不证明科学结论正确或来源身份。
不声称“无限精确上下文”或任意数据上的最佳压缩，也不把语义摘要当作无损恢复。

每个版本在 [Release](https://github.com/StarlitPupils/RKV-1/releases) 更新改动、结果和限制，
README 保留总体状态；原始结果随版本保存，tag 不改写。代码采用 [MIT](LICENSE)。
