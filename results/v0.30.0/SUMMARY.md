# v0.30 实验报告：标题/段落先行的开放检索与任务迁移

## 动机、冻结候选与判定范围

v0.29将来源已知/开放检索分开，定位为主要瓶颈。本轮只测一个预先冻结候选，
不接收目标论文身份：对标题单独一行、每个原段落单独一行，contentless FTS5
porter unicode61，沿用原问题STOP/前64唯一词/OR MATCH，无权BM25；按每篇最佳
单元分数、paper key、原句ID排序，取20篇不同论文。不是语义embedding/学习模型，
不在dev上调窗口/权重/融合。默认Memory/search/answer/CLI/HTTP不变。

辅助目录绑定精确snapshot、source-files和整DB SHA；每次查询验证原Memory索引、
辅助索引、命中原记录SHA/解析key-kind/投影指纹，不省验证换速度。旧索引遇到新
HEAD拒绝，须显式重建或选保留历史。新artifact不是Memory格式变更，只有显式API。
哈希用于完整性，不是对同时恶意改写DB和manifest的密码认证。

协议/驱动/全部54模块冻结`6370a14`，205测试运行、204通过、1权限跳过。见[冻结协议](../../docs/PARAGRAPH-RETRIEVAL.md)。

## 实际结论与下一步

- qasper-dev文档召回@5：44.279%→45.871%，实例差+1.592pp，77赢/61输。查询wall中位24.90→50.44ms；候选额外aux 5742950B。
- qasper-train文档召回@5：39.028%→41.998%，实例差+2.970pp，218赢/141输。查询wall中位34.73→116.62ms；候选额外aux 16855400B。
- scifact-dev文档召回@5：88.342%→81.117%，实例差-7.225pp，3赢/18输。查询wall中位21.51→49.09ms；候选额外aux 9044318B。
- scifact-train文档召回@5：89.175%→82.937%，实例差-6.238pp，8赢/47输。查询wall中位23.06→51.30ms；候选额外aux 9044318B。

QASPER dev的@5论文组区间跨零，train为正；24KB lexical完整参考分别260→284、
471→487，但train论文区间跨零。SciFact train/dev四个K均退步，claim组区间均为
负，新增任务没有支持迁移。不能仅用QASPER平均改善称通用检索收益。

候选全计aux后，QASPER dev/train计入总字节12191525/35931532B，已大于原JSON
11398686/31969387B；查询也更慢，未达到压缩与推理综合最优目标。即便不分配
完整公共运行时，仍不能声称本候选带来整个记忆系统净压缩。它只保留为显式实验
能力，不切换默认，不在当前gold上继续调权重/融合追求正结果。

下一项优先把同一冻结规则迁移到新来源任务，例如已准备但未做任务评分的公开
PubMedQA PQA-L；只做明确的自定义来源检索诊断，问题/答案字段不得进入证据索引。
不声称官方PubMedQA答案准确率，不把不同来源等同严格独立论文或盲测；先核对
原文身份/标注隔离和跨数据重叠边界，保留进一步退步的可能性。

```python
from rkv1.memory import Memory
from rkv1.memory_paragraph import ParagraphIndex
m = Memory('MEMORY')
index = ParagraphIndex.create(m, 'EXPLICIT-SIDECAR')['index']
result = index.search(m, 'scientific question', top_k=20)
```

## 数据、迁移和分母

| 任务 | 查询实例 | 唯一文本 | 目标claim/doc对 | QASPER非空参考分母 |
|---|---|---|---|---|
| qasper-dev | 1005 | 948 | 1005 | 927 |
| qasper-train | 2593 | 2451 | 2593 | 2240 |
| scifact-dev | 188 | 188 | 209 | None |
| scifact-train | 505 | 504 | 564 | None |

跨split同问句文本重叠：{'qasper_train_dev_question_string_overlap': 58, 'scifact_train_dev_question_string_overlap': 0}。

QASPER是已用公开任务，不是新独立来源/盲测/test。SciFact同已有5183篇abstract
来源，train505有证据claim用于新任务迁移；dev188复现旧基线，不称新语料。
train809/dev300全体中无证据304/112条预先排除正目标召回分母，不奖励空目标，
无官方test标签。SciFact只报文档召回/任一及全部目标命中，不评回答/证据句正确率。
其多文档recall先按claim平均，不把每个文档当独立样本。QASPER含无可答参考题的
目标论文召回与非空参考题覆盖分别计；未映射表格仍保留覆盖分母、无参考为null。

输入SHA/原tar SHA/公开源/许可见dataset-provenance.json，原文和问句/答案不发布。
Memory及辅助FTS只由原title/body构建，qas/claims/参考只供调度和独立评分，检索器
只接收问题，选择器只接收问题和已验证hits，均不接收gold身份/段落。

12轮新进程，12873正式题对、25746读取，24预热排除；QASPER129528上下文绑定。
三轮各条件keys/BM25/原文身份/原句选择/评分全一致。whole-paper逐题复现v0.29
QASPER全部六分数/原文/选择SHA及v0.15 SciFact dev前10 keys。相交命中来源逐字段
一致，所有原文件起止逐字节恢复、Memory和aux持久树逐文件大小/SHA均不变。

