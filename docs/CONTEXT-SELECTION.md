# v0.27 问题相关段落选择：同检索/同预算配对（结果前冻结）

依据v0.26全dev：@5论文44.28%，24KB完整参考232/927=25.03%，134题在已召回且
可映射条件仍被预算遗漏。本轮只改派生上下文选择，不改Memory检索或原来源。
检索未找到的论文不能由选择器补出，图表未映射项不删除，不输入gold来选句。

## 一个候选与完整身份

基线source-order为现有exposed_hits。候选lexical用查询内SQLite FTS5 contentless
paragraph(body)，只放top5已检索论文的原body段落，不复制title列。问题tokens
沿用Memory的Unicode词、STOP、唯一前64词；OR MATCH，porter unicode61，默认
BM25，score升序、原文档排名/段落序号破同分。未匹配段落依原顺序跟在后面。
无token/无匹配回退原顺序。没有新stop表、权重、embedding或学习/参数搜索。

按该完整顺序，仍采用原预算下skip-if-too-large，预算为8000/24000/48000正文
UTF8字节，最后按原文档/原段落序重新排列已选引用；保留citation_id和原句ID。
不把字符串切短拼成新句，不跨来源合成证据，title/JSON成本另计。rank临时索引
只活在一次query，不持久化。原Memory/default model responder仍source-order；
lexical是显式候选API，不默认替换或额外调用模型。

评分器新增score_selected，在评分前逐字段绑定所选对象回top5原hits，检查完整
句子数组/locator/title/citation_id等不变、句ID唯一合法、实际正文总字节不过限。
合成测试必须拒绝篡改原句/locator/句ID及重复；选择器只接受源已校验的hits。
对真实查询，Memory继续逐原成员验证CAS/record SHA和身份。

## 固定数据与迁移验证

dev仍原v0.3 281篇/1005题/SHA 2ae7ee62a65b1c4225791c70de80c2aad4e8998cf1fd4f09a53103db4f21af93。
另用v0.3 train原JSON 31969387B、888篇/2593题、SHA
9458bfe76074a8fa8d1685af02bcc73537aa6d338ad20591dfaff1946bc88bf4。
来源/压缩包SHA/CC BY4.0沿用version_data.py。train原文曾用于CAS存储实验，但
未做本轮任务评分；称新增任务评测论文，不称新科学来源或严格盲测/官方test。
规则在查看train覆盖结果前冻结，不在train gold上调参，不训练模型。报告各split
问题实例/唯一字符串、跨split论文/问题文本重叠，重复问句与多标注不是独立论文。

两个split分别构建原默认固定/Zlib/v3初始库，互不加入对方语料。dev使用v0.26
相同label以使快照/完整来源身份可精确比较；train标签v027-qasper-train。检索
top20、上下文只top5。每split三轮新进程，seed20261025+r打乱题序，各一预热排除；
共10794正式查询/6预热。每一次检索结果同时给两选择器，不重复检索来掺入差异。
dev基线逐题keys/排名/完整来源SHA及三个预算评分须和v0.26完全一致。

全体非空可答参考、可文本映射子集、按题和按论文宏平均、全部失败分类沿用
QASPER-COVERAGE.md，不是官方QA/F1。逐预算报告baseline→lexical完整覆盖赢/输/
持平、最佳参考段落召回差、预算单调性回归。1000次按论文组的bootstrap，固定
seed20261025，对论文宏平均配对delta取排序样本2.5/97.5百分位（索引24/974），
只作该公开数据的描述区间，不把题/轮当独立论文或普遍因果证明。不预设必须正。

## 时间与资源

查询top20 wall/CPU单列，共用同一实际检索结果。lexical排序prep wall/CPU和每个
预算choose wall/CPU分别测；离线为三预算只排序一次，但每预算完整收费一次prep，
不把prep除以3。条件顺序按每题固定SHA+轮seed打乱。评分/身份审计时间另计，
不得把离线gold评分时间混入生产选择器时间，或把省略检索后的时间称端到端。
报告每预算search+prepare+choose，实际进程总时长/RSS另列；无跨query缓存。
所有round原完整hits/所选引用身份SHA/评分须一致，壁钟允许自然波动。

源准备不计build；全源读取/索引/校验/HEAD计入。两个库起止完整源逐字节恢复，
读前后持久树大小/SHA不变。全部53模块/HTML源在两策略各计一次，临时词法索引
不占持久字节、但计CPU/进程RSS；公共运行时未全额分配，源码增量另列。分别列
实际context JSON（标题/句ID/转义/结构开销），不称正文预算为完整API预算。

本轮不因dev改善自动设默认。只有零绑定错误、同预算下明确代价/赢输，并在未
调参的train有支持，才考虑下一版显式接入；默认变更/模型质量仍须独立验证。
原问题/证据/原JSON留本机，公开固定SHA/无原文指标和聚合；0新增API请求，不读取
密钥。无E3/多跳/长期会话/形式证明/冷缓存/跨机器/掉电/并发/GC结论。
