# v0.48.0 实验报告：公共批查询API在固定1/3/32条科学记录下的成本

## 结果和独立门槛

公共Memory.lookup_many与memory_batch.py逐字沿v0.47，不改算法/预算或默认集成，单独对比原逐key.lookup。36 fresh worker唯一计划完成，1152bundle、13824原record绑定、36整corpus逐字节恢复及9组同轮同size四条件proof/完整memory树一致。每个固定size独立验收：

| 每bundle key数 | 所有CAS计数完全相等控制 | 时间联合≤1 | query wall中位比 | query CPU中位比 | parent完整wall中位比 |
|---:|---|---|---:|---:|---:|
| 1 | True | False | 1.014194 | 1.090909 | 1.032696 |
| 3 | True | True | 0.380688 | 0.378378 | 0.797522 |
| 32 | True | True | 0.099776 | 0.096154 | 0.254230 |

均为同轮API ON/OFF三对比中位数，OFF为原逐key.lookup。query wall/CPU/parent完整process wall三者均≤1才该size通过，零CPU分母null失败，不加epsilon/轮数/重新选择source。单key低摊薄控制与全部反方向保留；不能用总体平均替代某个size失败，也不从跨版本绝对时间推速度。三个重复轮仍是确定性原source工作负载，不是独立科学任务样本或总体置信区间。

本轮新的是公共实现及1/3/32批量的成本范围，既有科学语料已使用过，size3 key组等v0.46 spread，不叫新的独立科学验证。没有语义检索/未知paper定位/自然语言问题/生成回答或真实长期会话；通过也不证明回答质量、生产吞吐或无限上下文。默认lookup/CLI/UI未切换，E3净收益/E4整体仍未完成。

## 输入、选择器、预算和次数

SciFact corpus.jsonl原8307875B/5183唯一doc_id，SHA b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62。沿v0.30及更早的公开来源、archive SHA与abstract许可，详dataset-provenance.json。不读claims/labels，不改源布局/字节，不加更新。原科学全文/完整hits/恢复副本留本地.tools，公共JSON只有key/SID/locator/record/hit/proof SHA与计数/费用。

沿原SHA256(ASCII rkv046:+key)、key排序，每size取前32×size key切32组，Random(20261026+round)打乱组顺序。32/96/1024个文档集合嵌套，最大唯一1024文档；13824次绑定不是13824独立文档。size3组与旧v0.46相同，已见事实不当新数据；没有换salt或调selector追正。新单元检查排序不依赖dict顺序、嵌套/唯一计数/与旧3key相同、非法size/不足拒绝、独立原证审计与公共无文本。

docs/api-bundle-inputs.json在正式前冻结九个plan SHA/数量/入证范围。输入预备只解析source、做确定性计划和字节长度核对，无lookup/codec结果；CPU/wall未测保持null，不能回填或当免费。每bundle最大入证B为size1=3348、size3=9548、size32=57875，均<公共API原默认1MiB，所以原预算完全不改；这也不是CAS读/总RAM上限。

260检查259通过/1Windows权限跳过，代码/协议/原输入SHA/计划于`38742a5936858ad943782533f0a65e454eb11517`冻结，exact candidateCI `40351186775`成功后唯一36worker，正式重试0、训练0、新模型API0。首次推送固定提交因schannel TLS握手失败，只通过已知本机proxy重推同一提交成功；原失败记录B/SHA见measurement-context.json，发生在CI/正式测量之前，没有换代码或重跑实验。

size1/3/32×API OFF/ON×meterOFF/ON×3轮。A–D=size1 off/off,on/off,off/on,on/on，E–H=size3，I–L=size32，固定ABCDEFGHIJKL/BADCFEHGLKJI/IJKLGHEFCDAB。36进程各32bundle，全体1152bundle/13824接受绑定/36全源恢复，9组四条件身份。所有都是显式known-source已知SID，无无证问题/正式拒绝控制，不能当1152次回答成功；原拒绝合同由v0.47必要单元延续。

## 原证、工作量与计量

独立auditor用全源原lineoffset/length/行SHA/JSON doc_id/title/abstract构造完整expected hit（D0/key/title/sentences/rankNone/source_bytes_verified/原SID locator），不是仅对比两个同源候选。另重新读取每worker私有完整proof、public SHA/locator、plan SHA与全部文件树，确认原HEAD/树前后不动、无remember/派生答案、36源逐字节相同。新的科学公共JSON递归拒绝原文成员字段。

base-only无delta回放，事前要求全部CAS整数计数ON/OFF完全相等，不能事后要求严格下降或把相等说成读取字节节省。首轮各size原值（其他轮计数也保留）：

| size | API | 应用CAS返回B/32bundle | decoder输出B | 解码次数 | selected record B（按出现次数） |
|---:|---|---:|---:|---:|---:|
| 1 | off | 745601 | 2097152 | 32 | 53929 |
| 1 | on | 745601 | 2097152 | 32 | 53929 |
| 3 | off | 2283382 | 6422528 | 98 | 155245 |
| 3 | on | 2283382 | 6422528 | 98 | 155245 |
| 32 | off | 24528629 | 69003707 | 1055 | 1629136 |
| 32 | on | 24528629 | 69003707 | 1055 | 1629136 |

