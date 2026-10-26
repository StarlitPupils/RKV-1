# v0.43.0 实验报告：同原记录跨文件块布局负控制

## 结论与边界

固定layout×cache×meter完整2×2×2，各3轮24个fresh worker；2400 proof、6840原record绑定、624历史文件恢复以及每布局四条件文件一致性通过。跨块工作量迁移门槛 **True**，但解码量仅减少1.5406%（应用CAS返回少1.5457%），trace wall成对中位反而增加3.8495%、CPU增加3.3708%、parent完整wall增加1.9613%；**两个布局的时间联合门槛都失败**。默认缓存不集成、不调65536B cap。

| 布局 | 工作量严格减少 | 时间联合≤1 | trace wall中位比 | trace CPU中位比 | parent完整wall中位比 |
|---|---|---|---:|---:|---:|
| clustered | True | False | 0.9139510499995432 | 1.0588235294117647 | 0.9881146466665539 |
| separated | True | False | 1.0384947600856715 | 1.0337078651685394 | 1.0196127788200267 |

v0.42在同块已见合成负载解码量下降约65.5%，本版在相同原行/事实/问题/gold下变更文件布局，检查局部机制能否迁移。此处两个布局仍为已知合成显式引用链、known root/指定SID；不是新科学数据、开放检索、自然语言多跳、长期对话或模型回答收益。时间为本次成对测量，不把跨版本绝对时间差当提速。E3净压缩收益与E4整体仍未通过。

同块工作量仍减少65.5052%，wall中位比0.914，但CPU中位比1.0588使本批时间联合失败；v0.42原通过结果不覆盖，不能用一次通过声称稳定加速。三次重复任务的计时有量化/系统噪声，不等于独立科学统计样本。

分散布局meterON每100trace OFF有3978次block decode、228629972B输出，ON3917次/225107739B、61hit/3818eviction；同块分别287次/18808832B与99次/6488064B、188hit/0eviction。分散布局本身OFF工作量已大幅提高，超过了三hop数量能解释的源块读取。当前仪表没有按调用角色分解，所以不能断言全部来自index replay或以缓存命中解释全部工作量。下一步优先另冻重复验证/请求资源范围诊断，不能简单增cap追收益。

## 冻结、输入及干预

本机248检查247通过/1Windows权限跳过后，完整代码/协议/输入manifest在`fc8732a98740212def36b14e8fe453cc9e196c34`冻结；候选CI `40327182731`成功才执行唯一正式计划。原64 runtime仅版本号更改，QueryBlockCache、CASTraffic、evidence_path、原fixture/gold/auditor保持v0.42字节。冻结analyzer不根据结果改门槛。

clustered保留原records.jsonl；separated将doc_id<96按doc_id%3、其余768 distractor按(doc_id-10000)%3分到step-0/1/2.jsonl，保留组内原顺序。13epoch每条原JSONL行包括CRLF逐字节不变；无新增padding/记录、无训练/参数搜索。manifest逐epoch列各文件bytes/SHA、原corpus SHA、原行multiset SHA，单元核验全13epoch。

三文件各介于32768和65536B，每文件恰好一CAS块且三ID不同，因此三hop定位不同块；cap不能同时装两个该源块。文件分割还会改变压缩、索引、更新和持久化成本，下面全部收费，不能说只改变了cache算法。clustered与separated不是等SID/等path/等offset：各proof仍须绑定各自真实SID/locator/record SHA/JSON成员。

## 计划、分母与独立审计

A/B/C/D=clustered的cacheOFF/meterOFF、ON/OFF、OFF/ON、ON/ON；E/F/G/H为separated同四条件。三轮顺序固定ABCDEFGH、BADCFEHG、GHCDEFAB。每worker先13次ingest，再生成并fsync96问题，之后才查询；生成规则/seed公开已知，不能叫未知迟到问题泛化。4096B入证、3hop、65536B retained payload不变，24worker各timeout600s。

每worker96主问题=93complete+2missing+1cycle，另4控制与2篡改负审计。总2304主问题=2232complete+48missing+24cycle、96控制、48篡改负审计符合预期；不能将2304全报为成功回答。2400 proof接受6840个绑定。独立auditor实际读取指定SID原record核SHA和JSON成员；624历史文件（clustered156+separated468）逐字节恢复符合冻结生成器。

