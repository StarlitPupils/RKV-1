# v0.31 实验报告：PubMedQA原始成员与冻结检索迁移

## 问题、来源与冻结边界

v0.30段落候选在QASPER改善、在SciFact退步且更贵。本轮将完全相同的候选迁移
到新来源PubMedQA PQA-L，不调权重、融合、窗口或默认。候选模块与v0.30逐字节
相同，whole-paper搜索/lookup/命中验证方法及STOP的AST相同；变化只在新增显式
来源reader与v4重绑定白名单，不将适配新输入称新检索算法。

全部55模块/协议/驱动冻结`5c713c1`，210测试运行、209通过、1权限跳过。协议见[PUBMEDQA-TRANSFER](../../docs/PUBMEDQA-TRANSFER.md)，算法核对见algorithm-compatibility.json。

## 结论与决策

自定义PMID定位@1为957→950，@5为984→986，@10为990→988，@20为994→992。
@5仅净多2题（5赢/3输），描述区间跨零；MRR@20为0.970238→0.965823，配对区间
也跨零。没有支持稳定正迁移，不能用单个K的+2题称算法改进。与v0.30 SciFact退步
共同说明该单元粒度候选缺乏跨任务支配证据，保持显式、默认不换，不继续调gold权重。

候选额外1249639B，查询wall中位10.855→14.712ms。基线计入2152450B低于原JSON
2584787B（约少16.73%）；候选3402089B反而大约多31.62%。这只是当前实际账本，
共享运行时未全额分配，不能把基线数字称完整部署净压缩。候选未通过综合成本/
收益门槛，本轮新交付是可逆来源支持及透明迁移边界，无模型正确率结果。

后续保留现有词法默认作为离线基线，停止在这几套gold上追加融合/权重搜索。
工程优先回到路线中尚未完成的E2代码/数学字节表示候选，先冻结类型规则、计足
控制流/字典/解码器成本、再检验精确恢复和codec对照；E3及真实推理另需独立设计。