576meterON case守恒：opens=attempts=success、readcalls=2opens、readB=payload+84opens、decoded=raw+compressed；576meterOFF计数null而非零。576 API ON元数据核admitted_source_bytes等原record总长、max_source_bytes=1MiB/maxkeys32，OFF batch_result null。每条原record照常读取核stored/raw/record SHA，无decoded块cache、无method patch；公共API真实关闭/清理由冻结v047必要测试覆盖，不借旧QueryView观察峰冒充本版RAM。

应用CAS read返回B/decoder输出不是SSD物理或全系统IO，SQLite C层/metadata/OS缓存未覆盖。单key没有减少重复view的摊薄机会，额外输入/SQL预检/结果封装可能有成本；按本轮原始门槛保留实际结果，不据结果改公共实现。

## 时间、CPU和RSS原值

| 轮 | size | API | meter | 应用CAS B | decoded B | query wall s | query CPU s | parent完整wall s | 观察peakRSS B |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 1 | off | off | null | null | 0.180170 | 0.171875 | 1.382927 | 88444928 |
| 1 | 1 | on | off | null | null | 0.182727 | 0.187500 | 1.319465 | 88592384 |
| 1 | 1 | off | on | 745601 | 2097152 | 0.184829 | 0.187500 | 1.318342 | 88559616 |
| 1 | 1 | on | on | 745601 | 2097152 | 0.188055 | 0.187500 | 1.322482 | 88444928 |
| 1 | 3 | off | off | null | null | 0.543328 | 0.531250 | 1.680948 | 89235456 |
| 1 | 3 | on | off | null | null | 0.206838 | 0.187500 | 1.363883 | 88637440 |
| 1 | 3 | off | on | 2283382 | 6422528 | 0.552460 | 0.562500 | 1.716048 | 89608192 |
| 1 | 3 | on | on | 2283382 | 6422528 | 0.219760 | 0.203125 | 1.359212 | 88506368 |
| 1 | 32 | off | off | null | null | 5.801916 | 5.687500 | 6.978015 | 89772032 |
| 1 | 32 | on | off | null | null | 0.573801 | 0.546875 | 1.781093 | 89575424 |
| 1 | 32 | off | on | 24528629 | 69003707 | 5.933837 | 5.859375 | 7.162084 | 89178112 |
| 1 | 32 | on | on | 24528629 | 69003707 | 0.607421 | 0.625000 | 1.800171 | 89632768 |
| 2 | 1 | off | off | null | null | 0.179759 | 0.171875 | 1.321197 | 88690688 |
| 2 | 1 | on | off | null | null | 0.180948 | 0.187500 | 1.364395 | 88895488 |
| 2 | 1 | off | on | 745601 | 2097152 | 0.191262 | 0.203125 | 1.344351 | 88662016 |
| 2 | 1 | on | on | 745601 | 2097152 | 0.181805 | 0.171875 | 1.339227 | 88866816 |
| 2 | 3 | off | off | null | null | 0.555271 | 0.546875 | 1.700364 | 89812992 |
| 2 | 3 | on | off | null | null | 0.211803 | 0.218750 | 1.356078 | 88559616 |
| 2 | 3 | off | on | 2283382 | 6422528 | 0.548868 | 0.546875 | 1.736497 | 89694208 |
| 2 | 3 | on | on | 2283382 | 6422528 | 0.213802 | 0.203125 | 1.359953 | 88854528 |
| 2 | 32 | off | off | null | null | 5.753441 | 5.703125 | 6.947864 | 89362432 |
| 2 | 32 | on | off | null | null | 0.576375 | 0.515625 | 1.766356 | 89767936 |
| 2 | 32 | off | on | 24528629 | 69003707 | 5.894544 | 5.843750 | 7.094050 | 89104384 |
| 2 | 32 | on | on | 24528629 | 69003707 | 0.602346 | 0.578125 | 1.784303 | 89767936 |
| 3 | 1 | off | off | null | null | 0.179262 | 0.171875 | 1.307247 | 88522752 |
| 3 | 1 | on | off | null | null | 0.186470 | 0.187500 | 1.350670 | 88600576 |
| 3 | 1 | off | on | 745601 | 2097152 | 0.187428 | 0.171875 | 1.327857 | 88752128 |
| 3 | 1 | on | on | 745601 | 2097152 | 0.190341 | 0.203125 | 1.382644 | 88322048 |
| 3 | 3 | off | off | null | null | 0.580119 | 0.578125 | 1.765572 | 89518080 |
| 3 | 3 | on | off | null | null | 0.207455 | 0.218750 | 1.392446 | 88469504 |
| 3 | 3 | off | on | 2283382 | 6422528 | 0.592037 | 0.593750 | 1.770755 | 89591808 |
| 3 | 3 | on | on | 2283382 | 6422528 | 0.228782 | 0.234375 | 1.456830 | 88625152 |
| 3 | 32 | off | off | null | null | 5.764632 | 5.640625 | 6.955657 | 89047040 |
| 3 | 32 | on | off | null | null | 0.575169 | 0.593750 | 1.763619 | 89722880 |
| 3 | 32 | off | on | 24528629 | 69003707 | 5.888057 | 5.843750 | 7.109088 | 89333760 |
| 3 | 32 | on | on | 24528629 | 69003707 | 0.617739 | 0.593750 | 1.848161 | 89665536 |

