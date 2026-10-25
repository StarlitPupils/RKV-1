# 复现实验

## v0.22：原封保留库上的v4查询准备

[PROJECTION-QUERIES.md](PROJECTION-QUERIES.md)与49模块/runner于659c354冻结。实际
v0.21发布模块、当前批量/强制复制消融、当前直接读取和v3参考，六根15状态各三轮。
6336正式、720历史身份查询对齐旧reader/原发布记录；108未来探针阴性，180进程
前后全树不变，30历史快照实例整源核验。官方全体重绑定查询配对约1.18–1.20倍，
小基础/少量重绑定无稳定免复制收益，v4仍慢于v3；默认不切换。[全结果/消融](../results/v0.22.0/SUMMARY.md)。
新源码HTML增加1269B一次，持久文件完全不变；无压缩/提交时序新结论。174测试
通过/1权限跳过，0新科学问题/模型调用，本机温缓存，旧v0.21仍兼容当前v4。

## v0.21：投影指纹与当前原文定位

[MEMORY-PROJECTION.md](MEMORY-PROJECTION.md)及49模块/runner于419b6b8冻结。官方
QASPER三发布固定/Gear与9状态合成控制，三策略各三轮，全部历史保留。4752正式/
540历史身份查询对齐重建，135快照实例整源核验，81未来探针阴性。真实组省空间
但查询变慢；v4显式候选，默认预算v3不变。官方正文投影未变，不称真实正文修订。
计全部Python/HTML，Gear另计完整实测库；公共运行时未全额分配。[完整矩阵/负结果](../results/v0.21.0/SUMMARY.md)。
170测试通过/1权限跳过，0新科学问题/模型调用，旧v0.20拒绝新应用清单v4。

## v0.20：增量回放预算

[REPLAY-BUDGET.md](REPLAY-BUDGET.md)及48模块/runner于7df94f7冻结；4控制×4策略×3轮。
4032正式/10176历史身份查询对齐重建，2544快照实例整源核验，未来探针全阴性。
已见42更新回归及默认固定分块复测均解决；独立原记录/CAS字节消融能触发检查点。
目标组多写基础索引，回归43/79部分查询反而更慢，详见[完整矩阵](../results/v0.20.0/SUMMARY.md)。
新建库默认启用，旧库显式memory-budget只改未来写入；旧慢视图不修复。全部RKV
Python/HTML源码计一次，Gear加整个实测库，公共运行时未全额计，不与v0.19口径混比。
164测试通过/1权限跳过，0科学问题/模型调用；仅合成定向控制、本机温缓存。

## v0.19：真实发布与长历史边界

[MEMORY-HISTORY.md](MEMORY-HISTORY.md)与实现/runner于26a8e89冻结。QASPER dev
原始三次发布与独立100更新合成控制，完整重建/v3增量都用同Gear/Rust，各三轮。
1800正式、2496完整身份历史查询匹配；606未来探针阴性，624历史快照全源验证。
真实组无增量空间优势，控制在25%边界查询出现严重退化，不能只报最后空间省
89.38%。四份完整源36033B/实测库元数据124419B各计一次，公共运行时未全额分配。
[完整矩阵/负结果](../results/v0.19.0/SUMMARY.md)，旧实测库随Release另附。

## v0.18：查询资源与延后定位消融

[MEMORY-QUERIES.md](MEMORY-QUERIES.md)和实现/runner于4926af6冻结。实际v0.17发布
模块、只复用资源消融、新默认延后定位，固定/Gear两组五阶段各三轮；90新进程、
17,190正式查询、90预热。188主张和3探针逐阶段一致，22历史快照整源重读，持久
文件逐个SHA不变。无跨查询缓存/模型调用/新压缩结论。计整个search调用，启动另列，
RSS含全进程。两份专用源增加3801B一次，公共运行时未全额分配。
[全结果](../results/v0.18.0/SUMMARY.md)。

## v0.17：连续更新的CAS/索引消融

[MEMORY-UPDATES.md](MEMORY-UPDATES.md)与实现/runner于d7de9e7冻结，5条件三轮
各11快照。8070正式查询、1815旧快照查询，165历史快照整源重读核验；0次模型生成。
固定/Gear、v2/v3、Gear Python/Rust分别对照；原文/历史全部保留计费。统一计三份
源，Rust加完整实测库/原始元数据，公共运行时未全额分配。旧实测库随Release另附，
与CI新库区分。离线分析可用--native-library覆盖本机文件路径，SHA须完全匹配。
[结果](../results/v0.17.0/SUMMARY.md)。

