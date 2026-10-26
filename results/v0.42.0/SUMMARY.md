# v0.42.0 实验报告：单trace有界已验证块复用

## 结论

完整2×2（cache OFF/ON × meter OFF/ON）各3轮、12个fresh worker。1200 proof与v0.40逐case一致，1152主问题/48控制/24篡改负审计符合预期，3420原record绑定、同轮四条件全memory文件集合/字节/SHA相等。工作量门槛 **True**，不带CAS仪表的时间联合门槛 **True**。不隐去失败方向，不自动集成默认路径。

本版仅解释并测试v0.41发现的重复整块解码。fixture链节点本来就集中在同块，明显有利于复用；即使门槛通过，也不能推广到跨块、真实科学问题/长对话或模型回答能力。E3净压缩收益与E4整体仍未验收，0新增模型调用。

## 冻结与方法

246本地检查245通过/1Windows权限跳过后，cache候选/计量驱动/独立analyzer/协议于`b04bb05fea32359f73cbae58355f8d5d128988a4`冻结，CI `40320128717`成功后唯一正式计划执行。原64 runtime仅版本号变化，旧v0.40 worker/fixture/源清单与v0.41 cas_traffic字节不变，无新数据挑选/训练/模型构建。原13源SHA、96问题seed、3hop和4096B入证均不改，正式重试0。

因为v0.41 observer trace wall中位比1.1168，本版预先采用完整factorial而不是只在meter ON下比速度。A=cacheOFF/meterOFF、B=cacheON/meterOFF、C=cacheOFF/meterON、D=cacheON/meterON；固定ABCD、BADC、CDAB三轮顺序。meter OFF的缓存配对才评时间；meter ON配对只评CAS工作量，observer×cache交互留在原值。未追加轮次追显著，CPU量化0保留。

## 缓存和完整性合同

新QueryBlockCache是独立评测程序，只在一个目标SID trace内包装该Store实例block。固定65536B retained decoded payload上限，LRU；key=(content hash,expected_size)。miss调用原Store.block，保留stored/raw SHA、EOF、codec与长度校验；容纳时在decode前按expected_size淘汰；超cap块正常读/解码但不入cache。hit再核key/正整数size、实际len和raw SHA。每hop的原Memory record SHA/JSON成员绑定仍执行。

hit不重新读取文件或核stored hash，这是请求内已验证内容视图；新trace必须重读验证，不能跨请求/目标SID/memory保留。异常和正常scope退出都恢复原实例方法、清空payload。内部index replay同content hash可共享，但不把请求状态带入下一次查询。没有更改Archive/Memory格式或默认设置。

真实CAS必要检查覆盖重复读仅miss调用原函数、两块LRU淘汰、oversize不入cache、wrong size拒绝、缓存内容改写raw SHA拒绝、异常恢复和新trace遇坏源拒绝。破坏仅用owned单元临时副本，没有破坏原数据后重跑。原v0.40完整进程漏项保持原样，本版父测完整wall沿v0.41新sidecar合同，不回填旧记录。

## 精确分母和机械结果

每worker96主问题（93完成/2missing/1cycle）+4预算/跳数/非法引用/未知key控制+2篡改负审计。12worker合计1152主问题=1116 complete+24 missing+12 cycle、48控制、24负审计，不能报成1152全都回答。1200 proof保持旧值、原路径和相同指定SID；3420接受的原record绑定全部通过。每轮四条件全memory文件相等，HEAD与所有已有文件SHA保持，新增派生路径仍单独收费。

meter ON600trace守恒，meter OFF600计数null；cache ON600请求满足requests=hits+misses、payload peak≤65536、退出payload0，正式负载无oversize/解码失败。meter ON时实际decode_successes=cache misses。cache OFF计数null，非把未观测当零。所有原始worker/meter/parent JSON逐项保存。

## 成本原值

