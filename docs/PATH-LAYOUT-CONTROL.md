# v0.43 冻结协议：跨文件块布局负控制

先完整核验v0.42实际发行，再冻结本版代码/协议/输入manifest及CI，唯一一次24worker计划。仅本机CPU离线合成机制迁移，0模型API，不更改默认Memory/Archive路径。64 runtime只变版本；原QueryBlockCache、CASTraffic、evidence_path和gold/auditor字节不变。

## 唯一变化与输入

clustered保留v0.40一份records.jsonl。separated将同一原始JSONL记录按step分到三个文件：doc_id<96按doc_id%3，其余768 distractor按(doc_id-10000)%3；顺序保持原顺序，每条原始行含CRLF逐字节不变。没有额外记录/填充/训练或改变事实/问题/gold。每个文件介于32768与65536B，每个有一块且三文件块ID不同；三个hop定位到不同文件块。路径/offset/SID必然变化，所以不能要求跨布局proof字节相同；记录SHA/quote/值/路径key/状态/预算用量须相同。文件分割可能改变压缩/索引/更新/整树成本，逐项收费，不把这些变化当只改了缓存。

两布局各13epoch，先全部ingest再固定seed生成96问题（32链×SID e0/e6/e12）；same known fixture不称未知数据。冻结manifest列每个epoch全部文件大小/SHA、原corpus SHA及记录multiset SHA。每轮source实际恢复13次逐字节核验；独立auditor继续从指定SID原文件读取每个locator并验证record SHA及JSON成员。

## 完整2×2×2与精确分母

layout clustered/separated × cache OFF/ON × meter OFF/ON，各3轮=24 fresh worker。A/B/C/D为clustered的off/off、on/off、off/on、on/on，E/F/G/H为separated对应四条件。轮顺序固定ABCDEFGH、BADCFEHG、GHCDEFAB。原4096B入证/3hop/65536B缓存payload不调。每worker96主问题（93complete/2missing/1cycle）、4控制、2篡改负审计。总2304主问题=2232complete+48missing+24cycle，96控制、48负审计、2400 proof、6840接受绑定。单worker timeout600s，失败不覆盖重跑。

每布局同轮四条件proof和完整memory文件集合/字节/SHA相等；clustered proof逐case等v0.40；跨布局仅比较独立语义规范化结果及每条原record SHA，不删掉SID核验：各proof仍须绑定自己的实际SID/文件/offset。questions包含SID因此跨布局SHA不同，case顺序/chain/epoch须同。HEAD/旧文件保持，派生100路径记录继续收费。

## 成本与事先门槛

沿v0.42 trace scope，miss保留原校验，hit验raw SHA，退出清空，scope不跨请求。cacheON1200trace requests=hits+misses，payload峰值≤65536、退出0；正式无oversize。meterON1200守恒（readB=payloadB+84×opens，decoded=raw+compressed，decode成功=cache misses），meterOFF1200计数null。cacheOFF计数null。SSD物理/全系统IO/冷缓存/跨机继续null，不能拿应用计数冒充。

工作量门槛逐布局各3对meterON：ON应用CAS read和decoded输出均严格小于OFF。跨块迁移工作量门槛只看separated，若任一相等/更大则失败，不能改成≤追正结果。时间联合逐布局只用meterOFF三对ON/OFF的trace wall、trace CPU、父完整process wall比率中位数都≤1；CPU分母0则null且不通过，不加epsilon/追加轮次。meterON时间和observer交互只诊断。工作量减少、时间通过仍不是生产净收益；同块旧方向是否复现照实保留。

每child JSON/meter侧车/父紧包subprocess.run至退出的完整wall与报告SHA分别exclusive+fsync，失败退出/timeout也留parent；不回写旧记录。保留每轮原值、计量OFF/ON时间及RSS观察值，metadata/瞬态/解释器/依赖未分配成本不能免费。65536仅retained payload，不是全部RAM。缓存浅层引用图、worker RSS观察点非完整进程外采样，按原scope说明。

完整递归runtime Python+HTML、所有复用/专用评测源码、全部memory文件/旧snapshot/derived/残留、source输入、questions/partial/ledger/log/JSON/sidecar/报告图表及训练/编解码/查询/observerCPU分别计账。没有训练/权重/字典，新native仅既有功能smoke，非本候选性能。

必要测试先验证13epoch原始行multiset、文件大小和step定位、实际CAS三块不同、原proof/cacheproof一致/独立原证绑定/退出清空；完整检查后冻结、CI成功再正式跑。独立analyzer核实际历史源恢复和所有proof/计数/账本，不调已见结果。交付原始JSON/标准图实际视觉检查/详实报告/README/release，CI后实际资产SHA/递归源码/仓库外actual wheel及current native/实际sdist布局脚本与缓存smoke/最终proof重下载才完成。E3净收益/E4整体/开放检索/自然语言多跳/真实长会话/回答质量/无限上下文仍未验收。
