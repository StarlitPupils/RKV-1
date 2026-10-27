# v0.58.0 实验报告：canonical词法/图索引的无损postings存储格式

## 结论：完整恢复通过，预定主联合失败

**预定typed/zstd空间False / 加载False / 联合False**。唯一72 fresh worker全部逐字节恢复原index JSON，追加72次从实际落盘frame独立decode及source/恢复文件复核通过；24个数据/方法/codec cell三轮frame SHA确定。原字段/TF/ID/locator/图/平均长度/浮点参数全部保留，不是量化或摘要。

两个原索引是既有词法/来源共现图JSON，不是LLM参数权重。本版只测索引存储及恢复到consumer-ready对象的成本，科学问题/推理/查询/回答质量试次0、监督训练0、远程模型调用0。归档原科学source CAS和旧质量结论不变，v057失败的35MB句索引完全不作为本实验目标。

固定主候选typed+zstd须在两个原模型上均比四种plain profile中完整空间最小者小，才space gate通过；EntailmentBank未胜best plain LZMA，故False。匹配Zstd的加载gate也False；不能把同codec或LZMA矩阵空间点改成主联合已通过。

预定完整矩阵仍有空间点：typed/LZMA相对best plain/LZMA，EntailmentBank frame930794→864534B、加整个typed源码后的完整空间净少60122B；SciFact1657218→1123730B、完整净少527350B。仅是这两个已见索引上的空间结果，不是加载、检索或推理收益，未据此改默认。

## 全矩阵字节结果与完整费用

| 数据 | codec | plain frame B | typed frame B | plain完整活动路径B | typed完整活动路径B |
|---|---|---:|---:|---:|---:|
| entailmentbank | raw | 4629798 | 3383841 | 9689774 | 8449955 |
| entailmentbank | zlib | 1815577 | 1357763 | 6875553 | 6423877 |
| entailmentbank | zstd | 1230530 | 1073265 | 6290506 | 6139379 |
| entailmentbank | lzma | 930794 | 864534 | 5990770 | 5930648 |
| scifact | raw | 10152962 | 2339333 | 20736102 | 12928611 |
| scifact | zlib | 2872248 | 1301290 | 13455388 | 11890568 |
| scifact | zstd | 2270991 | 1277256 | 12854131 | 11866534 |
| scifact | lzma | 1657218 | 1123730 | 12240358 | 11713008 |
| synthetic_control | raw | 354117 | 71875 | 1138412 | 862308 |
| synthetic_control | zlib | 78654 | 54263 | 862949 | 844696 |
| synthetic_control | zstd | 68550 | 53728 | 852845 | 844161 |
| synthetic_control | lzma | 56470 | 47178 | 840765 | 837611 |

frame已包含130B同容器header。完整活动路径=frame+实际写出的restored raw JSON+全部66递归Python/HTML 426112B+共同frame wrapper 4196B；typed还收费整个transform源码 6138B。不能只报typed二进制payload，也不能省略当前SDK仍需raw JSON文件的消费路径。

原输入模型是全campaign共享的单份，实际15136487B另计。所有72worker实际frame+恢复文件共 **480473583B**（约480MB），保留用于审计，不说整个工作目录因压缩变小。输出报告/sidecar/源码/图/旧模型也继续占空间。压缩frame单独存储并透明加载的SDK路径尚未实现，不能拿未来不保留raw文件的假设计当前部署收益。

| 数据 | typed codec | 同一数据best plain codec | typed完整B-best plain完整B | typed完整空间胜 |
|---|---|---|---:|---|
| entailmentbank | raw | lzma | 2459185 | False |
| entailmentbank | zlib | lzma | 433107 | False |
| entailmentbank | zstd | lzma | 148609 | False |
| entailmentbank | lzma | lzma | -60122 | True |
| scifact | raw | lzma | 688253 | False |
| scifact | zlib | lzma | -349790 | True |
| scifact | zstd | lzma | -373824 | True |
| scifact | lzma | lzma | -527350 | True |
| synthetic_control | raw | lzma | 21543 | False |
| synthetic_control | zlib | lzma | 3931 | False |
| synthetic_control | zstd | lzma | 3396 | False |
| synthetic_control | lzma | lzma | -3154 | True |

