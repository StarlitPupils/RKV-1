# v0.31 PubMedQA原始成员与冻结检索迁移：结果前冻结协议

v0.30 QASPER平均改善、SciFact全K下降，额外索引与查询成本增加，不切换默认。
本轮不调候选：whole-paper与rkv1-paragraph-ftsv1的STOP/前64词/OR/BM25/最佳
单元归并/标题一次/前20不同论文保持v0.30规则；候选模块逐字节相同，whole-paper
search/lookup/命中验证方法及STOP的AST相同，来源分派另加显式reader。迁移到新增来源
PubMedQA PQA-L，只测明确的自定义来源定位，不是官方yes/no/maybe回答准确率。

官方https://github.com/pubmedqa/pubmedqa commit
1cbae8e92f72f20c8d3747cbb3bf5bc53554d997 的data/ori_pqal.json，2584787B，
SHA256 8b3276be8942ebbd77f3ddcda12c1749bf0e490045a736fd8438ee40cf37a41d，
Git blob SHA1 38db7750761c78950ed32303e7545bdaa513390c。MIT仓库LICENSE另存SHA。
原文件1000 PMID/1000唯一问题、3358 CONTEXTS条目；最大原成员4233B。只做来源/
形状与精确范围预检，尚无本任务评分；不当预检作QA/检索收益或官方独立test。

新增显式*.pubmedqa.json reader，原完整JSON字节不改写，不以合成JSONL替代真值。
重用严格members扫描，key='pubmedqa:'+原正数ASCII PMID(1–16字符、无前导零)，title='PMID '+
原ID（原文件无文章title，不能拿QUESTION当标题），sentences仅原CONTEXTS字符串
数组，不切句/修剪/规范化；允许空数组但不奖励空证据。精确原成员offset/length/
SHA包括原key、colon和value；原file SHA+snapshot绑定不变。1MiB成员上限。
QUESTION/LONG_ANSWER/final_decision/reasoning_*预测/LABELS/MESHES/YEAR均不投影，
原字节仍保留在CAS。questions/long answers/答案不是来源证据。

source kind pubmedqa-json-member-v1；原Memory v1–v4/CAS/归档格式不变。v4明确加入
该来源的投影重绑定白名单，注释/问句改动只改变原始locator，不改FTS/body。旧
v0.30实际发行读取器必须拒绝新来源，不能静默接受为旧QASPER；旧来源读写/默认
不变。不自动接入新回答UI/API，不增加模型调用。

先冻结reader/测试/本协议/驱动，再用完整1000问题。only QUESTION用于查询，
原PMID用于独立目标文档评分；每条CONTEXTS不作有标注证据，LONG_ANSWER也不作
精确证据真值。pool1000全体，每题一个目标，@1/5/10/20、MRR@20、无命中、配对
赢/输/持平与问题bootstrap1000次(seed20261025，排序24/974)，本集每PMID一题，
不把三轮当3000独立论文。不计算QA/F1/证据覆盖，保持null；每个任务提供论文的
原协议与本项目开放检索改造明确区分，不称官方排行榜成绩。

三轮新进程，SEED20261025+r打乱题序与检索条件，每进程每检索器1预热排除；
3000题对、6000正式读取、6预热排除。各轮keys/BM25(1e-10)/原文身份/定位一致，
交集论文title/CONTEXTS/locator逐字段一致。所有结果必须source_bytes_verified。
完整原文件起止逐字节恢复，Memory+aux持久树逐文件大小/SHA不变，无写回答案。

输入与既有SciFact和QASPER语料做仅空白归一化拼接body的精确SHA重叠检测、问句
文本重叠计数；不同ID命名空间/零精确匹配不证明论文独立，近重复未测。将重复
边界列出，不从新dataset就声称全新独立论文/严格盲测。

原Memory默认固定/Zlib/v3构建，另显式aux；每个条件实际top20原记录重新核验、
aux每查询收整DB SHA。计Memory原目录B、aux index+manifest全额B、源模块新增B及
全部55模块/HTML一次B、构建wall/CPU、每查询wall/CPU、完整进程wall/RSS。公共
Python/SQLite/OS/安装/pyc未全额分配，不称完整部署。对同安装基线不计aux，候选
全计，跨语料wall不可直接当同任务加速。

适当测试：精确UTF8/转义/CRLF成员范围、重排/改名/问句变更历史隔离、真body编辑、
原句ID、v4重绑定、重复keys/nonfinite/非法schema/超大记录拒绝、问题/答案/预测
字段不进入两类FTS/模型上下文；旧实际v0.30 reader拒绝新来源，正常旧来源兼容。
0模型/API请求，不读取密钥。无需为迁移退步调参/融合重测；报告所有负结果。
每版公开代码、冻结协议、无原文原始JSON、图表、详细报告与README/Release，
CI通过后实际下载SHA/仓库外安装复测。原PubMedQA/私人资料/科学词项索引不发布。
E3、模型质量、多跳、长期会话、形式证明、冷缓存/跨机器/并发/掉电仍未测。

## 执行

先从[v0.30 Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.30.0)下载
实际wheel，SHA256 f97a92f1c89dfc6b1c60514a9ad39125975a0ec5e83a947d1a797f1177875950。
`--fetch`仅获取固定公开数据及重叠检查所需的SciFact/QASPER，不调用模型；已有数据
可传`--input`并省略它。路径必须为新的out/work目录，不覆盖旧实验。

```powershell
python -m scripts.run_pubmedqa_transfer --fetch --legacy-wheel PATH_TO_ACTUAL_V030_WHEEL --out results/local-pubmedqa --work .tools/local-pubmedqa
```

仓库外核验范围已更正：v0.24–v0.30 Release追加`external-install-verification.json`，
实际wheel/对应native安装目标和执行目录均在仓库外，同Windows解释器/依赖；旧
tags/实验记录保留，不称跨机器。新发布继续采用真正的仓库外目标。
