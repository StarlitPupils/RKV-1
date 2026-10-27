# v0.68.0 实验报告：多来源显式规则推导与原文件证据链

## 结论与阶段

H1全部216预定处置/36完整独立闭包 **True**；H2来源与工作预算拒绝/历史一致/篡改拒绝 **True**。正式216证书分为36完整闭包、144来源集合不全、36逻辑工作不足；72历史certificate对象逐byte一致，12篡改拒绝，7原文件历史恢复通过。所有类别保留，预算不足未升级为unknown，来源遗漏未升级为完整推断。

本版首次把显式规则推导跨到多个原文件，并把证明定位到真实原SID/path/recordoffset/length/SHA。来源集合边界和推导正确性是分开的审核，完整来源后才解析公理并允许逻辑闭包。**适用范围是人工显式signed Horn公理，不是自动自然语言抽取、科学真理、可靠NLI或回答收益。** E3净收益/E4整体/真实长会话/无限上下文未完成，v0.64词面关系质量负结果保持。

## 冻结、来源与精确次数

源/协议/全部source与planSHA冻结 `5160e9dcf2404553cd8b5af73970b175e67c9170`，exactCI `40461655492`成功后唯一1fresh worker，timeout600s，重试0。380检查379通过/1既有Windows权限skip；新11测试覆盖跨filejoin、重复localID、旧SID/迟到反证/负query、source/work不足及错误升级、strictscope/源tuple/offset/SHA/SID/premise篡改、返回scope深拷贝隔离、全局recordcap、坏grammar、query/budget输入与216plan。没有新科学或训练，当前模型加载0，模型API0；已有全部source/model/训练/历史snapshot成本保留。

初始one.logic.jsonl含edge(a,b)+、edge(b,c)+、edge(c,b)-，two.logic.jsonl含4条edge/reach传递和正回边/显式负规则；两个file故意复用same/negative编号。新late.logic.jsonl含reach(a,c)-，notes.txt非eligible，不当已解析或全知识覆盖。初始7records、更新8records，规则join真实跨file，身份使用(path,id)tuple，公开certificate为二维字符串list，避免字符串拼接alias或把不同来源的同id错误合并。

6query的expected预先固定：edge(a,b)+支持；reach(a,c)+支持→冲突；reach(c,b)+反驳；edge(c,a)+未知；unrelated(a,c)+未知；reach(a,c)-反驳→冲突。正负显式通道独立，矛盾不推出无关结论，不把未出现当默认否定。3stage初始/更新/更新后历史SID×3caller模式full/reversefull/omitlast×2sourcebudget exact/minus1×2workbudget0/100000×6query=216；正式前plan完全可见，属于受限机制，不是未知科学盲测。

## 算法、来源范围与独立验证

复用既有SignedVerifier前向匹配算法，通过实验子类把每个原file独立parse后的record以tuple键放进同一finite程序；旧单file引擎及v0.67loader/sourcechecker字节不改。每source原record citationoffset保持，不拼接source再生成虚假单file引用。全局<=1024records/64rules，不让每file有效绕过总上限；每规则<=3前提/3range-restricted变量，无函数/默认否定/NL到公理转换。

loader先从实际pinned snapshot metadata枚举.logic.jsonl全集，1..8files、总payload<=1MiB且caller列表必须等全集。来源不足的certificate为空proof，独立审计器重算metadata全集与拒绝reason，0source payload读取，不给逻辑verdict。已完整来源的inner byte-scope中grammar/logic/science flags仍False，因为该scope仅证明byte覆盖；outer source_grammar_verified在全部原source语法解析后True。outer complete记录引擎闭包已完成，独立audit closure_completeness_verified另核实它，两者不当科学verified。

独立auditor复用与主引擎不同的sourceparser/grounding oracle，严格检查outer/innerschema和scope、全eligible file SHA、每条原record读出的byteSHA、tuple身份、变量替换与拓扑premises。complete时独立有限grounding固定点必须与certificate atom全集相同；partialwork只核soundDAG，不声称闭包完整。预算100000只是candidateatom比较/新增推导计数，不是完整CPU/RAM/I/O保证，independentgrounding容量100000单列超限异常而非unknown。

