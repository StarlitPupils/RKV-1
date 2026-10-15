# RKV-1 — Reversible Knowledge Vault

面向科学知识与推理的可逆记忆研究项目。原始证据逐字节保存；摘要、图谱、语义索引和
神经记忆作为未来辅助表示，最终结论能回到精确来源。

[![tests](https://github.com/StarlitPupils/RKV-1/actions/workflows/ci.yml/badge.svg)](https://github.com/StarlitPupils/RKV-1/actions/workflows/ci.yml)
[版本发布](https://github.com/StarlitPupils/RKV-1/releases) · [路线](docs/ROADMAP.md) · [格式](docs/FORMAT.md)

## 当前版本：v0.10.0 · 精确数值字节原型

E2新增显式`byte-shuffle-{2,4,8}-v1`和`xor-shuffle-{2,4,8}-v1`策略。
它们重排原始字节，或先对相邻字做XOR，再重排；不解析/舍入数值、不改端序，
残尾原样保留。数值策略写新 **v4** 平块归档，旧读取器拒绝v4；默认none仍写v2，
CSV/v3单元/CAS格式不变。块/文件/manifest SHA、有界解压和发布fsync均保留。

实测两个公开数据库各一条原始int16记录：EEGMMIDB S001R01的完整EDF+，以及
PTBDB s0010_re的dat/xyz/hea；另有固定种子随机字节负对照。无采样或文件转换，
原始头和注释也计入；每组12条件、五轮、全部同v4容器。
**180次正式完整恢复、34,560次正式范围读取**，另36次完整预热、4,320次查询预热
全部逐字节一致。本机90项测试：89通过、1符号链接权限跳过；Windows/Linux CI通过。

下表在本次Zlib6/Zstd3、64KiB/1MiB集合内，分别按体积选最小归档，包含全部
容器成本；另给每个候选全额加专用numeric.py源文件 **1,431 bytes**。这不是完整
部署成本；无额外DLL、模型或字典，公共Python/core/codec未全额分配。

| 原始记录 | 策略 | 归档+专用源 bytes | 对最小普通净节省 | 编码 ms | 恢复 ms |
|---|---|---:|---:|---:|---:|
| EEG | 普通 Zstd/1MiB | 682,548 | 基线 | 14.268 | 7.874 |
| EEG | 重排 Zlib/1MiB | 640,179 | **6.21%** | 114.230 | 8.417 |
| EEG | XOR重排 Zlib/1MiB | 585,333 | **14.24%** | 174.255 | 35.985 |
| ECG | 普通 Zlib/1MiB | 865,389 | 基线 | 44.029 | 9.307 |
| ECG | 重排 Zlib/1MiB | 629,142 | **27.30%** | 62.011 | 8.007 |
| ECG | XOR重排 Zlib/1MiB | 637,699 | **26.31%** | 120.620 | 32.224 |

**字节重排有值得继续验证的空间收益；XOR不自动更优。** EEG的XOR进一步缩小存储，
但恢复中位需普通最小归档约4.57倍时间；ECG中XOR既比单纯重排大，也恢复更慢。
所有真实记录的候选编码均比相同codec/块的普通编码慢，五轮均如此。

也存在有利的局部工作点：ECG/Zlib/64KiB重排归档减少26.90%，同轮恢复、常驻p95、
重开p95配对加速分别1.30×/1.97×/1.31×，均5/5轮更快；编码加速倍率为0.657×（更慢）。
大块虽能减少元数据，仍需整块反变换/校验，不能从压缩率直接推断随机读取改善。
所有配对倍率逐轮相除再取中位，不用两个耗时中位之比替代。

![数值字节策略的完整归档与专用源成本](results/v0.10.0/numeric-costs.png)

噪声12条件全部回退普通块，但策略标签仍增加12/13bytes，专用源另计，编码尝试
还需时间；因此默认保持none。v4数值本轮只测独立归档，未与共享CAS组合测量，
不能将本轮收益与v0.9的共享节省比例叠加。

```powershell
python -m scripts.run_numeric --out results/local-numeric
python -m scripts.summarize_numeric results/local-numeric
python -m rkv1 pack data/numeric/eeg eeg.rkv --codec zstd --chunk-size 65536 --transform byte-shuffle-2-v1
python -m rkv1 verify eeg.rkv
python -m rkv1 unpack eeg.rkv restored
python -m rkv1 compare data/numeric/eeg restored
```

运行器先下载并校验原始数据；[协议/格式/执行说明](docs/NUMERIC.md)、
[完整记录](results/v0.10.0/SUMMARY.md)、[数据来源与引用](docs/DATASETS.md)、
[独立核对](results/v0.10.0/validation.json)。首批仅两个int16单记录，4/8字节与浮点
特殊位模式仅为正确性测试；真实浮点数组、专业压缩器广泛对照、冷缓存/跨机器/
跨日和推理质量未测。本版没有数值Rust加速，E2仍待扩大，E3/E4尚未实测。

## 既有同格式对象 IO 消融与第二个真实版本家族（v0.9.0）

新增显式 `--io-backend bounded` 与 Windows `--publisher rename` 候选：减少重复的
目录/对象长度查询，用有界读取检查精确 EOF；发布使用不覆盖已有目标的重命名。
每个新文件仍 flush/fsync，复用仍验证旧对象，全部原文/存储摘要保留；CAS 格式不变。
**默认仍为 reference/link**，Gear 默认仍为 Python，Rust 扫描须显式选择。

QASPER v0.1→v0.2→v0.3，加 Evidence Inference v1.2→v1.3→v1.4 的两张原始主 CSV 表；
每家族八条件、五轮本机温缓存。冻结 v0.8 Store 与当前 reference 作对照，全部 Gear
条件使用同一个实测 Rust 库。**240 次正式完整恢复、92,160 次正式范围读取**，另
48 次恢复预热、5,760 次查询预热全部逐字节一致。同表示完整存储树、快照与账本
完全相同；QASPER 结果也与 v0.8 同表示的字节相同。

| 三版指标 | QASPER | Evidence Inference 两表 |
|---|---:|---:|
| 独立 1 MiB 归档 bytes | 31,519,475 | 3,760,981 |
| 共享 Gear CAS bytes | 23,946,864 | 2,608,262 |
| 共享 Gear + 整份原生库 bytes | 24,071,283 | 2,732,681 |
| 含库后相对独立归档节省 | 23.63% | 27.34% |
| reference 提交中位 s | 2.397 | 0.223 |
| 组合候选提交中位 s | 2.124 | 0.214 |
| 组合提交配对加速中位 | **0.974×，2/5 轮更快** | **1.026×，4/5 轮更快** |

**IO 候选未证明稳定、全面提速，因此不升级默认。** 配对倍率先按同轮 reference/
candidate 计算，再取中位；它与两个耗时中位之比不同。单独 bounded 的提交配对
为 0.889×/0.766×，单独 rename 为 0.760×/0.929×；负结果和全部波动均保留。
bounded 常驻范围 p95 配对为 1.103×/1.081×，重开为 0.991×/1.036×；收益依赖指标。

![同字节 IO 消融的中位与五轮观测](results/v0.9.0/io-ablation.png)

原生库继续复用 v0.8 实测 DLL 123,904 bytes + 原始元数据 515 bytes，各家族上表全额
加一次。Evidence Inference 的 prompts 三版完全相同，约占每版原文 17.9%；较高共享
收益不能直接推广到全文或独立科学数据。逻辑字节包含所有对象/头/双摘要/快照/
配置/未引用对象；文件数据分配另记，目录/MFT/日志与公共运行时未全额分配。

本机 82 项测试：81 通过、1 Windows 符号链接权限跳过；Windows/Linux CI 通过。
覆盖损坏与尾部多字节、复用验证、并发发布、同步/快照失败、不覆盖已有文件和旧版
读取兼容。冷缓存、跨机器、跨日、断电耐久性和推理质量未测，E3/E4 尚未实测。

```powershell
python -m rkv1 store-init vault --chunker gear-v1 --codec zstd
python -m rkv1 store-add vault data/qasper-versions/v0.1 --io-backend bounded --publisher rename --chunker-backend rust --native-library native/rkv1_core.dll
python -m scripts.run_io --native-library native/rkv1_core.dll --out results/local-io
python -m scripts.summarize_io results/local-io
```

先从 [v0.9 Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.9.0) 解压
`rkv1-native-measured-v0.9.0-windows-x86_64.zip` 到 `native/`，保留原始 `native.json`。
该冻结实测库与通用平台新构建资产分开标识，不能假定其二进制相同。
[完整记录](results/v0.9.0/SUMMARY.md) · [IO 协议与复现](docs/IO.md) ·
[数据来源](docs/DATASETS.md) · [独立核对](results/v0.9.0/validation.json)。下一优先项
转向 E2 数组/数值类型，先做完整成本基线和负对照，再决定编码方案。

## 既有热点剖析与精确 Rust Gear 扫描（v0.8.0）

冻结v0.7源码的cProfile诊断定位到逐字节Gear循环；v0.8新增显式Rust扫描后端。
同一表、u64递推、最小/最大边界和流状态保持不变。Python仍组装原文字节，执行
全部哈希、压缩、旧对象验证、fsync和发布。CAS格式与默认Python后端不变。

原始QASPER三个发布，六条件、五轮本机温缓存；Python/Rust所有轮次的完整存储树、
对象账本及快照ID相同，并与v0.7已发布的同表示存储树字节完全一致。
**90次正式完整恢复、34,560次正式范围读取**，另18次恢复预热、2,160次查询预热
全部逐字节一致。本机75项测试：74通过、1 Windows符号链接权限跳过；跨平台CI通过。

| 三版存储/扫描方式 | 完整逻辑存储 bytes | 三版提交中位 s | 完整恢复中位 s | v0.3重开p95 ms |
|---|---:|---:|---:|---:|
| 独立RKV / 固定1MiB | 31,519,475 | 0.623 | 0.260 | 2.233 |
| 共享CAS / 固定64KiB | 35,981,908 | 3.970 | 0.572 | 4.704 |
| 共享CAS / Gear Python | 23,946,864 | 28.989 | 0.519 | 3.893 |
| 共享CAS / Gear Rust | **23,946,864** | **2.971** | 0.517 | 3.793 |

同轮提交配对加速中位：共享Gear **9.88倍**、独立Gear **10.54倍**，两者均5/5轮
更快。配对比值中位与表内耗时中位之比不是同一统计量；结论使用本轮内部对照，
不将历史版本耗时变化直接当作迁移收益。恢复/读取仍用同一Python实现，未获Rust解码收益。
共享配对逐轮加速范围8.15–16.66倍，仅为观测范围；Rust三版提交wall为1.70–3.56秒，
波动仍存在，不声称统计显著或固定倍率。

实测冻结DLL 123,904 bytes + 原始native.json 515 bytes，整份共享资源 **124,419 bytes**。
三版共享Gear加一次全额库成本为 **24,071,283 bytes**，相对旧独立1MiB归档节省
**23.63%**；公共Python/codec/OS和目录/MFT/日志未全额分配，不是完整部署或物理卷成本。
提交仍为旧1MiB归档 **4.77倍耗时**，完整恢复约 **1.99倍**，重开p95约 **1.70倍**。
原生扫描解决了主要诊断热点，综合性能仍有明确取舍。

![Gear同存储字节的提交与资源成本](results/v0.8.0/gear-tradeoffs.png)

```powershell
python -m rkv1 store-init vault --chunker gear-v1 --codec zstd
python -m rkv1 store-add vault data/qasper-versions/v0.1 --label v0.1 --chunker-backend rust --native-library .tools/native-v0.8-measured/rkv1_core.dll
python -m scripts.run_gear --native-library .tools/native-v0.8-measured/rkv1_core.dll --out results/local-gear
```

[完整记录](results/v0.8.0/SUMMARY.md) · [原生协议/复现](docs/NATIVE.md) ·
[逐轮原始结果](results/v0.8.0/qasper-gear.json)。Release另附
`rkv1-native-measured-v0.8.0-windows-x86_64.zip`，保留通过源CI的实测库和元数据原字节。
通用新构建库须按自己的身份使用，不能假定与实测库相同。源/输入/库/元数据前后
指纹一致；诊断树与主实验均保留。一个家族三版、温缓存五轮；冷缓存、跨机器、
跨日和科学推理质量未测。对象 IO 消融和第二个版本家族由 v0.9 补充；E2 其他类型待开展。

## 既有真实版本序列与共享 CAS（v0.7.0）

新增可选目录 CAS：不可变内容对象、独立快照、全量/局部恢复与逐层校验。支持固定
分块和简单 Gear CDC；对象按原文字节 SHA-256 寻址，跨版本引用已有对象，实际只
存一份。旧归档 v1/v2/v3 和 pack/read/unpack 默认行为保持不变。

使用 QASPER 官方原始 train/dev **v0.1→v0.2→v0.3**，保留原始文件名和全部字节，
不重序列化 JSON。一个语料家族、三次真实发布，128,076,252 bytes 原文；八条件：
独立 RKV、同格式独立 CAS、共享 CAS，固定64KiB/1MiB及 Gear scale64KiB。
**120 次正式完整恢复 + 24 次预热恢复、46,080 次正式范围读取 + 2,880 次查询
预热全部逐字节一致**。本地70项测试：69通过、1符号链接权限跳过；跨平台CI通过。

所有方法 Zstd3，无CSV/模型/字典/原生后端。同边界的独立/共享 CAS 快照ID相同，
对象文件字节并集相同，避免将不同编码表示的收益当成共享效果。

| 三个版本的存储方式 | 完整逻辑文件 bytes | 分配文件数据 bytes | 文件数 | 三版提交 s |
|---|---:|---:|---:|---:|
| 独立 RKV / 固定1MiB | 31,519,475 | 31,522,816 | 3 | 0.650 |
| 独立 CAS / Gear64 | 35,408,908 | 38,224,616 | 1,436 | 23.040 |
| 共享 CAS / 固定64KiB | 35,981,908 | 39,780,480 | 1,928 | 3.100 |
| 共享 CAS / Gear64 | **23,946,864** | **25,759,992** | 914 | 22.529 |

共享 Gear 相对同格式独立 Gear 节省 **32.37%**；相对独立1MiB RKV逻辑字节减少
**24.03%**，但提交约 **34.69倍耗时**，三版完整恢复约 **2.00倍耗时**。v0.3 的
跨版本独特对象复用 **94.21%**（独特原文91.23%）；固定64KiB对应仅4.83%/4.84%。
v0.3 新增对象+快照约1.05MB，固定1MiB约10.42MB。固定分块会受字节偏移影响，
CDC改善了这组真实修订的复用，Python扫描/大量对象也增加了时间成本。

![三版存储与累计增长](results/v0.7.0/version-storage.png)

逻辑字节包含所有对象头/双摘要/payload、快照/config与未引用对象；额外报告文件
数据分配空间和文件数。目录/MFT/日志/公共运行时未全额计入，不称为完整物理卷
占用。Gear64是mask scale，实际平均块约89,500 bytes（约87.4KiB），
不是与固定64KiB实际平均严格匹配，也不是FastCDC复现。

[本轮完整记录](results/v0.7.0/SUMMARY.md) · [格式/协议/执行说明](docs/STORE.md) ·
[固定数据来源](results/v0.7.0/dataset-provenance.json)。使用 store-init/store-add/
store-verify/store-unpack/store-read/store-stat。局部验证只证明触及对象；每次复用
验证旧对象，完整恢复验证文件。失败提交可留下计费对象，无GC和断电耐久性证明。
仅本机温缓存、一个语料家族；冷缓存/跨机器/跨日、E3/E4科学推理质量未测。
Gear热点剖析与原生扫描已由v0.8补充；其他真实版本家族和E2类型仍待扩大。

## 既有 Rust 反变换与本机配对（v0.6.0）

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
冷缓存/跨机器/跨日、推理质量未测。真实版本序列、CDC与共享CAS已由v0.7补充；
数组/代码/数学类型、E3/E4仍待开展。

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
| E1 无损核心 | v1/v2/v3兼容；共享CAS、真实版本复用与Gear分块；v0.8显式Rust扫描，格式不变 |
| E2 类型感知可逆编码 | CSV、小单元访问与冻结Rust反变换已有本机配对；其余类型待开展 |
| E3 神经预测 + 熵编码 + 精确残差 | 后续，计入模型和解码成本 |
| E4 科学记忆、检索、证据回溯与可验证推理 | 后续，尚无质量结果 |

Rust 已用于可选CSV反变换与Gear扫描。传统归档的`--base`复用编码结果，仍写独立
完整快照；目录CAS可跨版本只存一份对象。两者仍全量读源、计算哈希并验证旧对象。

[FORMAT Draft 0.3](docs/FORMAT.md) 只恢复普通文件路径和内容，不保留权限、时间戳、
空子目录或链接；恢复合计上限 2 GiB。v3 需 v0.5.0+，默认 v2 仍可由 v0.2.0+ 读取。
SHA-256 用于完整性检查，不能证明来源身份或科学结论正确。当前没有神经压缩、
无限精确上下文或科学推理收益的验证。

[首版 v0.1.0 记录](results/v0.1.0/SUMMARY.md) 与 [v0.2.0 记录](results/v0.2.0/SUMMARY.md) 保留；各版协议不同，不能直接把耗时
变化全归为单个优化。每版本在 [Release](https://github.com/StarlitPupils/RKV-1/releases)
更新改动、结果和限制；tag 不改写。代码 [MIT](LICENSE)。
