# v0.50.0 实验报告：仅问题文本的封存开发集证据定位

## 结论与门槛

冻结代码后，使用训练标注构建一次共享词法索引/共现图/ID置换控制，单独锁定model SHA，再首次打开封存Task1 dev。固定三方法×三轮、9 fresh worker完成。**质量门槛True，时间门槛False，质量与时间联合False**。

| 方法 | 每轮评分物理题 | 全部源ID组找全题 | macro ID组recall | micro ID组recall | 全literal组覆盖题 | macro literal recall |
|---|---:|---:|---:|---:|---:|---:|
| lexical | 187 | 12 | 0.261750 | 0.204167 | 4 | 0.107164 |
| graph | 187 | 22 | 0.306802 | 0.248611 | 6 | 0.114969 |
| permuted_graph | 187 | 9 | 0.221770 | 0.172222 | 4 | 0.098252 |

原187开发物理行，按冻结规则排除与train qid或normalized question相同的0行，每worker评分187行，合格unique qid为187。三次重复结果完全确定，但独立题目样本数不乘3或方法数；未解/改写保留分母，没有只取可解题追召回。质量是来源ID/原文组覆盖，不能称生成答案正确率、自然语言蕴含证明或真实长期会话收益。

主质量门槛事前要求graph的macro ID recall严格胜lexical和置换图，且完整ID覆盖题数≥两者，三轮都满足才True。时间单列graph/lexical三对query wall、query CPU、parent完整wall比中位数都≤1，零CPU分母null失败，不加epsilon/额外轮。实际三比为1.001570/1.048387/1.014759。完整模型/源码/文件/训练费用仍另记，门槛通过也不称完整部署TCO净收益。

## 来源、已见训练诊断与新开发边界

