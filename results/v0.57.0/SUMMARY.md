# v0.57.0 实验报告：按最佳原句匹配重排整篇论文

## 结果与预定门槛

**来源质量False / 时间False / 联合False**。比较同一已见SciFact分母下的原paper BM25、原训练graph、唯一新sentence_max候选，均返回完整原论文记录、最多12篇/4096原B，无扩大预算或缩成句子返回。

| 方法 | gold论文完整找全主张 | macro paper recall | micro paper recall | recovered gold组 | 实际入证篇数均值 |
|---|---:|---:|---:|---:|---:|
| paper_lexical | 139 /188 | 0.750443262 | 0.698564593 | 146 /209 | 2.862416 |
| paper_graph | 139 /188 | 0.751773050 | 0.703349282 | 147 /209 | 2.862416 |
| sentence_max | 109 /188 | 0.588209220 | 0.545454545 | 114 /209 | 2.721477 |

质量预定为sentence_max macro严格>两个baseline且完整数≥两者，三轮均满足。时间预定为相对paper_lexical的query wall/CPU/parent完整wall三对比中位数全部≤1，零分母null失败，无epsilon/补轮。实际 **1.9477697549563793/1.9090909090909092/1.6913879441307562**。质量/时间/联合单列，不以局部正方向掩盖成本或退步。

这是已见开发数据上的探索性排序试验，不是未知数据、独立新领域或真实长会话验证；9fresh worker不把同一188个有gold主张乘9成独立科学样本。是否有统计显著性、生成回答提升、NLI/verdict收益均未验证。新索引及RAM/构造时间另计，不由质量门槛推压缩或总成本收益。

## 动机与固定比较对象

v056原whole-paper容量诊断显示graph49个不完整主张只有9个gold本身装不下，另40个有容量但没找全；gold-aware上界179/188不是部署成绩。由此只试一个改变检索表示/排序的候选，不提高4096，不改返回源单位、不再调k1/b/graph或只挑正例。

原数据corpus5183paper/8307875B SHA b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62；原model10152832B SHA f062c7a784421b71bbfaf3c299be78ff323a391847afbf5420e4c06a4d422be0。原dev300行/训练ID或规范化claim SHA排除2/实际检索298，其中188有gold质量评分、110无gold为null但全部计检索成本。原claim/labels/SUPPORT或CONTRADICT/cited_doc_ids不进入排名函数。

两个baseline保持原scripts.evidence_retrieval/scifact_graph逐字不变，固定ASCII tokens/STOP、BM25 k1=1.2,b=.75、训练graph6+6/tie和原skip预算；原model不重训。SciFact本项目早已使用，冻结防止本轮看结果后改候选，不把它称封存未知题目。原v053时间/联合失败、v051 literal负方向、E3完整净收益失败继续保留。

## 唯一新候选与返回单位

每abstract原句分别建BM25检索文档，只用句子的decoded文本，不拼标题、gold、claim或答案。对全部有正匹配的句子打分，再对每paper取最大句分；句tie固定unitID、父paper tie原paperID。每paper只出现一次，最后仍调用原paper_model的admit，按完整原JSONL记录length计12篇/4096B、超剩余skip继续。

这同时改变检索单元/IDF语料统计/只使用abstract文本，并非单独隔离某一个因素的因果实验；不能把质量差异全部归因于“切句”。新sidecar只是研究索引，原PaperRetriever的模型schema明确拒绝，默认API/Memory/CLI/UI不集成新方法。它没有把只返回小句子的量当整篇budget，source context仍包含整parent的标题/abstract/JSON/换行。

新索引实际45952个原句单元、5183个父paper，其中空token单元912，JSON B **35012961**；component B {"parents": 1164800, "shared": 33848139}，外层JSON开销仍在总B。原model和新索引都私有，全部费用保留，没有免费源表或免费词表。

## 冻结顺序和一次索引构造

v056实际资产/源码/物理外安装/finalproof完整核验后才采用。code/protocol/input freeze `889223b1727a7cb369c55f2ec032f5bf0f105793`、exactCI `40425317740`成功后，只读corpus+原model构造一次无监督源索引，不读dev查询/gold；不是新增监督/神经训练。独占fsync写新sidecar，再于UTC 2026-10-27T00:19:40.985744+00:00冻SHA **b670a732a494e1e518014f7bc0477e9e17a6e2693f2a08b45f2009cbce4daa37**，之后唯一9worker评分。

