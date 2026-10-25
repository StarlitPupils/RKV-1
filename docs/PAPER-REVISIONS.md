# v0.23 独立真实正文修订基线（结果前冻结）

目标：将验证从QASPER正文相同的数据集发布转到独立真实论文正文修订；先建立
原始JATS整篇记录基线，禁止为获得增量收益临时调高256KiB预算或改写原文件。
数据规则在读取论文内容/性能前固定：eLife官方elife-article-xml提交
ed4962931df3720e9e96cf93fb165a754d1df212的preprints目录，按数值论文ID升序，
前六篇同时有v1/v2/v3且每个文件<=1MiB。选中85562、86668、86670、86689、86721、
86805；18原始文件Git blob/大小、SHA256、版本和逐篇CC BY/CC0链接固定于
elife-revisions-inputs.json。不是随机领域代表样本，选择偏向早期三版本论文；没有
按压缩收益筛选，也不将12转换当12独立论文。正文投影均确有变化是预检事实，非
选样条件；原始文件名/字节保留。

来源：
https://github.com/elifesciences/elife-article-xml/blob/ed4962931df3720e9e96cf93fb165a754d1df212/README.md
该官方仓库保存每次修订，本文只使用上述固定18文件，不追踪动态master。

新来源kind=elife-jats-article-v1，精确记录是整个原XML，offset=0，包含原声明/
DOCTYPE/所有字段，<=1MiB沿用原型限制。单独记录重读恢复publisher ID与匹配的
base DOI，不使用文件名构造身份，不把重新序列化XML/JSON称原文。必须是无默认
命名空间research-article，唯一eLife publisher ID与10.7554/eLife.ID base DOI，
恰一title/body；有版本DOI可保留。用单遍Expat+TreeBuilder，外部DTD不读取、不
请求网络；内部实体声明/外部实体引用拒绝，截断/多根/重复身份/未知模式拒绝。

检索投影为article-title内联文本、普通abstract的p、主body的p（一个p不再重复
枚举其嵌套p）；不索引sub-article/review/response、fig/table-wrap、supplementary-
material/boxed-text/ref-list/fn-group及正文section标题。保留所有原字段在CAS；
FTS文本是提取表示，不承诺数式/表格的科学语义完备。QASPER投影无变化，记忆v4
仍使用既有指纹编码与projection标记，新增kind才解释JATS，需v0.23来源解码器。
允许相同key/kind的JATS精确投影未变时重绑定；真正文变化仍普通FTS重放。物理
CAS1/归档v1–v6与应用清单v1–v4不变；旧v0.22不能解码新JATS来源，不称向后可读。
默认仍预算v3，v4显式，无自动迁移。

三策略compact-full-v2 / compact-budget-v3 / compact-projection-v4，分别固定
64KiB/Python与Gear64KiB/精确旧Rust库，各3轮=18新库。先同时放6篇v1，然后按
ID逐篇升级v2、再逐篇v3，共13快照，保留每份原文、索引、清单，无GC。顺序
20261025+round打乱；同组各策略源/标签/CAS必须一致。不是按论文发布时间排序
的真实服务流，而是明确受控的交错修订时间线。源准备不计commit，全部源读取/
解析/预算/验证/HEAD发布计入commit。

预检显示每次旧+新整篇记录均>256KiB，因此预算v3/v4预期每次以record-bytes建
完整检查点，即13份基础；完整重建也13份。应原样报告这个粒度限制，不能按结果
修改预算。新候选未必省索引，Gear CAS复用须和索引收益分开计。真实变更不强行
归类标注；统计各版本投影摘要/段落数/旧新字节。未来段落策略另定版本协议。

18查询：6个初版标题，以及每篇两次修订的首个按位置不同的当前段落，各取前8个
唯一ASCII字母长度>=4且非STOP词。不是人工科学问题/gold答案，不以命中效果选题；
所有阶段/策略复用同组同轮顺序，仅公开query SHA，不发布问题/正文。每个阶段
新查询进程、1预热排除；18条件×13阶段=234进程，4212正式查询。每次在初版快照
重查4题共936历史身份查询，234次人为不存在标记阴性控制（不是新科学反例）。
234快照实例结束全源SHA/大小重开，当前源逐字节比对；含轮次/策略重复。

全部正式/历史查询比较key顺序、BM25绝对差<=1e-10、title/sentences/完整locator
身份摘要；每次返回仍验证CAS stored/raw、原记录SHA与身份，v4另核投影SHA。
各同分块策略CAS整树一致，查询前后整库持久树大小/SHA不变。query wall/CPU包括
整个search与释放，进程启动另列；worker选题解析原输入、RSS含整个进程/输入，
不与v0.22不同输入方式历史RSS直接比。按题/轮配对取中位，全矩阵包含空间/提交/
查询/RSS。全部50模块及HTML一次，Gear加整个精确实测库/元数据一次；Python/
SQLite/OS、pyc、安装/文件系统元数据未全额分配，非完整部署净压缩。

0模型调用/新增科学QA；只有新6篇/12真实正文转换。仅本机温缓存，无E3、多跳、
长期对话、形式证明、新问答质量、冷缓存/跨机器、掉电/并发/GC结论。原始科学
输入/问答原文/私有研究不发布，公开固定来源/SHA/聚合和不含原文的查询身份摘要。

```powershell
python -m scripts.run_paper_revisions --fetch --out results/local-revisions --work .tools/local-revisions --native-library measured/rkv1_core.dll
```