四profile固定raw、Zlib6、Zstd3、LZMA6，有限矩阵中的best plain不是所有codec/所有level的全局最优。随机结构控制也完整保留，不因有/无收益丢弃；它是人工随机postings，不是白噪声或理论不可压缩性证明。

## 加载与编码代价

| 数据 | 方法/codec | encode wall中位s | encode CPU中位s | decode到model-ready wall中位s | 对应CPU中位s | parent全wall中位s | 三轮观察peakRSS最大B |
|---|---|---:|---:|---:|---:|---:|---:|
| entailmentbank | plain/raw | 0.006138 | 0.000000 | 0.032629 | 0.031250 | 0.227792 | 67600384 |
| entailmentbank | typed/raw | 0.166111 | 0.171875 | 0.201401 | 0.203125 | 0.535546 | 67207168 |
| entailmentbank | plain/zlib | 0.128847 | 0.125000 | 0.044413 | 0.046875 | 0.338041 | 62038016 |
| entailmentbank | typed/zlib | 0.256459 | 0.250000 | 0.206864 | 0.203125 | 0.630453 | 64565248 |
| entailmentbank | plain/zstd | 0.018781 | 0.015625 | 0.035593 | 0.031250 | 0.217895 | 60768256 |
| entailmentbank | typed/zstd | 0.176707 | 0.171875 | 0.200269 | 0.203125 | 0.537268 | 64110592 |
| entailmentbank | plain/lzma | 1.136560 | 1.140625 | 0.068376 | 0.062500 | 1.365397 | 92938240 |
| entailmentbank | typed/lzma | 0.881733 | 0.875000 | 0.232181 | 0.218750 | 1.273288 | 92127232 |
| scifact | plain/raw | 0.013342 | 0.015625 | 0.099225 | 0.109375 | 0.367273 | 117067776 |
| scifact | typed/raw | 0.597297 | 0.578125 | 0.695717 | 0.703125 | 1.527890 | 102350848 |
| scifact | plain/zlib | 0.264783 | 0.265625 | 0.116527 | 0.109375 | 0.615236 | 102420480 |
| scifact | typed/zlib | 0.710674 | 0.703125 | 0.702635 | 0.687500 | 1.648857 | 100192256 |
| scifact | plain/zstd | 0.036113 | 0.031250 | 0.105302 | 0.109375 | 0.374488 | 101507072 |
| scifact | typed/zstd | 0.609480 | 0.593750 | 0.696567 | 0.671875 | 1.533742 | 100614144 |
| scifact | plain/lzma | 3.159156 | 3.140625 | 0.150336 | 0.140625 | 3.539354 | 135290880 |
| scifact | typed/lzma | 1.092640 | 1.078125 | 0.730060 | 0.734375 | 2.044610 | 100048896 |
| synthetic_control | plain/raw | 0.000490 | 0.000000 | 0.002191 | 0.000000 | 0.105271 | 30076928 |
| synthetic_control | typed/raw | 0.012410 | 0.015625 | 0.015028 | 0.015625 | 0.127489 | 29573120 |
| synthetic_control | plain/zlib | 0.005422 | 0.000000 | 0.002702 | 0.000000 | 0.109424 | 29519872 |
| synthetic_control | typed/zlib | 0.014587 | 0.015625 | 0.015495 | 0.015625 | 0.131623 | 29634560 |
| synthetic_control | plain/zstd | 0.002415 | 0.000000 | 0.002228 | 0.000000 | 0.109706 | 30052352 |
| synthetic_control | typed/zstd | 0.014293 | 0.015625 | 0.015311 | 0.015625 | 0.129984 | 30035968 |
| synthetic_control | plain/lzma | 0.056957 | 0.062500 | 0.004249 | 0.000000 | 0.160794 | 48066560 |
| synthetic_control | typed/lzma | 0.024114 | 0.031250 | 0.016959 | 0.015625 | 0.141557 | 46477312 |

