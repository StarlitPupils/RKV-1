# v0.29 实验报告：来源已知与开放检索的差距分解

## 问题与冻结设计

v0.26–27采用全库定位论文，而QASPER原任务给定论文。本轮把“调用者提供来源”
与“仅问题检索”分开：新增显式Memory.lookup，不把已知目标身份当作开放检索
能力。原选择器、三个预算、原语料、默认策略和所有原存储格式均不变。

三条件为open-top5、known-source、oracle-if-recalled。后者按标注目标从已召回
top5中过滤，未召回则空，是用到目标身份的事后诊断，不可部署为开放检索。
known直接接收paper_key，不接收问题/答案；两选择器只看问题和已验证正文。
实验结果是完整参考段落暴露，不是回答正确率或官方QASPER F1。

```python
from rkv1.memory import Memory
result = Memory('MEMORY').lookup('qasper:already-known-paper-id')
# result['scope'] == 'explicit-known-source'; rank为None，缺失key为[]。
```

key须为1–512字符且无NUL；snapshot可显式读取保留历史，不指定时读当前HEAD。
该Python能力尚未接入memory-answer/CLI/HTTP，不向既有回答流程自动提供来源。

运行模块/驱动/协议在`222dda9`冻结，200测试运行、199通过、1项Windows符号链接权限跳过。协议见[KNOWN-SOURCE](../../docs/KNOWN-SOURCE.md)。

## 主要结论与优先级

- dev的24KB lexical：open 260，known 764，oracle-if-recalled 352，共同分母927。known减open净差504，可分解为去其他论文的诊断净差92，以及提供未召回来源的额外412；后者明显更大，来源定位是当前主要瓶颈。known仍有127题无整组全文映射参考、36题可映射但预算遗漏。
- dev已知来源8KB下，lexical相对原顺序净增26.11pp，同时302赢/60输；不能称逐题支配。
- train的24KB lexical：open 471，known 1728，oracle-if-recalled 674，共同分母2240。known减open净差1257，可分解为去其他论文的诊断净差203，以及提供未召回来源的额外1054；后者明显更大，来源定位是当前主要瓶颈。known仍有392题无整组全文映射参考、120题可映射但预算遗漏。
- train已知来源8KB下，lexical相对原顺序净增25.40pp，同时723赢/154输；不能称逐题支配。

dev已知来源24KB的lexical配对论文组区间仍跨零；train该区间为正，但已重复使用
公开任务，不能据此自动改默认。48KB known lexical距全文映射上限dev仍差2题、
train差10题；图表/非文本未映射上限本身也限制暴露率。没有新的模型质量结论。
因此下一优先项是冻结一个不接收目标身份的开放检索候选，计辅助索引/构建/查询
完整成本，与本版复现基线配对；避免继续只增加已知来源预算或在这些gold上搜参数。

## 数据、分母与重复控制

| split | 论文 | 问题实例 | 唯一问题文本 | 有非空可答参考 | 至少一组全文映射 |
|---|---|---|---|---|---|
| dev | 281 | 1005 | 948 | 927 | 800 |
| train | 888 | 2593 | 2451 | 2240 | 1848 |

沿用公开QASPER v0.3 dev/train，SHA见dataset-provenance.json；这是已用数据的任务
分解，不是新独立科学来源、盲测或test。参考未映射项仍保留分母，无非空可答参考
保持null；不奖励空集合。问题文本/证据/原JSON未公开，FTS不包含qas/答案标注。

两个split独立新建原默认固定/Zlib/v3，labels与v0.27相同。三轮新进程，每轮题序/
读取操作顺序随机，seed20261025+r；10794正式问题对、21588读取、194292上下文
绑定，12预热读取排除。所有轮次身份/评分/原句选择一致，open逐题keys、BM25、
原始来源身份与全部预算分数精确复现v0.27。起止整文件恢复、持久树大小/SHA不变。

## 全体非空参考的覆盖结果

![来源条件与预算](known-open-coverage.png)

