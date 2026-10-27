# v0.56.0 实验报告：整论文证据的gold-aware容量上界

## 结论及不能外推的边界

**H1（正图未找全主张至少半数，即使知道gold也装不下）=False**，9/49，比例0.1836734693877551。**H2（正图漏证至少半数单篇本身>4096B）=False**，4/62，比例0.06451612903225806。原始分母/空分母null规则完整保留，不追加轮或调预算。

v054“正图62个漏证组均被原prefix剩余byte预算拒绝”，描述的是原顺序的剩余容量，不能直接推出gold自身放不下。这里全知gold条件下最多能完整容纳 **179/188** 主张、micro最多195/209组、macro recall ceiling 0.968173759。这些是不可部署oracle上界，不是实际检索成绩、预算干预收益或新增回答分数。

| 既有方法 | 实际完整主张 | 实际不完整 | 不完整且gold本身装不下 | 不完整但gold有容量放入 | 漏gold组 | 漏组单篇>4096B |
|---|---:|---:|---:|---:|---:|---:|
| lexical | 139 /188 | 49 | 9 | 40 | 63 | 4 |
| graph | 139 /188 | 49 | 9 | 40 | 62 | 4 |
| permuted_graph | 139 /188 | 49 | 9 | 40 | 63 | 4 |

原graph仍139/188完整、147/209组，v053仅多1个gold组/时间及联合失败不变。本版没有重新检索或生成答案，不把oracle和actual之差称已经实现的增益；即便gold能放入，也可能无法从问题中正确定位、排序或判别证据。

## 固定问题与来源信任链

只用v053原round1三份已审计公开report和同SHA私有model locators，先核report/model/source SHA、原proof SHA、selected原B/12篇上限与gold组一致。不读private query-check、不读科学原corpus或Store范围，不训练、不构新图、不再评分科学质量。原来源/标注身份由v053独立原文/rationale审计及v055实际API原proof验证提供；本版只是信任已冻结结果的诊断，不称新增独立原证绑定。

原dev300行、2训练重叠继续排除；三方法共有298原记录，其中188有gold/110无gold。本版仅188唯一有gold主张各计算一次容量（209个按主张计gold来源组），3×188=564条方法对照是派生记录，不增加独立科学样本。无gold行不造空正确分数。sourceID跨主张重复不去掉其原主张分母，也不称209独立论文样本。

原model SHA f062c7a784421b71bbfaf3c299be78ff323a391847afbf5420e4c06a4d422be0、实际全load 10152832B；原source SHA b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62。所有gold必须在locators且原length正整数，不猜来源/不语义合并。同一个主张重复goldID只计一次原记录B，原whole JSONL记录含标题/abstract/JSON及换行，不换成decoded字符/句子以缩小容量。

## 先冻结的假设与精确运行

前v055 actual资产/66源码+HTML/物理外API/currentnative/finalproof全完成后才采用本候选。code/protocol/input freeze `b3a58f531dcd0f9c7c57aa1ee8ca33460d6ea5ee`，exact candidateCI `40422554387`成功后唯一 **1 fresh诊断worker**，600s超时，0重试。父完整wall/退出码/error/childSHA独占sidecar；失败保留不覆盖。

H1分母是原graph实际不完整主张，分子是其中全部gold记录在12篇/4096原B下不可完整装入；H2分母是原graph未找回gold组，分子为对应单篇原记录长度>4096。空分母fraction=null、supported=False。没有根据看见结果改H1/H2或丢负例。

## 上界算法与独立核对

最多12原paper、4096原B，所有gold价值同为1。贪心按原record长度升序/ID tie挑最短gold，求最多可装多少组；另独立0/1动态规划在budget0..4096状态求最大数量并限制12。逐主张两算法结果相等才接受；完整可行还独立检查gold个数≤12及总原length≤4096。

