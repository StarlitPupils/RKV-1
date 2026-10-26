# v0.50 冻结协议：仅问题文本的词法检索与训练共现图对照

## 可证伪假设与验收

v049实际发行全部核验后实施。本版第一次在封存Task1 dev上检验question-only来源定位；没有生成答案、NLI或推理证明。比较三固定方法：lexical BM25、训练gold来源共现graph扩展、同图ID固定置换permuted_graph负控制。主门槛为graph的源ID组macro recall严格>另外两方法且完整ID覆盖题数≥另外两方法，三重复轮均满足；时间联合为graph/lexical的query wall/CPU/parent完整wall比三对中位数均≤1（零CPU分母null失败）。quality和time分别判并报告联合，不用额外字节费用抵消召回，不称完整TCO净收益。所有反向/未解分母保留，不调预算/参数/分数追正。

## 原数据、图训练与开发隔离

沿docs/entailment-inputs.json官方repo固定daac2fdb7ab52ec3ef8f2953f59288c1edd7c2f0，原corpus11941source IDs→11521精确decoded文本组，Task1 labels-train1313行/1308uniqueqid，Task1 labels-dev187物理行。此协议冻结前dev原字节只已下载/SHA/行数核验，从未JSON解析/看题目答案/评分；v049已见训练源253未解和3369UUID改写保持，不补gold进corpus。不使用Task3已检索context/relevance、question答案/hypothesis当检索特征。根license与上游限定沿原说明，原语料/私有model不得发布。

模型只读corpus和Task1 train。原source_alignment精确alias/UUID优先/无UUID只精确文字fallback不改。每训练问题proof叶source代表组成无向完全共现边，边权为共现的distinct训练qid数，重复训练qid不加倍；未解不构边。训练原source-ID标注包含文字改写，这只是监督来源共现关系，不称语义逻辑图。词法索引仅corpus原句ASCII a-z0-9小写tokens，长度>1、复用原memory.STOP；不stem/同义词或embedding。BM25固定k1=1.2,b=.75，N为11521精确文本组，avgdl含零token文档。重复query词按频数加分，排序score降序、sourcekey升序，浮点平台/解释器照实记录，不称跨机bitwise规范。

先完成267测试（266pass/1Windows权限skip）并冻结算法/driver/analyzer/本协议/原输入manifest/exact CI。随后训练构建**一次**共享词法index+graph+permuted控制，训练子进程parent完整wall/CPU/RSS/实际字节全部收费，唯一model原始JSON写exclusive+fsync。模型包含postings/源locator/alias/训练qid和normalized question SHA，原model私有。训练完成另exclusive+fsync保存model SHA、源/训练SHA、分组件bytes、code/protocol freeze、训练父完整wall和UTC时间，再明确记录dev未解析，之后才允许打开dev。失败不删除重训练或改变参数。模型freeze metadata公开但postings/边/原text不公开。

置换固定：全部source代表key排序，与按SHA256(ASCII rkv050control:+key),key排序的同集合一一对应，双端替换graph edge；保持非零degree/weighted degree多重集，控制和正图共用source/词法，不以dev调salt。

## 查询算法和gold范围

lexical取BM25完整有正分候选。graph/permuted_graph先保留top6词法种子；每个种子的邻接权重按总weight归一，乘种子原BM25分累加邻居，排除已种子，取score降序/key升序前6neighbor，再接原完整词法序列，稳定去重。无边则回退原候选。全方法相同最多12source组、4096原JSON member B，按候选顺序依次入证，单项超剩余预算skip继续，不回填gold或扩大budget。source member B含原key/colon/escaped value，非decode文本长度、CAS读B或RAMcap。候选源ID由算法选择，query只接收question字符串，拒绝整row；gold不传入ranking/admit，只有selected和verified hits生成后才计算gold。

先排除dev中训练qid或normalized question(casefold/whitespacecollapse) SHA相同的物理行，统计排除总数及原因保留；此规则冻结前固定，不根据成绩排除。其余全部187原物理行中的合格行评分，重复devqid不自动合并，独立uniqueqid数另报；没有事后只选可解题。macro按每物理题source组recall等权，micro总组数比另列。primary source-ID groups：gold叶映射精确alias代表，未解以annotation SHA为不可检索标记仍留分母，重复相同source只计1组。这个ID覆盖不等于改写句子语义已证明。