| stage |72证书verdict分布 |constructor+infer+independentaudit累计wall s |累计CPU s |
|---|---|---:|---:|
| initial | {'incomplete_source_set': 48, 'incomplete': 12, 'supported': 4, 'refuted': 4, 'unknown': 4} | 0.142848 | 0.093750 |
| updated | {'incomplete_source_set': 48, 'incomplete': 12, 'supported': 2, 'inconsistent': 4, 'refuted': 2, 'unknown': 4} | 0.161609 | 0.171875 |
| historical | {'incomplete_source_set': 48, 'incomplete': 12, 'supported': 4, 'refuted': 4, 'unknown': 4} | 0.142301 | 0.109375 |

正式source不全144次均constructor与独立preflight实际source调用0，work不足36次均保持incomplete而非完整unknown，36complete的全部原记录DAG和独立fullclosure通过。初始和历史72份certificate对象相同，路径逆序也归一为同一source顺序。证明中实际跨file规则proof节点累计 **144**（各query闭包重复计，非distinct科学证据）；原record bindings **420**。同fileID分开，既不按同id误合并也不以相同文本改写原来源。

12负控制包含tuplepath、offset、sourceSHA、SID、premise、scope、额外字段、scientificflag、answer、innerscope伪造、falseworkcomplete、falsesourcecomplete，全部拒绝，失败分母保留。每主certificate先exclusive落盘再审计，禁止覆盖失败重跑。

## 完整成本与未测项

Constructor+infer应用source返回 **77400B**，独立audit额外 **211212B**，全部原file恢复含notes另 **2300B**。audit包含bytecoverage整file读+独立parse整file读+逐proofrecordrange重读，明确计费；sourcebudget仅loaderpayload，不能称全pipeline读取上限。篡改拒绝的返回B未装表为null而非0。metadata/SQLite/OS/物理SSD读取、冷缓存/跨机未测，source0read不是物理0IO。

完整worker wall **5.011878s** / CPU **0.906250s** / peakRSS **35991552B**，父完整subprocess wall **5.142249s**。observer成本在CPU/wall内，无OFF对照，单ownedmechanism一轮不声称速度/生产推理收益。平台CPU计时有粒度，局部0不代表无CPU费用。

完整递归66Python+1HTML源码 **426112B**；全部183份当前experimental scripts保守收费 **1525473B**，含历史/未执行共享脚本，不当真实动态import集合；新protocol/tests/input程序另外列。全部ownedsource、CAS/旧新snapshot/216privatecertificate和残留work文件 **441995B**，逐size/SHA在raw-worker/source-resource。模型当前0B不抹除全部旧模型/训练/source和snapshot历史费用；依赖/OS二进制、allocator/metadataRAM未分配保持显式，payloadbudget不是总进程memory上限。

## 可运行交付与后续

```powershell
python -m unittest discover -s tests
```

source_set_logic.py的SourceSetVerifier接收actual Store、显式SID、完整callerpaths，独立audit_source_set_logic.py验证原fileproof；source_set_fixture.py公开owned可重建输入，run_source_set_logic.py是冻结campaignCLI，不依赖私有科学model。正式驱动需对应freeze和不存在的work/out，重复路径拒绝。scripts只走sdist/experiments，不默认进SDK/UI；runtime66模块只version、HTML同前。

![多来源原证与拒绝边界](source-set-logic.png)

图已实际视觉检查，坐标/分类分母/预算边界清楚。报告是tag前状态，localactualoutsidewheel/currentnative/actualsdist新旧smoke、finalbuild/sourceaudit、ReleaseCI/实际7assetsSHA/全source/outsideactualreleaseinstall/finalproof8下载后，以published-verification.json判发行完成，原formal结果不回写。

下一步需另冻多文件重命名/拆分/合并的证据原范围与变形一致性，或有实际独立数据与受信语言解析候选时另做科学验证。不能从受限形式机制通过跳到真实NLI或无限上下文完成，也不能继续调已见词袋参数追正。0新增模型API，原science/model/私研/模板/个人报告/密钥不公开。
