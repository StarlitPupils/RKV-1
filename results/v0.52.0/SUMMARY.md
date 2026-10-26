# v0.52.0 实验报告：已见检索漏证分解与gold-aware上界

## 结论和原实验边界

六个已见结果诊断worker完成1578题方法记录/6204源ID组排他分类、独立动态规划核oracle数量与B。先定“graph两个split中原前12候选因字节预算被排除的组占漏证≥50%”假设 **False**，dev/test实际比例 **0.000000/0.000000**。这是原序列位置诊断，不能证明改某个参数的因果收益，也没有调预算重测。

**新增科学评估试次0、训练0、新模型B0、新原source-range绑定0。** 重放既有v050/v051固定模型排名，原dev/test科学成绩和负结果保持，不把上界当新检索、推理或生产收益。原科学source和original byte binding已在前版实际核验，本版只核report/query/model SHA与locator metadata，不冒充新物理来源恢复。

| split | 方法 | 物理题记录 | 已恢复 | 源无法定位 | 无候选 | 候选但不在前12 | 前12字节排除 |
|---|---|---:|---:|---:|---:|---:|---:|
| dev | lexical | 187 | 147 | 46 | 250 | 277 | 0 |
| dev | graph | 187 | 179 | 46 | 230 | 265 | 0 |
| dev | permuted_graph | 187 | 124 | 46 | 250 | 300 | 0 |
| test | lexical | 339 | 266 | 75 | 520 | 487 | 0 |
| test | graph | 339 | 292 | 75 | 496 | 485 | 0 |
| test | permuted_graph | 339 | 221 | 75 | 520 | 532 | 0 |

各方法同split分母相同：dev720源ID组/test1348组。三个方法共6204组不是独立科学事实数，1578=(187+339)×3也不是新独立题目样本。原v051 literal完整graph4<lexical6、macro literal反向，以及24题ID变差保留；原v050成本联合失败也不回填。

## 排他分类与已知gold上界

顺序冻结：selected先判recovered；无原model locator判unresolved_source；不在该方法完整冻结候选判no_candidate；在候选但不在稳定去重前12判below_count_prefix；其余判byte_budget_excluded。selected可能因skip长项而来自第12后，先判恢复避免误记。标签只是原位置，不代表提高k/预算或加graph必然有益；排序/候选和source身份未解决项都不能用oracle泄漏补进原系统。

三种上界知道gold：全可定位源ID、仅原完整候选内可定位源ID、严格literal组。每目标组unit收益1，在原12facts/4096 memberB中按length/key升序选最短组可最大化可命中数量。未解/nonliteral标记仍留分母，不创造source或语义证明。

| split | 方法 | 原macro IDrecall | 原ID全覆盖题 | gold源ID上界macro | 源ID可全题 | 候选内oraclemacro | 候选可全题 | literal上界macro | literal可全题 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| dev | lexical | 0.261750 | 12 | 0.945714 | 153 | 0.655072 | 65 | 0.366936 | 15 |
| dev | graph | 0.306802 | 22 | 0.945714 | 153 | 0.679113 | 71 | 0.366936 | 15 |
| dev | permuted_graph | 0.221770 | 9 | 0.945714 | 153 | 0.655072 | 65 | 0.366936 | 15 |
| test | lexical | 0.251233 | 22 | 0.946238 | 275 | 0.605190 | 91 | 0.411079 | 42 |
| test | graph | 0.262793 | 25 | 0.946238 | 275 | 0.623323 | 98 | 0.411079 | 42 |
| test | permuted_graph | 0.203937 | 16 | 0.946238 | 275 | 0.605190 | 91 | 0.411079 | 42 |

这些oracle上界不是可部署成绩、不是新模型，也不是“换个预算已提升”的实验。依赖正确gold的最优选择没有解决未知问题如何定位证据。literal上界更不当NLI/回答正确率；annotation改写不能通过metadata诊断变成语义证明。

## 输入冻结、检查和独立审计

输入固定为原v050/v051 round1三方法public report及精确私有question-check，report/query SHA和B在[manifest](../../docs/retrieval-gap-inputs.json)。模型SHA2f82ee4b28c943038e7a37ddcbd8871443f7a441ddd45a1af599decc8bade183、4629668B不改，原evidence_retrieval和65runtime除发行版本逐字等v051。没有再打开原科学标签/source全文或触发新Store读range。

270检查269通过/1Windows权限跳过。新增2必要测试用32组小合成长度，对贪心oracle和穷举全集求最优对照，核exact/不足/candidate限制；另核五类别唯一/守恒/错误selected拒绝。代码/协议/输入在`0b6f8fe2c8e77050dbb4110618ec5aa988fe1cdd`冻结，exact candidateCI `40368073580`成功后唯一6诊断worker，0重试；确定性已见数据不机械重复三轮或宣称新科学验证。

