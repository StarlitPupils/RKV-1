# v0.45.0 实验报告：单trace固定SID的已验证v3 SQLite视图复用

## 结论

两布局×viewOFF/ON×meterOFF/ON各3轮、24fresh worker唯一计划完成。2400proof、6840原record绑定、624历史文件恢复和6组同布局四条件memory完整文件身份通过；全部proof/原SID/locator/来源与v0.43一致。分散布局严格减少工作量与同块计数相等的联合机制门槛 **True**；两布局不带仪表时间联合门槛均见下表。

| 布局 | 先验工作量规则 | 机制门槛 | 时间联合≤1 | trace wall中位比 | trace CPU中位比 | parent完整wall中位比 |
|---|---|---|---|---:|---:|---:|
| clustered | exact_equality | True | True | 0.6077644409389654 | 0.47058823529411764 | 0.9216289721528562 |
| separated | strict_reduction | True | True | 0.40167122626942 | 0.39325842696629215 | 0.6589398600964274 |

分散布局每100trace应用CAS返回9169552→3524832B（少61.5594%）、decoded输出228629972→88037110B（少61.4936%），block decode3978→1535。同块仍814700B/18808832B、287decode，正好满足无源回放的相等控制，不把相等说成读取节省。

meterOFF trace wall成对中位比clustered0.607764、separated0.401671；父完整process wall比0.921629/0.658940，CPU比0.470588/0.393258。三个时间指标都按先验门槛判断，逐轮反向/RSS/observer费用全留，不从跨版本绝对时间推速度。本次三轮重复同一合成机制，非独立科学统计样本，未提供总体任务置信区间。

默认Memory/Archive不改，候选只在assessment脚本；无decoded块缓存，不叠加v0.42 LRU。已知合成显式链/known root/指定SID，不是新科学、开放检索、自然语言多跳、真实长会话、回答提升或无限上下文；E3净压缩收益/E4整体仍未验收。

## 请求一致性和安全边界

QueryView仅单次使用、固定显式SID、manifest v3。trace定时内部进入原QueryResources、原_manifest完整验证，再用原memory_index.view构建/验证一次SQLite视图。有delta为原in-memory replay副本，无delta为readonly base连接；构建后PRAGMA query_only=ON拒绝写SQL。

临时包装同Memory.lookup，沿原512字符/NUL限制与LOCATORS SQL，拒绝缺省/其他SID。每hop仍调用原_verified_hits及原Store.block，读取并核stored/raw SHA、EOF、长度、codec、原record SHA和JSON成员。没有缓存decoded源块、没有提前建view后只测查询。scope退出恢复lookup、关闭真实SQLite连接、清空QueryResources及helper引用，新trace新实例重新验证。v1/v2/v4明确拒绝，本候选不作为通用兼容入口。

**验证时刻有明确差异**：一次请求使用开始时已完整验证的不可变视图，不承诺每hop重查所有未选中源/索引。如果外部在请求中途篡改未再选择的文件，这个trace未必观察到；不能冒充与旧per-lookup重验的观测时刻完全等价。任何被选中的原record仍每次读取校验，损坏必须拒绝；新trace必须拒绝坏base/delta/选中源。仅单线程/无并发writer场景，不称生产化。

必要测试用真实Store验证原proof及独立audit、spy确认一次实际view和每hop原record验证、旧SID/新HEAD不混、缺省/换SID/作用域外拒绝、写SQL拒绝、连接真关闭及实际资源映射清空。请求中选中源坏字节和新trace坏base/delta/源均拒绝，异常路径恢复lookup，旧v1/v2/v4明确拒绝。没有根据性能结果放宽校验。

## 冻结与唯一计划

253本地检查252通过/1Windows权限跳过（最终readonly log）后，代码/协议/输入引用于`4a0bfab61ad667f7c7c707057c35eed6969d382c`冻结，exact candidateCI `40337615085`成功再正式运行；正式重试0。原64 runtime仅版本字面量变化；旧v0.43 base_worker/fixture/gold/auditor/manifest及v0.44 CAS仪表字节不变，4096B入证/3hop/65536chunk/默认replay预算不调。

