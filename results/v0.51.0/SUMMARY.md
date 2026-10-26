# v0.51.0 实验报告：原模型与检索方法在封存官方test上的迁移

## 结论与预定门槛

原v0.50模型、BM25/graph/置换控制全部参数不改，封存test协议/原字节身份/exact CI冻结后才首次JSON解析官方test，唯一9fresh worker完成。**源ID质量True / 时间True / 联合True**。新训练0、新模型B0，实际仍使用完整4629668B私有模型，不能把复用说成模型免费。

| 方法 | 每轮评分物理题 | 全部源ID组找全题 | macro ID组recall | micro ID组recall | 全literal组覆盖题 | macro literal recall |
|---|---:|---:|---:|---:|---:|---:|
| lexical | 339 | 22 | 0.251233 | 0.197329 | 6 | 0.117415 |
| graph | 339 | 25 | 0.262793 | 0.216617 | 4 | 0.114925 |
| permuted_graph | 339 | 16 | 0.203937 | 0.163947 | 4 | 0.096361 |

原test340物理行，按先冻结的训练及已见dev qid/规范化问题SHA排除1行，剩339物理题全评分，独立uniqueqid=338。未解/UUID改写不丢分母。九worker原证核验36612次、9整corpus逐字节恢复、完整Store树前后跨worker相同、三方法proof三轮确定；独立题目样本不能乘3或方法数。

主门槛沿v050：graph macro ID recall严格胜lexical和置换控制，完整ID覆盖题数≥两者，三轮均满足。时间联合graph/lexical的query wall/CPU/parent完整wall三对比中位数全部≤1；实际0.997968/0.909091/0.989354，零CPU分母null失败，不加epsilon/补轮。质量和成本门槛分别保留，不能用某个正方向掩盖联合失败或整体低覆盖。

严格literal负方向必须并列：graph全literal组完整覆盖为4题，lexical为6题；macro literal recall也从0.117415降到0.114925。source-ID主门槛通过不能覆盖这个反向，更不能说整体语义证据/回答质量通过。整体source-ID找全25/339仍低，不能把弱增益包装为完整科学推理。

本批query wall中位比0.997968仅约0.2%减少、parent约1.1%，旧dev时间联合False保留；不把本批窄门槛通过称稳定加速或生产性能保证。query计时包含不同selected原记录的读取，未隔离相同I/O下的graph算法CPU增益；不从CPU比单独推算法提速。

## 与原开发集的关系

| 方法 | v050 dev macro IDrecall | dev完整ID覆盖题 | 本test macro IDrecall | test完整ID覆盖题 |
|---|---:|---|---:|---|
| lexical | 0.261750 | 12 /187 | 0.251233 | 22 /339 |
| graph | 0.306802 | 22 /187 | 0.262793 | 25 /339 |
| permuted_graph | 0.221770 | 9 /187 | 0.203937 | 16 /339 |

两个split题目/排除口径不同，跨split绝对分数变化不能当算法变化或显著性证据。原dev质量True/时间False/联合False、15题相对lexical变坏的事实不改；此次test是同一初等科学题库/同一public corpus的独立官方split，非未知领域、跨机器或真实会话复测。没有在dev微调k/seed/预算、重新训练或加入dev共现边。

## 原始数据与模型封存