独立analyzer按gold组重新分类，并采用0..12组最小费用动态规划核最优可命中数量/byte/唯一性，与worker最短组贪心实现不同。原selected/admitted重放必须逐字等旧report，原hit offset/length/SHA等model locators。父真实退出码/childSHA/完整process wall、各原proof引用和六个输入指纹核验，6204组守恒。不能把metadata相等叫新的原文损坏拒绝试验。

![已见漏证分解](retrieval-gap.png)

标准图已实际打开核图例/单位/余白/堆叠不裁切。颜色是排他组位置，柱总高同split相等；没有把gold oracle画成可部署模型分数或给在线提速坐标。

## 费用原值与资源范围

| split | 方法 | 重放诊断wall s | CPU s | workerwall s | workerCPU s | parent完整wall s | 观察peakRSS B | 应用层input read返回B |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| dev | lexical | 0.237317 | 0.250000 | 0.275213 | 0.281250 | 0.376049 | 52006912 | 5715502 |
| dev | graph | 0.247310 | 0.234375 | 0.287068 | 0.296875 | 0.387237 | 52158464 | 5715767 |
| dev | permuted_graph | 0.254320 | 0.265625 | 0.292177 | 0.296875 | 0.406854 | 52023296 | 5716162 |
| test | lexical | 0.445855 | 0.437500 | 0.487644 | 0.484375 | 0.590512 | 55275520 | 6591028 |
| test | graph | 0.448960 | 0.437500 | 0.491108 | 0.484375 | 0.591121 | 55214080 | 6593028 |
| test | permuted_graph | 0.456222 | 0.453125 | 0.499031 | 0.500000 | 0.600281 | 55054336 | 6593330 |

每worker实际加载4.6MB同一model（含词法/正图/控制图），另读原report、私有query、manifest，loaded_bytes逐项列。读返回B不是SSD/全系统IO，未覆盖metadata/OS/解释器读；物理/全系统/冷缓存/跨机继续null，不能填0。工作目录可空，因为本版没有新Store/index/frame，child/parent写到out并exclusive+fsync；不漏记不存在的0文件和实际输出。

原模型部署B、历史共享训练wall 1.455500s/CPU 1.437500s、父完整wall 1.547749s照列，训练新增0不是模型免费。原输入/旧报告/query/model是本版引用成本，不重发私有原科学问题；所有当前加载B/SHA与modelSHA在metadata。六诊断输出child+parent共2694767B，driver日志0B，原历史多轮文件费用在旧报告保留，不重写旧结果。

65递归Python+HTML源码416514B，专用/复用脚本B/SHA按实际集合核对；协议/输入metadata/测试源码另计。新oracle代码也计费用，不能用新source体积换一个并非可部署的上界去声称压缩/推理净收益。observed RSS为worker区间系统峰，完整model/query/proof对象均占内存，不是全生命周期增量RAM。平台/依赖未分配不称完整TCO。

独立DP/分类/排名重放/原SHA/图表分析额外wall 4.328134s、CPU 2.765625s、观察RSS 103747584B，不含初始解释器启动及写分析计时记录，不能当在线推理或新科学评估时间。

## 交付与下一步

新work/out运行scripts.run_retrieval_gap --model本地同SHA模型，再scripts.analyze_retrieval_gap带work/out/model/freeze/test-log；需要原版本生成的私有query记录或本地合法同SHA科学输入自行重建，原问题/fullmodel不重分发。程序/冻结协议/无原文原始JSON/标准图/详实报告/README/release/GitHub，CI后actual5资产SHA/65递归源码/tag/诊断程序、物理仓库外actual wheel+current native/actual sdist新partition/oracle/candidate边界合成smoke与旧功能、最终proof重下载全通过才完整收尾。

本诊断不能作为在这些test上调参追分的借口。下一项应另冻独立数据或新候选的可证伪实验，并尊重原缺证/改写事实；不将gold喂入query或补到source。旧24模型API耗尽0新增调用，本机CPU离线。E3净收益仍失败，E4整体/真实长会话/NLI/生成回答质量/无限上下文未完成；原science源/questions/privatequery/model图postings/帧恢复副本/私有研究模板个人报告密钥不发布。

图表视觉复核发现初图stacked autoscale顶端过紧/裁切，保留原冻结analyzer及原PNG，另冻plot_retrieval_gap.py只设12%上边距与总数标签。新图实际打开检查通过，初/新SHA、新脚本B/SHA/commit和额外绘图CPU/wall在figure-postprocess.json；未重跑诊断/模型/评分，追加源码收费。复现原分析后可运行该plot-only入口，不能把绘图修复算新实验。
