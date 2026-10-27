# v0.62 冻结协议：已见来源覆盖提升与训练问题字面相似度

先完整v061发行proof再采用。本版只分析固定train/dev原问题和v061既有三角色第一轮rawreport，追加核其他两轮proof不变；不调用检索、不训练、不新评分候选、不读科学原corpus/CAS范围。已有v061质量True/时间False/联合False与完整费用不改。字面相似度不是语义泄漏检测或无泄漏证明。

原809train按已有normalized-question SHA去重成807组；不以答案/证据/预测来挑训练子集。对原298检索dev逐一取同旧tokenizer（小写ASCII词+stop）词集合与807train的最大精确Jaccard intersection/union，空union规定0，阈值固定4/5，所有并列最佳train只记录SHA，保留110无goldnull。原2重叠排除沿用，不改变188annotated/209来源组。

1fresh诊断worker，600s/0retry，父完整subprocess wall，原input/报告SHA/B冻结、没有参数搜索。4必要检查包括4/5边界、精确分数并列/重复、空或无交集不虚构相同、normalized精确、全部win/loss/tie和完整转移、分母/类型错误拒绝。335完整检查334pass/1权限skip后freezecode/protocol/input，exactCI通过再唯一诊断。

H1至少一半正增益落在近似问题组：对188有gold问题，用candidate与lexical recovered/gold精确Fraction差；positive sum(>0 delta)的near份额>=1/2才True；无positive时null并False。不是只数新增complete的三个问题、不是net正负抵消。H2非近似组仍有正来源覆盖：该组n>0，candidate macro严格高lexical且complete count不低，才True；无该组记null/False。控制同分组列全部质量指标和每题负方向，不重调alpha或近似阈值。两个H纯诊断，不称因果/泛化验证。

独立audit不用candidate best_match或classify，直接按集合intersection/union和整数交叉乘独立找最大/阈值、核最佳SHA集合/同normalized、原question ID与gold/每题proof及两额外轮一致，独立分组/精确delta/方向/全部sum守恒；worker有298+188记录，110null不当0；无源range绑定0，沿用v061已核原source报告SHA，不冒充新原文校验。334/335测试、runtime/freeze、全部input/程序/源码/HTML实际B/SHA对账。

原base10152832B/sidecar609487B与训练CPU、v061全部9worker科学CAS/副本/历史负结果保留且沿用账本；新报告/rawJSON/图/诊断源码/协议/输入/所有log/parent/分析CPU/RSS另计。不生成真实原文/问题文本到publicJSON，只ID/SHA/分数/计数。SSD/全系统IO/冷缓存/跨机null。

可运行code/必要tests/冻结协议/rawJSON/标准图实际查看/详报告/README/release，CI后actual7baseassetsSHA/66Python+HTML/Rust+scripts/物理外actualwheel/currentGear/currentpostings/actualsdist新Jaccard与旧smoke/finalproof8完成后才下一版。0远程模型（旧24耗尽）；E3净收益/E4整体/NLI/回答/真实长会话/无限上下文未完成。
