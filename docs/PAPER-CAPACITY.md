# v0.56冻结候选协议：SciFact整论文证据容量上界

v055实际资产/66源码+HTML/物理仓库外新API与旧功能/finalproof已完整核验后采用本候选。必要4项合成检查通过：穷举与DP/贪心、边界及prefix反例、空分母及拒绝、真子进程人工worker/SHA篡改拒绝；完整289检查以实际log为准。代码/协议/input/exactCI先冻结成功，后唯一1fresh诊断worker，未运行不得称交付。

动机：v054显示正图62个漏掉gold均在原候选扫描时被剩余byte预算拒绝。这个结果不能等同“gold本身不可能装进4096B”。它可能只是较前的无关论文先占预算；需在不动原排序/模型/预算的情况下区分容量上界与实际prefix浪费，避免直接扩预算追正。

预先两个假设：H1至少一半正图未全部找全的主张，其全部gold原整行在12篇/4096原B限制下即使知道gold也不能全部装入；H2至少一半正图漏掉的gold组，单篇原整行本身>4096B。若相应分母为0则null并判未支持，不能因没有负例写通过。所有比例/分母逐条保留，不把同一主张的多个gold当独立主张。

输入仅v053同SHA私有model locators/三个round1公开report、v055完整最终proof身份；不需要private query-check、不读原科学语料或Store范围、不训练/不重新检索/不重新评分科学质量。原gold使用已由v053完整source/rationale审计通过的ID集合，并记录信任链；不是本版新增独立源验证。

精确一次fresh诊断worker，三方法相同188条有gold主张/110无gold行先核raw proof/ID/selected/B/SHA，确认各方法同row的gold集合一致。容量上界对每个有gold主张只算一次（188个）、方法对照3×188=564条派生指标，原gold组209不乘3当独立样本。正式超时600s/0补轮，独占输出/childSHA/完整parent wall；失败不覆盖。新的原source范围绑定/科学检索试次/训练/远程模型调用全部0。

保持原单位whole original JSONL record，locators的length正整数；不得用sentence/字符数缩小容量。gold-aware oracle选最短gold记录（等价值1）求最大可容纳gold数；另独立0/1 DP按budget0..4096和max12求最优count，相等才接受。完整可行直接核gold个数≤12且sum原length≤4096。只有知道gold才可用此oracle，因此不是可部署检索器或实际干预，不报告提高预算后的收益。

按三个原方法记录：原recover/complete与oracle最大recover/complete差距；原incomplete中intrinsically_impossible与capacity_possible_but_not_recovered分开；每missed gold单篇超预算/单篇可容纳但原prefix拒绝分开；gold总B/最短方案B，source原SHA来源链。无gold行不造空正确分数。

测试应检验贪心/独立DP在不同count和容量下对穷举集合一致，尤其单篇恰4096、4097拒绝、重复gold不重复计费、总gold能装但实际prefix先占满、不可解整集合、空分母null和不支持H1/H2。不能只写镜像实现测试。

计费：完整原10152832B模型read/load，历史训练CPU/旧model/所有源快照与派生文件继续收费；实际新read_bytes返回B仅应用model/report，不是SSD物理IO，全系统/冷缓存/跨机仍null。worker与parent wall/CPU/RSS、源码实际66递归Python+HTML、所有专用/复用脚本及metadata/输出/图/历史目录另列，不称全机TCO。只改runtime版本，默认接口/Memory/CLI/UI不改。

标准图明确gold-aware bound/actual不同，0起点、总数余白，实际视觉检查。详实报告保留H1/H2负结果、原v053联合失败；README/release/原始aggregate JSON/代码协议测试/CI成功后Release、actual5资产SHA/66+HTML/实际物理外wheel+currentnative/API及新sdist oracle smoke/最终proof重下载，全收尾再下版。

根据结果再决定是否另冻新证据单位/原排序策略的独立实验，不调此批参数。E3净收益失败，E4整体、真实长期会话、生成回答/NLI/科学verdict/无限上下文仍未完成。0新模型API调用授权，原科学/claims/fullhits/model/私有研究模板个人报告密钥不发布。
