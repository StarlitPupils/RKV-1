# v0.53 冻结协议：固定同型检索方法的SciFact论文证据迁移

## 假设与已见数据范围

v052 actual发行/65源码/外部安装/finalproof全通过后实施。把v050/51的固定BM25/训练来源共现graph/ID置换控制迁移到SciFact原论文记录。SciFact本项目v015/v030及更早已用，不能称未知数据/封存新题验证；新的只是同型图方法和本完整字节工作点的领域/单位迁移，不在该dev调参追正。初等句子任务的graph窄收益不外推论文领域，v051 literal负结果保持。

主quality gate仍graph macro gold-paper recall严格胜lexical和置换控制，完整gold-paper覆盖题数≥两者，三轮都满足；time gate仍graph/lexical query wall/CPU/parent完整wall比三对中位数≤1，零CPU分母null失败，无epsilon/追加轮。quality/time/联合各列，所有负方向/逐claim胜负保持。固定算法未胜也不改seed/k/预算追正，默认Memory/CLI/UI不集成。

## 原byte与迁移适配

原data/scifact/corpus.jsonl 8307875B/5183doc，SHA b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62；claims_train809行/175616B SHA f4c8fa82d8bd0653a9cc8d61a6ea48c25eacea64e90af5dbf390ebb1b74372f0；claims_dev300行/65007B SHA86f0435d08fdb65d1aa41d1472684f57e6e71930626497bdf4d7a9ec1a632217。原官方archive SHA和许可(CC-BY-4.0 claims、ODC-By-1.0 abstracts)在scifact-graph-inputs.json，不重分发原source/原claim/模型。

官方任务说明https://github.com/allenai/scifact/blob/master/README.md区分证据文档/rationale/label；本版只评文档来源定位，不评SUPPORT/CONTRADICT分类、rationale优选或医学结论。claim文本单独作为query，不使用cited_doc_ids给检索起点、不拼evidence/label/答案。新投影只用原title+'\\n'+各abstract句，原corpus记录/科学事实不改，512词等外部截断不存在。

单位明确从EntailmentBank短句source组改为整篇SciFact原JSONL记录，字节预算仍12facts/4096原recordB而非12句或4096decoded字符。两个任务数值不能直接比较召回/预算难度。相同text的两个论文ID仍不同原来源，不沿短句alias合并身份；这是原科学schema适配，不是事后调identity追高分。model locators指原整行offset/length/rawSHA，标题/abstract句也各SHA；原Store zlib/fixed65536/bounded读原line、保留stored/raw/member身份校验。

## 只训练一次与候选不调

scripts/evidence_retrieval.py中tokens/question_identity/BM25/ranking/admit/metrics逐字等v052，k1=1.2,b=.75、原STOP/token/tie规则、6lexicalseed+6加权邻居、12/4096/skip继续和rkv050control置换salt全不变。新scifact_graph.py只适配原记录/全paperID独立身份、title/abstract投影、train evidence-paper集合和原whole-record hits，不用EntailmentBank权重冒充跨ID可迁移模型。

一次source lexical index+监督共现图构建只读原corpus/claims_train，所有809训练claim ID和规范化claimSHA用于排重；只有有evidence的训练集合构边，未标evidence不造边，边权distinct训练claimID数，不用cited_doc_ids或label真值/反值加权。训练金标准paperID与每evidence句索引必须对应原source/abstract范围，不存在/越界明确失败，不静默丢源。控制图双端同ID固定置换，degree/weighted-degree多重集相同。

273完整检查272通过/1Windows权限跳过（3新：原paperID不合并/offset/重复与坏rationale拒绝；distinct训练ID计边/忽略cited_doc_ids与label/置换degree；原record预算exact/不足/真Store损坏拒绝）。代码/协议/input/exactCI冻结成功后仅训练一次，exclusive+fsync模型原byte；另modelSHA/组件B/SHA/source trainSHA/训练CPUwallparentwall/RSS冻结，再评分已见dev。准备阶段只核原byte/schema和原项目已知计数，不提前构新图/评分；真实训练失败不覆盖重训/调参。没有新远程模型调用/GPU/预训练模型下载。

## dev分母和唯一9worker

原dev300行，按训练claimID或规范化claimSHA同一规则排重并记录（旧项目重叠0，但按实际计数判，不先硬写0）；其余全部claim都检索并核原source。官方300中有evidence标注188、无gold-evidence标注112为旧项目已知分布；没有gold的行仍实际检索/计时间与绑定，但paper_metrics=null、不按空gold“正确”或“错误”回答计，不从无gold推科学真假。仅有标注且未排重的子集是quality分母；原raw/检索/标注/无标注/排重五个数都公开，不藏分母。

lexical/graph/permuted三个方法各3freshworker=9，固定ABC/BCA/CAB，Random(20261027+round)仅打乱300行，三方法同轮同顺序。每合格claim一次选/验证，无teacher paperID输入ranking。先生成selected和完整原byte hits，之后才用evidence纸ID集合评分，micro/macro/完整覆盖和逐题win/loss/tie保留。paper source匹配不等于SUPPORT/CONTRADICT分类、rationale语义蕴含、生成答案或NLI验证。

每worker600s，失败/超时原退出码/异常/childSHA/完整parentwall保留，不覆盖重跑。9完整corpus逐字节恢复、Store整树前后/跨worker相同，每方法proof三轮确定；三轮不是三独立科学样本。独立analyzer直接JSONL raw line/原docID/title/abstractSHA/Store实际range比对，按原evidence重建gold paper集合并核每rationale索引，不依赖相同适配器自证；纯模型排名重放只诊断，不算新正式试次/训练。

## 全部费用和交付

原整行预算4096B可能只能入证少于12篇、单篇过预算则skip，入证篇数min/max/mean逐worker公开；不能把篇数减少当free压缩，也不能把读到论文就说正确rationale或推理已完成。query包含原BM25/graph/admit、snapshot打开和原source读取核验，gold后算、ingest/模型加载/序列化/恢复/worker CPU与父启动到退出完整wall另列。所有方法实际载入完整model含两图，source/模型/训练成本不免费；percomponent部署情景和实际loadB区分。

全部原input/私有model/index/图、Store全部CAS/config/snapshot/残留、source副本/plan/privateclaim-check/ledger/child/parent/log/图/全部源码实际B/SHA记账，273测试/协议/inputmetadata另列。65递归Python+HTML仅版本；旧句子模型仍私有历史资产，与新paper模型费用分开，不称新domain训练免费。observed RSS非完整生命周期增量RAM，4096入证不是CAS/OS读取/RSS上限；未覆盖SSD物理/全系统IO/冷缓存/跨机继续null，平台依赖未分配不称完整TCO。

代码/冻结协议/无原文rawJSON/标准图实际视觉检查/详实报告/README/release/GitHub，CI后actual5资产SHA/65递归Python+HTML/tag/新适配器/driver/auditor、物理仓库外actualwheel+currentnative/actualsdist新paperID/graph/whole-record预算与原Store合成smoke/旧功能/最终proof重下载全核验后再下一版。原science原料/claims/fullhits/privatequery/models-postings图/帧恢复副本/研究模板个人报告密钥不发布。

本机CPU离线、旧24模型API用尽0新增调用，来源定位/已见benchmark迁移不是未知科学验证或医学建议；E3净收益失败，E4整体/真实长期会话/语义证明/生成回答质量/无限上下文未完成。后续另冻新假设/数据，不在此dev改预算或改label口径追正。
