# v0.30 开放检索候选：结果前冻结协议

v0.29确认来源定位是主要瓶颈。下一轮只测一个显式候选：按段落/标题独立单元
建contentless FTS5，以每篇论文的最佳单元BM25排序（数值较小优先）。标题仅一行，
每个正文段落一行，不在每段重复标题；同原porter unicode61、STOP、前64唯一词，
OR MATCH、默认无权BM25，不搜索窗口/权重/融合/重排参数，不输入目标paper key。
按BM25、paper key、sentence ID（标题=-1）确定排序；取前20个不同论文，不补池。
这是词法粒度对照，不是语义向量检索或新增学习模型。

新增显式辅助索引目录index.sqlite+manifest.json，排除在Memory持久树之外；只读
绑定一个精确snapshot及source-files、全索引SHA。建立时解析验证全原始来源，只有
title/body入FTS，locator/论文key/投影指纹另表；绝不索引qas/claims/答案/参考。
查询先验证Memory原manifest、aux manifest/index SHA和snapshot匹配，原始记录
按range/record SHA/解析key-kind/投影指纹逐命中核验。源更新后必须显式重建或读旧
snapshot，绝不静默使用过期索引；缺失/损坏/错snapshot/符号链接失败。辅助内容
哈希仅用于完整性，并非对恶意同时改写索引与manifest的密码认证。

默认Memory/search/answer/CLI/HTTP不变，无新增原存储格式。基线仍原whole-paper
BM25；候选与基线各实际验证top20来源，再给同原source-order/lexical、8/24/48KB
正文预算，保留原句ID及精确locator。两条件的评分是同完整独立gold scorer，不
由gold引导检索或选择。不以模型正确率称覆盖指标。

固定数据：QASPER v0.3 dev281论文1005题/train888论文2593题，SHA沿旧协议。
新增任务迁移：SciFact同已用5183篇abstract corpus；完整train505个有证据claim，
dev188个有证据claim。原train任务未用于候选评价，规则先冻结；不是新语料/严格
盲测/官方test。不使用SciFact claims_test标签。只检索claim文本，gold文档列表仅
供独立评估，所有无证据claim不赋正召回（分母规则预先明确）。SciFact train809/
dev300总量、任务纳入数、非空目标文档数564/209、重复文本/跨split重叠另列。
SciFact原JSONL SHA从datasets.SCIFACT核验，原tar SHA/许可保留。新索引不混三个库。

每任务三轮新进程，seed20261025+r打乱读取条件/题序；每进程每检索器一预热排除。
共12873正式题对、25746读取、24预热读取；QASPER129528选择器/预算绑定，SciFact
只比较parent召回@1/5/10/20，另列每claim所有目标召回/至少一个目标，平均先按
claim不当gold文档独立。QASPER参考分母/未映射/null规则沿原，不删负结果。基线
QASPER与v0.29逐题top20 keys/BM25/来源身份/六评分相同，SciFact dev前10 keys与
v0.15对照；三轮各条件keys/BM25/来源身份/覆盖/原句SHA全相同。含分层失败/赢输/
预算非单调与按论文组1000 bootstrap；SciFact按claim bootstrap，不当段落为样本。

每个条件全实际wall/CPU、排序/选句/独立评分分开；新索引查询含每次整DB SHA，
不省完整性换速度。全进程RSS和wall单列，包含所有任务/指标而不分摊成单策略RAM。
aux构建wall/CPU、实际index+manifest B、原Memory B、新模块和全部54模块/HTML源
一次全计，基线不收候选index费用，候选需额外全收；共享runtime/安装/pyc未全额
分配，不能称完整部署净压缩。aux的科学词项索引不发布，公开无原文聚合/原始JSON。
查询起止原Memory及aux树逐文件大小/SHA不变、全原文逐字节恢复；原子发布/损坏/
历史/标注隔离/稳定tie/Unicode/bool top_k拒绝等适当测试。SQLite关闭并fsync后
才发布manifest；未完成的目录不可打开，保留失败残留、不覆盖既有目标，不称掉电证明。

只有零绑定错误、原基线复现、完整成本/损失披露才接受。QASPER/SciFact可改善也
可退步，跨任务或预算退步保留；不因现有dev改善改默认，不二次调规则追求正结果。
真实LLM/远程API调用0，不读取密钥；冷缓存/跨机器、推理质量、E3、多跳/长期对话/
形式证明等仍未测。若候选收益混合，下一步优先独立迁移/剖析，而非调权重重试。

技术语义依据：[SQLite官方FTS5](https://www.sqlite.org/fts5.html)，contentless列
不存原内容、rowid之外读回为NULL；BM25较小更匹配。因此元数据另表、排序升序。
