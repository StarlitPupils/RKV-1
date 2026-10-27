# v0.66.0 实验报告：有限规则程序的独立真值与变形一致性

## 结论与阶段

H1原来源证书和独立真值机制 **True**；H2重命名/记录顺序/显式符号翻转一致性与跨源拒绝 **True**。1296/1296主证书、972/972非base变形比较、36/36跨SID负控制和48/48历史完整source恢复通过。原v0.65引擎/独立审计器逐byte不变，默认SDK/UI不集成。

这是人工有限域内的机制健壮性验收，**不是自然语言多跳、科学NLI泛化、回答质量或无限上下文证明**。显式结构化公理如何从自然语言可靠获得仍未实现；source真实和形式推导合法不能证明公理科学真实。v0.64真实关系分类质量失败、E3净压缩和E4整体未完成的结论不改。

## 冻结与正式次数

冻结 `1e13a6cbb3f906db37bc18acea7c67c45e48e91c`，exactCI `40457716964`成功后唯一1fresh worker、timeout600s、0retry；完整361检查360pass/1既有权限skip。新增4合成测试检查固定生成、48不同源、重命名/符号闭包双射、不修改原输入、recordorder仅改行序以及非法variant拒绝。0新训练、0当前模型加载、0远程API。旧模型/原科学source/训练/全部snapshot历史成本继续保留，不用本轮0加载抹掉已有费用。

12program seed2026102700+i，每program8signedfacts+7rules；域固定c0/c1/c2，predicate edge/reach/flag。3条正edge形成环，1条反向负edge固定，其他4fact从剩余signed atoms不放回抽一次。该小环有利于闭包检查，不代表自然语言或科学多样性。7规则含传递、显式负前提、负传播、重复变量、固定常量与递归回边，没有函数项或默认否定，不从矛盾爆炸出任意结论。

每program4variant：base；实体及predicate双射改名；seed固定recordline重排；全部fact/rulehead/premise符号翻转。变形query一并改名或翻转，原query3predicate×3left×3right=27，每variant27。12×4×27=1296；非base12×3×27=972。所有48原source SHA在inputmanifest先冻结，没挑选最好seed/方向/轮次。生成方法和变形预期在正式之前可见，不称盲测。

## 独立验收和控制

base expected由独立有限grounding oracle计算，不调用主引擎作gold；所有主证书再独立解析原source、重读每个原record、核对推导DAG并用有限grounding证明完整闭包。H1每题要求complete且verdict等于base真值在变形下的对应结果；H2另要求972不变量和36wrongbaseSID拒绝。顺序变化会改变citation offset/sourceSHA，因此不要求不同源证书SHA相同。不是对所有程序的数学完全性证明，也没有科学独立样本或统计显著性声称。

| variant |324查询verdict分布 |
|---|---|
| base | {'unknown': 72, 'supported': 164, 'refuted': 47, 'inconsistent': 41} |
| rename | {'unknown': 72, 'supported': 164, 'refuted': 47, 'inconsistent': 41} |
| record_order | {'unknown': 72, 'supported': 164, 'refuted': 47, 'inconsistent': 41} |
| polarity_flip | {'unknown': 72, 'supported': 164, 'refuted': 47, 'inconsistent': 41} |

每variant在一个显式SID上查询，query前后CASledger相同；全部48snapshots在最终HEAD后分别恢复原source并比SHA。每nonbase第一份certificate被交给对应baseSID必须拒绝，36负例全保留。每份主证书先exclusive写本地再审计，失败不覆盖或重跑；正式本轮无失败重试。

预算100000仅候选atom比较/新增推导，非CPU/RAM/物理I/O限制。独立grounding cap100000，超限是VerificationCapacityExceeded，不是unknown。原v0.65预算不完整/篡改控制不回写；本轮没有新增预算性能或生成回答实验。

## 全部费用与来源

成功源record绑定 **31644**；成功constructor+独立auditor+48完整恢复的应用source返回 **8034446B**，拒绝控制read量未计为null。不能叫SSD物理IO或全系统SQLite/metadata/OS读，冷缓存/跨机未测。

| variant |12stage累计wall s，含ingest/constructor/27infer+audit/负控制 |累计CPU s |
|---|---:|---:|
| base | 3.015797 | 2.890625 |
| rename | 2.952901 | 2.765625 |
| record_order | 3.165974 | 2.968750 |
| polarity_flip | 2.987125 | 2.765625 |

完整worker wall **19.373094s** / CPU **12.953125s** / peakRSS **32403456B**，父完整subprocess wall **19.488596s**。这是单轮机制成本，不能用variant间时间差声称提速；计时有平台粒度，0值非0成本。

整库递归66Python+1HTML完整源码 **426112B**。当前全部175份实验scripts保守收费 **1487759B**，包括共享/未执行历史脚本，不声称是动态实际import集合；冻结协议/测试/input等另记。48owned源副本、全部CAS/旧新snapshot、1296完整privatecertificates及全部残留工作文件 **12434979B**，逐文件size/SHA见raw-worker/source-resource。当前loaded model0B，历史模型训练/source费用见v0.65与更早账本，全部保留；依赖/系统二进制与OS/allocator未分配成本明确保持，不从源码B推出总内存。

## 交付和边界

```powershell
python -m unittest discover -s tests
```

logic_metamorphic.py提供固定owned生成与双射变形，run_logic_metamorphic.py提供独立sourceSHA检查和1worker运行。正式CLI需对应frozencommit和本地唯一work/out路径，重复路径拒绝。原引擎及独立checker不改；本版runtime66模块仅version，HTML同前。

![有限规则变形机制图](logic-metamorphic.png)

图已实际视觉检查，坐标/标签/分母和变形范围清楚。当前报告为tag前状态，本地实际outsidewheel/currentnative与actualsdist新旧smoke、finalbuild/sourceaudit、ReleaseCI/实际7baseSHA和最终proof8重下载完成后，以published-verification.json判定发行完成，不改原实验。源码与ownedaggregate公开，原科学语料/模型/私有研究/模板/个人报告/密钥不发布。本轮未完成自然语言到受信公理、开放证据关系或真正长期回答测试，不能当E4整体验收。
