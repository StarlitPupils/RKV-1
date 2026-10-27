# v0.67.0 实验报告：证据来源集合不完整时明确拒绝“读全”声明

## 本轮结论和项目位置

H1来源集合36case/12完整独立审计 **True**；H2的24次预检不完整零source读/12历史一致/10无效完整proof拒绝 **True**。36个固定case中12完整、24明确incomplete_source_set，后者是预期保守拒绝，不是丢掉的失败样本。全部10无效完整证明输入被拒绝，7份原文件从历史/更新SID逐byte恢复通过。

本版只证明机器来源文件集合的字节覆盖。`source_grammar_verified`、`logical_closure_verified`、`scientific_entailment_verified`对所有输出始终False，`generated_answer=None`。不解析来源公理语法、不执行跨文件规则join、不生成回答，更不表示来源在科学上正确或理解自然语言。v0.64关系分类质量失败、E3净收益和E4整体未完成的结论保持。

## 为什么做这项边界实验

旧单file形式闭包只能断言该file公理内部的结果，不能因为漏检了后来文件，就把“不知道”变成“结论不存在”。此版先把“eligible来源是否完整加载”独立于“规则是否推导成立”和“科学事实是否正确”。即使字节读全，后两项仍False；未读全只能明确incomplete，不能给全局unknown。eligible后缀政策也不覆盖普通自然语言文档或世界全部知识。

## 冻结与次数

冻结 `6655390d3dcf19d68d0febe293d04b3bd4139dfd`，exactCI `40459565942`成功后唯一1fresh worker，timeout600s，重试0。完整369检查368pass/1既有Windows权限跳过；新增8owned测试覆盖独立SHA/预算预检/零source读/新旧SID/路径和strictscope/固定plan/观察器异常清理。formal0之前冻结planSHA和两source状态的全部文件SHA，不根据结果调budget或case。0新训练、0当前模型加载、0模型API；旧模型训练及全部历史source/snapshot费用保持。

owned初始one.logic.jsonl正fact、two.logic.jsonl规则、非eligible notes.txt；updated追加late.logic.jsonl负fact。字节虽为显式机器公理样例，本轮没有验证语法或进行跨文件推导。3stage为initial/updated/历史initialSID在newHEAD之后。每stage的full/omitlast/reversefull3种caller列表×budget0/总B减1/exact/总B加1四种budget=12case，3×12=36。完整12、不完整24、历史同case proof12一致，所有预期在冻结plan明示，不是未知科学盲测。

## 方法与独立审计

实际snapshot metadata枚举所有以.logic.jsonl结尾的路径；名字必须满足固定小写规范相对路径。caller列表去顺序归一但拒绝重复alias，必须与eligible全集相同；1..8files、全eligible原payload<=1MiB且不超过caller budget。没有eligible/超8file/漏file/预算不足返回incomplete_source_set和空payload；非法参数或畸形eligible路径ValueError。metadata预检在任何source payload读取之前。

独立审计不调用loader作真值：独立枚举同SIDeligible全集，要求严格17key格式及固定scope文本，完整读取每个原file比length/SHA；禁止把scope描述或额外answer字段注入成“全部科学知识已验证”。10负控制包括path/hash/SID/三个verification flags/budget/incomplete输入/scope/extra-key。incomplete输入是接口有效性控制，不称伪造科学结论。规范语法/逻辑/NLI flags始终False。

实际loader和independentauditor分别套窄范围Snapshot.read_range计数，正常/异常后恢复原method，新增单元测试核对真实返回B及清理。观察器成本计入总CPU/wall，本轮没有OFF对照或提速主张。每case CASledger前后不变，源budget只管loader返回的原sourcepayload。

## 全36case分母