encode含原JSON规范验证/TF布局变换/codec/各SHA；plain不承担typed解析成本。decode到model-ready从decode开始、经过严格frame校验/解压/重建原JSON、再json.loads成现有consumer对象，不能把typed先重建再解析的成本藏掉。其后完整原字节/JSON一致性核验、写恢复文件/重读/source recheck另在worker和parent内，详细各阶段在72份rawJSON。

预定typed/zstd相对plain/zstd的三配对中位数：

| 数据 | model-ready wall比 | CPU比 | parent全wall比 | 加载gate |
|---|---:|---:|---:|---|
| entailmentbank | 5.596171631102595 | 6.5 | 2.463488555653676 | False |
| scifact | 6.573270074200201 | 6.142857142857143 | 4.063203341280244 | False |
| synthetic_control | 6.990348544635995 | None | 1.1848347530869208 | False |

两个原索引的model-ready约慢5.60倍/6.57倍，不能称综合加载优化。人工控制CPU出现零分母时按冻结规则记null且失败，不加epsilon或追加迭代追稳定正数。即使某个codec更省frame空间，也不消除CPU、构造、恢复raw文件或model对象RAM成本。

observed RSS只是过程观察peak，非生命周期增量或常驻精确RAM。编码器、解码器、JSON对象和codec C缓冲都占内存，64MiB源payload/65MiB typed cap不等于RSS cap。平台/解释器/依赖二进制/pycache未完整分配，源码账本不是全机TCO。SSD物理/全系统IO/冷缓存/跨机仍null，不将应用read/write B当物理磁盘实测。

## 冻结输入、次数与身份

v057 actual发行/66源码/物理外SDK/currentnative/sdist/finalproof完整后才采用。code/protocol/input freeze `3ab06440027edd63c076202b8cf65522a317ec81`、exact candidateCI `40429799623`通过后唯一72worker。原EntailmentBank index4629668B SHA2f82ee4b28c943038e7a37ddcbd8871443f7a441ddd45a1af599decc8bade183；原SciFact index10152832B SHAf062c7a784421b71bbfaf3c299be78ff323a391847afbf5420e4c06a4d422be0。两者早已用于旧实验，不能称独立未知科学样本。

人工控制seed20261027：256docID、1024token、每token8doc、正TF1..65535，doc_lengths为聚合TF。只在冻结前构造原输入并记SHA，不提前测两个原模型压缩结果。它不是神经训练，不用于改变真实模型参数，原索引weight和源catalog不动。

3数据×2方法×4codec×3轮=72，A plain/raw B typed/raw C plain/zlib D typed/zlib E plain/zstd F typed/zstd G plain/lzma H typed/lzma，轮序ABCDEFGH/HGFEDCBA/EFGHABCD，三数据顺序固定，600s/worker、0补轮/重试。三轮同数据cell是机械/时间重复，不把两个原模型乘72当独立科学域。

## 格式与严格恢复契约

RKVPOST1为独立实验frame，不属于主归档v1-v6或RKVTEXT/neural frame。header为little-endian `<8sBBQQQ32s32s32s>`：magic8、method1（plain0/typed1）、codec1（raw0/Zlib1/Zstd2/LZMA3）、原/变换/存储长度各u64、原/payload/stored SHA各32B，共130B。

typed保留shared.postings以外所有原canonical JSON metadata，doc字典取metadata.doc_lengths原ID字典序。payload依次为metadata长度uvarint/metadata原canonical JSON（postings空placeholder）、doc数/token数/pair数，再每原token UTF8长度/字节、posting数及正doc-index delta/原正TF。无语义合并、重写或丢字段，opaque graph/locator/参数和float原序列化亦保留。