构造worker wall 2.223665s/CPU 2.171875s，父完整wall 2.327705s，观察peakRSS 207142912B。构造实际读原source 8307875B+旧model 10152832B，编码/序列化/新postings和metadata成本都在内；新index1次、监督训练0、远程模型调用0。准备只有人工fixture，不提前在真实source上构新index或评分。

9worker是ABC/BCA/CAB，A=paper_lexical、B=paper_graph、C=sentence_max，Random(20261027+round)同轮同题序，每600s/0重试。每worker独立Store zlib/fixed65536/bounded/同label和源SID，父退出码/error/childSHA/完整wall独占sidecar；失败/负向不覆盖、不追加轮。

## 精确原文、结构位置和独立审计

原句定位结构解析原JSON字符串，保留引号/转义/UTF8 byte offset/length/SHA，绑定paperID/sentence index和完整parent rawSHA。重复同文本不跨paper或句序合并；标题/嵌套decoy不能冒充abstract。raw original span保留JSON原escape，不通过改写JSON拼回原文。

每selected父paper实际Store读取完整原record，保留stored/raw/codec/EOF/size及parent SHA/docID/title/abstract校验。新候选best句hint从已验证完整parent原bytes按结构range切出，再核unit SHA、decoded文本及原句序；不跳过parent校验，也不因hint小宣称CAS物理读取减少。主入证B仍整篇；额外hint locator/hash和序列化proof B另计，不称4096是总prompt/metadata/RAM上限。

独立analyzer先用已冻结QASPER root-member decoder及JSONDecoder.raw_decode定位原abstract数组元素，重算全部unit offset/length/原SHA/decodedSHA、TF/postings/doc_lengths/N/avgdl，完整 **45952** raw-memory单元绑定与索引逐项相等；不是调用相同构造器自证，也不是同文本就算同结构位置。随后独立原JSONL/gold/rationale/实际Store父范围和hint范围、三轮proof/Store全树/9整源恢复校验。

实际selected父原Store绑定7551次，审计追加hint实际范围绑定2433次。完整catalog是从已载原raw内存结构定位，不冒充同次数SSD或Store读；排名重放是额外审计，不算新增正式试次。公开raw JSON仅ID/locator/SHA/指标/费用，无原科学句、claim、fullhits或索引postings。

## 逐题退步和hint辅助定位

| 轮 | sentence_max相比 | 主张recall胜 | 负 | 平 |
|---|---|---:|---:|---:|
| 1 | paper_lexical | 5 | 36 | 147 |
| 1 | paper_graph | 5 | 37 | 146 |
| 2 | paper_lexical | 5 | 36 | 147 |
| 2 | paper_graph | 5 | 37 | 146 |
| 3 | paper_lexical | 5 | 36 | 147 |
| 3 | paper_graph | 5 | 37 | 146 |

每轮仍188主张分母，不能用全局数字掩盖受损题。新候选首轮选中gold论文的best hint落在任一已标rationale句集合为75/114（0.6578947368421053）；这只是额外句位置提示的覆盖，不验证SUPPORT/CONTRADICT、语义蕴含、rationale集合完整性或生成答案。非gold选中论文不混入这个辅助分母，全部source主评分与逐题负方向仍保留；两个旧baseline没有hint功能，值null而非0。

## 原始时间、模型加载与RAM

| 轮 | 方法 | query wall s | query CPU s | workerwall s | workerCPU s | parent完整wall s | 观察peakRSS B | 额外新index实际load B |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | paper_lexical | 1.207962 | 1.218750 | 1.886004 | 1.828125 | 1.997678 | 122449920 | 0 |
| 1 | sentence_max | 2.361821 | 2.312500 | 3.270677 | 3.203125 | 3.397469 | 223887360 | 35012961 |
| 1 | paper_graph | 1.224385 | 1.234375 | 1.922424 | 1.843750 | 2.033037 | 122683392 | 0 |
| 2 | paper_lexical | 1.203450 | 1.203125 | 1.886031 | 1.859375 | 1.999269 | 121929728 | 0 |
| 2 | sentence_max | 2.319631 | 2.296875 | 3.228823 | 3.156250 | 3.353597 | 223854592 | 35012961 |
| 2 | paper_graph | 1.230366 | 1.140625 | 1.916440 | 1.765625 | 2.026158 | 122494976 | 0 |
| 3 | paper_lexical | 1.200637 | 1.171875 | 1.886767 | 1.781250 | 1.995889 | 121909248 | 0 |
| 3 | sentence_max | 2.338565 | 2.265625 | 3.250042 | 3.046875 | 3.375823 | 223952896 | 35012961 |
| 3 | paper_graph | 1.231938 | 1.218750 | 1.911572 | 1.875000 | 2.032271 | 121311232 | 0 |