| case |loader budget B |complete |拒绝原因 |实际loader source调用 |loader源返回B |
|---|---:|---|---|---:|---:|
| initial-full-zero | 0 | False | source_payload_budget_insufficient | 0 | 0 |
| initial-full-minus_one | 277 | False | source_payload_budget_insufficient | 0 | 0 |
| initial-full-exact | 278 | True | None | 2 | 278 |
| initial-full-plus_one | 279 | True | None | 2 | 278 |
| initial-omit_last-zero | 0 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| initial-omit_last-minus_one | 277 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| initial-omit_last-exact | 278 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| initial-omit_last-plus_one | 279 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| initial-reverse_full-zero | 0 | False | source_payload_budget_insufficient | 0 | 0 |
| initial-reverse_full-minus_one | 277 | False | source_payload_budget_insufficient | 0 | 0 |
| initial-reverse_full-exact | 278 | True | None | 2 | 278 |
| initial-reverse_full-plus_one | 279 | True | None | 2 | 278 |
| updated-full-zero | 0 | False | source_payload_budget_insufficient | 0 | 0 |
| updated-full-minus_one | 383 | False | source_payload_budget_insufficient | 0 | 0 |
| updated-full-exact | 384 | True | None | 3 | 384 |
| updated-full-plus_one | 385 | True | None | 3 | 384 |
| updated-omit_last-zero | 0 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| updated-omit_last-minus_one | 383 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| updated-omit_last-exact | 384 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| updated-omit_last-plus_one | 385 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| updated-reverse_full-zero | 0 | False | source_payload_budget_insufficient | 0 | 0 |
| updated-reverse_full-minus_one | 383 | False | source_payload_budget_insufficient | 0 | 0 |
| updated-reverse_full-exact | 384 | True | None | 3 | 384 |
| updated-reverse_full-plus_one | 385 | True | None | 3 | 384 |
| historical-full-zero | 0 | False | source_payload_budget_insufficient | 0 | 0 |
| historical-full-minus_one | 277 | False | source_payload_budget_insufficient | 0 | 0 |
| historical-full-exact | 278 | True | None | 2 | 278 |
| historical-full-plus_one | 279 | True | None | 2 | 278 |
| historical-omit_last-zero | 0 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| historical-omit_last-minus_one | 277 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| historical-omit_last-exact | 278 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| historical-omit_last-plus_one | 279 | False | caller_set_differs_from_snapshot_eligible_set | 0 | 0 |
| historical-reverse_full-zero | 0 | False | source_payload_budget_insufficient | 0 | 0 |
| historical-reverse_full-minus_one | 277 | False | source_payload_budget_insufficient | 0 | 0 |
| historical-reverse_full-exact | 278 | True | None | 2 | 278 |
| historical-reverse_full-plus_one | 279 | True | None | 2 | 278 |

所有24不完整case实际loader source调用0；metadata读取未被该计数覆盖，不能说物理0I/O。12完整case的原payload dict逐byte等于ownerfixture，独立SHA覆盖通过。initial/historical相同case proof完全相同，更新后遗漏late来源不会退化成完整声明。

## 原始成本、预算范围与完整账本

Loader source应用返回合计 **3760B**，独立auditor额外 **3760B**，原全file恢复（包含非eligible notes）另 **812B**。拒绝control的返回B未仪表化为null而非0；source metadata/SQLite/OS读取和SSD物理IO也未测。不能把单loader budget称完整查询I/O上限，auditor/recovery已明确另计。

完整worker wall **5.177907s** / CPU **0.859375s** / peakRSS **33390592B**，父完整subprocess wall **5.304079s**。每case含loader observer+独立audit的wall/CPU、ingest和旧新snapshot身份、36scopeproof逐项在raw-worker.json。平台计时粒度下0值非无CPU开销。本轮是单次机械验收，不比较性能收益。

整库递归66Python+1HTML源码 **426112B**；全部179份当前scripts保守收费 **1503220B**，包含共享/未执行旧脚本，不称观察到的动态import集合。新协议/测试/inputprograms另外列，全部source/CAS/旧新snapshot/36privateproof与所有残留工作文件 **31364B**，逐size/SHA见source-resource/raw-worker。当前model0B，旧训练/source/model与历史文件不删除不当免费。依赖/系统二进制、metadata/allocator/OS RAM未分配项显式保留；payload<=1MiB不等于整个进程RAM<=1MiB。

## 可运行交付、图与未实现项

```powershell
python -m unittest discover -s tests
```

source_universe.py是显式SID/path集合loader，audit_source_universe.py是独立字节覆盖审计，source_universe_fixture.py是公开owned可重建样例，run_source_universe.py为冻结唯一worker驱动。无需私有科学模型；正式CLI需对应frozencommit及不存在的work/out目录，拒绝覆盖。scripts走sdist/experiment，不默认并入SDK/UI；旧signedengine和metamorphic脚本均不改，66runtime仅版本、HTML同前。

![来源集合完整与预检拒绝](source-universe.png)

图已实际视觉检查，坐标/分母/预算限定清楚。当前报告是tag前状态；localactualoutsidewheel/currentnative与actualsdist新旧smoke、finalbuild/sourceaudit、GitHub ReleaseCI/实际7assetsSHA/全源码和最终proof8重下载齐备后，以published-verification.json判发行完成，不改原测量。

这仅完成来源集合边界StageA，跨文件原证推导DAG尚未实现，较宽私有v067-next-protocol提案不是已交付功能；下一步须另冻跨文件规则join/重复ID/原record定位及独立closure。自动自然语言到受信公理、可靠NLI、真实长会话和回答、E4整体/无限上下文仍未完成；冷缓存/跨机器/物理IO未测。0新增远程模型调用，原科学/模型/私有研究/模板/个人报告/密钥不公开。
