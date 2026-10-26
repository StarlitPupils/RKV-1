# v0.54.0 实验报告：已见SciFact漏证的入证拒绝与图暴露诊断

## 结论、预设假设和边界

**H1（正图漏掉gold论文组至少一半被原剩余byte预算拒绝）=True**，实际比例1.000000。**H2（至少一半有gold主张的top6词法seed有正图边）=False**。这两个是已见结果的定位诊断，绝不是提高预算/增加图边后的实测收益，也不改变v053仅多1篇gold、完整仍139/188、质量True/时间False/联合False的结论。

| 原方法 | recovered | no_candidate | byte_rejected | count_stop |
|---|---:|---:|---:|---:|
| lexical | 146 | 0 | 63 | 0 |
| graph | 147 | 0 | 62 | 0 |
| permuted_graph | 146 | 0 | 63 | 0 |

每方法209个既有gold paper组，四类互斥合计209；总627组来自同一188条有gold主张×3方法，不是627独立问题。三worker各298条（188有gold、110无gold），894条诊断记录不是新增894次科学检索试验。原300行中的2条训练重叠继续排除、不补回；无gold行照常计成本，但gold_categories为空、不产生正确/错误回答分数。

## 为什么需要实际扫描，而不是只看前12名

固定预算是4096原论文JSONL整行B、最多12篇。原admit遇到超剩余B的论文跳过继续，可能接纳排名更后的短记录。v052短句任务的first12位置分区不能直接套到论文，把rank>12全归“篇数上限”会误解释真正的字节拒绝。

本版独立admission_trace按原完整去重候选顺序逐个扫描：已选篇数等于12之后的候选=count_stop；未满12但原整行length超剩余预算=byte_rejected；实际选入=recovered；gold根本不在候选=no_candidate。所有gold必须在原model locators，未知原来源明确失败；原source length必须正整数。每条独立扫描的selected序列和used B须逐项等原v053 proof与冻结admit重放，否则整worker失败，不静默改分类。

byte_rejected表示**在原排序和已选前缀下**这篇未能放入，不表示该gold单篇>4096，也不证明提高预算一定改善目标；替换排序、冗余和CPU成本都未干预测量。count_stop与no_candidate同样只是当前固定序列位置原因，不是语义失败或算法因果归因。保留反例和原预算，未用gold做oracle选证。

## 图暴露与有限增益

| 方法 | 有gold且top6 seed任一有边的主张 | 所有检索主张中selected顺序不同于词法 |
|---|---:|---:|
| lexical | 0 /188 | 0 /298 |
| graph | 26 /188 | 2 /298 |
| permuted_graph | 12 /188 | 3 /298 |

图结构暴露只检查原top6词法seed在固定图中是否有非空邻接；另逐条记录active_seed_count、全部邻居union大小和不在完整词法候选中的邻居数。它不保证邻居被top6扩展采用、能入4096B预算、与gold相关或产生正确回答。lexical自身不使用图，暴露记0是方法行为；控制图使用固定ID置换。changed_selected_order是顺序/成员变化提示，不等于质量正收益。

v053真实训练809行、505有gold、正图64节点/60无向边；5183原paperID从不按相同文本合并。图小和暴露统计可以解释工作点受限，但不能在此dev补边或调seed追正。旧EntailmentBank的graph效果和literal负方向仍保留，不因这个论文任务另造泛化结论。

## 冻结输入与确切运行次数

前版v053 tag `748def47bccd25330b561d34da488b4f6738e9b0`，finalproof `f9750cdc2b40bbbb77c063670cb5fa5b6226f782179b9a6219bd64cea9749419`的实际资产/65源码/物理仓库外actual wheel/currentnative/actualsdist/proof重下载全部通过后，才修改本公开候选。

本版代码/协议/输入SHA freeze `9a83df5f3749d952dd1845e5d6ee8dda535d2e76`、exact candidate CI `40374513981`成功后，唯一3 fresh诊断worker按lexical/graph/permuted顺序各一次，600s/worker，0重试。只是对v053 round1三份已验证report和对应私有query-check作重放；另外两轮不重算，不假装增加科学样本。所有输入report/privatequery/model原byte SHA在先冻结manifest，保留路径/bytes/hash，不公开原query文本。

worker核原report method/round/model/source SHA、原proof SHA、每问题规范化SHA及私有selected序列，再用原model/math重放排序与admit，逐项等原selected/B/ranked_candidates。聚合独立从每条gold_categories重数，核类别全集/守恒、原recovered数、annotated188和retrieved298、row index唯一，不只抄缓存总数。

