# v0.49 冻结协议：已见训练标注的原始来源身份就绪审计

v0.48 actual资产/全部65递归源码/物理仓库外安装/最终proof完全通过后实施。此版是新题库训练输入的独立物理来源诊断，不是未知问题检索/多跳推理/模型或回答收益实验。准备阶段已看过训练schema和映射数量；不能称这些计数未知或先验未见。严格就绪门槛不因已见负结果而放宽，开发集仍封存。

## 输入和唯一规则

官方allenai/entailment_bank固定commit daac2fdb7ab52ec3ef8f2953f59288c1edd7c2f0，data/public_dataset/entailment_trees_emnlp2021_data_v2。原始Git blob SHA1与本项目SHA256/bytes在entailment-inputs.json，源文件留.tools/entailmentbank-preparation。root LICENSE为Apache-2.0，不据此臆断全部上游facts独立许可；只发布程序/无原文metadata，不重分发科学语料。正式只打开corpus.json和labels-train.jsonl，绝不解析/使用两个dev文件、question/answer/hypothesis/context/relevance评分。准备下载dev仅为固定原字节身份，训练/开发不得混用。

Task3原训练1313条proof全空，不当gold；Task1 labels-train原1313行/1308唯一qid含权威proof。使用proof中sent数字标记的唯一叶集合，原meta triples和worldtree_provenance映射；无叶/缺metadata失败，不静默丢行。语料原11941源ID/11521精确decoded句子，420纯文本完全相同alias；代表固定lexmin源ID，原语料字节全部保留，不做语义/大小写/标点合并。

每叶若provided uuid存在原语料，按其原始来源ID→精确alias代表绑定，另明确比较annotation字符串是否逐字等该source句子；不能因ID存在就说改写annotation已获语义证明。uuid空/不存在时只允许annotation与原source decoded句子**完全相等**的fallback；否则unresolved，禁止模糊猜测、丢分母或把gold注释补进原语料。准备计数已见：5764叶出现=3982 UUID+1529精确文本+253未解；5511可来源绑定中2142 literal相等、3369 UUID绑定但annotation改写。正式必须独立核原成员，而不是把准备预检当已完成物理验证。

## 冻结正式计划和门槛

仅3fresh worker顺序round1/2/3，每worker只读原corpus/Task1 train，一份源副本创建原Store(zlib/fixed65536/bounded)，固定label train-source-alignment。用原memory_qasper.members解析精确JSON key+colon+value成员offset/length/rawSHA；逐5511可解叶实际从Store Snapshot.read_range读范围，核rawSHA和JSON {原key:原source句子}，原stored/raw/codec/EOF/size验证不绕过。每5764叶记录row index/qid/leaf ID/映射方式/fact ID/annotation SHA/literal状态/locator，不发布原句、问题、答案或proof。

全体17292重复叶检查、16533重复原成员绑定、3整corpus逐字节恢复，三轮都是同一已见训练输入，不是三独立科学样本。原Store全文件树在查询前后和跨轮完全相同，无remember/派生科学答案/模型。严格ID就绪门槛=未解0；严格literal门槛=所有5764叶annotation逐字等source。均应按实际计数判，不因预知失败换成“有部分就通过”。来源机械验证可通过，两个数据就绪门槛可失败；失败不等于已证明annotation错误，语义等价本版未测。retrieval_quality_gate=null，训练/远程调用0，不预览dev。

263检查262通过/1Windows权限跳过（含3新来源/alias/损坏必要测试），冻结程序/协议/输入manifest和65runtime仅版本、exact CI成功后唯一正式3worker。单worker600s，exclusive+fsync child/parent/ledger/source副本；真实退出码/异常/报告SHA/紧包subprocess.run到退出parent完整wall保留，失败不覆盖追加重跑。内部Store fsync未知null，不称断电或冷缓存。

## 独立审计、成本和交付

独立analyzer直接json.loads原corpus/Task1 train，重建纯文本alias和每叶映射，按物理raw slice核SHA/JSON/Store真实范围，不只检查同源候选相等。所有records跨轮相同、原Store tree/完整恢复相同；父计时/SHA和原始JSON完整核验。仅train两文件入口静态可审核，本版没有覆盖全系统的文件访问监视，不把no_dev标记冒充OS I/O审计。

全部Store对象/index/config/snapshots/残留、原source副本/ledger、共享原输入（含准备阶段额外下载但未使用的Task3/dev/license）、原始JSON/parent/log/图/源码分别按实际B/SHA记账。重复源范围读取不能当新科学事实数，原input read返回B不是SSD/全系统IO。worker CPU/wall/parent完整wall/源绑定诊断CPU/RSS/分析额外费用全部单列；观察RSS非完整增量RAM，平台/依赖未分配不称完整TCO。无图模型训练、无检索分数、无模型/字典新产物。

标准图实际视觉检查、详实报告/README/路线/release/GitHub，CI后Release，actual资产SHA/65递归Python+HTML/tag/程序，物理仓库外actual wheel+current native与实际sdist新alias/来源范围核验合成smoke、旧格式/CLI和最终proof上传重下载全通过才完成，再下一版。

后续若做训练图与词法检索，须另冻只用question的算法、train-only构图/模型SHA、固定预算/置换控制，再揭dev；未解目标保留负分母，UUID改写不冒充语义证明。E3净收益仍失败，E4整体/真实长期会话/回答质量/无限上下文未完成。本机CPU离线，旧24模型API耗尽无新授权；科学原文/段/帧/恢复副本、私有模型研究/课程模板/个人报告/密钥不发布；SSD物理/全系统IO/冷缓存/跨机未测。
