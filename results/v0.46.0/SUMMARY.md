# v0.46.0 实验报告：既有SciFact固定SID三键批查询的视图复用迁移

## 结论与验收

24 fresh worker的唯一冻结计划完成，768 bundle、2304原record绑定、24整corpus逐字节恢复、6组同轮同负载四条件proof和完整memory树身份全部通过。两个工作负载预定CAS计数相等控制与meterOFF时间联合门槛如下；正负方向均不改阈值。

| 工作负载 | 全CAS计数完全相等控制 | 时间联合≤1 | query wall中位比 | query CPU中位比 | parent完整wall中位比 |
|---|---|---|---:|---:|---:|
| spread | True | True | 0.439709 | 0.444444 | 0.814747 |
| repeated | True | True | 0.426059 | 0.405405 | 0.811258 |

比例均为同轮ON/OFF三对中位数，不从跨版本绝对时间推速度。每负载query wall/CPU/parent完整wall全部≤1才过联合时间门槛；CPU分母0时null失败，不加epsilon/重测追正。meterON时间只诊断，不把少触发仪表当算法收益。三个重复轮仍同一确定性工作负载，不是独立科学任务样本或总体置信区间。

本版**科学原始记录上的指定来源批读取机制实验**，没有问题理解、未知paper检索、自然语言多跳、生成回答或真实长期会话。原科学语料本项目已用过；本轮工作负载为新协议，不能称未知数据验证。即使时间门槛通过，也不证明回答质量、无限上下文或生产收益。默认Memory/Archive未集成，E3净压缩收益/E4整体仍未完成。

## 输入、选择器和独立身份

SciFact corpus.jsonl 8307875B、5183唯一doc_id，原字节SHA b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62。公开来源/原archive SHA和许可见dataset-provenance.json，沿项目v0.30及更早来源；不用claim/label、不改原字节/文件布局、不追加科学更新。标题/摘要/原行/恢复副本与完整hit proof只留本地.tools，不发布。

key按SHA256(ASCII rkv046:+key)再key排序，spread32bundle取前96互异key连续三元组；repeated32bundle取接续32key各重复三次，两个集合互斥。实际唯一选择128文档，不把2304次绑定当2304独立文档或成功回答。Random(20261026+round)只打乱顺序，同轮四条件相同，三轮仍相同128文档。

每bundle显式三key、固定SID，每lookup完整hits应只包含所指原record。没有检索难度/无证问答分母；正式负审计/无证控制为0，必要拒绝检查只在合成单元中，不混入正式分母。没有沿用trace的4096B入证预算：这是新的直接known-source批查询，actual selected record B单列，不能称4096B内任务或三跳推理。

原catalog按splitlines(keepends=True)读真实offset/length/行SHA/JSON成员，独立构造完整expected hit（D0/key/title/sentences/rankNone/source_bytes_verified/指定SID路径locator），原lookup与QueryView都要逐字段等它。analyzer再次读私有完整proof核原成员与公共SHA/locator，篡改不会只凭两个候选相等就通过。public各case只含key/SID/locator/record、hit、proof SHA和成本，递归拒绝科学文本字段；私有proof文件SHA/逻辑B照常计账。

## 冻结与执行

255检查254通过/1Windows权限跳过，代码/协议/输入SHA/选择器于`0400c5695ac1d854ada96bc7c75443f1e04eabd3`冻结，exact candidateCI `40342657404`成功后唯一正式运行；正式重试0、训练0、新远程模型调用0。原64runtime仅发行版本变化，scripts/query_view.py/cas_traffic.py字节等v0.45，无decoded块cache或SQL/graph观察器重调。

spread/repeated×viewOFF/ON×meterOFF/ON×3轮24新进程。A/B/C/D=spread off/off,on/off,off/on,on/on，E–H=repeated对应，固定ABCDEFGH/BADCFEHG/GHCDEFAB。每进程只读同一原source，创建原默认v3 memory、完成一次ingest，生成/fsync32bundle，再做96lookup；新work/out exclusive，单worker600s，真实退出码/报告SHA及紧包subprocess.run启动到退出的完整parent wall均保留。

base-only没有delta回放，因此事前要求meterON三对OFF/ON全部整数CAS计数完全相等，**不预期读取字节节省**；重复key仍原record每次读取，不是缓存功能。每轮工作量相同，首轮原值如下：

