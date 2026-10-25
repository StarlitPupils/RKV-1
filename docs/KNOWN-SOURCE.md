# v0.29 来源已知与开放检索：结果前冻结协议

v0.26–27在全库定位QASPER目标论文，原任务却提供论文。为区分这两类工作负载，
本轮保持同一dev/train原JSON、原选择器、三个正文UTF8预算，不改变检索或默认策略。
不调参数、不训练、不调用模型、不读取密钥。新增Memory.lookup(key,snapshot=...)，
只接受调用方已经知道的原证据key。该方法不从问题猜来源，不返回BM25分数；缺失
key为空，不回退检索。验证索引/当前locator/精确原记录SHA与解析身份，同search
共用原字节验证。v1–v4支持；v3位置重放和v4重绑定物化到查询内view，无跨query缓存。
这是明确提供来源的读取能力，不宣称优于开放检索或隐含提供gold来源。

## 三个明确条件

1. **open-top5**：原search(question,top_k=20)所得top5；问题是唯一检索输入。
2. **known-source**：独立lookup由任务提供的paper_key，只暴露这一篇；问题只供
   随后的段落选择。这是来源已知工作负载，不是开放检索改善。
3. **oracle-if-recalled**：从open top5中按标注目标key过滤出原目标hit；未召回则空。
   仅为事后诊断，使用了目标身份，不能部署为无来源检索或并入open成绩。若已召回，
   其原文/locator/所选原句ID须与known条件逐字节相同（citation ID/检索rank可不同）。

每条件source-order与lexical；原8000/24000/48000正文UTF8预算，top5/单来源对应
score_selected的top_k=5/1，oracle评分仍绑定open原top5，不能换造locator或句子。
两个选择器均不看参考段落。逐条件计算原完整参考覆盖、最佳参考段落召回、未映射
项/无参考项、按题及按论文均值、赢/输/持平、预算真→假回归，保留负结果。
known-source减open不是检索算法收益；oracle减open是去干扰的受控诊断，可能正负。
分别在目标已召回/未召回的题上分层；各参考集合非空才参与覆盖分母，不删除图表/
未映射证据，无参考保持null，不奖励空集合。不是官方QASPER QA/Evidence F1。

## 固定数据、轮次与一致性

沿用docs/CONTEXT-SELECTION.md的SHA：dev281篇1005题，train888篇2593题。
原文和两split任务此前已评测，不是新独立数据/盲测/test；不在这些gold上搜规则。
两个split独立新建默认固定/Zlib/v3，label仍v026-qasper-coverage/v027-qasper-train，
使snapshot、来源定位和open成绩可逐题对照v0.27。所有questions/annotations仅供
独立调度与评分，FTS仍只索引title/body，lookup只接收paper_key不接收答案。

每split三轮新进程，seed20261025+r打乱问题和两读取操作顺序；各进程先执行一次
search和lookup预热排除。共10794正式问题对、21588正式读取操作、194292条件/
选择器/预算绑定。三轮所有key、BM25(容差1e-10)、原文身份、覆盖与选择原句SHA须
一致；open逐题与v0.27全部相同。known来源身份与同题open命中若存在必须完全相同。
已召回时oracle与known的分数覆盖/recall/原句身份相同，未召回oracle上下文必须空。

读取wall/CPU分别计时；各条件词法prepare一次、每预算choose一次，但单预算延迟
完整加prepare，不除以3。oracle读取共用open，单列过滤CPU/wall；其组合时间是
search+过滤+选择的组件和，known为lookup+选择，不包含gold评分，不称真实模型
端到端延迟。rank为null表示未排序，不能把它当0分。实际context紧凑JSON字节另计，
不等于完整请求/token。进程总时长/RSS列出，不把全进程RSS归因给某个策略。

1000次论文组bootstrap，seed20261025；论文宏平均配对覆盖差，排序2.5/97.5
百分位索引24/974，作为公开集描述区间。重复轮次/同论文问题不能当独立论文。
三条件用同一个不变Memory；起止整份原文逐字节恢复、持久树各文件大小/SHA相同。
全部RKV Python/HTML源一次成本、lookup源码增量、build成本单列；不省略源验证来
追求提速。公共Python/SQLite/Zlib/OS/安装/pyc未全额分配，不是完整部署净压缩。

## 交付和判定

只有零绑定错误、open基线精确复现、失败与条件代价完整披露才接受本轮。性能
结果可正可负，不预设lookup更快；不改默认、不自动注入来源到memory-answer。
输出无原问题/参考/科学原文的原始JSON、图表、详实报告和版本说明。原JSON、
私人研究、个人报告/模板和密钥不发布。真实模型质量、E3、多跳、长期对话、形式
证明、冷缓存/跨机器、掉电/并发/GC仍未测。