A/B/C/D为clustered viewOFF/meterOFF、ON/OFF、OFF/ON、ON/ON；E/F/G/H为separated对应，固定ABCDEFGH、BADCFEHG、GHCDEFAB。每worker13epoch全部ingest后才生成/fsync96问题，公开已知结构/seed，不称独立未知迟到问题泛化。

每worker96主问题=93complete+2missing+1cycle、4控制与2篡改负审计。总2304主问题=2232complete+48missing+24cycle、96控制、48负审计符合预期，不能将2304全算成功回答。2400proof接受6840绑定；独立auditor实际读指定SID原record及JSON成员，624历史文件（clustered156+separated468）逐字节恢复。每布局同轮四条件proof和全部memory文件相等，HEAD/旧文件保持，派生100条路径继续收费。

## 原始工作量与时间

| 轮 | 布局 | view | meter | 应用CAS返回B | decoded输出B | trace wall s | trace CPU s | parent完整wall s | 观察peakRSS B |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | clustered | off | off | null | null | 0.320527 | 0.343750 | 1.380994 | 39550976 |
| 1 | clustered | on | off | null | null | 0.193421 | 0.109375 | 1.244276 | 39157760 |
| 1 | clustered | off | on | 814700 | 18808832 | 0.361773 | 0.375000 | 1.401822 | 39202816 |
| 1 | clustered | on | on | 814700 | 18808832 | 0.215359 | 0.218750 | 1.273505 | 39231488 |
| 1 | separated | off | off | null | null | 1.406036 | 1.390625 | 2.492743 | 39514112 |
| 1 | separated | on | off | null | null | 0.569010 | 0.546875 | 1.654556 | 39370752 |
| 1 | separated | off | on | 9169552 | 228629972 | 1.528675 | 1.453125 | 2.654218 | 39485440 |
| 1 | separated | on | on | 3524832 | 88037110 | 0.625904 | 0.562500 | 1.793896 | 39202816 |
| 2 | clustered | off | off | null | null | 0.318364 | 0.203125 | 1.334103 | 38948864 |
| 2 | clustered | on | off | null | null | 0.193491 | 0.156250 | 1.229548 | 39235584 |
| 2 | clustered | off | on | 814700 | 18808832 | 0.355657 | 0.343750 | 1.395723 | 39321600 |
| 2 | clustered | on | on | 814700 | 18808832 | 0.218697 | 0.093750 | 1.286948 | 39370752 |
| 2 | separated | off | off | null | null | 1.414124 | 1.328125 | 2.516508 | 39424000 |
| 2 | separated | on | off | null | null | 0.568013 | 0.484375 | 1.658227 | 39608320 |
| 2 | separated | off | on | 9169552 | 228629972 | 1.528792 | 1.421875 | 2.691025 | 39747584 |
| 2 | separated | on | on | 3524832 | 88037110 | 0.622553 | 0.531250 | 1.718378 | 39526400 |
| 3 | clustered | off | off | null | null | 0.310876 | 0.265625 | 1.361125 | 39297024 |
| 3 | clustered | on | off | null | null | 0.194588 | 0.125000 | 1.267441 | 39407616 |
| 3 | clustered | off | on | 814700 | 18808832 | 0.352692 | 0.312500 | 1.416755 | 39337984 |
| 3 | clustered | on | on | 814700 | 18808832 | 0.216426 | 0.218750 | 1.282242 | 39272448 |
| 3 | separated | off | off | null | null | 1.404883 | 1.265625 | 2.530848 | 39538688 |
| 3 | separated | on | off | null | null | 0.563685 | 0.500000 | 1.633396 | 39407616 |
| 3 | separated | off | on | 9169552 | 228629972 | 1.550188 | 1.468750 | 2.676356 | 39383040 |
| 3 | separated | on | on | 3524832 | 88037110 | 0.619583 | 0.593750 | 1.745028 | 39276544 |

meterON1200 trace守恒，meterOFF1200计数null而非零；viewOFF/meterON逐case所有计数等v0.43对应cacheOFF/meterON，不改旧基线。viewON1200均一次view、lookup_calls等proof.lookup_calls，退出lookup恢复/resources清空/连接真关闭且inactive；viewOFF观察null。原应用readB=payloadB+84×opens、decoded=raw+compressed、readcalls=2×opens等合同保持。

