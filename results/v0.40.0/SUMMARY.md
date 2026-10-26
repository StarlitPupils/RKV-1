# v0.40.0 实验报告：指定快照的显式三跳证据路径

## 结论及验收边界

三轮288个主问题全部满足预先指定的状态、终值和完整key路径：279条完成、6条因中间源删除明确missing、3条明确cycle；不是“288条全部回答”。另12个预算/跳数/非法引用/未知key控制均按预期不给值，6份篡改派生证明被独立审计拒绝。855个接受的原record绑定与39份完整历史源复核通过。

**机械门槛通过，但整份协议未全满足。** 事后发现冻结的父驱动没有记录协议要求的完整进程wall；只有从导入后开始的worker计时，不能冒充进程启动至退出的完整时间。资源记录完整性记false，完整process wall记null，保留原结果，不补造、不重跑覆盖。物理CAS读取/解压B原本就未仪表化，事先标null，仍为null。这些缺口与证明路径机械成功分别报告。

目前是E4首个合成证据基础设施组件，不是自然语言多跳、开放检索或真实长对话质量验收；E3科学净收益仍未通过。系统能在有限证据预算下回到指定历史原文，不代表无限存储或对所有未来问题都能正确回答。

## 目的、先验假设与冻结顺序

原路线要求先精确保全证据，未来任务再回源。本版只检验：已知起点和指定SID条件下，沿原文显式引用跨三个文档，所有hop能否保持相同SID与原字节身份，后续更新/删除会不会污染旧证据。协议不奖励词法/语义检索，也没有生成模型。

240本地检查239通过/1Windows权限跳过后，候选evidence_path.py、独立审计器/fixture/驱动及协议于`efc12820375924fd6134bf9b10f3418c66ac4056`冻结，CI `40311078879`成功。随后仅生成合成源的13组长度/记录数/SHA，0次ingest或query，清单于`643b6aeb677f66b8fec5a07d85005c053d6df6f1`提交后才跑三轮。正式评分重试0，原63模块除版本标识字节不变，新增一个显式组件；Archive/Memory/default未改。

## Fixture与“迟到”问题的真实含义

初始864个合成JSONL记录：32链×3节点+768干扰。原记录包含固定Unicode、JSON转义、CRLF、引号和1.00e-3字面量；不是任何真实科学实验事实。epoch0初始加12次单writer提交。每步六个chain terminal修订/长度padding更新；epoch6额外删chain31中间doc94；epoch12额外把chain30中间doc91指回doc90构成循环。两个额外结构变动已事先列明。

三个指定历史点为epoch0/6/12；每轮先完成全部13提交，才创建96问题的打乱清单、exclusive写入/flush+fsync锁SHA，再执行trace。时间线ingestion_finished≤questions_fsynced≤first_query_started全通过。结构/seed公开，所以这只是操作顺序上的迟到，不能叫真正未知任务或盲测。SID显式给出，不能叫模型自己完成了时间推理。

问题SHA如下，原始记录中还有相应阶段时间线：

- 第1轮：`8d87862e41d93f0f8b1eaf9fdd105906be98c1cc282b668a1798c35cb95a317f`。
- 第2轮：`08218b4e214f0564f4b4ad6622efd27e6055a8e8e0628b9d344779ee41c2c83f`。
- 第3轮：`58cf88f607c0f2347cd53274c307c47e3af7a0da2ea7f70c677abc16fb4875d7`。

gold来自fixture修订公式/删除循环条件和固定完整key列表，不从候选结果反算；三轮只是同fixture重复，不是三个独立科学样本。源完整SHA见docs/evidence-path-inputs.json，生成源码随包公开；真实科学语料、旧科学帧、私有研究/模板/个人报告不发布。

## 接口、证据与预算合同

trace(memory, root_key, snapshot=required)只调用Memory.lookup(key,snapshot=同一SID)，不调用search、不回退HEAD。原文必须有唯一完整RKVNEXT doc:数字或RKVVALUE指令。默认3跳、4096B证据入证预算；循环/缺证/非法引用/跳上限/预算不足返回独立状态，非complete时value=None。完整性异常抛错，不给猜测值。

证明包含每hop的key、原record父SID/path/offset/length/SHA、sentence_index、解码后的原句及UTF8 SHA，结果primary_evidence=false，派生记录不会替换原始源。独立auditor不调用trace或lookup、不复用其regex；从指定SID的CAS直接read_range，再按原JSON doc_id/abstract成员检查quote/哈希/引用顺序和终值。因为原文件ensure_ascii=True，解码句子的UTF8字节未必是原文件连续子串；合同是原record byte range+成员索引，不能虚称原句已有直接raw byte span。

**4096B只限制加入证明的原record字节，不是物理I/O上限。** lookup读到/验证记录后才知道长度，预算不足的原记录已发生读取但不加入证据。每轮runtime逻辑verified_record_bytes=52504B，admitted_record_bytes=52142B，独立审计逻辑请求另52142B；三轮分别157512B、156426B、156426B。它们不是磁盘读B或解压B。预算控制用1B时没有证据入选，但仍可能读取一条record；额外未知key/无指令也不能藏掉查询成本。

## 固定次数、成功与负控制

- 每轮96主问题中93 complete，2 missing，1 cycle；三轮288/288**状态/值/全路径**符合预期，其中279条有完整终值，9条按预期无值。
- 每轮4控制：doc0预算1→budget；doc0跳限2→hop-limit；doc10000→invalid-reference；doc999999→missing，共12个，全部无终值。
- 每轮2派生副本篡改：首hop错SID、末quote改写后重新计算quote SHA；独立原record审计6/6拒绝。没有破坏源库后重跑。
- 每轮接受285个原record绑定，三轮855；负审计拒绝尝试不混进这个数。每轮290次lookup，三轮870次，不把遇到cycle前的已访问节点或missing调用从成本里删去。
- 分析阶段额外从CAS完整读回39份历史源，与固定原字节及清单SHA一致。它是事后核验开销，不是新增query或吞吐复测。