| 工作负载 | view | 应用CAS返回B/32bundle | decoder输出B | 解码次数 | selected record B（重复计次数） |
|---|---|---:|---:|---:|---:|
| spread | off | 2283382 | 6422528 | 98 | 155245 |
| spread | on | 2283382 | 6422528 | 98 | 155245 |
| repeated | off | 2289018 | 6442473 | 99 | 153483 |
| repeated | on | 2289018 | 6442473 | 99 | 153483 |

meterON384bundle守恒：opens=decode attempts=success、readcalls=2opens、readB=payload+84opens、decoded=compressed+raw；384meterOFF计数为null而非零。384viewON每scope一次view/三lookup、readonly-base/snapshot峰1/delta0，退出恢复lookup/清空resources/关闭实际连接；384viewOFF的view stats null。全部24 memory树前后完全相等、HEAD保持指定SID，没有remember/新派生答案。

## 时间、CPU与RSS原始数据

| 轮 | 工作负载 | view | meter | 应用CAS B | decoded B | query wall s | query CPU s | parent完整wall s | 观察peakRSS B |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | spread | off | off | null | null | 0.552353 | 0.531250 | 1.712914 | 90816512 |
| 1 | spread | on | off | null | null | 0.239010 | 0.234375 | 1.395591 | 89632768 |
| 1 | spread | off | on | 2283382 | 6422528 | 0.557288 | 0.546875 | 1.717197 | 90755072 |
| 1 | spread | on | on | 2283382 | 6422528 | 0.250508 | 0.234375 | 1.392009 | 89718784 |
| 1 | repeated | off | off | null | null | 0.563961 | 0.578125 | 1.709488 | 90718208 |
| 1 | repeated | on | off | null | null | 0.240281 | 0.234375 | 1.386836 | 89731072 |
| 1 | repeated | off | on | 2289018 | 6442473 | 0.556527 | 0.562500 | 1.708732 | 90656768 |
| 1 | repeated | on | on | 2289018 | 6442473 | 0.242346 | 0.234375 | 1.404442 | 89890816 |
| 2 | spread | off | off | null | null | 0.536409 | 0.546875 | 1.698526 | 90771456 |
| 2 | spread | on | off | null | null | 0.237826 | 0.250000 | 1.404321 | 89837568 |
| 2 | spread | off | on | 2283382 | 6422528 | 0.574852 | 0.578125 | 1.765728 | 90513408 |
| 2 | spread | on | on | 2283382 | 6422528 | 0.257032 | 0.265625 | 1.429287 | 89751552 |
| 2 | repeated | off | off | null | null | 0.602930 | 0.609375 | 1.773852 | 90607616 |
| 2 | repeated | on | off | null | null | 0.241652 | 0.218750 | 1.385481 | 89817088 |
| 2 | repeated | off | on | 2289018 | 6442473 | 0.592184 | 0.578125 | 1.755292 | 90497024 |
| 2 | repeated | on | on | 2289018 | 6442473 | 0.259098 | 0.265625 | 1.432945 | 89378816 |
| 3 | spread | off | off | null | null | 0.575782 | 0.562500 | 1.761822 | 90394624 |
| 3 | spread | on | off | null | null | 0.253177 | 0.250000 | 1.422558 | 89309184 |
| 3 | spread | off | on | 2283382 | 6422528 | 0.596732 | 0.593750 | 1.825254 | 90873856 |
| 3 | spread | on | on | 2283382 | 6422528 | 0.261014 | 0.250000 | 1.457304 | 89690112 |
| 3 | repeated | off | off | null | null | 0.586129 | 0.562500 | 1.747232 | 90902528 |
| 3 | repeated | on | off | null | null | 0.252802 | 0.250000 | 1.434384 | 89595904 |
| 3 | repeated | off | on | 2289018 | 6442473 | 0.595279 | 0.578125 | 1.785453 | 90533888 |
| 3 | repeated | on | on | 2289018 | 6442473 | 0.258119 | 0.250000 | 1.443345 | 89710592 |

每bundle query计时包含scope enter/QueryView构建、完整核验、全部observe、三个lookup原record读取与exit关闭。helper/meter对象构造在query计时前，两条件规则相同，parent完整时间仍包含构造/启动/序列化/所有释放。独立audit不在query计时，但worker/parent与另列audit CPU/wall全部收费。SQLite C层/metadata/OS缓存未覆盖，应用CAS B不是SSD物理或全系统IO；冷缓存/跨机仍未测。

