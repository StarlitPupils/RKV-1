# v0.53.0 实验报告：固定图检索方法在已见SciFact整篇论文来源上的迁移

## 结论与结果大小

**论文来源质量True / 时间False / 联合False**。正图只让188条有证据标注的主张中的1条多找回1篇gold论文：micro从146/209到147/209，macro从0.750443262到0.751773050，完整找全题数仍139/188。其余187条主张与词法相同；不能把严格大于门槛通过称显著、稳健或实用收益。耗时联合失败，不继续调预算、seed或训练图追正。

| 方法 | gold论文全部找全主张 | macro paper recall | micro paper recall | 找回gold论文组 | 每条检索主张入证篇数均值 |
|---|---:|---:|---:|---:|---:|
| lexical | 139 /188 | 0.750443262 | 0.698564593 | 146 /209 | 2.862416 |
| graph | 139 /188 | 0.751773050 | 0.703349282 | 147 /209 | 2.862416 |
| permuted_graph | 139 /188 | 0.750443262 | 0.698564593 | 146 /209 | 2.862416 |

最后一列覆盖298条实际检索主张（含110无gold标注），质量列只覆盖188条有标注主张。三方法各条实际入证1–4篇，虽最多12篇，4096原整行B约束并未允许每条拿12篇。没有改为短句预算、裁剪原行或扩大4096使数字变好。

时间预定门槛为graph/lexical query wall、query CPU、父进程完整wall三对比中位数全部≤1，无epsilon。实际 **1.007687134/1.000000000/1.014496158**，wall约增加0.77%、父完整wall约增加1.45%，故False。只记录本机工作点差异，不把小幅时间波动当通用性能规律。零CPU分母将为null失败，本次分母均非零。

## 数据来源、分母和已见范围

本项目v015/v030等旧版已使用SciFact，**这不是未知数据或首次封存科学验证**。同型BM25/共现图/控制方法从EntailmentBank迁移到SciFact原whole-paper记录，但来源单位、任务和训练图都不同，不能把两个任务的绝对recall直接当算法进退或同难度对照。

