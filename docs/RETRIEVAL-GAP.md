# v0.52 冻结协议：已见检索结果的漏证分解与gold-aware上界

v051 actual发布/源码/物理外部安装/finalproof全核验后执行。复用v050 dev187和v051 test339合格物理题的原round1结果、原私有question-check与同一model，六个split×method各一个fresh诊断worker，合计1578记录/6204源ID组分解；没有新科学评估试次、没有新训练或新模型。不再打开原科学标签或source原文，只依据已完整核验并冻结SHA的原报告/原query/model做纯排名重放与诊断；本版新原source range绑定次数0，不冒充新的逐字节来源验证。旧9+9worker科学结果保持。

## 假设与唯一口径

事前固定诊断假设：在graph的dev和test两个已见split中，“gold仍在原排名前12但受4096B入证字节排除”的组，分别占所有漏证组至少50%。每个split均≥.5才门槛True，否则False，不把预算调大后追正。此阈值是诊断口径，不是可部署性能门槛或因果干预证明；准备只生成输入SHA/代码合成测试，未计算实际分类/oracle数量。旧总体低召回和test literal负方向已见，不称新未知科学验证。

每gold ID组排他分类：1 已selected=recovered；2 不在原model source locator全集=unresolved_source；3 不在该方法完整冻结候选序列=no_candidate；4 在候选但不在稳定去重前12=below_count_prefix；5 其余=byte_budget_excluded。顺序固定、组数守恒；已selected可来自skip长记录后较后位置，先判恢复再判prefix，不能凭排名>12说它未恢复。标签描述冻结序列位置，不证明改某参数就会恢复或产生回答收益。

same model/evidence_retrieval/ranking/admit原byte完全不变，固定12facts/4096memberB；诊断选择依据原私人question，不拼gold作query。纯排名重放要等原selectedIDs和admittedB，原hit locator offset/length/SHA等model locator，仅核metadata身份；不读Store/source或假称物理IO为0。原report和query SHA在retrieval-gap-inputs.json，model SHA固定2f82ee4b28c943038e7a37ddcbd8871443f7a441ddd45a1af599decc8bade183。

## Gold-aware最优上界不是检索器

对每题分别算：A 全部可在原source定位gold ID组、B 仅该方法完整候选中可定位gold ID组、C strict literal gold组。选取只允许gold，目标为固定12/4096约束下最多unit-value组；因各组收益1，按原record length升序/key升序贪心可得最多组数。Oracle知道gold，不是可部署检索、不是新模型，不能把其recall/完整可能题数当项目成绩或声称改预算已经提升。unresolved/nonliteral标记仍留目标分母，不能补到原corpus。

独立analyzer另用按组数的最小费用动态规划（0..12 DP）证明三上界的最优可选数量和实际所选B/唯一性，检查不靠同一个贪心实现自证。literal上界也不当NLI，逐字不相同annotation不可通过身份诊断变成语义正确。没有调整预算/k/graph/weights/tie/seed或训练，原quality/time数值一字不改。

## 冻结、次数与资源

270完整测试269pass/1Windows权限skip（2新必要测试：32组小合成随机长度的贪心与穷举全集对照，exact/不足/candidate限制；5排他类别/守恒/选项合同拒绝）。冻结源码/协议/input/exactCI后唯一6worker，固定dev lex/graph/control、test lex/graph/control，每个worker600s。失败保留返回码/异常/childSHA/父完整subprocesswall，不覆盖/追加重跑。因确定性已见数据，不机械重复3轮，也不计算在线提速门槛。

独立核六个原报告指纹、原querySHA、modelSHA、每1578原proof引用、候选重放/selected/admitted一致、6204组类别守恒、所有gold oracleDP数量/bytes。新worker only model+metadata+privatequery输入，全部加载read返回B/CPU/wall/RSS/父完整wall收费。没有新Store、索引/科学frame；工作目录可为空，输出child/parent exclusive+fsync。读取原query仍是真实科学问题，原文私有，输出只ID/类别/数量/SHA/上界与成本。

旧model4629668B每诊断worker实际载入，原共享索引/图和历史训练费用照列，不因本版训练0说模型免费。全部原input/report/query/model、六个child/parent/log/图/协议/source费用分开，65递归Python+HTML仅版本，专用/复用scripts按实际B/SHA，不漏旧bad和追加auditor原版本历史成本。observed RSS不是全生命周期增量RAM，gold oracle本来就不是推理部署内存预算；4096入证不是CAS/OS读取或RSS上限。

## 交付与限制

代码/必要检查/冻结协议/无原文原始JSON/标准图实际视觉检查/详实报告/README/release/GitHub，CI后actual5资产SHA/65递归Python+HTML/tag/诊断脚本、物理外部actual wheel+current native/actual sdist新partition/oracle合成DP守恒smoke/旧来源批查询CLI/最终proof上传重下载全部通过后下一版。原science source/questions/privatequery/fullmodel-postings图/帧恢复副本/研究模板个人报告密钥不发布。

本机CPU离线、0新远程模型API（旧24用尽）；本版纯已见数据诊断不称新科学验证、生产压缩/提速、NLI/生成回答或真实长期会话收益。E3净收益失败，E4整体/无限上下文未完成；SSD物理/全系统IO/冷缓存/跨机未测。下一项根据分解另冻新假设/数据，不用oracle泄漏来调本批测试成绩。