## 存储、派生记录与旧文件保持

每轮100个主问题/控制结果写入Memory.remember的answers区；这些是合成派生路径，库中record_type沿用通用derived-model-answer命名，不代表调用过模型。查询期间HEAD保持，所有query前已存在的memory文件SHA保持，新增文件只在answers/。没有把临时文件/旧快照或派生链藏在账外。

| 轮 | 查询前全memory B | 新增派生路径B | 最终全memory B | stats未分类差额B |
|---|---:|---:|---:|---:|
| 1 | 1005282 | 166682 | 1171964 | 0 |
| 2 | 1005282 | 166682 | 1171964 | 0 |
| 3 | 1005282 | 166682 | 1171964 | 0 |

每轮实际1171964B，含全部CAS/source snapshots、索引、manifests、HEAD及100派生文件；派生路径166682B照实收费。三轮分别新目录，不能把同一目录当三个样本。Memory.stats与完整递归文件账本差额均0；原ledger留本地，SHA写入公开raw。外部用于生成fixture的当前源文件和评测日志另属评测输入/工具，未冒充部署memory。

运行库递归64 Python模块+HTML共413548B；新增trace源码2880B已包含整库，不能再相加。独立fixture/auditor、驱动、准备器、冻结analyzer和最终plotter的字节/SHA另列source-resource.json。无外置权重/字典/训练/新native性能费用。Python/OS/文件系统及依赖不是完整部署TCO，未分配部分不能解释为免费。

## 时间、CPU与RSS：已测和缺失分开

| 轮 | 13 ingest wall s | 100 trace wall s | 100独立audit wall s | 100派生写wall s | worker内wall s | worker内CPU s | 采样peakRSS B |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.609149 | 0.538497 | 0.123537 | 0.145493 | 1.775669 | 1.593750 | 32411648 |
| 2 | 0.573577 | 0.493872 | 0.109084 | 0.141598 | 1.653834 | 1.562500 | 32796672 |
| 3 | 0.568362 | 0.502945 | 0.111880 | 0.134833 | 1.666570 | 1.531250 | 33333248 |

| 轮 | ingest CPU s | trace CPU s | audit CPU s | 派生写CPU s |
|---|---:|---:|---:|---:|
| 1 | 0.531250 | 0.484375 | 0.093750 | 0.156250 |
| 2 | 0.500000 | 0.546875 | 0.046875 | 0.140625 |
| 3 | 0.531250 | 0.468750 | 0.078125 | 0.109375 |

worker内总时间还包含合成源生成/写入、原ledger、JSON聚合和负审计等未逐项归因开销；不把所有CPU都算查询或用阶段和替代总成本。采样peakRSS是在worker写最终report之前的历史峰值，非外部完整生命周期采样。计时CPU可能有Windows量化，0值保留；不作跨方法加速或显著性声明。

父进程完整process wall未记录，明确null；不能由worker内wall加估计启动值补齐，也不能从文件mtime反推。protocol资源记录因此未全满足，resource-completeness-audit.json与validation.json写false。原始JSON逐项保留，后续新协议才能补测，不能覆盖本批失败。

fixture写fsync每轮13、问题冻结fsync1单列；Memory内部fsync次数未仪表化为null，不把这些算成全部库fsync次数。事后39源/文件账本分析wall 0.301488s、CPU 0.312500s，不充当query吞吐。

![状态、完整memory文件和阶段wall](evidence-paths.png)

初图图例遮柱，原图已保留本地；最终独立plot_evidence_paths只读聚合JSON，将图例放到数据区外，未改raw、门槛或实验。已实际打开最终图检查标题/单位/图例/柱形无覆盖。公开聚合数据可直接重绘，不需要私有输入。

## 复现与发行

先安装scientific可选依赖；运行prepare_evidence_paths生成不存在的新manifest（发布包已有固定清单，无需覆盖），再用全新work/out目录执行：

```powershell
python -m scripts.run_evidence_paths --work <新worker目录> --out <新结果目录>
python -m scripts.analyze_evidence_paths --out <结果目录> --work <worker目录> --freeze efc12820375924fd6134bf9b10f3418c66ac4056 --input-freeze 643b6aeb677f66b8fec5a07d85005c053d6df6f1 --test-log <实际240检查日志>
python -m scripts.plot_evidence_paths --metrics <结果目录>/derived-metrics.json --output <新图路径>
```

冻结analyzer需要Git历史及实际测试日志作出处核验，非脱离Git的独立程序；plotter只需公开聚合JSON。正式原轮不覆写，新的复现轮也不能替换原负结果。安装包smoke另计，不加入288/855分母。

240本地检查239通过/1权限跳过；CI成功后Release，实际资产下载SHA、64模块+HTML/文档/脚本/原始记录与tag核验、物理仓库外实际wheel/current native、显式三跳/旧值/预算拒绝及旧v0.39实际wheel读新来源、历史兼容和最终proof重下载后才算发行收尾。native仅Gear/CSV功能兼容，不是本版路径性能证据。

## 下一步

优先修复实验仪表：在独立新冻结协议中记录父测完整process wall，并实测CAS逻辑块解码/请求放大，区分入证预算、record请求B和真正文件/解压工作量。继续沿用本fixture时明确是已见机械负载复测，不能叫新推理验证，也不为好看而扩大4096B预算。真实开放检索、多跳自然语言、长期会话/回答质量需要另设任务与新增模型预算；当前0新模型请求，冷缓存/跨机/断电/无限上下文均未证明。