API完整调用或原lookup loop都在query scope内，包括输入核验、view/资源构建、原record读取/关闭与hits extraction。meter对象构造在query timer前，parent完整计时仍包含；API metadata/私有proof/publicSHA序列化在query timer后，worker/parent全部收费。独立audit另列CPU/wall，不混成在线查询成本。

![公共批查询不同批量的科学记录成本](api-bundles.png)

三行size1/3/32，三列meterOFF query wall/完整parent wall/观察RSS，标准图已实际打开核单位、图例和裁切。时间门槛只用meterOFF，meterON时间仅诊断，不把少触发仪表当算法加速。RSS为worker观察区间的系统peak，不是全生命周期外采样或实际增量RAM保证；原raw/catalog/私有proof累积均占RAM，ON/OFF都收费。

## 全部文件、源码和资源费用

首轮meterOFF文件/建库/审计成本；其他轮全在JSON：

| size | API | 完整memory B | 原source副本B | 其它worker文件B | ingest wall s | ingest CPU s | audit wall s | audit CPU s |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | off | 8420243 | 8307875 | 113388 | 0.810565 | 0.765625 | 0.000181 | 0.000000 |
| 1 | on | 8420243 | 8307875 | 113388 | 0.775137 | 0.750000 | 0.000173 | 0.000000 |
| 3 | off | 8420243 | 8307875 | 232641 | 0.771262 | 0.734375 | 0.000351 | 0.000000 |
| 3 | on | 8420243 | 8307875 | 232641 | 0.775871 | 0.734375 | 0.000334 | 0.000000 |
| 32 | off | 8420243 | 8307875 | 1966660 | 0.762527 | 0.687500 | 0.002327 | 0.000000 |
| 32 | on | 8420243 | 8307875 | 1966660 | 0.788350 | 0.718750 | 0.002017 | 0.000000 |

完整memory包含所有CAS/index/manifest/HEAD/残留，base-only没有历史科学更新，不能把36恢复叫36历史会话。其它worker文件包括私有fullhits（科学文本）、plan/完整ledger，它们不公开但B/SHA计账。36评测副本不是部署常驻36份要求。input/plan/privateproof/ledger各1fsync，child/parent exclusive+fsync，内部memory fsync未知null；所有源与末尾序列化/释放的费用也在worker与父完整subprocess wall内。

36 child+parent原始公共JSON共7921131B，driver日志0B。完整实际65 Python+HTML源码416514B；除版本字面量原runtime逐字等v047，新增selector/auditor/driver/analyzer及复用science/catalog/traffic/save专用源码B/SHA逐项在source-resource.json，协议/输入/测试另在measurement-context。模型/字典/训练新增0；未分配解释器/平台/依赖不称完整TCO。

SQLite逻辑页/metadata资源图/原生allocator没有在公共API里独立观测，保持未测，不能填零或把旧assessment的图峰复制过来。默认1MiB只限入证record，不限SQLite/CAS工作或RSS。derived-metrics各worker另列ingest/query/audit/recovery/workerCPU与parent完整wall，全部反向保留。

独立二次原证/全源/全树/计数/文本隔离与标准绘图额外wall 7.123625s、CPU 5.328125s、观察RSS 126283776B，不含初始解释器启动和写本分析计时记录，不能混进在线性能。输入预备CPU/wall原未测null保持不回填。

## 复现、发行与下一项

新work/out运行python -m scripts.run_api_bundles --corpus本地同SHA文件，再scripts.analyze_api_bundles带work/out/corpus/freeze/test-log。每worker600s，真实退出码/错误/child SHA与父完整process wall保留；不覆盖重跑失败。科学原文/完整hits/恢复副本留私有目录，新公共results只有无文本原始JSON/图/报告。

协议/源码/原始JSON/标准图/详实报告/README/release推送GitHub；CI后Release，实际资产SHA/65递归Python+HTML/tag与新旧程序，物理仓库外actual wheel+current native/API1/3/32及既有预算/旧SID/兼容功能、actual sdist新size selector/auditor合成smoke、最终proof上传后重下载全通过才完整收尾，再下一版。

下一优先项应处理未知问题如何找到证据的独立检索假设，而非在此1024文档上调预算/低批量阈值追正。新数据需先核来源/固定train与holdout边界再冻结方法，不能把文献结果当项目收益。旧24模型API耗尽，无新授权，继续本机CPU/离线。E3净收益仍失败，语义/图检索、真实长期会话、多跳回答、形式证明和无限上下文未验收；冷缓存/跨机/SSD物理/全系统IO未测。真实科学源/段/帧/恢复副本、私有研究模型/模板/个人报告/密钥不发布。