官方[allenai/entailment_bank](https://github.com/allenai/entailment_bank)固定daac2fdb7ab52ec3ef8f2953f59288c1edd7c2f0，Task1 test原1827479B、Git blob a0c64843ae49f789d74758bf143dcccf8dcf8ba5、本项目SHA ae02515bf620f2cc865a4c6ed60adba595aba575e3ab471ecd27d65e6ff9c52f。准备只下载/原byte/hash/换行数，未读题或gold；代码/协议和输入清单先冻结，然后test首次解析。源/原问题/fullhits/私有模型不公开，输入来源/许可范围沿[冻结manifest](../../docs/entailment-test-inputs.json)。

原corpus11941IDs/11521精确文本组/420alias，v050 train1313行/1308uniqueqid构建一次的model SHA **2f82ee4b28c943038e7a37ddcbd8871443f7a441ddd45a1af599decc8bade183**，byte完全不变。旧code/protocol ca9fddc和旧model freeze UTC 2026-10-26T16:46:13.392440+00:00早于dev/test评分；本test code/protocol `324676758ac2122f1dad7c5114381aea11e717c0`、exact candidateCI `40365132545`成功后，另freeze UTC 2026-10-26T17:07:20.892698+00:00、记录test未解析，再唯一运行9worker。新driver没有train入口，新训练0/新权重0，真实模型存储/加载/原训练成本仍收费。

新排除表在揭test前从已公开v050 dev IDs/normalized question SHA得到，遇到训练或已见dev同qid/规范化问题即排除并明记，不按成绩排除，不把原source高相关度预检当未知数据收益。其余物理题全部评分，重复testqid保留且unique数另报；原model本身未用dev加训练。

## 不变算法和两种证据口径

BM25固定k1=1.2,b=.75、ASCII tokens/原STOP，无embedding/同义词或远程模型。graph按训练问题gold来源ID组共现，distinct训练qid计边；正图3095节点/8088无向边，ID置换控制保持degree/weightdegree多重集。top6词法seed+6加权邻居，再接原词法全序列稳定去重。三方法最多12facts/4096原JSON memberB，超剩余skip继续，原tie/key规则不变，不因test结果重定方法。

ranking/admit只接question字符串和原model，选择/原source验证后才gold。拒绝整row输入，绝不拼answer/hypothesis/context/relevance。固定budget限制原record入证量，不限实际CAS/metadata/OS读取或总RAM；模型/Store/解释器照实计费。

主ID口径按Task1 proof叶source UUID优先、缺UUID只精确decoded文本fallback、alias代表lexmin；未解以annotation SHA不可命中标记留分母，同源只计一组。literal辅助只让annotation逐字等原source可命中；UUID改写和未解都继续留不可命中分母，不把来源ID存在当NLI/annotation正确性证明。每workergold映射：{"provided_UUID": 978, "annotated_text_differs": 832, "exact_decoded_text": 471, "unresolved": 75}。

源ID找全或literal组覆盖均不是生成答案准确率、自然语言多跳推理或生产收益。此候选仍在sdist assessment scripts，未新增wheel图检索API、默认Memory/CLI/UI不改。E3净收益/E4整体/真实长会话/回答质量/无限上下文未验收。

## 独立原文核验与逐题负方向

每selected source原Store zlib/fixed65536/bounded读指定SID/offset/length，保留stored/raw/member SHA/codec/EOF/size，再核原JSON成员身份；不删校验或用decoded缓存。public仅sourceID/locator/SHA/指标/费用，无原文问题或句子。独立analyzer重读raw slice及实际Store范围、独立重建gold、从同model纯排名重放核身份，诊断CPU单列，不能称新正式试次/再训练。

| 轮 | graph相比 | macro IDrecall逐题胜 | 负 | 平 |
|---|---|---:|---:|---:|
| 1 | lexical | 38 | 24 | 277 |
| 1 | permuted_graph | 63 | 9 | 267 |
| 2 | lexical | 38 | 24 | 277 |
| 2 | permuted_graph | 63 | 9 | 267 |
| 3 | lexical | 38 | 24 | 277 |
| 3 | permuted_graph | 63 | 9 | 267 |

没有用全局recall增加遮住受损题，也不把三次相同排名当独立显著性样本。v050原坏analyzer文件/日志保留，本版从已修复的三方法tuple审计器继承，未改原candidate或指标；新增合成真worker检查只提供corpus+test、固定模型、seen-dev排除、原source验证和模型文件不变。

## 原始时间与RAM

| 轮 | 方法 | query wall s | query CPU s | goldwall s | goldCPU s | workerwall s | workerCPU s | parent完整wall s | 观察peakRSS B |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | lexical | 1.701405 | 1.718750 | 0.473414 | 0.484375 | 2.350656 | 2.343750 | 2.465238 | 67379200 |
| 1 | graph | 1.697947 | 1.562500 | 0.439323 | 0.546875 | 2.310991 | 2.281250 | 2.429958 | 67248128 |
| 1 | permuted_graph | 1.707596 | 1.625000 | 0.432445 | 0.500000 | 2.314567 | 2.265625 | 2.430676 | 66629632 |
| 2 | lexical | 1.693013 | 1.734375 | 0.445783 | 0.375000 | 2.312728 | 2.281250 | 2.428167 | 66437120 |
| 2 | graph | 1.700932 | 1.531250 | 0.431027 | 0.562500 | 2.306725 | 2.296875 | 2.420903 | 66306048 |
| 2 | permuted_graph | 1.704806 | 1.640625 | 0.427560 | 0.500000 | 2.305027 | 2.312500 | 2.439982 | 66609152 |
| 3 | lexical | 1.702770 | 1.718750 | 0.428510 | 0.406250 | 2.306586 | 2.281250 | 2.423934 | 66576384 |
| 3 | graph | 1.695736 | 1.609375 | 0.412583 | 0.484375 | 2.283110 | 2.250000 | 2.398130 | 66588672 |
| 3 | permuted_graph | 1.720999 | 1.796875 | 0.438471 | 0.359375 | 2.336062 | 2.328125 | 2.451128 | 66580480 |

query包含完整检索/入证/snapshot开关/原selected读取核验，model加载/解析test/建Store在worker与父从启动到末尾退出的完整时间内；gold在选择后另列。私有question-check与公开proof序列化在query外但worker/parent内，没有把小函数时间冒充端到端成本。

![同一模型官方test迁移](question-test.png)

标准图实际打开检查：来源macro recall/完整ID覆盖率/query wall中位数，单位/标签/余白无裁切；并非生成答案准确率。未提供整个科学任务总体置信区间，RSS只是worker观察区间的系统peak，不是完整生命周期增量RAM。CAS完整B/SSD物理/全系统IO/冷缓存/跨机仍未测null。

## 完整模型、文件与源码费用

首轮实际文件/加载成本；其余轮JSON逐项保留：

| 方法 | 全Store B | 原source副本B | 其它私有worker文件B | 实际完整model加载B | 总入证B |
|---|---:|---:|---:|---:|---:|
| lexical | 315673 | 909930 | 139579 | 4629668 | 301680 |
| graph | 315673 | 909930 | 140219 | 4629668 | 303733 |
| permuted_graph | 315673 | 909930 | 140358 | 4629668 | 305576 |

实际每worker（包括lexical）载入同一4629668B完整模型；shared索引/locator/alias/训练qid-hash 3770271B、正图425128B、控制图434231B仅作为部署情景，不能声称实测lexical没有载graph。原一次训练wall 1.455500s/CPU 1.437500s、父完整wall 1.547749s作为历史共享成本仍列，新增训练0不是旧模型或训练免费。

共享私有输入及准备物理文件总21059287B（含未用Task3/train/dev/license/metadata与两个test副本），所有B/SHA在measurement-context；两个test byte副本为固定loader方便，不改原字节，也不说必须部署两份。每workerStore全部CAS/config/snapshot/残留、source副本、plan/真实question-check/ledger全计B；9评测副本非生产常驻9份。input/plan/privatequery/ledger/child/parent exclusive+fsync，内部Store次数null，不称掉电。

9child+parent公共原始JSON16436638B、driver日志0B。完整65递归Python+HTML源码416514B，原runtime仅版本；旧evidence_retrieval/source_alignment逐字等v050，专用/复用脚本实际B/SHA、协议/input/测试源码分别列。没有把私有模型图/原问题/科学源打包发布；平台/依赖未分配，不称完整TCO。

独立二次源/gold/排名重放/全树/全恢复/标准图额外wall 27.937384s、CPU 26.046875s、观察RSS 128946176B，不含解释器初始启动与写本计时记录。原source/index/catalog/所有proof也占RAM，入证4096B不等于RAMcap或物理读取cap。

## 复现与交付

原v050同SHA模型与原合法corpus/Task1 test；新work/out运行scripts.run_question_test，再scripts.analyze_question_test带work/out/inputs/model/model-freeze/freeze/test-log。268检查267通过/1Windows权限跳过，冻结CI成功后唯一9worker，无重跑/调参。原数据/私有模型自行在本地取得，不重分发。

代码/协议/无原文原始JSON/标准图实际视觉检查/详实报告/README/路线/release推送GitHub；CI后actual5资产SHA/65递归Python+HTML/tag/新旧脚本、物理仓库外actual wheel+current native/actual sdist新test worker/seen-dev排除/固定模型/原Store合成smoke及旧功能、最终proof上传重下载全通过才完整收尾，再下一版。

下一项应先诊断剩余漏证在不可定位来源、词法无召回、排序/图邻接或固定入证预算中的比例，而非在此test调参数追正；oracle诊断若实施须另冻协议并明确非可部署检索器。旧24模型API耗尽0新增，本机CPU离线；真实科学源/questions/fullhits/model图/帧恢复副本/私有研究/模板/个人报告/密钥不发布。E3净收益失败，E4整体/真实长期会话/语义证明/回答质量/无限上下文未完成。
