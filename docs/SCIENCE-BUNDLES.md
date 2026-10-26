# v0.46 冻结协议：既有 SciFact 的固定 SID 三键批查询迁移

## 假设与边界

仅在v0.45实际资产SHA、递归源码、仓库外安装与最终proof全部核验后实施。原scripts/query_view.py逐字节沿用v0.45，不调观察器/SQL/校验或默认集成，不叠加decoded块缓存。运行库64 Python+HTML除发行版本字面量不改。假设是请求内一次完整view验证能在科学记录批查询中减少查询时间；即使失败也保留。不是开放检索、科学问答、自然语言多跳、迟到问题、真实长对话或回答质量实验。

单writer ingest完成后只读，显式固定manifest v3、base-only SID。view入scope时原QueryResources/_manifest/view完整验证，每selected record仍原_verified_hits、stored/raw/record SHA与JSON身份；新scope重验。验证时刻边界同v0.45：不承诺每hop重查中途未选中源/索引的外部篡改，无并发writer/生产承诺。普通原Memory.lookup不改。

## 既有输入和选择器

本地既有SciFact corpus.jsonl，8307875 B、5183唯一doc_id，SHA256 b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62。原项目v0.30及更早已使用，不是未知或新科学数据；本轮新的是三键批查询工作负载。来源/归档与许可沿results/v0.30.0/dataset-provenance.json：SciFact官方公开data.tar.gz，archive SHA 11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be，abstracts ODC-By-1.0；不读claims/labels，不改原字节，不追加科学更新或改文件布局。复现者自行取得同SHA合法输入。

独立catalog按原splitlines(keepends=True)记录offset/length/原行SHA和JSON doc_id/title/abstract，仅本地。全部doc:key按SHA256(ASCII 'rkv046:'+key)、key排序。spread的32bundle各取排序前96key的连续3个；repeated取第96至127的32key，每个重复3次，两个集合互斥。每轮用Random(20261026+round)打乱bundle顺序，OFF/ON同计划，所有轮仍同一批记录，不称独立泛化样本。选择器/输入身份/次数冻结后不能看结果调参。

每bundle明确3次known-source lookup，不是三跳推理；每次原source验证且完整hit必须等原行JSON。无自然语言查询，没有无证问题，也没有成功回答分母。此直接lookup协议不沿用v0.40 trace的4096B入证预算；原budget实验不改，不把三键成本称4096B内任务。每bundle实际selected record B（重复计次数）单列，不限制CAS应用读取或RAM。

## 精确计划和门槛

spread/repeated × view OFF/ON × traffic meter OFF/ON ×3轮，共24 fresh worker。A/B/C/D=spread off/off,on/off,off/on,on/on，E/F/G/H=repeated对应。固定ABCDEFGH、BADCFEHG、GHCDEFAB顺序。每worker32bundle/96lookup；合计768bundle、2304接受原record绑定、24整corpus逐字节恢复、6组同轮同负载四条件proof/完整memory树相等。单worker600s，失败/超时真实记录并保留，不能覆盖或追加重跑追正；正式评分一次。

每bundle定时包含meter scope创建后的进入/退出、QueryView完整构建/observe/查询/原record验证/关闭；helper/meter对象创建在计时前，两OFF/ON同规则且parent完整计时仍包含。不提前创建view后只计SQL。独立audit/序列化/私有proof写盘单独或在worker/parent成本收费，不掺入query。meterOFF三对用query wall、query CPU、parent完整process wall的ON/OFF比中位数，三者均≤1才过每负载时间联合门槛；CPU分母0为null且失败，不加epsilon/额外轮。所有逐轮反向/RSS保留。

base-only无delta回放，meterON的OFF/ON预期所有CAS整数计数每对完全相等，三轮均等才过机制负控制；不事后换成严格下降。重复key仍每次原record读取，不期待块缓存收益。meterOFF的traffic null，viewOFF的view null，不用零冒充观测。ON每bundle view_builds1/lookup_calls3/readonly-base/snapshot峰1/delta峰0，退出lookup恢复/resources清空/连接真关闭，384 scope均核验。meterON384bundle守恒：opens=decode attempts=success、readcalls=2opens、应用返回=payload+84opens、decoded=compressed+raw；384 OFF继续null。应用CAS不是SSD/全系统I/O，SQLite C层/metadata/OS缓存继续未测。

## 原证、隔离与成本

独立audit直接用原行offset/length/SHA/JSON构造完整expected hit（D0/key/title/sentences/rankNone/source_bytes_verified/locator）逐字段比较，绑定指定SID/path。worker私有完整hitproof留.tools，public只发布case ID、key、SID、locator、record/hit/proof SHA、计数与成本。analyzer重读私有proof独立核验并核public身份，同条件完整memory树前后相同/HEAD同SID、全源恢复。新publicJSON递归拒绝title/abstract/sentences/quote/body/text/object字段，发布审核逐项检查，科学原文/摘要/恢复副本不进入Git或资产。

必要测试仅合成：CRLF/Unicode原offset/SHA、重复/不足/非法负载拒绝、SHA排序与输入dict顺序无关、96+32key互斥、真Store与QueryView一致、原JSON/SID/locator篡改拒绝、public无文本。完整255检查及exact frozen CI成功后运行唯一24worker。原QueryView安全测试继续适用，不把单元检查算正式科学负审计或回答收益。

每worker原source副本、全部CAS/index/manifest/HEAD/任何残留、私有proof/plan/完整ledger均记逻辑B，没有remember/新派生答案或科学更新；24评测副本不是部署24倍常驻要求。input/plan/privateproof/ledger各一次显式fsync，内部memory fsync未知null；child/parent report exclusive+fsync。24parent紧包subprocess.run启动到真实退出，包括序列化/末尾释放，不称query wall等于端到端总成本。

ingest/query/独立audit/full recovery/worker与父完整wall、CPU、分析绘图额外费用，observed peak RSS、SQLite逻辑page_count×page_size峰、Python metadata graph峰分别收费。后两者不相加冒充完整或增量RAM，不含所有allocator/SQLite原生buffer/patch对象；源raw与catalog科学文本也驻留worker RAM，两条件相同并纳入观察峰。helper graph observe在query定时内收费。全部递归Python+HTML及专用/复用程序实际bytes/SHA，模型/字典/训练新增0；解释器/平台未分配不当完整TCO免费。

## 交付和复现

独立新work/out：python -m scripts.run_science_bundles --corpus 本地同SHAcorpus --work 新目录 --out 新目录；唯一正式计划后，python -m scripts.analyze_science_bundles带work/out/corpus/freeze/test-log核验。不发布私有hits/source，只有无科学文本原始JSON与aggregate/图/报告。

标准图实际视觉检查、详实实验报告/README/路线/版本说明，推送GitHub；CI后Release，实际下载所有资产SHA/actual wheel与sdist完整递归Python+HTML和专用程序对冻结Git、物理仓库外实际wheel+current native与actual sdist新selector/auditor合成功能smoke、最终proof上传后重下载才完整收尾，再下一版。旧24模型API预算耗尽、本版0新模型调用、本机CPU离线；不发布科学原料/段/帧/恢复副本、私有模型研究/课程模板/个人报告/密钥。E3净收益仍失败，E4整体/无限上下文/真实长期会话/回答质量未完成；冷缓存/跨机/SSD物理/全系统I/O未测。