这不是top12候选位置分类，不改变v054实际admission_trace。selected_non_gold_original_bytes逐条记录原入证的非gold论文B，用于定位原prefix占用；它不是可以无代价识别并剔除的内容，因为部署时没有gold。这里不实施“移除非gold”或提高预算的干预。

必要4检查：不同budget/count下贪心和独立DP对穷举子集最优数一致；单篇4096可/4097不可、重复gold不重复费、gold能放但无关prefix先占1B的反例；空分母null和坏source/length/bool限额拒绝；真子进程人工188有gold+110无gold fixture，核H1/H2/完整上界，并确保SHA篡改明确拒绝且原结果不被覆盖。完整289检查288通过/1Windows权限跳过，冻结前通过后才正式读真实模型与report。

## 全部时间、RAM和读取范围

worker wall 0.171807s/CPU 0.171875s，parent从启动到退出完整wall 0.280067s，观察peakRSS 74121216B。worker的model+三原report.read_bytes实际返回11753132B，范围明确不含manifest/解释器/模块读，也没有原科学语料或Store范围读。这不是SSD物理读取或全系统IO，更不是新检索器不读源的收益。

parent独立gold总B/完整可行性及aggregate/标准图额外wall 0.658256s、CPU 0.609375s、观察RSS 115687424B，含重新读模型和原report；不把此成本归零或混入query提速。观察RSS不是整个生命周期增量RAM，4096原记录入证cap不是模型、瞬态、源副本或RAM上限。

原10152832B模型所有shared/postings/图仍加载，新增模型B0/训练0不表示原模型免费。历史训练wall 1.071652s/CPU 1.046875s、父 1.167893s保留。直接复用的原训练/v053及v055 worker目录实际保留146299374B，逐文件B/SHA在measurement-context，包含源副本、Store所有CAS/config/snapshot/残留、plan/query/ledger和模型。其他历史目录/旧模型/快照/派生报告继续保留并沿原成本账本记录，未删除换取空间收益；评测副本不声称部署必需常驻。

完整66递归Python+HTML 426112B，运行库仅版本，全部assessment专用/复用脚本实际B/SHA与协议/input/test另列，不只数新脚本。新的child/parent/aggregate/图/sidecar也占B。平台/依赖未分配，不称完整TCO。SSD物理/全系统IO/冷缓存/跨机器继续null。

![整论文容量上界诊断](paper-capacity.png)

标准图已实际打开检查：实际与gold-aware虚线上界明确区分、从0起、188/失败数留余白，标签/图例可读；不是实际问题的部署召回或答案准确率。纯已见数据诊断不作显著性结论。

## 复现和交付

合法保留原v053 model和公开round1 report，匹配docs/paper-capacity-inputs.json，在新out目录运行scripts.run_paper_capacity并指定model/manifest/freeze。输入原文和私有模型不重分发；不需要原科学corpus、query-check或新模型API。0新增科学试次/训练/原source range绑定/远程模型调用，不能拿已有source hash代替新的原证读测。

每版代码/冻结协议/rawJSON/标准图/详实报告/README/release/GitHub，CI后actual5资产SHA/66递归Python+HTML、物理外actualwheel+currentnative/实验API与旧sdist/新capacity贪心DP及分母smoke、最终proof上传重下载全部完成才完整交付。旧24次模型API已耗尽，仅CPU离线。

根据这个上界才另冻新的检索/证据单位假设；不能在此dev追改预算、candidate或图并称封存收益。**E3净收益失败，E4整体/真实长期会话/科学verdict/NLI/形式证明/生成回答质量/无限上下文仍未验收。**

本地包审计曾早于final build退出启动，读取未更新完的sdist而缺package-validation.json；build退出后该文件已确认存在。原失败日志B/SHA在local-packaging-recovery.json保留。只重建发行包并严格等退出成功后恢复包审计，原冻结候选/正式诊断/图不改不重跑，额外包装CPU/wall未计量为null。