| split | 正文预算B | 选择器 | open完整参考 | known完整参考 | oracle-if-recalled完整参考 |
|---|---|---|---|---|---|
| dev | 8000 | source-order | 107/927 | 315/927 | 160/927 |
| dev | 8000 | lexical | 179/927 | 557/927 | 264/927 |
| dev | 24000 | source-order | 232/927 | 740/927 | 338/927 |
| dev | 24000 | lexical | 260/927 | 764/927 | 352/927 |
| dev | 48000 | source-order | 295/927 | 797/927 | 365/927 |
| dev | 48000 | lexical | 307/927 | 798/927 | 365/927 |
| train | 8000 | source-order | 176/2240 | 595/2240 | 249/2240 |
| train | 8000 | lexical | 305/2240 | 1164/2240 | 454/2240 |
| train | 24000 | source-order | 445/2240 | 1652/2240 | 644/2240 |
| train | 24000 | lexical | 471/2240 | 1728/2240 | 674/2240 |
| train | 48000 | source-order | 570/2240 | 1831/2240 | 720/2240 |
| train | 48000 | lexical | 559/2240 | 1838/2240 | 723/2240 |

## 配对差与论文组描述区间

| split | 选择器/预算 | 对照（减open） | 赢/输/平 | 问题差pp | 论文差pp | 论文bootstrap区间pp |
|---|---|---|---|---|---|---|
| dev | source-order/8000 | known-source-minus-open | 208/0/719 | 22.438 | 22.425 | [18.877, 26.033] |
| dev | source-order/8000 | oracle-if-recalled-minus-open | 53/0/874 | 5.717 | 5.535 | [3.920, 7.279] |
| dev | source-order/24000 | known-source-minus-open | 508/0/419 | 54.800 | 53.705 | [49.858, 57.442] |
| dev | source-order/24000 | oracle-if-recalled-minus-open | 106/0/821 | 11.435 | 11.225 | [8.769, 13.654] |
| dev | source-order/48000 | known-source-minus-open | 502/0/425 | 54.153 | 52.890 | [49.179, 56.540] |
| dev | source-order/48000 | oracle-if-recalled-minus-open | 70/0/857 | 7.551 | 7.639 | [5.672, 9.846] |
| dev | lexical/8000 | known-source-minus-open | 381/3/543 | 40.777 | 40.658 | [36.832, 44.642] |
| dev | lexical/8000 | oracle-if-recalled-minus-open | 88/3/836 | 9.169 | 9.484 | [7.142, 11.929] |
| dev | lexical/24000 | known-source-minus-open | 504/0/423 | 54.369 | 53.114 | [49.066, 57.014] |
| dev | lexical/24000 | oracle-if-recalled-minus-open | 92/0/835 | 9.924 | 10.081 | [7.695, 12.509] |
| dev | lexical/48000 | known-source-minus-open | 491/0/436 | 52.967 | 51.910 | [48.070, 55.564] |
| dev | lexical/48000 | oracle-if-recalled-minus-open | 58/0/869 | 6.257 | 6.527 | [4.537, 8.707] |
| train | source-order/8000 | known-source-minus-open | 419/0/1821 | 18.705 | 19.943 | [17.911, 22.281] |
| train | source-order/8000 | oracle-if-recalled-minus-open | 73/0/2167 | 3.259 | 3.477 | [2.580, 4.498] |
| train | source-order/24000 | known-source-minus-open | 1207/0/1033 | 53.884 | 53.942 | [51.399, 56.444] |
| train | source-order/24000 | oracle-if-recalled-minus-open | 199/0/2041 | 8.884 | 8.831 | [7.526, 10.318] |
| train | source-order/48000 | known-source-minus-open | 1261/0/979 | 56.295 | 56.282 | [53.825, 58.822] |
| train | source-order/48000 | oracle-if-recalled-minus-open | 150/0/2090 | 6.696 | 6.442 | [5.308, 7.648] |
| train | lexical/8000 | known-source-minus-open | 875/16/1349 | 38.348 | 38.539 | [36.015, 41.128] |
| train | lexical/8000 | oracle-if-recalled-minus-open | 165/16/2059 | 6.652 | 6.558 | [5.280, 7.883] |
| train | lexical/24000 | known-source-minus-open | 1259/2/979 | 56.116 | 56.051 | [53.324, 58.471] |
| train | lexical/24000 | oracle-if-recalled-minus-open | 205/2/2033 | 9.062 | 8.604 | [7.252, 10.004] |
| train | lexical/48000 | known-source-minus-open | 1279/0/961 | 57.098 | 57.121 | [54.448, 59.694] |
| train | lexical/48000 | oracle-if-recalled-minus-open | 164/0/2076 | 7.321 | 6.955 | [5.709, 8.237] |