## 开放文档召回与迁移结果

![检索粒度与覆盖](paragraph-retrieval.png)

| 任务 | K | whole recall% | unit recall% | 赢/输/平 | 实例差pp | 组差区间pp |
|---|---|---|---|---|---|---|
| qasper-dev | 1 | 29.652 | 31.244 | 74/58/873 | 1.592 | [-1.318, 4.578] |
| qasper-dev | 5 | 44.279 | 45.871 | 77/61/867 | 1.592 | [-1.501, 3.687] |
| qasper-dev | 10 | 49.950 | 52.239 | 84/61/860 | 2.289 | [-0.783, 4.695] |
| qasper-dev | 20 | 56.020 | 59.602 | 96/60/849 | 3.582 | [0.091, 5.556] |
| qasper-train | 1 | 26.572 | 28.538 | 203/152/2238 | 1.967 | [0.514, 3.796] |
| qasper-train | 5 | 39.028 | 41.998 | 218/141/2234 | 2.970 | [1.282, 4.734] |
| qasper-train | 10 | 44.697 | 47.281 | 210/143/2240 | 2.584 | [0.528, 3.871] |
| qasper-train | 20 | 50.251 | 52.526 | 211/152/2230 | 2.275 | [0.313, 3.614] |
| scifact-dev | 1 | 70.700 | 62.899 | 7/23/158 | -7.801 | [-13.076, -2.660] |
| scifact-dev | 5 | 88.342 | 81.117 | 3/18/167 | -7.225 | [-11.702, -3.103] |
| scifact-dev | 10 | 94.211 | 88.874 | 3/14/171 | -5.337 | [-9.309, -1.862] |
| scifact-dev | 20 | 95.780 | 91.800 | 2/11/175 | -3.980 | [-7.092, -0.975] |
| scifact-train | 1 | 75.017 | 63.218 | 13/76/416 | -11.799 | [-15.297, -8.564] |
| scifact-train | 5 | 89.175 | 82.937 | 8/47/450 | -6.238 | [-8.696, -3.894] |
| scifact-train | 10 | 93.845 | 89.851 | 3/28/474 | -3.993 | [-5.875, -2.178] |
| scifact-train | 20 | 96.172 | 92.475 | 3/24/478 | -3.696 | [-5.710, -1.947] |

组区间：QASPER按论文均值重采样，SciFact按claim重采样，1000次seed20261025、排序索引24/974；仅描述该公开任务，不把重复轮次/段落当独立样本。任一/全部目标命中与论文宏平均见derived-metrics.json。

## QASPER同预算上下文完整参考

| 任务 | 选择器/预算 | whole完整参考 | unit完整参考 | 赢/输/平 | 问题差pp | 论文差区间pp |
|---|---|---|---|---|---|---|
| qasper-dev | source-order/8000 | 107/927 | 113/927 | 25/19/883 | 0.647 | [-0.705, 2.545] |
| qasper-dev | source-order/24000 | 232/927 | 246/927 | 55/41/831 | 1.510 | [-0.523, 4.489] |
| qasper-dev | source-order/48000 | 295/927 | 303/927 | 64/56/807 | 0.863 | [-1.691, 3.923] |
| qasper-dev | lexical/8000 | 179/927 | 184/927 | 40/35/852 | 0.539 | [-1.039, 2.920] |
| qasper-dev | lexical/24000 | 260/927 | 284/927 | 55/31/841 | 2.589 | [0.732, 5.095] |
| qasper-dev | lexical/48000 | 307/927 | 332/927 | 57/32/838 | 2.697 | [0.108, 4.543] |
| qasper-train | source-order/8000 | 176/2240 | 192/2240 | 48/32/2160 | 0.714 | [-0.145, 1.942] |
| qasper-train | source-order/24000 | 445/2240 | 480/2240 | 133/98/2009 | 1.562 | [0.518, 3.668] |
| qasper-train | source-order/48000 | 570/2240 | 616/2240 | 148/102/1990 | 2.054 | [0.630, 3.791] |
| qasper-train | lexical/8000 | 305/2240 | 321/2240 | 73/57/2110 | 0.714 | [-0.149, 1.941] |
| qasper-train | lexical/24000 | 471/2240 | 487/2240 | 102/86/2052 | 0.714 | [-0.707, 2.070] |
| qasper-train | lexical/48000 | 559/2240 | 596/2240 | 126/89/2025 | 1.652 | [0.413, 3.107] |

预算仅正文UTF8，标题/ID/JSON另计，不是完整prompt/token/账单；原句ID/locator不变。更好文档召回不必然改善有限预算覆盖；增加不同论文也改变段落排序IDF和竞争。不是模型准确率或官方QA/Evidence F1。

## 24KB失败分解及预算回归


### qasper-dev