| 轮 | cache | meter | CAS应用返回B | CAS解码输出B | trace wall s | trace CPU s | parent完整wall s | cache payload peak B | 引用图footprint peak B | 观察peakRSS B |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | off | off | null | null | 0.355091 | 0.281250 | 1.356911 | None | None | 39145472 |
| 1 | on | off | null | null | 0.341572 | 0.312500 | 1.343046 | 65536 | 66190 | 39534592 |
| 1 | off | on | 814700 | 18808832 | 0.419500 | 0.375000 | 1.470851 | None | None | 39428096 |
| 1 | on | on | 280993 | 6488064 | 0.386106 | 0.328125 | 1.486707 | 65536 | 66190 | 39383040 |
| 2 | off | off | null | null | 0.330024 | 0.265625 | 1.293767 | None | None | 39280640 |
| 2 | on | off | null | null | 0.326716 | 0.265625 | 1.322289 | 65536 | 66190 | 39038976 |
| 2 | off | on | 814700 | 18808832 | 0.372911 | 0.359375 | 1.350528 | None | None | 39387136 |
| 2 | on | on | 280993 | 6488064 | 0.328978 | 0.296875 | 1.296450 | 65536 | 66190 | 38944768 |
| 3 | off | off | null | null | 0.328244 | 0.281250 | 1.359307 | None | None | 38834176 |
| 3 | on | off | null | null | 0.314855 | 0.250000 | 1.296693 | 65536 | 66190 | 39211008 |
| 3 | off | on | 814700 | 18808832 | 0.374207 | 0.234375 | 1.379014 | None | None | 39518208 |
| 3 | on | on | 280993 | 6488064 | 0.328469 | 0.203125 | 1.274871 | 65536 | 66190 | 39120896 |

CAS计数是Python应用对象文件read返回B和CAS decoder输出工作量，沿v0.41范围，不是SSD物理IO/全系统IO，metadata/stat/buffer预取/SQLite C层未覆盖。4096B仍是入证record预算，65536B仍只限cache retained payload；都不能当实际读盘或总RAM上限。物理SSD、全系统读和冷缓存/跨机均未测。

引用图footprint只统计缓存实例/映射/被引用key和bytes的浅层图，包含payload但未覆盖所有patch bookkeeping/解释器/瞬态分配；不能称增量总RAM。worker RSS观察点仍在最终报告输出前，非完整生命周期外部采样。新cache源码、metadata、RAM与hash/CPU开销都不是免费。

## 事先成本门槛

meter ON三对cache ON应用CAS返回B与解码输出B均严格减少才通过工作量门槛：**True**。meter OFF三轮成对比率中位数：trace wall `0.9619275063736824`、trace CPU `1.0`、parent完整wall `0.989782083766798`；三者都≤1才过时间联合门槛：**True**。分母CPU若0则null且该门槛不通过；不加epsilon、追加轮或剔除反向例。

原始逐轮比率在derived-metrics.json，包含所有时间反向/噪声。meter ON的时间仅作诊断，不能将少触发仪表的差值当算法速度收益。若工作量通过而时间/RSS不理想，结论只能是减少了这个范围的工作量，不是完整生产净收益。

![工作量、不带仪表的时间和RSS](cached-paths.png)

标准图已实际打开核验，单位/图例/柱形无覆盖。左图使用meter ON，时间和RSS图使用meter OFF，避免混用观测条件。

## 全部费用与复现

每个独立memory目录仍1171964B，其中derived路径166682B，四条件所有源/旧snapshot/索引/manifests/HEAD/derived及残留SHA一致。12目录是评测重复，不能当实际部署需要12份。原始worker+meter/cache+parent JSON合计5166866B单列评测费用；本地fixture输入/原ledger/log、图表/其他分析metadata另属评测产物。

完整runtime64 Python模块+HTML共413548B；缓存/driver/analyzer、CAS仪表及复用旧worker/fixture的大小与SHA在source-resource.json，cache是评测候选源码，不冒充免费内建runtime。无权重/字典/训练或新native性能费用；平台/解释器/依赖未分配成本不能解释为完整TCO已覆盖。

复现用新的work/out：python -m scripts.run_cached_paths，再用冻结Git历史与实际246测试日志运行analyze_cached_paths。12 parent sidecar由subprocess.run前后perf_counter记录，含真实退出码/报告SHA并exclusive+fsync；原child报告不回写。失败/timeout600s保留，不覆盖重跑。

246本地测试245通过/1权限跳过。Release需CI后实际资产SHA/全部64模块+HTML/协议/脚本/raw、物理仓库外实际wheel/current native和实际sdist缓存命中/单次decode/清空及既有兼容、最终proof重下载通过后收尾。native仅既有功能smoke，非缓存性能证据。

下一步仅在当前额度允许时研究固定跨块负控制布局的迁移，先冻结源/预算和比对；不能根据这批same-block结果调cap或默认集成。真实开放检索/自然语言多跳/长期会话/回答质量/无限上下文仍未验证，旧24模型API预算耗尽，本版0新增请求。