解码先核类型/尺寸/单frame/三SHA，再严格规范uvarint与UTF8、doc/token顺序、正TF/范围/重复/EOF/count。原source≤64MiB，typed≤65MiB，TF≤2^31-1；通过metadata空placeholder和原JSON字节长度预算，在重复长ID展开前拒绝超过声明的重建，不能先生成任意大JSON再补长度检查。源码原文已非canonical/重复key/nonfinite/非法TF则typed明确拒绝；plain可逐字节包任意受限bytes。未声称所有JSON/模型通用或信息论最优。

## 物理文件与独立审计

每worker实际写private frame并fsync、重读frame，再decode和consumer-ready；写原恢复JSON并fsync、重读核SHA/源输入未变。两个fsync为文件操作，不是目录同步/断电实验。各phase wall/CPU及应用返回B分列，父从启动到退出完整wall含这些I/O与额外检查，原始过程失败即保留。

独立analyzer重新读取全部72实际frame/恢复文件/原输入，再decode72次并核源SHA、字节、JSON对象、header各字段与原report、work目录真实B/SHA、parent/child SHA、24cell三轮frame确定性。额外审计wall 19.877395s、CPU 18.062500s、观察RSS 136859648B单列，不当新正式轮/新模型推理。原科学source范围读取/问题试次均0，恢复的是索引JSON artifact。

310检查309通过/1Windows权限跳过，新增12项覆盖uvarint literal golden/边界/非规范/溢出、typed payload literal golden、Unicode/opaque float/bool/null/empty、schema/TF/noncanonical/duplicate/nonfinite拒绝、header/三SHA/截断/trailing、codec内层串帧、长ID重建size先验、delta0/count/EOF、旧frame/SDK拒绝、控制重建、真八cell worker/写盘/SDK-ready及SHA拒绝、CLI pack/unpack与已有输出不覆盖。不是只跑镜像happy path。

## 使用与部署边界

```text
python -m scripts.index_frame pack model.json model.rkvpost --method typed --codec lzma
python -m scripts.index_frame unpack model.rkvpost recovered.json
```

输出exclusive+fsync不覆盖已有文件。新frame不会被默认PaperRetriever当原JSON；如要使用须显式解包成原bytes，仍以原model SHA初始化SDK。独立格式源码在sdist/scripts，默认wheel/Memory/CLI/UI/归档格式不变，不假装透明压缩模型加载已经完成。

原2model历史训练与文件成本沿v050/v053账本保留，直接原训练目录实际14788889B的逐文件B/SHA在measurement-context；原source CAS/旧模型/句索引负实验及其他历史快照/派生记录不删，不以不发布私有数据当无存储。66递归Python+HTML 426112B、共同/专用format代码及全部assessment/test/protocol/input实际B/SHA分别列。

![完整活动路径与格式源码费用](index-frames.png)

图已实际打开核验，0起点、三数据单列、frame/恢复JSON/共同及额外源码都计入。细小codec差异以表/JSON为准，不截断纵轴夸大空间收益；图不展示神经推理或回答指标。

## 交付与下一步

代码/格式协议/rawJSON/图/本详实报告/README/release/GitHub，CI成功后actual5资产SHA/66+HTML/物理外actualwheel+currentnative/新sdist八profile逐字节恢复并加载原SDK合成model/全部旧功能/finalproof重下载后完整收尾。真实model/postings/frame/恢复文件不发布，0新远程模型API（旧24次耗尽）。

预定主联合失败不因矩阵LZMA空间点而改写。后续若优化，先用受控profile定位typed恢复CPU热点，再另冻实现及完整二进制/metadata费用；或明确实现可选加载接口并重新量度，不能以将来去掉raw文件/缓存/编译优化抵扣本轮成本。**E3旧净收益失败，E4整体、真实长期会话、verdict/NLI/生成回答/无限上下文未验收。**