按论文组1000次bootstrap，seed20261025，排序分位索引24/974；区间只描述该公开集。
known减open包含明确额外的来源信息与只看一篇的预算优势，不是新检索器效应；
oracle减open只在原top5召回条件移除其他论文，既可能赢也可能输；这同时改变
预算竞争和临时词法FTS的IDF/排序语境，不能单独归因为纯预算效应。逐题、分层、论文
宏平均及全部原样本见derived-metrics.json和*-round*.json，三轮不当独立论文。

## 24KB损失分类与来源召回分层


### dev

有参考927题，其中目标在open top5共410题。

| 选择器 | 分类 | open-top5 | known-source | oracle-if-recalled |
|---|---|---|---|---|
| source-order | budget-omitted-reference | 134 | 60 | 28 |
| source-order | complete-reference-exposed | 232 | 740 | 338 |
| source-order | no-fully-text-mapped-reference | 44 | 127 | 44 |
| source-order | no-nonempty-answerable-reference | 78 | 78 | 78 |
| source-order | parent-not-top-k | 517 | 0 | 517 |
| lexical | budget-omitted-reference | 106 | 36 | 14 |
| lexical | complete-reference-exposed | 260 | 764 | 352 |
| lexical | no-fully-text-mapped-reference | 44 | 127 | 44 |
| lexical | no-nonempty-answerable-reference | 78 | 78 | 78 |
| lexical | parent-not-top-k | 517 | 0 | 517 |

### train

有参考2240题，其中目标在open top5共880题。

| 选择器 | 分类 | open-top5 | known-source | oracle-if-recalled |
|---|---|---|---|---|
| source-order | budget-omitted-reference | 284 | 196 | 85 |
| source-order | complete-reference-exposed | 445 | 1652 | 644 |
| source-order | no-fully-text-mapped-reference | 151 | 392 | 151 |
| source-order | no-nonempty-answerable-reference | 353 | 353 | 353 |
| source-order | parent-not-top-k | 1360 | 0 | 1360 |
| lexical | budget-omitted-reference | 258 | 120 | 55 |
| lexical | complete-reference-exposed | 471 | 1728 | 674 |
| lexical | no-fully-text-mapped-reference | 151 | 392 | 151 |
| lexical | no-nonempty-answerable-reference | 353 | 353 | 353 |
| lexical | parent-not-top-k | 1360 | 0 | 1360 |

## 选择器迁移与非单调回归

| split | 条件 | 预算B | lexical赢/输/平 | 问题差pp | 论文差区间pp |
|---|---|---|---|---|---|
| dev | open-top5 | 8000 | 108/36/783 | 7.767 | [4.972, 10.736] |
| dev | open-top5 | 24000 | 78/50/799 | 3.020 | [-0.154, 4.880] |
| dev | open-top5 | 48000 | 54/42/831 | 1.294 | [-1.552, 3.543] |
| dev | known-source | 8000 | 302/60/565 | 26.106 | [22.039, 30.208] |
| dev | known-source | 24000 | 45/21/861 | 2.589 | [-0.456, 3.669] |
| dev | known-source | 48000 | 3/2/922 | 0.108 | [-0.538, 0.550] |
| dev | oracle-if-recalled | 8000 | 129/25/773 | 11.219 | [8.871, 14.937] |
| dev | oracle-if-recalled | 24000 | 24/10/893 | 1.510 | [-0.303, 2.332] |
| dev | oracle-if-recalled | 48000 | 1/1/925 | 0.000 | [-0.538, 0.215] |
| train | open-top5 | 8000 | 217/88/1935 | 5.759 | [3.076, 6.702] |
| train | open-top5 | 24000 | 162/136/1942 | 1.161 | [-0.405, 3.202] |
| train | open-top5 | 48000 | 104/115/2021 | -0.491 | [-1.694, 1.216] |
| train | known-source | 8000 | 723/154/1363 | 25.402 | [20.549, 26.412] |
| train | known-source | 24000 | 140/64/2036 | 3.393 | [2.159, 4.839] |
| train | known-source | 48000 | 14/7/2219 | 0.312 | [0.142, 1.110] |
| train | oracle-if-recalled | 8000 | 289/84/1867 | 9.152 | [6.143, 10.006] |
| train | oracle-if-recalled | 24000 | 63/33/2144 | 1.339 | [0.365, 2.037] |
| train | oracle-if-recalled | 48000 | 8/5/2227 | 0.134 | [-0.032, 0.653] |
| split | 条件 | 选择器 | 8k→24k真→假 | 24k→48k真→假 |
|---|---|---|---|---|
| dev | open-top5 | source-order | 0 | 0 |
| dev | open-top5 | lexical | 0 | 0 |
| dev | known-source | source-order | 0 | 0 |
| dev | known-source | lexical | 0 | 0 |
| dev | oracle-if-recalled | source-order | 0 | 0 |
| dev | oracle-if-recalled | lexical | 0 | 0 |
| train | open-top5 | source-order | 0 | 0 |
| train | open-top5 | lexical | 1 | 1 |
| train | known-source | source-order | 0 | 0 |
| train | known-source | lexical | 0 | 0 |
| train | oracle-if-recalled | source-order | 0 | 0 |
| train | oracle-if-recalled | lexical | 0 | 0 |

