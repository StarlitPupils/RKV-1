# v0.61 冻结协议：训练集词语关联的question-only来源定位

v060实际发行/8base资产/物理外wheel与current/measured native/finalproof完整后采用。已见SciFact corpus/train/dev，原BM25参数1.2/.75与wholepaper12/4096不变；只评来源ID，不评SUPPORT/CONTRADICT、NLI、rationale正确性或答案。原索引源SHA和distinct原paperID保持。0远程模型API，旧24已耗尽。

## 唯一候选及负控制

训练输入809原train行（807 normalized question SHA组），原base模型10152832B SHA f062c7a784421b71bbfaf3c299be78ff323a391847afbf5420e4c06a4d422be0，只用其固定source/postings/IDF及训练原claim文本+gold paperID，不读verdict标签；support/contradict文献都为相关来源。规范问题SHA相同的训练行union gold ID，按group一票，空gold组不作负标签。

每gold doc取原BM25单term分最高16词（IDF及TF/原长度规范同base，tie字典序）；每group gold词union，每query token q与不同target词t共现计distinct group，P(t|q)=support/包含q的annotated group数。每q保留最高support的8target，tie词典序。sidecar保存整数support/denominator，不存不可追查权重。

查询只收原claim字符串。原Counter词频不变，对各原q的关联票数qtf*support/denominator用精确Fraction相加，排除所有原query token，取最高8target，tie词典序，权重归一总量0.25；原BM25分数+.25归一扩展BM25分数排整篇原paper，再原admit12/4096。未命中关联则原lexical，无隐藏扩大预算。

control按所有learned query key的SHA(rkv061control:+key)/key排序循环移位一格，重新绑定整份target/support/denominator列表，≥2key时无fixed point，保持完整列表multiset与serialized bytes；<2key记控制不可用且quality gate失败，不临时换种子。不是有语义能力的模型、知识蕴含或新神经训练。

## 冻结与正式次数

本版前只做自有合成准备：10core/audit检查，原train schema/count/SHA/sourceID检查（809/807/505annotated/2817qterms），0真实learn、0新dev打开/评分。准备不是科学收益。11必要检查（加三角色实际Store toy worker/基线不加载sidecar/坏baseSHA拒绝）及本机完整331检查330pass/1权限skip后freeze code/protocol/input，exactCI成功才train一次；另冻actual sidecar SHA/B和training CPU/wall/RSS/所有组件B/SHA，才评分。原base不重训，真实sidecar不随public发布。

3方法A lexical B expansion C permuted_expansion ×3轮=9fresh worker，ABC/BCA/CAB，600s/worker0retry。每轮固定shuffle seed20261027+round，原300dev含2 trainID/normalized-question overlap排除，其余298中188有evidence、110无gold保持null。每query先ranking/admit/实际原record校验后才读gold，禁止把110当0或成功、禁止删坏例。baseline只load原base，candidate/control再load整个sidecar，constructor/全部验证/报告I/O计worker和parent；不能让baseline加载无用sidecar。query时间含原source证据校验，observer无。

H1质量：每轮candidate macro paper recall严格大于lexical和permuted control两者，complete question数≥两者；control不可用则False。H2时间：candidate/lexical query wall、CPU、parent wall三轮配对中位比均≤1，零分母null失败。联合H1&&H2。原sourceID/原文引用正确≠支持主张或答对问题，单known corpus不能称E4整体通过。

## 独立审计、成本和发布

独立ref scorer不调用candidate ranking/lexical helper，按整数关联/精确Fraction及原BM25公式重算9×298排名/admit，核模型/控制permutation/预算、原byte/locator/abstract-title SHA、全部gold/rationale index、逐题proof跨轮确定、9完整源恢复/readonly ledger与真实全部文件B。基线应与v053既有lexical逐题selected ID及来源证明相同，若不同保留并审计，不覆盖重跑。

全66递归Python+HTML、完整old base+新sidecar（含control）、专用源码/全部assessment/test/protocol/input、训练和model加载/查询/完整parent/CPU/RSS、rawJSON/图/log/sidecar、原CAS/所有旧快照和负实验残留均记录。无新DLL性能测量，已有native发行资产仅legacy功能核验；原训练成本保留，新sidecar不是LLM权重。物理SSD/全系统IO/冷缓存/跨机null。

代码/必要测试/冻结协议/无原文rawJSON/标准图实际查看/详实报告/README/release，CI后actual资产SHA/递归Python+HTML+scripts+Rust/物理外actualwheel+current native/actualsdist新扩展与全部旧smoke/finalproof重下载后完整交付。真实科学原文/模型token映射/fullhits/私有研究课程个人报告密钥不发布，任何未正式/未收尾阶段如实checkpoint。E3净收益/E4整体/真实长对话/回答/无限上下文未完成。
