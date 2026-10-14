# RKV-1 — Reversible Knowledge Vault

面向科学知识与推理的可逆记忆研究项目。原始证据逐字节保存；摘要、图谱、语义索引和
神经记忆作为未来辅助表示，最终结论能回到精确来源。

[![tests](https://github.com/StarlitPupils/RKV-1/actions/workflows/ci.yml/badge.svg)](https://github.com/StarlitPupils/RKV-1/actions/workflows/ci.yml)
[版本发布](https://github.com/StarlitPupils/RKV-1/releases) · [路线](docs/ROADMAP.md) · [格式](docs/FORMAT.md)

## 当前版本：v0.6.0 · Rust 精确反变换与本机配对

新增读取器实例级 `--decoder-backend rust --native-library ...`，只替换 CSV v1 的
字面量检查和精确反变换。保留原有受限解压、单元/父块/文件 SHA-256；两个后端
读取同一个归档。默认仍为 Python、Zlib/1 MiB、v2，CSV 和独立单元须显式启用。

Wine、超导材料、HTRU2；26 份确定性归档、52 个条件，**260 次正式完整恢复 +
52 次预热恢复、99,840 次正式范围读取 + 6,240 次查询预热全部逐字节一致**。
本机使用 v0.5 Release 的冻结 Windows DLL，库/元数据/源码/输入哈希前后一致。
本地 63 项测试：62 通过、1 符号链接权限跳过；Windows/Linux CI 验证新后端。

超导材料、Zstd、CSV：同归档 Python → Rust，恢复含库校验/加载、FFI 和复制；
范围已预热。五轮配对，不做显著性结论。

| 布局 | 总 bytes | 完整恢复 ms | 恢复配对加速 | 重开 p95 ms |
|---|---:|---:|---:|---:|
| 1 MiB 整块 | 7,442,705 | 427.17 → 91.94 | 4.63× | 30.997 → 4.496 |
| 1 MiB + 64 KiB 单元 | 7,817,638 | 395.15 → 99.45 | 3.97× | 2.457 → 1.009 |
| 1 MiB + 16 KiB 单元 | 8,423,479 | 626.74 → 120.09 | 5.22× | 1.491 → 0.924 |

上述 CSV 恢复/重开均五轮更快，但普通 Zstd/1 MiB 本轮恢复 **61.08 ms**、重开
**2.346 ms**；不能把 CSV 后端加速当作普通编码已被全面超过。额外 DLL+元数据
**121,747 bytes** 单列部署成本：本轮体积最小的超导材料 CSV/Zlib 归档 7,284,903
bytes，比最小普通 Zstd 的 7,548,059 bytes 减小 263,156 bytes；计入一次原生资源后
净省 **141,409 bytes**，恢复却为 **136.34 ms**（普通约61.08 ms）。Wine 单份归档
的节省不足抵消原生资源；HTRU2 CR-only 回退并无变换收益。默认策略保持不变。

![原生后端空间与读取代价](results/v0.6.0/native-tradeoffs.png)

[完整配对结果](results/v0.6.0/SUMMARY.md) · [原生协议与执行说明](docs/NATIVE.md) ·
[库来源](results/v0.6.0/native-provenance.json)。归档格式不变，兼容 v1/v2/v3；
Release 附 Windows/Linux 原生库 ZIP，复现实验须选协议指定的冻结二进制。
冷缓存/跨机器/跨日、推理质量未测。下一优先项为真实版本序列、CDC 与共享 CAS；
数组/代码/数学类型、E3/E4 仍待开展。

## 既有独立单元与索引实验（v0.5.0）

显式 `--unit-size` 生成 RKV v3：1 MiB 父块内含独立 16/64 KiB 单元，每个单元有
大小、codec、变换标志和原始 SHA-256。二进制索引按需校验并缓存，范围请求只
解码触及单元；完整恢复继续验证父块和文件。默认仍写 v2，CSV 仍关闭。

四组科学输入、53 个条件；**265 次正式完整恢复 + 53 次预热恢复、101,760 次正式
范围读取 + 6,360 次查询预热全部逐字节一致**。本地 56 项测试：55 通过、1 权限跳过。
所有大小包括索引；对照包含整块、直接小块、普通编码及关闭索引缓存。

Zstd、同源码/同请求、温缓存，各轮 p95 中位数：

| 数据 / 变换 | 布局 | 总 bytes | 重开 p95 ms |
|---|---|---:|---:|
| 超导材料 / CSV | 1 MiB 整块 | 7,442,705 | 30.921 |
| 超导材料 / CSV | 直接 16 KiB 块 | 8,761,101 | 13.645 |
| 超导材料 / CSV | 1 MiB + 16 KiB 单元 | 8,423,479 | 1.378 |
| QASPER / none | 1 MiB 整块 | 10,660,769 | 2.221 |
| QASPER / none | 直接 64 KiB 块 | 12,415,158 | 5.208 |
| QASPER / none | 1 MiB + 64 KiB 单元 | 12,299,774 | 0.870 |

两层单元相对同大小直接小块改善了较大语料的打开成本并减少元数据；常驻读取并非
全胜。超导材料/CSV/16 KiB 对直接小块节省 3.85%，配对重开 p95 加速中位约9.75倍；
但对原1MiB CSV归档仍增大约13.18%，完整恢复也未必更快。不能只拿整块 CSV 作参照：
普通 Zstd 的两层64KiB方案本组重开约0.703ms，优于相同CSV约2.463ms。

![独立单元空间与重开延迟](results/v0.5.0/unit-tradeoffs.png)

[本轮记录](results/v0.5.0/SUMMARY.md) · [协议](docs/UNITS.md) · [v3 格式](docs/FORMAT.md)。
v0.5 读取器兼容 v1/v2/v3；旧读取器不支持 v3。局部读取只证明触及单元，完整 verify
检测所有损坏；索引摘要的校验链不代表来源身份。单元哈希尚未实现跨父块 CAS/增量共享。

Rust 新增精确 CSV 反变换 C ABI 候选，Windows/Linux CI 做函数及 Python 差分验证，
Release 附带平台库/来源哈希；本轮时序实验全部使用 Python，尚无 Rust 加速结论。
下一里程碑量化原生内核，再推进真实版本序列/共享块存储。冷缓存/跨机器继续未测。

## 既有 CSV 反变换试验（v0.4.0）

在首版无损核心之上加入 Zstd、可关闭的跨文件去重、可选数值 CSV 列重排，以及
manifest version=2；新读取器仍能恢复首版归档。默认 Zlib/1 MiB、CSV 变换关闭；
codec、块大小和变换策略由参数选择。

本版新增 HTRU2 脉冲星候选与 Superconductivity 超导材料数据，固定 ZIP/原始成员
哈希。CSV 反变换保留全部校验，把按单元 Python 索引改为列切片 + zip；与冻结旧
反变换读取同一归档、匹配同一查询。默认仍为 Zlib/1 MiB，CSV 关闭，格式仍为 v2。

**18 个条件、90 次正式完整恢复 + 18 次预热恢复、15,360 次正式范围读取 + 1,920
次预热读取全部逐字节一致。** 本地 44 项测试：43 通过、1 权限跳过。

| 数据 / codec | CSV 对同 codec 归档节省 | 旧/新 CSV 完整恢复耗时 | 新 CSV/普通恢复耗时 |
|---|---:|---:|---:|
| Wine / Zlib | 4.62% | 1.21× | 6.68× |
| Wine / Zstd | 0.40% | 1.09× | 2.17× |
| Superconductivity / Zlib | 11.79% | 1.15× | 7.17× |
| Superconductivity / Zstd | 1.40% | 1.16× | 6.94× |

优化使有实际变换的条件恢复速度提高约 9–21%（耗时减少约 8.6–17.1%），但仍明显慢于普通编码，超导材料条件
峰值内存增加约 1.5–1.9 MiB。与本轮最小普通归档 Zstd 比，超导材料的最小 CSV
归档 Zlib 只再省约 3.49%，恢复慢约 11.1 倍，不能把同 codec 的 11.79% 当作全面优势。
HTRU2 为 CR-only，当前 CSV v1 不适用，回退保留全部原文，启用策略仅多 10 bytes
头部成本；不为获得正结果改换行。正则验证与整块重建仍是后续优化候选，尚无 Rust 加速。

![CSV 空间收益与恢复代价](results/v0.4.0/csv-tradeoffs.png)

[本轮完整结果](results/v0.4.0/SUMMARY.md) · [E2 配对协议](docs/CSV-TRIALS.md) ·
[成本账本](results/v0.4.0/runtime-footprint.json)。发布前 CI 再运行跨平台 Python/Zstd 和 Rust 骨架测试。

## 已完成的多轮读取评测（v0.3.0）

上一版沿用 RKV v2 格式和压缩核心，补强 E0 读取协议。SciFact/QASPER × 三种 codec
× 三种块大小，18 个配置；每配置两个连续批次、每批五轮不同查询种子。常驻读取器
与每次重开分别使用独立 worker，配置/轮次/模式交错打乱，记录打开、读取和关闭
阶段。非跨块请求完全配对；原始请求、样本、执行顺序和输入/源码指纹随版本保存。

全部归档先完整校验，每个请求逐字节验证，实验末尾检查输入、实现和归档未变。
正式范围读取 **161,280 次**，另有 **10,080 次预热读取**，全部逐字节一致；
共 360 个独立 worker，18 个完整校验的归档与 v0.2 对应条件字节完全相同。
计时前预读完整归档，只报告本机温缓存结果；冷缓存、跨机器与跨日结果明确未测。
该版本地 **38 项测试：37 通过、1 权限跳过**；
发布流水线再运行 Windows/Linux、Python 3.10/3.13 和 Rust 骨架测试。

读取统计报告十轮各自 p95 的中位数、最小/最大值和配对方向；范围不是置信区间。
[本轮结果](results/v0.3.0/SUMMARY.md) · [读取协议](docs/READING.md)。

Zstd、温缓存、按文件字节加权的短范围请求：

| 数据 | 块 KiB | 常驻：十轮 p95 中位 ms | 每次重开：十轮 p95 中位 ms |
|---|---:|---:|---:|
| SciFact | 64 / 256 / 1024 | 0.177 / 0.442 / 1.749 | 1.465 / 1.027 / 2.140 |
| QASPER | 64 / 256 / 1024 | 0.152 / 0.413 / 1.623 | 5.298 / 2.014 / 2.321 |

常驻时 64 KiB 在两组全部十轮都快于 1 MiB，但归档增加 14.41%/16.46%。重开时
256 KiB 对 SciFact 十轮全胜，对 QASPER 九轮胜过 1 MiB，后者收益更小且有波动。
QASPER 64 KiB 清单打开中位约 4.658 ms，说明只优化块解码不能解决重开成本。
这些结果支持按读取器生命周期选候选配置，尚不改变默认策略。

## 压缩观察（v0.2.0）

以下为同容器、1 MiB、去重开启、无变换的归档大小，包含所有容器元数据。

| 语料 | 原始 bytes | Zlib 6 bytes | Zstd 3 bytes | Zstd 归档节省 |
|---|---:|---:|---:|---:|
| SciFact | 8,582,267 | 2,863,283 | 2,745,550 | 4.11% |
| QASPER train/dev | 43,368,073 | 10,902,467 | 10,660,769 | 2.22% |
| UCI Iris/red wine | 88,750 | 25,150 | 26,681 | -6.09% |
| Wine red/white | 348,625 | 93,493 | 98,417 | -5.27% |

Zstd 在这两组科学文本上编码、恢复更快，CSV 的最小体积则由 Zlib 获得。
小块改善范围读取延迟，但增加压缩损失和索引开销；选择应结合查询工作负载。
在相同流式容器下，两 codec 恢复内存相近，首版与整流 TAR 的内存差距受实现方式影响。

E2 的列重排保留数值原文、表头、换行及跨块边界。Zlib 条件下归档节省约 **4.6–4.7%**，
但 Python 解析、恢复和范围读取明显变慢，所以保留为可选试验。真实输入在本次三种
固定分块下没有重复块收益；合成对照验证去重机制，但不代表自然科学语料。

[多轮读取与打开方式图](results/v0.3.0/reading.png)

[完整结果与原始样本](results/v0.2.0/SUMMARY.md) · [复现协议](docs/EXPERIMENTS.md) ·
[数据署名/许可](docs/DATASETS.md) · [运行时成本记录](results/v0.2.0/runtime-footprint.json)

归档字节不等于部署总占用。本机可选 Zstd distribution 另占约 1.13 MB；共享 RKV
源码、transform 模块以及安装占用都记录在成本账本，Python/全部共享原生依赖尚未
分摊到单归档。本版没有外部字典、模型权重或语义索引。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[bench]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m rkv1 fetch data/scifact --dataset scifact
.\.venv\Scripts\python.exe -m rkv1 pack data/scifact data/scifact.rkv --codec zstd
.\.venv\Scripts\python.exe -m rkv1 verify data/scifact.rkv
.\.venv\Scripts\python.exe -m rkv1 unpack data/scifact.rkv data/restored
.\.venv\Scripts\python.exe -m rkv1 compare data/scifact data/restored
.\.venv\Scripts\python.exe scripts/run_controlled.py --out results/local-controlled
.\.venv\Scripts\python.exe scripts/summarize_controlled.py results/local-controlled
.\.venv\Scripts\python.exe scripts/run_reading.py --out results/local-reading
.\.venv\Scripts\python.exe scripts/summarize_reading.py results/local-reading
.\.venv\Scripts\python.exe scripts/run_csv_trials.py --out results/local-csv
.\.venv\Scripts\python.exe scripts/summarize_csv.py results/local-csv
.\.venv\Scripts\python.exe scripts/run_units.py --out results/local-units
.\.venv\Scripts\python.exe scripts/summarize_units.py results/local-units
```

Python 3.10+；Linux/macOS 使用 `.venv/bin/python`。核心 Zlib 模式可安装 `pip install -e .`，
Zstd 可仅安装 `.[zstd]`。绘图可另装 `.[plots]`。归档默认不覆盖，恢复目标须不存在。

```powershell
python -m rkv1 pack data/scifact data/small-blocks.rkv --codec zstd --chunk-size 65536
python -m rkv1 pack data/scifact data/no-dedup.rkv --codec zstd --no-dedup
python -m rkv1 fetch data/wine --dataset wine
python -m rkv1 pack data/wine data/columns.rkv --codec zlib --transform csv-columns-v1
```

## 路线与版本

| 阶段 | 状态 |
|---|---|
| E0 基准 | 完成首版、受控对照和多种子读取评测；仍是单机温缓存 |
| E1 无损核心 | 可选 v3 单元/二进制索引；v1/v2 兼容，父块粒度复用 |
| E2 类型感知可逆编码 | 独立 CSV、小单元访问、完整成本对照；Rust 反变换候选未测本机性能 |
| E3 神经预测 + 熵编码 + 精确残差 | 后续，计入模型和解码成本 |
| E4 科学记忆、检索、证据回溯与可验证推理 | 后续，尚无质量结果 |

Rust 已有格式边界与 CSV 反变换候选，本轮尚未接入性能路径。增量编码可验证并
复用旧块，仍全量读源并写出独立完整快照；中间插入会改变固定块边界。

[FORMAT Draft 0.3](docs/FORMAT.md) 只恢复普通文件路径和内容，不保留权限、时间戳、
空子目录或链接；恢复合计上限 2 GiB。v3 需 v0.5.0+，默认 v2 仍可由 v0.2.0+ 读取。
SHA-256 用于完整性检查，不能证明来源身份或科学结论正确。当前没有神经压缩、
无限精确上下文或科学推理收益的验证。

[首版 v0.1.0 记录](results/v0.1.0/SUMMARY.md) 与 [v0.2.0 记录](results/v0.2.0/SUMMARY.md) 保留；各版协议不同，不能直接把耗时
变化全归为单个优化。每版本在 [Release](https://github.com/StarlitPupils/RKV-1/releases)
更新改动、结果和限制；tag 不改写。代码 [MIT](LICENSE)。