| 选择器 | 分类 | whole-paper | best-unit |
|---|---|---|---|
| source-order | budget-omitted-reference | 134 | 137 |
| source-order | complete-reference-exposed | 232 | 246 |
| source-order | no-fully-text-mapped-reference | 44 | 47 |
| source-order | no-nonempty-answerable-reference | 78 | 78 |
| source-order | parent-not-top-k | 517 | 497 |
| lexical | budget-omitted-reference | 106 | 99 |
| lexical | complete-reference-exposed | 260 | 284 |
| lexical | no-fully-text-mapped-reference | 44 | 47 |
| lexical | no-nonempty-answerable-reference | 78 | 78 |
| lexical | parent-not-top-k | 517 | 497 |

### qasper-train

| 选择器 | 分类 | whole-paper | best-unit |
|---|---|---|---|
| source-order | budget-omitted-reference | 284 | 301 |
| source-order | complete-reference-exposed | 445 | 480 |
| source-order | no-fully-text-mapped-reference | 151 | 171 |
| source-order | no-nonempty-answerable-reference | 353 | 353 |
| source-order | parent-not-top-k | 1360 | 1288 |
| lexical | budget-omitted-reference | 258 | 294 |
| lexical | complete-reference-exposed | 471 | 487 |
| lexical | no-fully-text-mapped-reference | 151 | 171 |
| lexical | no-nonempty-answerable-reference | 353 | 353 |
| lexical | parent-not-top-k | 1360 | 1288 |
| 任务 | 检索器 | 选择器 | 8k→24k真→假 | 24k→48k真→假 |
|---|---|---|---|---|
| qasper-dev | whole-paper | source-order | 0 | 0 |
| qasper-dev | whole-paper | lexical | 0 | 0 |
| qasper-dev | best-unit | source-order | 0 | 0 |
| qasper-dev | best-unit | lexical | 0 | 0 |
| qasper-train | whole-paper | source-order | 0 | 0 |
| qasper-train | whole-paper | lexical | 1 | 1 |
| qasper-train | best-unit | source-order | 1 | 0 |
| qasper-train | best-unit | lexical | 1 | 0 |

所有失败、回归SHA和输题保留；同一预算均值改善不能推出逐题支配，预算改变也可能换选。

## 实际空间、构建与查询成本

| 语料库 | 原Memory B | 额外aux B | aux单元数 | Memory构建wall/CPU s | aux构建wall/CPU s |
|---|---|---|---|---|---|
| qasper-dev | 6065400 | 5742950 | 14156 | 0.6829/0.6250 | 0.4042/0.3906 |
| qasper-train | 18692957 | 16855400 | 49463 | 2.5346/2.3125 | 1.9790/1.9531 |
| scifact | 8420254 | 9044318 | 51135 | 0.9807/0.8750 | 0.9453/0.9219 |

全部54模块/HTML一次383175B，候选模块7475B另列。同实测安装两条件全计源；基线不计aux，候选全计index+manifest，不把新索引免费。SciFact两个任务共用同一个原库/aux，不将其当两套同时部署空间累加。

| 任务 | 检索器 | 计入总B | 查询wall中位/p95 ms | CPU均值ms | 整个进程RSS中位MiB |
|---|---|---|---|---|---|
| qasper-dev | whole-paper | 6448575 | 24.901/33.588 | 24.767 | 88.11 |
| qasper-dev | best-unit | 12191525 | 50.443/71.775 | 50.513 | 88.11 |
| qasper-train | whole-paper | 19076132 | 34.729/46.391 | 34.715 | 181.45 |
| qasper-train | best-unit | 35931532 | 116.621/174.194 | 115.379 | 181.45 |
| scifact-dev | whole-paper | 8803429 | 21.513/32.447 | 21.637 | 54.13 |
| scifact-dev | best-unit | 17847747 | 49.090/89.568 | 52.111 | 54.13 |
| scifact-train | whole-paper | 8803429 | 23.064/33.169 | 23.412 | 58.82 |
| scifact-train | best-unit | 17847747 | 51.303/92.491 | 54.280 | 58.82 |

aux每查询收整DB SHA和原Memory校验/原记录重读，不省校验。query/selector/离线gold评分分开；词法prepare每预算完整计一次，读取+选择为组件和，不是模型端到端。全进程RSS含标注/所有策略/结果，不分摊为某策略独立RAM。公共Python/SQLite/Zlib/OS、安装/pyc/文件系统未全额分配；计入总B不是完整部署净压缩。

## 决策与限制

完整报告保留全部任务/预算的正负结果；候选规则不按这些gold调整，不替换
默认检索器，不自动混合分数或补充oracle来源。学习/语义模型0、远程模型调用0，
不读取密钥；旧24次预算不扩大。若迁移或预算有退步，先分析失败与独立迁移，
不调权重重试追求正结果。真实模型质量、E3、多跳、长期对话、形式证明、冷缓存/
跨机器、掉电/并发/GC仍未测。单机暖缓存表现不能外推为这些能力或通用最优。

技术语义依据：[SQLite FTS5官方文档](https://www.sqlite.org/fts5.html)。contentless
正文列不存原内容，元数据另表；BM25数值更小表示更匹配，因此用升序排序。