预算扩大后greedy换选可能失去原完整参考；所有回归SHA保留，不删题，不由均值提高推断逐题支配。

## 时间、完整性与成本

| split | 实际Memory B | 全部RKV源一次B | 计入合计B | 进程RSS中位MiB | open top20中位/p95 ms | lookup中位/p95 ms |
|---|---|---|---|---|---|---|
| dev | 6065400 | 375700 | 6441100 | 81.65 | 22.653/32.450 | 5.625/8.437 |
| train | 18692957 | 375700 | 19068657 | 166.61 | 32.085/44.154 | 12.712/17.846 |

lookup所在memory.py相对v0.28净增加2077B；所有53模块/HTML全额计一次，三条件共用同一个不变库，原生库特定成本0。构建wall/CPU与目录账本见build.json。

| split | 条件 | 选择器/预算 | 读取+选择组件和中位/p95 ms | context JSON中位/p95 B |
|---|---|---|---|---|
| dev | open-top5 | source-order/24000 | 22.701/32.516 | 25689/26783 |
| dev | open-top5 | lexical/24000 | 27.217/39.290 | 25687/26564 |
| dev | known-source | source-order/24000 | 5.637/8.451 | 23796/25847 |
| dev | known-source | lexical/24000 | 7.048/10.361 | 23796/25735 |
| dev | oracle-if-recalled | source-order/24000 | 22.663/32.454 | 2/25568 |
| dev | oracle-if-recalled | lexical/24000 | 23.311/33.352 | 2/25488 |
| train | open-top5 | source-order/24000 | 32.141/44.200 | 25708/26620 |
| train | open-top5 | lexical/24000 | 37.488/51.484 | 25699/26576 |
| train | known-source | source-order/24000 | 12.725/17.855 | 24761/26031 |
| train | known-source | lexical/24000 | 14.179/19.696 | 24784/25871 |
| train | oracle-if-recalled | source-order/24000 | 32.095/44.157 | 2/25629 |
| train | oracle-if-recalled | lexical/24000 | 32.707/44.906 | 2/25512 |

lookup读取一个显式来源，open验证top20，不能把两者耗时比称同任务加速。lookup
没有绕开索引/CAS/记录SHA或重新解析，历史overlay/rebinding物化成本仍收费。
每预算完整收费一次词法prepare，选择与离线gold评分分离；oracle另计原search和
过滤。表中是逐query组件和，不是模型端到端延迟；整个进程RSS包含全部数据/
标注/策略/结果，不是某条件独立内存。CPU原样本保留，计时分辨率可能出现0。

正文预算不含标题/句ID/JSON/转义/问题/system/API结构。另列context紧凑JSON，
不等于真实wire/token/账单。共享Python/SQLite/Zlib/OS、安装/pyc/文件系统成本未
全额分配，不能声称整个系统净压缩。模型0次，冷缓存/跨机器保持null。

## 判定、限制与下一步

本轮提供可核验的来源条件分解及显式lookup，不改变默认检索/选择，不向开放任务
自动注入目标身份，不把oracle当可部署算法。仅当调用者明确指定来源时使用lookup。
已知来源仍可能因预算/排序遗漏、图表未映射而无法完整暴露参考，完整暴露也不保证
模型理解或回答正确。原句ID/精确locator保持，派生输出不升格为证据。

下一步先冻结一个不接收目标身份的开放检索候选，并补独立任务迁移验证；
不在既有gold上反复调规则追求正结果。真实模型新增评测仍需新增明确调用预算。
E3神经压缩、语义/图检索、多跳、长期会话、形式证明、冷缓存/跨机器、掉电/并发/
GC均不由本报告得出结论。每轮原始JSON、冻结SHA、图表与负结果保留。
