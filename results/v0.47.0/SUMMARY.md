# v0.47.0 实验报告：可选公共批查询API与入证预算机械验收

## 交付结果

增加可从已安装wheel调用的Memory.lookup_many，接受1..32个显式来源key、指定历史SID和原record入证字节预算。它把此前仅assessment脚本内的“请求开始验证一次视图、每条原record照常核验”机制做成独立入口；原Memory.lookup、CLI和默认UI行为保持，接口不使用method/global patch或unittest.mock。

冻结唯一6worker完成126case：108主case=54正确返回+54预期预算拒绝，18控制=6重复key正确返回+6重复预算拒绝+6缺失空结果。合计66返回/60预期拒绝、666原record绑定、36完整历史合成源文件恢复；所有原SID/原line/JSON/完整memory树/HEAD与计量守恒通过。**没有提速对照或科学问答实验，performance_gain_gate=null**。不能把126都说成回答成功，也不能将v0.45/46旧assessment的科学性能直接外推新实现。

## 接口、资源边界和调用

```python
from rkv1.memory import Memory

memory = Memory("memory-directory")
sid = memory.current()  # 显式选择并固定此次请求的历史版本
result = memory.lookup_many(
    ["doc:0", "doc:1", "doc:2"],
    snapshot=sid,
    max_source_bytes=4096,
)
for item in result["results"]:
    print(item["source_key"], [hit["locator"] for hit in item["hits"]])
```

keys仅有限list/tuple长度1..32，每key原str/1..512/NUL限制；不接受字符串充当列表或无界iterator。SID合法且必须显式，绝不回退HEAD。max_source_bytes严格int、拒绝bool，范围0..32MiB、默认1MiB。全部输入在manifest/SQLite/CAS访问前拒绝非法值，原支持v1/v2/v4的lookup仍保留，本新批接口仅v3，其他manifest明确拒绝。

进入原QueryResources/_manifest/view一次完整核验，SQLite设置query_only=ON；原LOCATORS SQL依输入顺序取每key至多2行，合法v3原scan已保证全局key唯一，>1拒绝畸形索引，不将截断说成完整结果。先预检所有selected record length总和（重复key每次计费），超预算ValueError、不返回部分结果；预检后每项仍原_verified_hits、原stored/raw/record SHA、codec/EOF/size与JSON成员校验，无decoded块cache。缺失key为空hits/0B，可在零预算成功；重复key仍逐次校验原record。

**入证预算不是实际读取或RAM上限**：预算拒绝之前构建/验证view可能已回放delta并读CAS，SQLite/metadata/OS读取也不受此预算约束。60次预期预算拒绝中，实际应用CAS返回非零为 **36次**，逐次read/decoded原值保留在derived-metrics.json，不改成零。单record原格式上限1MiB和32keys不等于整个进程32MiB；SQLite视图/资源/解释器/解析对象另计。新API没有暴露长寿命连接或可跨请求对象。

请求一致性沿已声明边界：进入时完整验证view，每selected原record每次重新验证；不承诺每key重查中途未选中源/索引的外部篡改，新请求重验。单线程/无并发writer验收，不因未patch旧lookup就声称线程/并发生产保证。context全部退出/关SQLite/清QueryResources后才返回结果，所有异常同样退出。

## 检查、冻结和正式次数

259检查258通过/1Windows权限跳过。四个新必要单元用真Store覆盖exact/1B不足、重复key收费和原校验、多文件唯一key、missing零预算、32key；非法类型/长度/SID/预算在manifest前拒绝、v1/v2/v4拒绝；旧SID/新HEAD、query_only实际拒绝写SQL、连接真关闭/映射清空和预算异常；坏selected源、下一请求坏base/delta拒绝。早期开发fixture误用了跨文件重复key（原全局唯一性会拒绝），过大更新又触发base重建，测试fixture修正为合法唯一key与单record更新；均是冻结前合成预检，不计正式试次。

代码/协议/输入引用在`d09c6a850a552f6d3743c49703f1e4ab45dc2368`冻结，exact candidateCI `40347032596`成功后唯一正式6进程，重试0。原path_layout_fixture/evidence_path_fixture/cas_traffic与path-layout-inputs字节等v0.46，旧memory.py除新代理method逐字不变，旧其他runtime除发行版本不改。新增memory_batch.py，按实际递归集合65 Python+HTML收费，不沿用旧64数目。

两既有合成布局clustered/separated各三轮，固定C/S、S/C、C/S。每worker先完成epoch0/1/2全部ingest，再查显式旧SID；每epoch取doc0..n-1，n=1/3/32，exact成功和required-1拒绝，18主case；另epoch0 doc0×3 exact/不足与missing零预算三控制。6×21=126，成功666绑定的重复出现照计，不是666独立文档/科学样本。36历史完整文件恢复为同块9+分散27。