全部worker实际加载原10152832B model；只有sentence_max再加载新sidecar 35012961B。模型read/JSON解析/校验时间每worker model_load字段另列，在worker/parent内；不能把新方法还载着旧postings/graph说成已节省RAM。部署可否去掉旧无用结构未测，不能把未来优化当当前成本。

query含排名/whole-record入证/snapshot开关/原parent读取及hint原slice验证；gold在选证后另计，model/source/dev读、ingest、私有query-check、报告/完整恢复在worker/parent内，详细gold/ingest/recovery在原JSON。观察RSS是process观测peak，不是完整生命周期增量RAM或常驻精确额。原字节入证cap不限制CAS/OS IO；SSD物理/全系统IO/冷缓存/跨机仍null。

独立全catalog/postings/原gold/source/hint/排名重放/全树/恢复/图额外wall 17.254356s/CPU 15.468750s、观察RSS 264327168B，单列不归零。所有源/index/JSON对象/expected postings在审计期也占RAM。

## 完整文件和源码成本

原监督model历史训练wall 1.071652s/CPU 1.046875s、父 1.167893s保留。原model完整10152832B、新sidecar 35012961B、新构造CPU和metadata不免费；归档原source CAS没有因为换排序变小，本版不宣称完整净空间收益。

本次直接复用与新index/worker目录全部保留283641256B，逐文件B/SHA在measurement-context，包括各源副本、所有CAS/config/snapshot/残留、plan/private-query/ledger及模型/构造记录。其他历史模型/快照/派生文件不删，沿旧版本成本账本保留；评测9份不是声称生产必须常驻9份。每个worker完整Store与源副本/其他文件B在原JSON，公开报告/parent/log/图自身也计存储。

完整66递归Python+HTML 426112B，runtime仅版本；专用/复用assessment脚本、全部新parser/auditor、协议/input/test实际B/SHA另列。9child+parent原JSON5908679B，worker日志0B。平台/解释器/依赖未分配，不称全机TCO或生产成本已证明。

![已见SciFact最佳原句重排](sentence-parent.png)

图实际打开检查，0起点/标签/余白无裁切，三面板分别source recall/完整gold-paper覆盖率/query wall中位数；不是答案准确率或未知数据泛化。原source和私有索引/model不重分发，输入来源及许可沿原SciFact manifest。

## 检查、复现和交付

298检查297通过/1Windows权限跳过，新增9项覆盖原escapes/Unicode/CRLF/重复句/decoy结构、sourceSHA/父子位置/预算/损坏拒绝、max-sentence父去重/tie/整record计费、旧SDK拒绝新research schema、独立catalog拒绝标题/重复句位置冒充及TF篡改、真三方法worker/排重/hint/全源恢复。冻结前为澄清索引只管排序而非返回句子，将metadata改为text_projection/parent_score并完成最终全库检查后才freeze；没有修改已见正式结果追正。

复现需原合法corpus/claims_dev、同SHA原paper model；先源index build一次/另冻SHA再运行脚本9worker，最后独立analyzer。精确输入/次数/门槛见[协议](../../docs/SENTENCE-PARENT.md)，不以私有模型缺失假装可以无源运行。没有新远程模型API（旧24次耗尽）。

代码/协议/rawJSON/标准图/本报告/README/release/GitHub，CI成功后actual5资产SHA/66+HTML/物理外actualwheel+currentnative/新sdist parser/index/父定位与排序及旧SDK明确拒绝新schema/旧功能/finalproof重下载全部通过才完整交付。研究候选不默认集成。**E3净收益失败，E4整体、科学verdict/NLI/形式证明/真实长期会话/生成回答质量和无限上下文仍未验收。**