clustered proof逐case等v0.40；跨布局比较原值/状态/路径key/quote/record SHA/预算计数，只有合法的SID/path/offset差异不作字节相等要求。每个布局同轮四cache/meter条件的完整proof与memory文件集合/bytes/SHA完全相同（6组），HEAD及所有旧文件保持，新增100份derived路径继续收费。

正式重试0。正式worker启动前发生两次私有launcher预检失败：LF manifest原本与冻结Git blob字节相同，但Git stat需刷新；随后private launcher缺workspace sys.path。修正仅私有驱动/索引stat，不改变冻结源/协议，原两份失败日志及SHA本地保留，未有worker目录/科学分数产出，不能误计为正式实验重跑。正式24个return_code、独立parent SHA/完整wall原值均保留。

## 工作量、时间及RAM原值

| 轮 | 布局 | cache | meter | 应用CAS返回B | CAS解码输出B | trace wall s | trace CPU s | parent完整wall s | 观察peakRSS B |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | clustered | off | off | null | null | 0.347046 | 0.265625 | 1.421686 | 39055360 |
| 1 | clustered | on | off | null | null | 0.317183 | 0.296875 | 1.401820 | 39067648 |
| 1 | clustered | off | on | 814700 | 18808832 | 0.375679 | 0.390625 | 1.451199 | 39313408 |
| 1 | clustered | on | on | 280993 | 6488064 | 0.341924 | 0.328125 | 1.404030 | 38916096 |
| 1 | separated | off | off | null | null | 1.473747 | 1.312500 | 2.608617 | 39677952 |
| 1 | separated | on | off | null | null | 1.529041 | 1.515625 | 2.674919 | 39481344 |
| 1 | separated | off | on | 9169552 | 228629972 | 1.617817 | 1.546875 | 2.769462 | 39555072 |
| 1 | separated | on | on | 9027821 | 225107739 | 1.615804 | 1.531250 | 2.752093 | 39661568 |
| 2 | clustered | off | off | null | null | 0.319898 | 0.265625 | 1.358933 | 39124992 |
| 2 | clustered | on | off | null | null | 0.292039 | 0.281250 | 1.342782 | 39366656 |
| 2 | clustered | off | on | 814700 | 18808832 | 0.364242 | 0.234375 | 1.444232 | 39141376 |
| 2 | clustered | on | on | 280993 | 6488064 | 0.329857 | 0.343750 | 1.421635 | 39043072 |
| 2 | separated | off | off | null | null | 1.413393 | 1.406250 | 2.509109 | 39690240 |
| 2 | separated | on | off | null | null | 1.472726 | 1.421875 | 2.558320 | 39583744 |
| 2 | separated | off | on | 9169552 | 228629972 | 1.604901 | 1.546875 | 2.734576 | 39571456 |
| 2 | separated | on | on | 9027821 | 225107739 | 1.590962 | 1.546875 | 2.695537 | 39628800 |
| 3 | clustered | off | off | null | null | 0.343834 | 0.390625 | 1.422421 | 39247872 |
| 3 | clustered | on | off | null | null | 0.317639 | 0.296875 | 1.417347 | 39276544 |
| 3 | clustered | off | on | 814700 | 18808832 | 0.384470 | 0.296875 | 1.462309 | 39206912 |
| 3 | clustered | on | on | 280993 | 6488064 | 0.349821 | 0.375000 | 1.439566 | 39313408 |
| 3 | separated | off | off | null | null | 1.483558 | 1.390625 | 2.664332 | 39624704 |
| 3 | separated | on | off | null | null | 1.540667 | 1.437500 | 2.667972 | 39383040 |
| 3 | separated | off | on | 9169552 | 228629972 | 1.607861 | 1.703125 | 2.732466 | 39616512 |
| 3 | separated | on | on | 9027821 | 225107739 | 1.650570 | 1.656250 | 2.810246 | 39542784 |

