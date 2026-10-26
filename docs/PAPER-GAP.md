# v0.54 冻结协议：已见SciFact固定结果的入证拒绝与图暴露诊断

v053 actual资产/65源码/外部安装/finalproof全完成后才能改公开候选。只诊断v053固定模型及round1三方法已有298条检索proof，不改方法/模型/预算/样本，不训练、不重新科学评分、不读取科学原source范围。全部source身份/gold从先前通过独立审计的公开report取得；真实query字符串只从原私有query-check读取并验证SHA。是已见结果诊断，不是新未知数据/新查询试次/因果干预。

预先假设H1：graph未找回的gold论文组中至少50%在原固定扫描中因剩余byte预算拒绝；若无miss则False。H2：188条有gold主张中至少50%在原top6词法seed具有一条正图边。两个假设各判，不能等同提高预算或加边后的实际收益。维持4096原recordB/12篇/6+6，不做oracle选证/参数搜索。

精确3 fresh诊断worker，lexical/graph/permuted各1，600s，0正式检索评测worker/0训练/0新科学源绑定；失败不补轮不覆盖。读同一model SHA f062c7a784421b71bbfaf3c299be78ff323a391847afbf5420e4c06a4d422be0，原v053训练/每方法round1 JSON/parent/私有query-check SHA在首次诊断前输入manifest冻结，且先完整测试/代码协议CI冻结。v053另外两轮不重复计算、不增加样本数。

每worker298条（188有gold/110无gold）、每方法209gold组，三方法894条/627组。先核原proof SHA、question SHA、model/source SHA，重放原排名/原admit并逐项等原selected及admitted B；新独立admission_trace扫描去重全序列，互斥gold组分类recovered/no_candidate/byte_rejected/count_stop（先检查已达12才停止，超剩余B跳过继续）。不是v052的first12位置分类：整篇记录可能先拒绝多篇后接纳更后候选，绝不能把rank>12一概归count。所有gold必须是原locators已知source，未知身份明确失败。

graph暴露为top6词法seed中有非空边的个数、所有邻居union大小、邻居不在完整词法候选数；只数可见图结构，不看gold挑seed，不称实际扩展全部被采用。另报告与词法selected列表是否改变，gold类别数守恒/原recovered数相同。无gold行gold_categories为空/不评分，但照常诊断/计成本。所有输出只ID/hash/计数，无原科学句/claim/模型图/postings。原source绑定信任范围严格限既有SHA审计结果，0新range校验，不补称实测新Store读。

worker完整wall/CPU/RSS/所有input.read_bytes应用返回B、model实际全load/文件SHA、parent启动到退出wall独占sidecar；三worker全rawJSON、图、独立aggregate守恒/重复ID/proof字段检查费用分别列。无新模型，但10152832B原模型/原训练CPU与旧快照仍收费，完整递归Python+HTML/所有专用复用脚本/测试协议/sidecar历史报告保留。应用read B不是SSD/OS IO/冷缓存，后者及跨机null；不能把诊断运行时间当原query提速。

必要合成测试：exact预算/超B跳过后续/重复rank/12篇早停/未知source与非法length限额拒绝、first6图暴露/词法控制、真子进程toy model/proof输入SHA篡改拒绝。冻结后才能读真实私有query并正式诊断。标准图从0坐标留总数余白，实际视觉检查；每版详实报告/rawJSON/README/release，CI成功后actual资产SHA/递归Python+HTML/实际外部wheel+currentnative+actualsdist新diagnostic smoke/finalproof重下载，完成才下版。

旧24模型API已耗尽，0新远程调用、本机CPU离线，默认Memory/CLI/UI不集成。E3净收益失败，E4整体/科学verdict/NLI/生成回答/真实长会话/无限上下文仍未验收。不能因H1/H2成立或不成立改这批预算/图追正。