![科学记录批查询成本](science-bundles.png)

标准图已实际打开检查，两行分别spread/repeated，query/parent时间与RSS独立图，单位、图例和坐标无裁切。全部用于时间判断的条件为meterOFF，RSS只为worker观察区间的系统peak，不是完整生命周期外采样或增量RAM保证；反方向不隐藏。

## RAM、存储与完整费用

下表首轮meterOFF；其他轮逐case/逐worker原值全在JSON。SQLite逻辑页峰page_count×page_size和Python metadata引用图不是完整/增量RAM，不能相加称总内存，也没有64KiB view上限；原raw与完整科学catalog均驻留worker，OFF/ON相同并进入观察RSS，未假称最小部署内存。

| 工作负载 | view | 完整memory B | 原source副本 B | 其他私有worker文件 B | SQLite逻辑页峰 B | Python metadata图峰 B |
|---|---|---:|---:|---:|---:|---:|
| spread | off | 8420243 | 8307875 | 232833 | None | None |
| spread | on | 8420243 | 8307875 | 232833 | 5455872 | 44294 |
| repeated | off | 8420243 | 8307875 | 231233 | None | None |
| repeated | on | 8420243 | 8307875 | 231233 | 5455872 | 44294 |

完整memory含全部CAS/index/manifest/HEAD/空answers及任何实际残留；base-only不产生旧历史科学快照，不能将本次24全源恢复叫24历史会话。source是同一个原corpus的每worker副本；other含私有完整hit科学文本、plan和全文件ledger，它们不公开但B/身份并未免费。24评测副本不是部署常驻24倍要求。input/plan/privateproof/ledger各一次显式fsync，memory内部未知null；child/parent各exclusive+fsync，所有日志/父侧车收费。

24 child+parent原始公共JSON共2086667B、driver日志0B，原source/私有proof/全树分别计账。完整递归64 Python+HTML源码413548B；assessment_programs逐文件B/SHA包括新selector/auditor、driver、analyzer及复用QueryView/traffic/save helper。协议与测试源码B/SHA另在measurement-context.json；不是只算新模块或漏掉递归experiments。解释器/平台/依赖未分配费用不称完整TCO免费；训练/模型/字典新增0。

derived-metrics逐worker另列ingest/query/audit/recovery/workerCPU和parent完整wall；分析额外wall 5.515880s、CPU 3.828125s、观察RSS 113840128B，包含私有原证/全部源恢复/全树与公共无文本核对/标准绘图，不含初始解释器启动和写分析计时记录，不能混为在线查询性能。

## 请求一致性与交付限制

沿v0.45单scope/固定显式SID/仅v3原校验：请求开始完整验证一次view，每次selected record仍原验证；不承诺每hop重查请求中途未选中源/索引的外部篡改，新scope重验。单线程/无并发writer、readonly base，无decoded块复用，不作为默认入口或生产承诺。旧格式和旧功能继续检查。

复现用独立新work/out运行scripts.run_science_bundles --corpus本地同SHA文件，再scripts.analyze_science_bundles带work/out/corpus/freeze/test-log。原科学文献/完整proof不得放入公开results。协议、程序、无原文原始JSON、标准图/报告/README/版本说明推送GitHub；CI后Release，actual5资产SHA/递归Python+HTML/tag与冻结程序、物理仓库外actual wheel+current native、actual sdist新selector/auditor/text-free proof合成smoke及既有格式/CLI、最终proof上传重下载全通过才完成。

下一项须据本结果另冻可证伪假设，不能在这128文档上改selector、预算、观察器追更好分数。旧24模型API预算已用尽，无新远程授权，本版0调用；真实科学源/段/帧/恢复副本、私有研究模型/课程模板/个人报告/密钥不发布。真实长期会话/回答质量/无限上下文未证明，E3净收益仍失败，E4整体未验收。

## 发行前安装核验故障保留

首次新增actual sdist隔离smoke子程序漏import json，NameError中止，原失败日志留本地，B/SHA见measurement-context.json。只修私有发行核验脚本，保留旧日志另开resume日志，仓库外安装/actual sdist selector与auditor/既有功能复测通过；没有重跑或覆盖24worker科学实验，也没改冻结runtime/协议/selector。生成子程序更早的换行转义问题由编译预检发现并修复，不计科学试次。