原模型SHA **f062c7a784421b71bbfaf3c299be78ff323a391847afbf5420e4c06a4d422be0**、实际10152832B，未改任何权重/locator/postings/图/参数。本版**新科学检索试次0、新训练0、新科学源range绑定0、新Store0、新原source副本0、新远程模型调用0**。gold及source身份信任范围来自原v053完整独立审计与冻结report SHA；本版不再次打开原科学corpus或Store read_range，不能把重放当新增独立原证验证。

## 时间、RAM和输入读取成本

| worker | worker wall s | worker CPU s | parent全wall s | 观察peakRSS B | 已计application输入read返回B |
|---|---:|---:|---:|---:|---:|
| lexical | 1.380491 | 1.359375 | 1.484955 | 74035200 | 10740245 |
| graph | 1.387615 | 1.375000 | 1.494214 | 74190848 | 10740269 |
| permuted_graph | 1.384136 | 1.390625 | 1.488667 | 74194944 | 10740267 |

input.read_bytes统计范围仅model+该方法原report+私有query-check返回B，明确不含manifest、解释器/模块加载、OS缓存或后台读；每个worker确实载入同一10152832B完整model，lexical也未去掉两图。source模型/全部metadata/派生记录/RSS不被4096入证上限限制。这些是诊断运行费用，不是v053检索加速，也不能把此版0source range读取当检索器免费读源。

整个driver含三子进程等待/聚合/标准图wall 5.032507s；driver自身CPU 0.562500s不含子CPU（上表另列），观察RSS 78835712B。初始解释器启动/计时记录末尾写入不含于driver自报，三parent则测从启动到退出完整wall。worker退出码/错误/childSHA均独占sidecar，失败不覆盖重跑。

SSD物理/全系统IO/冷缓存/跨机继续null；observed peakRSS不是完整生命周期增量RAM，应用返回B不等于磁盘真实读取。未报告统计显著性或跨平台稳定性能。

![已见SciFact拒绝位置与图暴露](paper-gap.png)

标准图已实际打开检查，两个面板从0起，209组和188题上界留余白、标签/图例可读无裁切。图只是已有结果分类与图结构暴露，不是提高预算后的曲线或模型答案正确率。

## 完整成本、历史资产与必要检查

原模型训练wall 1.071652s/CPU 1.046875s、父完整wall 1.167893s仍作为历史共享成本；0新训练不表示原模型免费。原v053训练和9worker目录全部实际物理文件共112484835B，逐文件B/SHA在measurement-context，包括历史Store所有CAS/config/snapshot/残留、原source副本/私有claim-check/plan/ledger/模型/报告，保留不删。它们是既有评测资产，不声称部署要常驻9份。

完整65递归Python+HTML 416514B，runtime仅版本；所有实际专用/复用assessment脚本B/SHA、协议/input/test另列，不只数新脚本。旧其他任务模型/历史快照/报告未删，不把不随发行包发布等同无费用。平台、依赖及全机TCO未分配，私有科学原料/claims/model/postings/frames/restored bytes不发布。

277检查276通过/1Windows权限跳过。新增4检查：exact预算/超B跳过后续/重复rank/达到count停止、未知来源/非法length/限额拒绝、first6图暴露和词法对照、真子进程toy proof/SHA篡改拒绝。冻结前首稿真worker合成测试发现str output传给Path-only exclusive helper，已改Path后四检查通过，属于候选开发修复，不是真实诊断重跑。私有父控制器首次CI通过后导入scripts失败（未加入仓库sys.path），发生于任何诊断worker/输出目录创建前；仅修私有控制器并另存resume日志后唯一运行3worker，冻结代码/协议不变，原失败日志及SHA保留。原v050/v052及之前失败仍保留。

## 复现、交付与下一步

取得原v053同SHA私有model/三个query-check、公开round1 report并匹配docs/paper-gap-inputs.json，在新out运行 `python -m scripts.run_paper_gap --out <新目录> --model <原model> --manifest docs/paper-gap-inputs.json --freeze <本版冻结SHA>`。命令不训练、不读原科学corpus/Store，不需要新远程模型；私有query原文自行本地保留，不从公开报告猜造。

本版公开代码/协议/无原文raw JSON/标准图/详实报告/README/release；CI后实际5资产SHA、递归Python+HTML与tag、实际外部wheel/currentnative和actualsdist新增admission skip/count/conservation/图暴露smoke、全部旧功能及最终proof重下载后完整收尾。默认Memory/CLI/UI不改、不发布科学原文/个人研究/模板/密钥。

后续只能另冻独立假设或实现严格来源校验的实验API；不能用本次诊断事后改变这批4096B/seed/图再声称封存收益。**E3净收益失败，E4整体、真实长会话、verdict/NLI/语义证明、生成回答质量和无限上下文尚未完成。**