事先门槛为separated三对meterON的ON read/decoded都严格<OFF，clustered三对都完全相等；不能把原要求改成弱不等追收益。分布局时间只用meterOFF三对中位trace wall/CPU/parent完整wall均≤1；CPU分母0则null失败，不加epsilon、不追加轮数。meterON时间仅诊断，不把少触发仪表当优化加速。

应用CAS read返回B和decoder输出不是SSD物理/全系统IO；SQLite C层/metadata/stat/OS预取未覆盖部分继续null。4096B只限制入证record，不限制读盘；65536是源chunk大小，不限制view全部RAM。

![两布局视图复用成本](view-paths.png)

标准图已实际打开检查，单位/图例与两布局分行无覆盖；工作量用meterON，时间/RSS用meterOFF。RSS保留反向和系统噪声，仅原worker观察区间，非完整生命周期外采样；不能凭相近RSS宣布没有内存费用。

## RAM、完整文件与诊断费用

下表第1轮viewON/meterOFF，其他轮原值均在JSON：SQLite逻辑页为page_count×page_size，不是实际增量总RAM；Python图只遍历manifest、QueryResources映射与Snapshot.files等容器/引用对象，排除SQLite原生buffer/allocator和所有patch bookkeeping。两项不相加冒充完整RAM。scope内observe和所有建view/核验/关闭费用已在trace计时内收费。

| 布局 | 完整memory B | derived增加B | 当前source B | 其他worker文件B | SQLite逻辑页峰B | Pythonmetadata图峰B | 快照峰数 | delta峰数 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| clustered | 1171964 | 166682 | 169654 | 371141 | 180224 | 3996 | 1 | 0 |
| separated | 955146 | 166227 | 169654 | 362061 | 180224 | 16490 | 2 | 1 |

每100trace clustered100个readonly base view；separated64个in-memory replay副本+36个readonly base view，ON每worker100view/290lookup。SQLite逻辑页峰180224B不是额外180224B常驻保证，更不是64KiB缓存；文件树虽不变，延长一个连接/内存视图生命周期仍有成本。

完整memory包含全部CAS源/旧snapshot/index/manifest/HEAD/derived/残留；各布局与旧v043完全同树，路径/分割本来不同，不把两布局源存储差当QueryView压缩收益。其他worker文件含questions/freezes/partial/ledger。24目录是评测重复，非部署需要24份。

24 child+meter/view+parent原始JSON共10665559B，driver日志0B，图/协议/汇总metadata另计。完整64 Python+HTML源码413548B，专用与复用评测程序逐个bytes/SHA在source-resource.json；新QueryView/driver/analyzer/旧基线依赖不免费。所有ingest/trace/独立audit/derived/workerCPU和父完整process wall单列，后者紧包subprocess.run到退出，包含启动/序列化/末尾释放。worker RSS观察点不包含全部末尾侧车输出。

独立原证/历史源恢复/全树与计数/绘图额外wall 12.340778s、CPU 10.578125s、观察RSS 91205632B；排除解释器启动和写本计时记录，不混入在线性能。无训练/模型/字典/新远程调用，平台/解释器/依赖未分配费用不能当完整TCO免费。native只既有CSV/Gear功能smoke，非本候选性能。

## 复现和发行

新work/out运行python -m scripts.run_view_paths，再用冻结Git和最终253测试日志运行scripts.analyze_view_paths。每worker600s，exclusive+fsync child/meter/parent侧车，真实退出码、完整parent wall及实际报告SHA保留；失败不覆盖重跑。

协议/代码/输入引用/rawJSON/标准图/本报告/源码账本/README/release随版本。CI后实际5资产SHA/递归Python+HTML/actual sdist候选及raw对tag、actual wheel+current native物理仓库外安装、actual sdist QueryView原proof/固定SID/只读/真关闭/新scope及旧格式/来源/CLIsmoke、最终proof上传后重下载通过才完整交付。候选在sdist scripts中，默认wheel运行库未集成该路径。

下一步须另冻独立安全/工作负载转移假设，不能把这批已见两布局当真实长期收益或直接默认集成。旧24模型API预算耗尽，无新授权，本版0调用；真实科学语料/段/帧/恢复副本、私有模型研究/模板/个人报告/密钥不发布。冷缓存/跨机/SSD物理/全系统IO/真实长会话/回答质量/无限上下文未测或未证明。