## v0.16：索引消融与增量成本

[MEMORY-INDEX.md](MEMORY-INDEX.md)于5126566冻结三个策略、四阶段和三轮协议。
相同来源/标签/CAS，保留全部历史，不发模型请求；查询在新子进程完成，计时含SHA
与增量重放，进程启动另列。4,275次正式查询及1,764次旧快照检查对齐完整索引；
108次既有请求/引用离线核对不是新推理。归档/CAS不变，新v2应用清单不兼容v0.15
读取器。完整成本/延迟/RSS见[结果](../results/v0.16.0/SUMMARY.md)。

## v0.15：证据记忆与真实模型基线

[MEMORY.md](MEMORY.md)及45个Python模块在864e43d冻结后，执行188条主张三轮
检索及预定12条主张×两条件共24次真实API调用，无重试。分析脚本重建全部请求SHA，
核对追加日志、原始记录、派生回答身份及gold评分；不保存密钥或完整摘要提示词。
模型判定与字节引用绑定分开。资源计全部保留快照与完整索引，不称系统净压缩。
[结果](../results/v0.15.0/SUMMARY.md)。分析不会调用模型：

```powershell
python -m scripts.analyze_memory results/local-memory --work .tools/local-memory --test-log path/to/test.log --plot
```

生成结果目录须不存在；分析派生文件须尚未生成，不覆盖正式已发布结果。真实API
重跑需显式--api，每个新运行最多24次生成；不把合同测试当真实模型实验。

## v0.14：跨领域与文本对照

[CROSSDOMAIN.md](CROSSDOMAIN.md)于ff73852冻结输入、矩阵与门槛。六组各8条件，
五轮、同v4、相同逐文件同步；240次正式完整恢复、43,520次正式范围读取全部一致。
2/8新科学工作点通过同codec/块验收，编码成本独立披露，文本控制不算语义编码。
阶段与范围JSONL同发行包保存，所有正式发布重试20次保留计时；主结果不删除
涉及重试的配对，双方首次发布成功子集只作事后诊断。原始文件/归档/专用源SHA
冻结，八个已见ECG配置完整编码SHA与v0.10相同，历史时序不作跨批次因果比较。


## v0.13：恢复同步与历史工作量更正

协议见[PERSISTENCE.md](PERSISTENCE.md)，实际结果见[SUMMARY](../results/v0.13.0/SUMMARY.md)。
冻结源f893e66后，四案例×close/files×十轮，另每案例/策略一次预热；新子进程、
同归档SHA、工作区E卷、打乱顺序，80+8输出全逐字节验证。归档与外部真值比较不在
恢复计时内；校验、文件同步、关闭、目录发布及其有界重试在计时内。首次中止、
协议修订、全部最终失败/重试记录保留，不以整次恢复重试选择好时序。
v1–v6共198条模拟异常与强杀检查，不代表真实掉电、自动孤儿恢复或跨机器性能。
历史100归档SHA重现及96,000请求工作量重算只更正解析账本，不是新延迟实验；
24个分段配置受影响，固定布局不变，旧数据不覆盖，0/8验收计算不变。


Python 3.10+。Zlib 核心只依赖标准库；Zstd 安装固定版本的可选依赖。