存在key的原独立lookup参考hit与API逐字段相等，missing控制使用冻结空结果（独立auditor确认原fixture无此key），另独立auditor按冻结fixture原line/offset/SHA/JSON构造expected hit，并真实读指定SID范围；不是仅检查两段同源代码相等。原epoch0/1结果不能被最新HEAD代替。预算拒绝result为None、精确错误文本，原tree和HEAD不动，无remember/派生答案；各layout三轮全树相等。合成记录允许公开，未引入真实科学原文。

## 原始成本和应用CAS工作

全部126case打开旧CASTraffic作诊断，守恒readcalls=2opens、opens=attempts=success、readB=payload+84opens、decoded=raw+compressed。预算拒绝view工作仍计费；这些不是SSD物理或全系统I/O，SQLite C层/metadata/OS缓存未覆盖。没有meterOFF性能对照或生产吞吐结果。

| 轮 | 布局 | 返回 | 预算拒绝 | instrumented API wall s | API CPU s | parent完整wall s | 观察peakRSS B | CAS应用返回B | decoder输出B |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | clustered | 11 | 10 | 0.125920 | 0.171875 | 1.048117 | 37928960 | 919725 | 21430272 |
| 1 | separated | 11 | 10 | 0.114853 | 0.062500 | 0.989132 | 37441536 | 740515 | 18694983 |
| 2 | clustered | 11 | 10 | 0.125492 | 0.140625 | 1.035007 | 37609472 | 919725 | 21430272 |
| 2 | separated | 11 | 10 | 0.114630 | 0.078125 | 0.980975 | 37490688 | 740515 | 18694983 |
| 3 | clustered | 11 | 10 | 0.126282 | 0.140625 | 1.037130 | 37429248 | 919725 | 21430272 |
| 3 | separated | 11 | 10 | 0.113843 | 0.062500 | 0.982513 | 37404672 | 740515 | 18694983 |

![公共批查询API机械验收成本](batch-api.png)

标准图已实际视觉检查：三张为instrumented API/完整worker wall/观察RSS，布局/轮次/单位清楚，不呈现ON/OFF速度比。本版没有提速门槛，全部数字只是成本观察，不做显著性或总体科学收益推断。原API内部wall与父/worker费用分别保留；父完整subprocess wall包含启动、参考读取、序列化与末尾释放，不能把小的函数wall称整个流程成本。

## 全部文件、源码、CPU和RAM费用

首轮完整文件/建库/audit成本如下，全部轮原值在JSON：

| 布局 | 完整memory B | 当前source B | 其它worker文件B | ingest wall s | ingest CPU s | audit wall s | audit CPU s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| clustered | 204568 | 169538 | 6864 | 0.087888 | 0.093750 | 0.068759 | 0.046875 |
| separated | 198252 | 169538 | 5496 | 0.084818 | 0.062500 | 0.088686 | 0.125000 |

memory包括全部CAS、三代旧snapshot/index/manifest/HEAD/实际残留，不只最后一代；source当前文件、完整ledger另计。初始source write额外fsync为0，不能夸称这些评测输入持久化；memory内部fsync未知null，ledger和child/parent侧车exclusive+fsync。报告保存返回码/异常/SHA，失败不覆盖追加重跑。六个评测目录不是部署常驻六份成本。

65 Python+HTML实际源码416514B，旧v0.46为413548B，增加2966B；新memory_batch.py为2512B，method代理增加也计入全库。source-resource.json按实际集合逐个bytes/SHA，专用/复用driver/analyzer/fixture/meter/save代码另列，协议/测试源码B/SHA在measurement-context.json。既有v0.33源码账本追加更正保持，旧tag不重写。

6 child+parent原始JSON共817846B，driver日志0B。原lookup参考、独立audit、ingest、全恢复、workerCPU/parent完整wall均收费；不训练、不加模型/字典/远程请求。SQLite/资源图/全RSS没有独立完整增量测量，observed process peak不是全部生命周期外采样，不能宣称内存免费或入证预算等内存上限。平台/解释器依赖未分配，不称完整TCO。

独立二次源/原证/全树/计数/绘图额外wall 3.166626s、CPU 1.734375s、观察RSS 84209664B，不含初始解释器启动和写计时记录；不是在线查询时间。冷缓存/跨机/SSD物理/全系统IO继续未测。

## 发布与后续

新work/out运行python -m scripts.run_batch_api，再scripts.analyze_batch_api带work/out/freeze/test-log。可选API与文档、冻结协议、原始JSON、图、详实报告/README/release推送GitHub；CI后Release，实际资产SHA/递归65 Python+HTML/tag/评测代码、物理仓库外actual wheel+current native、新lookup_many exact/不足预算/旧SID/输入拒绝与旧功能、actual sdist机械驱动auditor合成smoke、最终proof上传重下载全通过才完成。

当前完成的是可逆存储/来源回溯与可调用批查询基础。E3神经压缩净收益仍失败，E4的开放语义/图检索、真实长期对话、多跳科学推理和回答质量未验收；无限上下文没有完成。下一项必须另冻新假设，不能在本批fixture上调预算或把机械通过叫生产性能。旧24模型API用完、无新授权，本版0新调用，本机CPU离线。真实科学源/段/帧/恢复副本、私有研究模型/课程模板/个人报告/密钥不发布。