固定[官方PubMedQA仓库](https://github.com/pubmedqa/pubmedqa)commit `1cbae8e92f72f20c8d3747cbb3bf5bc53554d997` 的[原始ori_pqal.json](https://raw.githubusercontent.com/pubmedqa/pubmedqa/1cbae8e92f72f20c8d3747cbb3bf5bc53554d997/data/ori_pqal.json)，2584787B、SHA256 `8b3276be8942ebbd77f3ddcda12c1749bf0e490045a736fd8438ee40cf37a41d`。仓库[LICENSE](https://github.com/pubmedqa/pubmedqa/blob/1cbae8e92f72f20c8d3747cbb3bf5bc53554d997/LICENSE)原文可查，原科学数据不发布。

1000 PMID、1000唯一问题、3358 CONTEXTS条目，全部纳入。原任务给定context，
本项目人为改为在这1000篇中找来源：只评价精确目标PMID@K/MRR@20，不是官方
PubMedQA yes/no/maybe准确率、官方test/QA F1或科学结论正确率。其他命中的相关性
没有完整标注，不能计算通用precision。规则在本任务评分前固定，schema/范围
做过预检，不称严格盲测；近重复/同论文跨数据身份未全面验证。

## 原始字节、来源身份与标注隔离

新增显式*.pubmedqa.json类型，不改写原JSON。存储名ori_pqal.pubmedqa.json，
字节与原ori_pqal.json完全相同；每个原key/colon/value的offset/length/SHA保留。
独立核对1000原成员范围和投影：key=pubmedqa:PMID，title=PMID加原ID，正文严格
等于原CONTEXTS数组，不切句/修剪。文件没有独立文章标题，不能用QUESTION替代。
QUESTION/LONG_ANSWER/决策/预测/LABELS/MESHES/YEAR原字节留在CAS，但不进入FTS、
返回段落或模型上下文。合成marker测试两类检索及context payload均不泄漏这些字段。

v4显式加入新来源重绑定白名单，问句/注释/重排/改名变化仍绑定新原字节，原文
正文编辑必须更新投影；历史不能出现未来文本。原Memory v1–v4/CAS/归档格式不变，
来源类型需新reader。实际v0.30发行wheel按固定SHA在仓库外安装，lookup/search
对新来源均按QASPER schema错误拒绝，HEAD和持久树不变，不是模拟旧版错误。

与既有数据的精确重叠统计：`{'body_normalization': 'Concatenate original array items with spaces, collapse whitespace only; retain case and punctuation. This is overlap detection, not source normalization.', 'SciFact_exact_normalized_body_overlap': 0, 'near_duplicates_or_true_paper_independence': None, 'SciFact_dev_question_text_overlap': 0, 'QASPER_dev_exact_normalized_body_overlap': 0, 'QASPER_dev_question_text_overlap': 0, 'SciFact_train_question_text_overlap': 0, 'QASPER_train_exact_normalized_body_overlap': 0, 'QASPER_train_question_text_overlap': 0}`。本集自身规范化body重复组0、涉及0条。仅折叠空白并拼接数组条目，保留大小写/标点；不同ID空间或零精确匹配都不证明论文独立，近重复未测。

## 正式轮次与文档定位结果

三轮新进程、seed20261025+r打乱题序/条件；3000题对、6000读取、6预热排除。
重复轮次用于一致性/计时，不当3000独立论文。各轮keys/BM25/原文身份/MRR一致，
两检索器交集来源逐字段一致；起止原文件逐字节恢复，Memory和aux树大小/SHA不变。

![冻结迁移与完整计入空间](pubmedqa-transfer.png)

| K | whole命中/1000 | unit命中/1000 | 赢/输/平 | 差pp | PMID组bootstrap差区间pp |
|---|---|---|---|---|---|
| 1 | 957 | 950 | 9/16/975 | -0.700 | [-1.700, 0.300] |
| 5 | 984 | 986 | 5/3/992 | 0.200 | [-0.300, 0.800] |
| 10 | 990 | 988 | 2/4/994 | -0.200 | [-0.700, 0.300] |
| 20 | 994 | 992 | 0/2/998 | -0.200 | [-0.500, 0.000] |

MRR@20：whole 0.970238，unit 0.965823；配对差-0.004415，区间[-0.010025457875457876, 0.0008366782340466553]。

每PMID仅1问题，按PMID/问题1000次bootstrap，seed20261025、排序索引24/974；仅描述本公开集，不代表独立重复科学研究或普遍因果。无命中数和全部原始记录见derived-metrics.json与round*.json；无QA/证据段落真值指标，保持null。

![配对变化与描述区间](pubmedqa-paired-delta.png)

## 构建、查询与存储成本

| 条件 | 计入总B | 查询wall中位/p95 ms | CPU均值ms | MRR@20 | 无任何命中 |
|---|---|---|---|---|---|
| whole-paper | 2152450 | 10.855/17.643 | 11.620 | 0.970238 | 0 |
| best-unit | 3402089 | 14.712/23.041 | 15.354 | 0.965823 | 0 |

原Memory 1767888B，aux(index+manifest)1249639B、4358单元，全部55模块/HTML一次384562B，新reader模块1169B单列。基线不收aux，候选全收；两条件同一实测代码安装均全计源。原JSON 2584787B，目录账本见build.json。

Memory构建wall/CPU 0.180944/0.171875s；aux 0.111057/0.109375s。整个worker RSS中位52.60MiB、全进程wall中位28.523s。包含数据/标注/双条件/所有结果，不能分摊为某策略独立RAM。

每查询含原Memory校验、aux整DB SHA（候选）、top20原记录重读/投影验证，不省略
完整性来换速度。bootstrap/独立评分不混入查询wall/CPU，CPU有计时分辨率0样本。
公共Python/SQLite/Zlib/OS、安装/pyc/文件系统未全额分配，计入总B不等于完整部署
成本；本任务pool规模/投影粒度与旧任务不同，不跨语料把绝对耗时称同任务加速。

## 安装核验范围更正与决策

v0.24–v0.30早期烟测用仓库内隔离安装目标、仓库外执行目录，原“仓库外安装”
表述不够准确。已全部补做物理上位于仓库之外的新wheel/对应native安装与外部
cwd复测，Release追加external-install-verification.json并回读SHA；旧tag/正式
观测/原核验记录保留。同Windows解释器和依赖，冷缓存/跨机器仍未测。新发布沿用
严格外部安装方式。更正不改变任何压缩/检索/模型结果。

本轮保持完整正负结果与默认，不以来源定位成功替代模型回答正确，不通过调参
改变迁移结论。具体收益和成本应按上表本任务判断；仍需要更大/独立任务、语义/
多跳和实际推理评测。新增真实模型预算未授权，模型调用0，答案与证据覆盖保持
null。E3神经压缩、长期会话、形式证明、冷缓存/跨机器/并发/掉电等均不由此证明。