官方[任务说明](https://github.com/allenai/scifact/blob/master/README.md)区分证据文档、rationale句和支持/反对标签。本版只评原论文来源覆盖，不评SUPPORT/CONTRADICT、rationale优选、医学结论或生成回答。原corpus 5183论文/8307875B，SHA b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62；训练809行/175616B，dev300行/65007B，其SHA、archive身份和许可在[冻结输入清单](../../docs/scifact-graph-inputs.json)。claims CC-BY-4.0、abstracts ODC-By-1.0；原数据不随发行包重分发。

原dev300行：按训练claim ID或规范化claim SHA排除2行；剩298行全部实际检索、读取核原source并计费。其中188行有evidence用于质量评分，110行无gold-evidence，paper_metrics=null，绝不按空gold计“正确”或“错误”回答。原112条无gold中有2条训练重叠，不能提前硬写重叠0。排除行的原row index/claimID/原因在每份raw JSON，不依成绩剔除。有标注188个主张、209个gold来源组是独立科学分母；三轮和三方法不将其乘9当独立样本。

## 冻结顺序与唯一一次训练

代码/协议/input freeze `1e9f7b6b6c08f1b3a93289f9e5e6a40584b1f767`；exact candidate CI `40371530467`成功后才构建一次实际模型。模型独占写入/fsync，另冻SHA **f062c7a784421b71bbfaf3c299be78ff323a391847afbf5420e4c06a4d422be0**、10152832B、UTC 2026-10-26T17:48:45.575091+00:00，随后才用此candidate评分dev。known_project_data=true明确旧项目已见，dev_not_scored_with_this_candidate_before_model_freeze只限本候选，绝不等同未知题目。前版v052完整实际发行proof核验后才改本版。

训练809行，505行有evidence；只用训练evidence paperID集合造共现边，边权为distinct训练claimID数，64图节点/60无向边。未标evidence不造边，paperID必须存在且rationale句索引必须在原abstract范围。不用cited_doc_ids作检索起点，不按SUPPORT/CONTRADICT标签正负加权。控制图固定双端ID置换，degree/weighted-degree多重集相同。科学论文ID即使title/abstract完全相同仍是不同来源，不沿短句alias文本合并身份。

训练构建wall 1.071652s、CPU 1.046875s、父从启动到退出wall 1.167893s、观察peakRSS 113184768B。这是确定性词法索引+监督共现图构建，不是神经模型训练。新增训练恰1次、正式重试0、远程模型调用0。

## 不变方法与原文身份

scripts/evidence_retrieval.py及source_alignment.py逐字等v052，固定ASCII tokens/原STOP、BM25 k1=1.2,b=.75、tie score降序/key升序；6词法seed+6加权邻居后接完整词法序列稳定去重。入证上限12、4096原JSONL整行B，超剩余预算skip继续，无embedding/同义词/预训练模型。

新adapter只将原title与abstract各句作为词法投影，将source身份换成原整篇JSONL记录。query只拿claim字符串，ranking函数不接evidence/cited_doc_ids/label/answer。先检索、原source读取验证，再gold评分，防止答案偷渡。新增candidate仍在sdist assessment scripts，未向wheel默认Memory/CLI/UI集成图检索。

每selected paper由指定SID/原offset/length/rawSHA定位；Store zlib/fixed65536/bounded读原完整记录，原stored/raw/codec/EOF/size校验保留，另核原paperID/titleSHA/abstractSHA。没有decoded缓存或跳过原校验。public JSON只保留ID/locator/hash/指标/费用，无原科学文本/主张/fullhits/模型postings图。

## 正式运行与独立审计

3方法各3 fresh worker，固定ABC/BCA/CAB；每轮Random(20261027+round)同题序。唯一9worker均正常退出，无追加试次/挑最快轮。7677原论文范围绑定、9完整corpus逐字节恢复、Store整树前后/跨worker相同、各方法proof三轮确定。父启动到退出的完整wall有独占sidecar及childSHA，未把小函数计时冒充端到端。

独立analyzer直接读原JSONL行重建paperID/offset/length/title/abstractSHA、gold evidence paper集合和rationale范围，并对实际Store原range复核；另作冻结model纯排名重放确认proof。审计不是新增正式科学试次或训练。机械身份正确不证明科学语义或回答正确。

| 轮 | graph相比 | 主张recall胜 | 负 | 平 |
|---|---|---:|---:|---:|
| 1 | lexical | 1 | 0 | 187 |
| 1 | permuted_graph | 1 | 0 | 187 |
| 2 | lexical | 1 | 0 | 187 |
| 2 | permuted_graph | 1 | 0 | 187 |
| 3 | lexical | 1 | 0 | 187 |
| 3 | permuted_graph | 1 | 0 | 187 |

所有轮只有同一条主张多一篇、没有主张recall下降；控制与词法总体计分相同但selected source并非必然逐项相同，总入证B不同保留。来源覆盖改善不能推导错误主张判定或自然语言多跳收益。

## 原始CPU、wall与RAM

| 轮 | 方法 | query wall s | query CPU s | gold wall s | gold CPU s | worker wall s | worker CPU s | parent全wall s | 观察peakRSS B |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | lexical | 1.210560 | 1.218750 | 0.002347 | 0.000000 | 1.886275 | 1.828125 | 1.993521 | 122097664 |
| 1 | graph | 1.217181 | 1.218750 | 0.002284 | 0.000000 | 1.914846 | 1.921875 | 2.022420 | 122769408 |
| 1 | permuted_graph | 1.232494 | 1.250000 | 0.002356 | 0.000000 | 1.930172 | 1.828125 | 2.053995 | 121872384 |
| 2 | lexical | 1.204814 | 1.156250 | 0.002422 | 0.015625 | 1.894899 | 1.843750 | 2.002312 | 121876480 |
| 2 | graph | 1.230553 | 1.156250 | 0.002358 | 0.000000 | 1.928102 | 1.812500 | 2.037615 | 121581568 |
| 2 | permuted_graph | 1.225018 | 1.218750 | 0.002275 | 0.000000 | 1.903782 | 1.875000 | 2.008709 | 121905152 |
| 3 | lexical | 1.208747 | 1.203125 | 0.002357 | 0.000000 | 1.896862 | 1.781250 | 2.004647 | 121331712 |
| 3 | graph | 1.218039 | 1.187500 | 0.002272 | 0.015625 | 1.902488 | 1.859375 | 2.009691 | 121573376 |
| 3 | permuted_graph | 1.223566 | 1.156250 | 0.002304 | 0.000000 | 1.907340 | 1.812500 | 2.015442 | 121999360 |

query包含排名、预算、snapshot开关和原selected source验证；gold在选择后另计。模型加载/dev解析/Store ingest/私有claim-check/proof序列化/整源恢复均在worker/parent内，不能从query单项推所有部署费用。实际Store ingest与恢复CPU/wall逐worker在derived-metrics/raw JSON。输入read返回B字段只是应用层源及dev文件读取量，不是SSD物理或全系统IO。CAS全读取/metadata/SQLite/cache未作本版全面计量；SSD物理/全系统IO/冷缓存/跨机继续null。

![SciFact固定方法迁移](scifact-graph.png)

标准图已实际打开检查：三面板单位/标签/余白无裁切，坐标从0起；由于真实增益极小，图柱几乎相同，精确差异以表和原JSON为准，不截断纵轴夸大。图展示来源覆盖和时间，不展示回答准确率。RSS是worker观察peak，不是完整生命周期增量RAM；4096入证上限不是总RAM、解码或物理IO上限。

## 模型、旧资产、全部文件与源码账本

| 方法 | Store全部B | source副本B | 其它worker文件B | 实际完整model加载B | 全检索入证原record B |
|---|---:|---:|---:|---:|---:|
| lexical | 2963638 | 8307875 | 98336 | 10152832 | 1169465 |
| graph | 2963638 | 8307875 | 98336 | 10152832 | 1169555 |
| permuted_graph | 2963638 | 8307875 | 98336 | 10152832 | 1169793 |

新模型10152832B：shared词法索引/locator/训练排重metadata 10146658B、正图3064B、控制图3072B，外层JSON开销仍在总B。全部三方法实际载入同一完整模型，不把组件部署情景说成实测词法未载图。旧EntailmentBank模型4629668B仍是私有历史资产，不在本次query加载、不改写，也不因换任务从历史总成本中删除。

保留的data/scifact与训练目录全部文件（含不用的旧source/metadata/模型/训练报告）共18738461B，逐文件实际B/SHA在measurement-context，9worker各自Store所有CAS/config/snapshot/残留、原source副本、plan/privateclaim-check/ledger逐项保留费用；9份评测副本不声称生产必须常驻9份。全项目以前的历史报告/快照继续保留，本版不把旧资产删除算压缩收益。平台/解释器/依赖未分配，不称完整TCO。

9份child JSON加parent原始报告4802637B、driver日志0B。完整65递归Python+HTML 416514B，runtime只版本；所有实际专用/复用assessment脚本B/SHA列source-resource，协议/input/test源码另列measurement-context，没有只数单文件或硬编码旧模块数冒充完整运行库。恢复副本/模型/源语料均私有，不能因不发布当不存在。

独立审计/实际二次读取绑定/纯排名重放/全恢复/标准图额外wall 11.741987s、CPU 10.093750s、观察RSS 153178112B，单列、不计正式query。sidecar/图/public JSON也占存储；写文件exclusive+fsync只支持机械写入记录，不称断电实验。

## 验证、复现与后续

273检查272通过/1Windows权限跳过。新增3检查覆盖不同paperID不合并/原offset/重复paper和坏rationale拒绝、distinct训练claimID共现/忽略cited与label/置换degree、原record预算exact及少1B/真实Store损坏拒绝。候选代码测试后冻结，正式科学输出不覆盖、不补轮。

复现需合法取得冻结corpus/claims_train/claims_dev及manifest SHA匹配，在新work/out运行scripts.run_scifact_graph的train入口一次，另冻model SHA再9worker；之后scripts.analyze_scifact_graph作独立审计。完整命令/精确次数/时间界限见[协议](../../docs/SCIFACT-GRAPH.md)及公开输入清单，原数据和私有模型自行本地准备。无新远程模型服务预算，旧24次耗尽。

交付代码/冻结协议/无原文raw JSON/图实际视觉检查/详实报告/README/路线/release；CI成功发布后实际5资产SHA/65递归Python+HTML/tag/adapter/driver/auditor、物理仓库外actual wheel+current native、actual sdist新paperID不合并/共现图/whole-record预算/原Store合成smoke与旧功能、最终proof上传重下载全部通过才完整收尾。

这一工作点表明旧图的收益不能稳健外推领域：只增加1个原paper组，联合门槛失败。后续应优先做可调用且有严格来源校验的实验性接口或另冻失败来源诊断，不继续在这个dev调参数。**E3净收益仍失败；E4整体、真实长期会话、rationale语义证明、生成回答质量和无限上下文尚未完成。**