meterON共1200trace的read/decode守恒通过；meterOFF1200计数null而非零。cacheON1200满足requests=hits+misses、payload峰值≤65536、退出payload0、无oversize；meterON且cacheON时decode_successes=cache misses。hit仍验key/size/raw SHA，每record仍走原完整绑定，miss保留原CASstored/raw/EOF/codec/长度校验。新trace重验，scope结束恢复实例方法，不跨请求保留。

应用CAS read返回B和decoder输出B不是SSD物理/全系统I/O；SQLite C层/metadata/stat/OS预取未覆盖部分保持null，冷缓存/跨机未测。4096B限制入证记录，不限制读盘；65536限制保留payload，不限制metadata/瞬态/总RSS。peak_retained_graph_bytes含映射、引用key与bytes浅层图，未包含全部patch/解释器分配；RSS仅沿worker原观察区间，非完整生命周期外采样。

门槛事先冻结：每布局三对meterON的cacheON read及decoded都严格<OFF才通过工作量；任一相等也失败。各布局时间联合只用meterOFF三对ON/OFF的trace wall/CPU/parent完整wall比率中位数都≤1；分母CPU为0则null且失败，不加epsilon、不追加轮次。逐轮反向例、RSS噪声、meterON时间全部在原JSON/derived-metrics.json保留，meterON时间不用于速度结论，减少仪表调用不能冒充算法提速。

![两布局工作量、无仪表时间和观察RSS](layout-paths.png)

图已实际打开核验：左右列单位明确、两布局分行、图例不遮柱；工作量用meterON，时间/RSS用meterOFF。工作量减少或时间门槛通过仍不等于生产完整净收益。

## 全部存储、CPU及评测成本

下表取第1轮cacheON/meterOFF，各布局四条件整树均相同；源/旧snapshot/index/manifests/HEAD/derived/残留均包含在memory。其他worker文件包括questions/freezes/partial-cases/full-ledger，不能将派生/残留隐去。源码/父侧车/原始报告在表外另收；24目录是评测重复，并非实际部署需要24份。

| 布局 | 完整memory B | derived增加B | 当前输入文件B | 其他worker文件B | retained payload峰B | 引用图峰B |
|---|---:|---:|---:|---:|---:|---:|
| clustered | 1171964 | 166682 | 169654 | 371193 | 65536 | 66190 |
| separated | 955146 | 166227 | 169654 | 362180 | 57833 | 58487 |

原始24 child+meter/cache+parent JSON共10452651B，driver日志0B；图表/协议/汇总/诊断metadata另计。各worker全部ingest、trace、独立audit、derived写入、workerCPU/wall、父完整process wall均在原JSON与derived行表，不能只报读取节省。完整64 Python+HTML源码413548B，评测程序逐项bytes/SHA在source-resource.json，缓存、仪表、布局生成器、复制驱动与analyzer不免费。没有训练/模型/字典费用；平台/解释器/依赖未分配费用不能解释为完整TCO。

独立诊断历史恢复/原证审计/全树核对/绘图额外wall 15.549291s、CPU 13.671875s、观察RSS 89960448B，范围到写诊断计时前，排除启动；它不算在线trace性能。可用新work/out运行python -m scripts.run_layout_paths，再python -m scripts.analyze_layout_paths --freeze及原测试日志复现，禁止复用正式目录覆盖旧轮。

## 交付与下一步

冻结协议docs/PATH-LAYOUT-CONTROL.md、全部原始JSON/输入manifest/源码账本/标准图/本报告随版本交付。Release在CI后生成，再实际下载5资产核SHA/递归64 Python+HTML/actual sdist候选源与results对tag；actual wheel和current native物理仓库外安装，actual sdist布局生成器/缓存/仪表及旧格式/历史来源smoke，最终proof上传后重下载方为完整交付。native仅CSV/Gear功能检查，不是本候选计时证据。

下一步优先根据跨布局异常放大另冻请求内重复验证/资源生命周期诊断，而非增cap或默认集成；当前未测调用角色不可回填。仍无新增远程模型授权（旧24次耗尽），本版0次；科学原语料/私有模型/研究/模板/个人报告/密钥不发布。真实开放检索、自然语言多跳、真实长期会话、回答质量与无限上下文未验证。