严格literal辅助口径：仅annotation逐字等原source的目标可命中，改写或未解各用annotation SHA不可检索标记，仍留分母；没有用annotation改写作原语料或NLI判断。两套完整覆盖/recall/未解/改写数同时报告。gold来自Task1 proof，不从Task3 top25候选或relevance当真值。题目本身含正确答案与否不改，只使用官方question字段，不拼接answer/hypothesis。

## 精确执行、独立验收与资源

固定3方法×3轮=9fresh worker，顺序lexical/graph/permuted、graph/permuted/lexical、permuted/lexical/graph，ABC/BCA/CAB。每worker每合格物理题一次检索，seed Random(20261027+round)仅打乱原187行，三方法同轮同序。质量三轮相同只验证确定性，独立科学样本数不能×3或×方法。每worker600s，失败/超时真实记录，不覆盖追加轮追正；正式科学评估唯一9worker计划。每轮model/full source和dev SHA再核。

每worker创建固定zlib/fixed65536/bounded Store只存原corpus，label question-retrieval；每query计时包含BM25/graph/admit、一次snapshot开关和每selected成员原Store.read_range+stored/raw/recordSHA/JSON身份。没有decoder缓存/校验删除，原member无法核验就失败。所有hit含原SID/path/offset/length/rawSHA/decoded句SHA，public没有原句/问题/答案。独立analyzer读raw slice+Store实际范围、逐sourceJSON核，重建gold两口径；从冻结model纯函数重放排名以核身份，是独立诊断CPU不是新评估试次或再训练。Store树前后/九worker完整相同、9整源逐字节恢复，所有proof三轮同方法确定。

worker加载同一完整模型（lexical也加载graph），实际load全部model字节/RSS/CPU收费；同时报理想部署词法shared/positivegraph/controlgraph各bytes和SHA，不说lexical真的未加载graph。模型训练一次CPU/parentwall/源文件/私有model、所有原input（未用Task3/dev副本）、Store/config/snapshot/CAS/源副本/plan/private-query-check/ledger/child/parent/log/图/源码全计账；私有query-check含真实question仅留.tools，其B/SHA不免费。input/plan/private-query/ledger/报告exclusive+fsync，内部Store fsync未知null，不称断电。

query CPU/wall、gold审计/ingest/全恢复/workerCPU和父紧包subprocess.run到退出的完整wall分别收费，父含加载模型/解析dev/末尾序列化与释放。观察RSS不是全生命周期增量RAM，source/index/catalog/fullproof都占内存。未测CAS/SSD物理/全系统IO/冷缓存/跨机继续null，不从计数推理吞吐；模型/专用程序/65递归Python+HTML（runtime仅版本）按实际B/SHA，未分配平台依赖不称完整TCO免费。

## 交付

必要单元：手算BM25、精确alias/稳定次序/无词匹配、重复qid去权/图置换degree守恒/不读answer/context/hypothesis、原record预算exact/不足/重复去重、unresolved/literal分母、真Store原member绑定与损坏拒绝。独立protocol/code freeze/exactCI→train once→modelSHA freeze→dev reveal严格顺序，不把预检或paper结果当项目收益。

代码/冻结协议/无原文原始JSON/图实际视觉检查/详实报告/README/路线/release/GitHub，CI后actual资产SHA/递归65Python+HTML/tag/新脚本、物理仓库外actual wheel+current native与actual sdist新BM25/graph/control/原Store来源合成smoke、旧功能/最终proof重下载全通过后下一版。原科学源、postings/私有模型图、question/fullhits/帧/恢复副本、私有研究/模板/个人报告/密钥不发布。

本机CPU离线0新远程模型API（旧24用尽）。这是未知问题原始来源定位，仍非语义蕴含证明/开放科学回答/真实长期会话。E3净压缩收益仍失败，E4整体/长期会话/回答质量/无限上下文未验收。
