# v0.47 冻结协议：可选公共三十二键内批查询 API 的机械验收

v0.46 actual资产/仓库外实际wheel与current native/实际sdist新selector与auditor/最终proof全通过后实施。不是新的科学性能验证：旧科学基准采用assessment QueryView，不能将其耗时结论直接外推本新实现。原Memory.lookup、CLI与默认UI均不改行为，增加显式Memory.lookup_many(keys, *, snapshot, max_source_bytes=1<<20)。本版只检验可调用接口的合同、原文绑定、拒绝与成本，不设置提速/推理收益门槛。

## 可调用合同

keys仅有限list/tuple，长度1..32，逐key沿原str/1..512/NUL限制；显式合法SID必须提供，无HEAD回退。字节预算严格int（不接受bool）0..32MiB，默认1MiB。全部输入在manifest/SQLite/CAS访问前验证。仅v3，新接口对v1/v2/v4明确拒绝，原lookup仍原兼容路径。

rkv1.memory_batch.lookup_many进入原QueryResources/_manifest/view一次完整核验，SQLite query_only=ON。直接用原LOCATORS SQL按输入顺序预取每key至多2行，合法v3原scan的全局key唯一；若>1拒绝畸形索引，不把截断当完整结果。所有行length含重复key的每次出现，累计大于max_source_bytes立即ValueError，没有部分结果。预检完成后每key原_verified_hits，原stored/raw/record SHA/codec/EOF/JSON成员校验均保持，无decoded块缓存、无method/global monkeypatch或unittest.mock依赖。每个重复key仍重新原record校验。缺失key返回空hits、入证0B，零预算允许全缺失。成功只在context全部退出后返回，每项source_key/hits保留输入顺序，顶层SID/scope/admitted_source_bytes/max_source_bytes/max_keys/consistency/wall_s。

字节预算只是原record入证量，不限制view构建、delta回放、SQLite/metadata/OS读取或总RAM。特别是预算拒绝前构建view仍可产生CAS工作，不能声称0I/O。单record原格式1MiB、合法key唯一与32keys共同约束所选记录，但解释器/解析对象/SQLite buffer/完整资源图另计，max_source_bytes不是RSS上限。

请求一致性沿候选已声明边界：进入时完整验证view，每selected原record每次再验证；不承诺每key重验中途未选中源/索引的外部篡改，新请求重验。无并发writer/生产承诺。新实现不patch Memory.lookup，原方法对象保持，但不能从此推断线程/并发写验收。所有异常自动关闭SQLite/清空QueryResources，不泄漏scope给调用方。

## 必要检查和精确正式计划

四个新单元检查：exact和1B不足预算、重复key逐次收费/原校验、多源文件但全局唯一key、missing零预算/32key边界；非法长度/类型/SID/预算在manifest前拒绝，v1/v2/v4拒绝；旧SID/新HEAD绑定、实际readonly SQL拒绝/连接真关闭/resource映射清空、budget异常与坏selected源恢复原lookup；32次重复、下一请求坏base/delta拒绝。早期合成fixture误用跨文件重复key/过大更新导致自动base重建属于开发预检修正，正式语料和次数不据结果调整。完整259测试、冻结代码/本协议/原fixture SHA引用与exact CI成功后唯一正式6worker。

原path_layout_fixture/evidence_path_fixture字节保持v0.46，docs/path-layout-inputs.json原SHA参考不改；只使用已知epoch0/1/2。clustered/separated×3轮=6fresh worker，顺序C/S、S/C、C/S，每worker3次ingest全部完成后HEAD为epoch2，再查询显式epoch0/1/2。每epoch批量keys doc0..n-1，n=1/3/32，各exact预算成功与required-1预算拒绝，18主case每worker；另epoch0 doc0重复3次exact成功/1B不足拒绝、missing doc999999零预算空结果成功，3控制每worker。总108主case=54成功+54预期拒绝，18控制=6重复成功+6重复拒绝+6missing空成功，126总case=66成功结果+60预期预算拒绝；666接受record绑定，36完整历史合成源文件恢复（同块9/分散27）。不能把126都称成功回答。

每case使用原独立lookup产生参考hits（含完整成本），API正确结果逐字段相等；独立auditor读原SID的真实range并比已冻结fixture原line/offset/SHA/JSON key/title/abstract；每个oldSID须等其原epoch，不能被最新HEAD覆盖。预算拒绝返回None/error精确匹配且无部分结果，worker完整memory树/HEAD前后相等，无remember/派生答案。各layout三轮全树相等，文件数/全部B包括所有CAS、旧snapshot/index/manifest/HEAD/残留均计账。

全部126case开启既有CASTraffic，只作诊断成本与预算边界，不作优化收益比较；CAS整数守恒，预算拒绝非零读取保留原值，不要求全为零。API instrumented_call wall/CPU、内部wall、baseline/独立audit/ingest/recovery/worker CPU与parent完整process wall、observed peak RSS分别收费。没有meterOFF性能对照，因此performance_gain_gate始终null，不能冒充速度验证；SQLite/metadata/全RAM未完整覆盖继续明确未测。三个轮不是独立科学样本。

单worker600s；新work/out exclusive，child/parent/ledger实际fsync，源input write没有额外fsync（0）不夸称输入持久化；内部memory fsync未知null。父侧车紧包subprocess.run启动到退出，保存返回码/异常、报告实际SHA；失败不覆盖或追加重跑。源/完整ledger/原始JSON/全部日志和其它文件成本保留，原合成记录可公开，不引入真实科学文本。

## 源码和发行

新增memory_batch.py及Memory.lookup_many代理方法，原memory.py其余逐字节沿v0.46，原其它runtime除版本不改；递归模块数按实际集合核对（预计65 Python+HTML），不硬编码旧64。旧v0.45/46科学性能均属旧assessment实现；本版源码增加/默认UI未集成，功能机械通过不等于生产/推理收益。

代码/协议/原始JSON/标准图实际视觉检查/详实实验报告/README/release说明/GitHub，CI成功后Release，实际资产SHA/完整递归Python+HTML/tag/专用程序、物理仓库外actual wheel+current native/new public lookup_many exact预算/不足预算/旧SID/输入拒绝与既有功能，实际sdist机械驱动与auditor合成smoke、最终proof重下载全部通过才完整交付再下一版。

本机CPU离线0新模型API，旧24预算用尽；不发布真实科学源/段/帧/恢复副本、私有模型研究/模板/个人报告/密钥。冷缓存/跨机/SSD物理/全系统IO/真实长期会话/回答质量未测或未证明，E3净收益仍失败、E4整体/无限上下文未验收。