官方[EntailmentBank](https://github.com/allenai/entailment_bank)固定commit daac2fdb7ab52ec3ef8f2953f59288c1edd7c2f0，corpus原11941 source IDs/11521精确文本组/420alias，Task1 train1313行/1308uniqueqid，dev187物理行。原Git blob、本项目SHA256/bytes/原URL在[输入身份](../../docs/entailment-inputs.json)，科学源/原问题/完整私有模型不发布。Task3检索context/relevance和空proof不当本项目输入或gold。

v049训练输入已有253未解和3369 UUID改写，严格source/literal就绪失败继续保留。正图是训练标注来源ID共现，不是逻辑蕴含规则；原ID存在不能证明改写annotation语义等价。此版新增的是在封存dev上的question-only检索，不声称未知科学领域或真实对话泛化。

训练读取源corpus及Task1 train；运行时ranking/admit只接收question字符串和冻结模型，绝不传入gold/answer/hypothesis/context/relevance。选择/原文hits生成后才调用gold映射。dev训练重叠规则在揭封前冻结：qid或casefold/whitespacecollapse问题SHA相同则排除并列原因，不能按成绩排题。dev原byte先下载/SHA并未解析，直到模型freeze后才第一次解析；代码和记录证明这个运行顺序，没有全系统文件访问监视或外部可信时间戳承诺。

## 两套gold与原始来源

主ID口径按Task1 proof叶、原UUID存在优先定位精确alias代表，UUID缺失只允许annotation与source decoded句子逐字fallback；未解以annotation SHA不可检索标记继续留分母。相同source alias只计一组，不把重复叶扩大独立样本。strict literal辅助口径只有annotation逐字等原source才可命中，UUID改写和未解均以不可检索标记留分母；它也不是NLI判定，不说改写一定错误。

每worker相同gold映射计数：{"provided_UUID": 552, "annotated_text_differs": 466, "exact_decoded_text": 218, "unresolved": 46}。ID覆盖与literal覆盖都公开，不能只选较高口径声称推理成功。每selected事实从原Store指定SID的corpus.json原key+colon+value范围读取，核stored/raw/member SHA/codec/EOF/size，再核JSON身份；decoded句子也只发布SHA。

独立analyzer直接raw slice+原Store范围重读，重建gold两口径，不只比较两个候选相等；并从冻结model纯函数重放排名/预算核身份。重放是独立诊断成本，不是追加正式试次/再训练。共核20196次selected原成员绑定、9整源逐字节恢复、9完整Store树前后与跨worker相等；三方法各自proof三轮确定。

## 冻结算法、一次训练和模型成本

267检查266通过/1Windows权限跳过，代码/协议/输入引用于`ca9fddca20024e8f7c3fd5910219022b22f825d1`冻结，exact candidateCI `40361713232`成功后训练一次。训练结束独立exclusive+fsync model-freeze，SHA **2f82ee4b28c943038e7a37ddcbd8871443f7a441ddd45a1af599decc8bade183**，记录UTC 2026-10-26T16:46:13.392440+00:00，之后才揭dev。正式评估9worker重试0、真实训练1、远程模型调用0；合成必要测试的微型构造不算真实科学训练。

BM25固定ASCII a-z0-9小写tokens、len>1、原memory.STOP，无stem/同义词/embedding，k1=1.2,b=.75；N为精确source组，avgdl含零词文档。query词频按次数加权，score降序/key升序。训练graph按每问题可定位gold来源组的无向共现边，weight为distinct训练qid数，未解不构边、重复qid不加倍。图3095非零节点、8088无向边，不把这些边叫语义证明。

graph/permuted先取6词法seed，邻居归一weight×原seedBM25分累加取前6，再接完整原词法序列稳定去重。控制图对全部source代表按固定rkv050control:+key哈希排列做双端ID置换，非零degree/weighted-degree多重集守恒，不调dev salt。三方法都最多12facts/4096原JSON member B，顺序入证，超剩余预算skip继续，不填gold；此budget不是CAS I/O/全RAM上限。

一次训练worker wall 1.455500s、CPU 1.437500s、观察RSS 83959808B，父完整训练进程wall 1.547749s。私有完整model 4629668B；共享词法/locator/alias/qid-hash 3770271B、正图425128B、控制图434231B，组件SHA/bytes均在model freeze metadata。完整JSON外层键等开销也在model总B，不能只加payload冒充总模型。

实际每worker都加载同一完整model（lexical也加载graph/control），实际加载B/RSS/CPU全收费；只将组件B作为可能单方法部署情景，不声称实测lexical未载graph。训练没有GPU/远程LLM，确定性构建的共现模型仍计一次训练和全部权重/索引费用，不称免费规则。

## 汇总审计器故障和追加冻结

原analyze_question_retrieval.py中三处方法tuple在删除隐私字段的开发替换中误变成字符串('lexical')，首个读取round-1-l.json即FileNotFoundError，未生成aggregate或图。原冻结文件/失败日志保留。另增scripts/audit_question_retrieval.py仅恢复这三处固定方法tuple，编译/差异核对后Git独立冻结再审计同一批9worker；没有再训练、重跑正式query、改变gold/指标/门槛。实际追加源码B/SHA/commit和原失败日志身份在audit-correction.json与source-resource另收费，追加说明见docs/QUESTION-RETRIEVAL-AUDIT.md。最终Release CI覆盖全部源码。

此候选仅在sdist scripts，不集成默认Memory/CLI/UI或新增wheel语义图API；依赖本地同SHA科学输入和私有训练模型，不能把评测脚本的能力冒充已默认提供的产品功能。

## 逐题胜负与时间原值

| 轮 | graph相比 | ID recall胜 | 负 | 平 |
|---|---|---:|---:|---:|
| 1 | lexical | 33 | 15 | 139 |
| 1 | permuted_graph | 44 | 7 | 136 |
| 2 | lexical | 33 | 15 | 139 |
| 2 | permuted_graph | 44 | 7 | 136 |
| 3 | lexical | 33 | 15 | 139 |
| 3 | permuted_graph | 44 | 7 | 136 |

没有用总体均值掩盖受损题；该计数依原物理dev行，不当跨数据集显著性证明。逐题selectedIDs/gold组/原locator/字节预算/两套metrics及SHA在原始JSON中，科学题目/句子和postings/图边留私有。

| 轮 | 方法 | query wall s | query CPU s | gold审计wall s | gold CPU s | worker wall s | worker CPU s | parent完整wall s | 观察peakRSS B |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | lexical | 0.937908 | 0.843750 | 0.257382 | 0.296875 | 1.346517 | 1.265625 | 1.453490 | 62046208 |
| 1 | graph | 0.939381 | 0.890625 | 0.249181 | 0.281250 | 1.342014 | 1.312500 | 1.451122 | 60407808 |
| 1 | permuted_graph | 0.935096 | 1.000000 | 0.231163 | 0.156250 | 1.315502 | 1.312500 | 1.423698 | 60448768 |
| 2 | lexical | 0.922157 | 0.984375 | 0.231672 | 0.125000 | 1.305986 | 1.250000 | 1.413197 | 60973056 |
| 2 | graph | 0.939691 | 0.984375 | 0.233638 | 0.187500 | 1.324606 | 1.312500 | 1.434054 | 60256256 |
| 2 | permuted_graph | 0.931471 | 0.921875 | 0.233176 | 0.250000 | 1.316212 | 1.265625 | 1.423830 | 60293120 |
| 3 | lexical | 0.938133 | 0.968750 | 0.263252 | 0.203125 | 1.352472 | 1.296875 | 1.460701 | 60411904 |
| 3 | graph | 0.937661 | 1.015625 | 0.267849 | 0.218750 | 1.359084 | 1.343750 | 1.486108 | 61456384 |
| 3 | permuted_graph | 0.933980 | 0.953125 | 0.237994 | 0.187500 | 1.323755 | 1.312500 | 1.430593 | 59973632 |

query时间含BM25/graph/ranking/admit、每题snapshot开关和原selected范围读取/校验；model加载/解析dev/建Store在worker与parent完整时间中收费。gold解析在选择之后另列，私有question-check/公开proof SHA与序列化在query外但worker/parent内，不把小函数wall称整个流程成本。没有traffic仪表、SSD物理/全系统IO/CAS完整B观测，继续null；不能从召回或时间直接推生产吞吐。

![问题驱动来源定位结果](question-retrieval.png)

标准图已实际打开检查，左macro ID recall、中全部ID覆盖率、右三轮query wall中位数，非答案准确率。图坐标单位/方法名称/余白检查通过，全部负结果均保留。三轮质量重复只是确定性，未构造总体任务置信区间。

## 文件、源码、诊断和资源边界

第1轮全部逻辑文件与模型加载成本（其他轮JSON同样列）：

| 方法 | 完整Store B | 原source副本B | 其它私有worker文件B | 实际完整model加载B | 该worker总入证B |
|---|---:|---:|---:|---:|---:|
| lexical | 315668 | 909930 | 79310 | 4629668 | 166534 |
| graph | 315668 | 909930 | 79408 | 4629668 | 168663 |
| permuted_graph | 315668 | 909930 | 79560 | 4629668 | 167760 |

Store含CAS/config/snapshot/残留，私有其它文件含真实question-check、plan/完整ledger；原question虽不公开，B/SHA没有免费。共享准备目录含未用Task3/dev/license/metadata共17403646B，逐文件成本保留，不能说都是部署必需或免费。9评测副本不是生产常驻9份。input/plan/private-question/ledger/child/parent exclusive+fsync，内部Store fsync未知null，不称断电。

9child+parent原始公共JSON9086948B，driver日志0B。65递归Python+HTML源码416514B、旧runtime仅版本字面量，实际assessment新旧脚本逐B/SHA在source-resource，协议/输入metadata/测试源码另在measurement-context。真实postings/model图不发布，冻结metadata只含身份和成本；新增模型与训练成本不被省略。

observed peak RSS是worker区间系统峰，源/index/catalog/全records及解释器都占内存，不是完整生命周期增量采样。SQLite/原生allocator/全系统读取未覆盖不填零，不从4096B入证推RAMcap；平台/依赖未分配费用不称完整TCO。训练、加载、ingest、query/gold/recovery、workerCPU/parentwall都收费。

独立重放/原证/gold/全树/全恢复/图表分析额外wall 16.321041s、CPU 14.515625s、观察RSS 114839552B，不含初始解释器启动和写分析计时记录，不能混成在线查询或新科学试次。

## 发行与后续

先code/protocol freeze/exactCI，再run_question_retrieval --train一次、单独modelSHA freeze后，run_question_retrieval9worker，audit_question_retrieval核验（原analyze入口失败保留，修复说明见追加协议）。科学源和私有模型须使用本地合法相同SHA输入，不将原题/原文/图模型上传Git或Release。程序/冻结协议/无原文原始JSON/标准图/详实报告/README/release推送GitHub；CI后actual资产SHA/65递归源码/tag/程序、物理仓库外actual wheel+current native/actual sdist新BM25/训练图/置换控制/预算/原Store来源合成smoke、旧功能/最终proof重下载全通过才完整交付。

下一项必须据门槛与失败样例另冻假设，不在此dev上调k、alpha、预算、seed或模型追更高分。本轮只证明或证伪固定来源定位方案，仍非自然语言多跳推理/NLI/生成回答质量/真实长期会话。E3净压缩收益仍失败，E4整体/无限上下文未验收。旧24模型API耗尽无新授权，本机CPU离线0新远程调用；冷缓存/跨机/SSD物理/全系统IO未测。科学原文/问题/帧/恢复副本、私有model图/研究/模板/个人报告/密钥不发布。