v0.3.0 的多轮读取评测使用独立 [READING.md](READING.md) 协议与 run_reading.py；
下文保留 v0.2.0 的压缩/恢复矩阵。本机冷缓存与跨机器复测按用户选择保持未测。
v0.4.0 独立数值数据、CSV 反变换诊断和旧/新配对使用 [CSV-TRIALS.md](CSV-TRIALS.md)。
v0.5.0 的独立校验单元、直接小块与完整索引成本对照见 [UNITS.md](UNITS.md)。
v0.6.0 的冻结 Rust 内核、同归档后端配对与部署成本见 [NATIVE.md](NATIVE.md)。
v0.7.0 的原始版本序列、独立/共享 CAS、Gear CDC 和完整存储账本见 [STORE.md](STORE.md)。
v0.8.0 的冻结源码剖析、精确Rust Gear扫描、同存储树五轮提交配对与整份原生库
成本见 [NATIVE.md](NATIVE.md)。复现性能时使用Release的measured原生资产，保留
原始native.json；通用新构建资产只证明自身构建身份，不能替代已测二进制。
v0.9.0的同格式对象IO/Windows发布消融、冻结v0.8控制及第二个真实版本家族见
[IO.md](IO.md)，候选显式启用，默认保持reference/link。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[bench]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/run_controlled.py --out results/local-controlled
```

Linux/macOS 使用 `.venv/bin/python`。下载器复用 SHA-256 匹配的文件。重新实验使用
新输出目录，保留已发布记录。

## 操作命令

```powershell
python -m rkv1 fetch data/scifact --dataset scifact
python -m rkv1 pack data/scifact data/scifact-v2.rkv --codec zstd
python -m rkv1 verify data/scifact-v2.rkv
python -m rkv1 unpack data/scifact-v2.rkv data/restored-v2
python -m rkv1 compare data/scifact data/restored-v2
python -m rkv1 read data/scifact-v2.rkv corpus.jsonl --offset 1048570 --length 128 --out data/range.bin
python -m rkv1 pack data/scifact data/no-dedup.rkv --codec zstd --no-dedup
python -m rkv1 fetch data/wine --dataset wine
python -m rkv1 pack data/wine data/wine-columns.rkv --codec zstd --transform csv-columns-v1
python -m rkv1 bench-controlled data/scifact --out results/local-controlled/scifact.json
```

默认拒绝覆盖已有归档，恢复目录必须不存在。增量 --base 必须同块大小、codec、
transform。旧归档可继续验证/恢复；新归档需 v0.2.0+ 读取器。

## v0.2.0 受控协议

每个方法使用同一个 RKV1 v2 容器、同一套 manifest/块/文件 SHA-256、相同临时文件
写入、flush、fsync、原子替换和归档摘要。可变量为 codec、块大小、去重与可逆变换。

64 KiB、256 KiB、1 MiB × raw/Zlib 6/Zstd 3 × 去重开/关，共 18 配置。
UCI 与 Wine 另加两 codec × 三块大小的 CSV 列重排，各 24 配置。执行顺序以种子
20261014 打乱；每配置 1 次预热、5 次记录。每次归档字节必须相同，每次恢复由父进程
在计时外逐字节比较源目录。

`runtime-footprint.json` 记录共享 RKV/transform 源码以及本机可选 Zstd distribution
占用。所有 v2 条件部署同一份源码；codec 的安装开销须结合归档数量摊销，归档字节
不能视为完整部署成本。Python 与共享原生依赖仍未全额分配到单个归档。

编码、恢复、随机读取各用新 Python 进程，分别测峰值 RSS，包含解释器、codec 和
缓冲；恢复内存不含编码进程持有的原文。不计子进程启动时间；编码计时含归档摘要，
恢复含内部哈希校验。

随机读取每种可用类别 128 次：按文件字节加权、独立小文件/大文件组、跨块窗口。
请求最多 4096 bytes。open_reader 已打开清单；open_and_read 计入每次打开/关闭。
两者均温 OS 缓存，重新打开不等于冷磁盘。记录全部样本、median、样本标准差与
nearest-rank p95；不存在的类别为空。

真实数据为原 UCI、SciFact、QASPER train/dev v0.3、Wine Quality red/white。
合成重复仅做去重对照。来源与固定哈希随结果保存。受控实现支持 2 GiB 输入；
旧 bench 的历史 TAR 基准仍为 64 MiB。

## 增量场景

SciFact 最大文件 corpus：尾部追加、中间插入、等长替换、重命名；另测最小文件删除。
Zstd/1 MiB 下比较完整编码与旧块复用，1 次预热 + 5 次测量，每次逐字节比较恢复。
所有新快照独立，源文件仍全量读取。固定分块中间插入可能改变后续块地址，必须同时
报告复用比例、完整写出量与时间。

## 边界与发布

单机器、温缓存、后台负载未隔离；尚无能耗或推理质量结果。CSV 仅覆盖受支持数值
表格，净收益按完整归档字节比较，负结果也保存。受控对照不能代表所有成熟 seekable
系统。v0.1.0 方法与结果在其 tag 保留，两版协议不同，不直接比较耗时作因果结论。

本地测试、恢复验证、JSON、规范、README 和 Release 说明完成后打 tag。CI 运行
Windows/Linux、Python 3.10/3.13 的核心与 Zstd 测试，以及 Rust 骨架测试；通过后发布
wheel、源码包与实验记录 ZIP。

摘要和图形可从 JSON 重新生成（绘图依赖另装）：

```powershell
python -m pip install -e ".[plots]"
python scripts/summarize_controlled.py results/local-controlled --plot
```
## 数值字节实验

v0.10协议见[NUMERIC.md](NUMERIC.md)：两个公开原始int16波形记录与随机字节负对照，
同v4容器的普通codec/字节重排/XOR消融，完整归档与专用源模块成本分别记录。

v0.11协议见[SCIENTIFIC.md](SCIENTIFIC.md)：三个完整原始浮点FITS示例、前版同一ECG、
同一随机负对照，每组18条件、五轮、统一v5容器；新增单线程固定python-blosc1.11.4
无过滤/字节重排/位重排消融。完整恢复计入首次导入，正式范围读在查询预热之后；
依赖已安装的归档增量与整个专用库/适配源分配一次的成本分别报告。
所有请求跨条件/生命周期逐字节匹配；条件与轮次打乱，数据/源码/依赖SHA前后核对。
CI的Python矩阵安装scientific extra以覆盖专业codec，Rust仍只用于既有CSV/Gear。

v0.12类型/布局规则及联合验收在读取新验证文件压缩结果前冻结，见[LAYOUT.md](LAYOUT.md)。
每组20条件统一v6，五轮比较固定/分段与整文件/图像重排；新M13 float64与ROSAT
记录作为验证，Spitzer开发记录及ECG/噪声回退对照全部保留。编码器只识别FITS白名单。
本轮与既有归档core相同：打包文件flush/fsync，解包文件关闭后校验发布，未逐文件
fsync；此前部分说明对恢复持久性描述过强，当前规范已校正，不计未执行的操作。

## v0.23真实正文修订与JATS来源

eLife固定六篇三版本，12次正文投影变化，13状态、固定/Gear三策略各三轮。
JATS原始XML整文件为精确记录，新kind需v0.23，旧v0.22来源解码器拒绝；旧来源
兼容，应用清单/归档/CAS不改。4212正式/936历史身份查询对齐重建，177测试
通过/1权限跳过。所有预算策略逐次因旧+新整篇记录>256KiB完整检查点，v4无增量
索引收益；默认仍v3。0模型调用，新6篇非大样本；详见[PAPER-REVISIONS.md](PAPER-REVISIONS.md)。

## v0.24 JATS原范围审计与预算预检

协议docs/JATS-FRAGMENTS.md，51模块冻结3b296e1，复用六篇18文件/12修订；完整报告
results/v0.24.0/SUMMARY.md。9进程162解析、1854范围审计、26历史CAS快照、144相邻
必要条件规划。无生产片段索引/查询性能/新QA；181测试通过、1权限跳过。

## v0.25 内容锚定原范围

协议docs/JATS-ANCHORS.md，51模块冻结d0fdcdd，183测试通过/1权限跳过。
复用六篇18文件，1854范围/144规划/162解析/26历史CAS审计；固定/Gear content/v4
乐观仅3/12和2/12，完整父校验0/12，暂缓生产集成。完整报告results/v0.25.0/SUMMARY.md。

## v0.26 全QASPER dev覆盖

协议docs/QASPER-COVERAGE.md，52模块冻结8bc803c；3轮3015 top20正式查询/3预热，
1005问题/281论文，三轮完整身份/分数一致，187测试通过/1权限跳过。论文召回、
参考证据映射和上下文预算分别评分，无新API/官方F1。报告results/v0.26.0/SUMMARY.md。

## v0.27 同检索/同预算证据选择

协议docs/CONTEXT-SELECTION.md，53模块冻结a29175f，候选CI 40192284649通过；
10794查询/6预热、64764预算绑定，190测试通过/1权限跳过。规则未在train gold调参，
24KB区间跨零、48KB train有净退步，保持显式、不切默认。报告results/v0.27.0/SUMMARY.md。

## v0.28 上下文API合同

协议docs/CONTEXT-API.md，53模块冻结b950894，候选CI 40195294012通过；13正式
本地fixture/0远程模型，旧默认实际POST全等，原句/字节/拒绝路径验证。首个审计
驱动路径清单错误的尝试未接受，新目录重跑；报告results/v0.28.0/SUMMARY.md。
