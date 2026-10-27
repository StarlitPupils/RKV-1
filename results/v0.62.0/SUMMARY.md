# v0.62.0 实验报告：词语关联覆盖提升与训练问题字面相似度

## 结论与可解释范围

**H1至少一半正增益在近似训练问题组：False；H2非近似组仍有来源质量提升：True**。这是既有v061 rawreport与已见train/dev问题的诊断，无新检索、训练、模型API或科学source范围读取。不是检验未见语料的泛化，也不能证明无语义泄漏或因果关系。v061来源质量True/时间False/联合False、139→142/188和609487B额外sidecar、query约慢21.14%全部保持。

诊断阈值在看新相似度结果前固定为4/5 token-set Jaccard；只这一阈值，没有扫阈值/调混合权重来追正结果。原809train按已有normalized question SHA去重807组，原dev300排除2完全重叠后仍298（188annotated/110无goldnull），没有根据诊断结果重新选试次。

| 组 | 方法 | annotated分母 | macro原来源recall | complete问题 | exact recall sum |
|---|---|---:|---:|---:|---|
| near | lexical | 34 | 0.696078431372549 | 23 | 71/3 |
| near | expansion | 34 | 0.7328431372549019 | 24 | 299/12 |
| near | permuted_expansion | 34 | 0.696078431372549 | 23 | 71/3 |
| nonnear | lexical | 154 | 0.7624458874458875 | 116 | 1409/12 |
| nonnear | expansion | 154 | 0.7754329004329005 | 118 | 1433/12 |
| nonnear | permuted_expansion | 154 | 0.7624458874458875 | 116 | 1409/12 |

“near”仅指与至少一个训练问题的字面词集合交并比≥.8，“nonnear”只是不满足这个阈值。它不代表语义独立/医学事实独立/相同论文不存在，不能把H2通过写成开放世界理解或稳定泛化。空cohort宏平均保持null，不填0，图若画零高度须按n=0解释无样本。

## 正负方向与精确分母

| annotated组 | 问题数 | win | loss | tie |
|---|---:|---:|---:|---:|
| near | 34 | 2 | 0 | 32 |
| nonnear | 154 | 2 | 0 | 152 |

所有188逐题方向保留，不只挑新增complete三个问题。定义delta=(candidate recovered/gold)-(lexical recovered/gold)，精确Fraction。正delta之和 `{'denominator': 4, 'numerator': 13}`；near正delta和 `{'denominator': 4, 'numerator': 5}`；负delta和 `{'denominator': 1, 'numerator': 0}`；net `{'denominator': 4, 'numerator': 13}`。near占全部正增益份额 `{'denominator': 13, 'numerator': 5}`，H1按≥1/2，不用正负抵消分母，也不把group数量当科学数据独立数。

H2要求nonnear annotated n>0、candidate recall sum/同n严格大于lexical且complete不低；控制同cohort列出所有质量指标。H1/H2都是描述性诊断，不能据此宣布已纠正训练依赖。110无gold样本只入相似度分布，原报告质量仍null，不参与recall或成败。全298相似组计数 `{'near': 51, 'nonnear': 247}`。

## 算法、精确比较和冻结

原tokenizer同v050/v061：casefold、ASCII字母数字长度>1及旧stop词过滤；词频归集合，没有stem/embedding/同义词/答案或gold参与最佳匹配。对807train问题逐一intersection/union，以精确分数找最大，所有并列最大训练问题仅记录SHA；无交集和空集合最大0，不虚构最佳SHA或把空union当1相似。normalized SHA精确重叠与Jaccard近似分别标注；被检298中精确重叠应0，原2排除保留。

4合成检查包括4/5精确边界/重复和顺序不变、空/不相交/normalized准确、全部win/loss/tie和完整转移、分母/类型拒绝；完整335检查334pass/1Windows权限skip，source/protocol/input freeze `d3f0c67bf35ba6ffd71665eb8d94deeec4d9f3fa`，exact CI `40447714225`成功后唯一1诊断worker，600s/0retry。没有重复9轮检索、重训或访问真实模型服务。

## 独立审计及成本

worker用Fraction scorer，独立analyzer不调用candidate best_match/classify，而用整数交叉乘重算298×807集合最大、threshold和最佳SHA集合；独立根据原selected/gold ID重算recall、各组n/complete/全部exactdelta/方向及positive+negative=net守恒。三角色全部原2/3轮proof逐题核第一轮，共2682既有proof检查；这些是已有report身份核对，不是2682新原文绑定。已见v061原source核验沿用其SHA账本，本版raw corpus/CAS range读取0。

worker wall 3.564066s、CPU 3.531250s、parent完整wall 3.666046s、观察peak RSS 39141376B；额外独立audit与图wall 2.600624s、CPU 1.031250s、peak RSS 92340224B单列。脚本同时持输入reports与train/dev对象，source输入cap不是RAM cap。RSS非精确增量/常驻；平台/解释器/依赖/pycache未全分摊。

共享既有输入5052608B，child/parent rawJSON 300578B，环境/统计/图/日志另计；66递归Python+HTML 426112B与全部诊断源码/协议/test/input逐文件B/SHA在source-resource。旧base10152832B、sidecar609487B、训练CPU、所有v061科学source CAS/副本/旧快照/负实验残留继续保留，成本账本不删除。没有新DLL/字典/模型负担可抵消；本轮不声称压缩或查询加速。SSD物理/全系统IO/冷缓存/跨机null。

![训练问题字面相似度与全部正负方向](query-similarity.png)

图已实际打开检查，0轴/recall0–1、cohort分母和所有298直方图、固定.8线；不是语义相似度、生成答案准确率或领域泛化图。raw worker只ID/SHA/计数/分数/既有metrics，无原train/dev文本或索引词表。

## 复现和交付

```text
python -m scripts.run_query_similarity --manifest docs/query-similarity-inputs.json --out NEW_PRIVATE_DIRECTORY
python -m scripts.analyze_query_similarity --manifest docs/query-similarity-inputs.json --out NEW_PRIVATE_DIRECTORY --freeze FROZEN_COMMIT --test-log TEST_LOG
```

输入须取得已有train/dev及v0619reports并核固定SHA，目录exclusive、不覆盖旧数据。代码/必要测试/协议/rawJSON/标准图/本详实报告/README/release，CI后actual7base资产SHA/66+HTML/Rust+scripts/物理仓库外actualwheel/currentGear/currentpostings/actualsdist新Jaccard与全部旧smoke/finalproof第8重下载后完整交付。

后续若验证来源覆盖提升，可按本诊断结论设计新的独立数据集或新的预先封存问题集，另冻输入/方法而不是追调本dev；literal nonnear仍非semantic independent。0模型API（旧24耗尽），E3净收益/E4整体/NLI/回答/真实长会话/无限上下文未验收。
