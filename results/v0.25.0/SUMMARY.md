# v0.25 内容锚定JATS片段实验报告

## 假设、基线与交付

v0.24固定18个原XML的927单元全无元素id，位置键无法避免段落插入级联，v4的
range乐观下界仅1/12修订可过预算。本轮新增显式content审计模式，冻结同一输入/
预算及whole、position对照，测试可证伪假设：内容指纹键减少级联，但改写会产生
删除+插入两个操作，重复段落/父上下文与较长元数据可能抵消优势。

key=父论文ID+title/abstract/body角色+派生text UTF-8 SHA256+相同role/text出现序号。
仍分别绑定完整父SHA与原连续range SHA。同text不同原标记可重绑定；text改写不
视为同key。无关唯一段落插入保持其他内容键，但重复段落序号不代表永久物理
段落ID，不声称语义身份。没有缩短SHA、调高预算或重写原XML来获得收益。

这是独立审计API，Memory默认/来源kind/清单均不改。已有position/xml-id模式和
默认mode的输出不变；新增合成测试覆盖插入、大小写改写、重复与markup重绑定。

## 方法与正确性

复用同六篇18版本/12真实修订，0新增独立论文/QA/模型请求。position/content
两规则共1854范围审计（同一原范围重复）、whole/position/content×3轮×18文件
共162解析、9新进程；固定/Gear各13状态，26历史CAS快照全源恢复并核SHA，持久树
不变。184测试运行，183通过、1符号链接权限跳过。输入原路径/版本名保留。

144个规划仅比较相邻状态，是最短回放必要条件，不代表实际累计overlay/检查点
数。保留25%变化、32changes、256KiB记录、2MiB CAS等门槛。range-only是未实现
局部解码器的乐观下界；当前完整父校验逐记录全读，无缓存，重绑定父身份也收费。

## 同批预算对照

| 分块 | 键规则 | 策略 | range下界可过/12 | 完整父校验可过/12 | 变化upsert中位 | 重绑定中位 | 下界失败原因 |
|---|---|---|---|---|---|---|---|
| fixed | whole | v3 | 0 | 0 | 1.0 | 0.0 | {'budget-record-bytes': 12} |
| fixed | whole | v4 | 0 | 0 | 1.0 | 0.0 | {'budget-record-bytes': 12} |
| fixed | position | v3 | 0 | 0 | 50.0 | 0.0 | {'budget-changes': 12} |
| fixed | position | v4 | 1 | 0 | 41.5 | 6.5 | {'budget-changes': 9, 'budget-cas-bytes': 2, 'admissible': 1} |
| fixed | content | v3 | 0 | 0 | 50.0 | 0.0 | {'legacy-change-limit': 9, 'budget-changes': 3} |
| fixed | content | v4 | 3 | 0 | 31.5 | 15.5 | {'legacy-change-limit': 4, 'budget-changes': 5, 'admissible': 3} |
| gear | whole | v3 | 0 | 0 | 1.0 | 0.0 | {'budget-record-bytes': 12} |
| gear | whole | v4 | 0 | 0 | 1.0 | 0.0 | {'budget-record-bytes': 12} |
| gear | position | v3 | 0 | 0 | 50.0 | 0.0 | {'budget-changes': 12} |
| gear | position | v4 | 1 | 0 | 41.5 | 6.5 | {'budget-changes': 9, 'budget-cas-bytes': 2, 'admissible': 1} |
| gear | content | v3 | 0 | 0 | 50.0 | 0.0 | {'legacy-change-limit': 9, 'budget-changes': 3} |
| gear | content | v4 | 2 | 0 | 31.5 | 15.5 | {'legacy-change-limit': 4, 'budget-changes': 5, 'budget-cas-bytes': 1, 'admissible': 2} |

## 每次真实转换的v4操作与门槛


### fixed

| 阶段 | 规则 | 删 | 增/改 | 重绑定 | 下界记录B | 下界CAS B | range门槛 | 完整父门槛 |
|---|---|---|---|---|---|---|---|---|
| 1 | position | 3 | 62 | 1 | 123456 | 8126464 | budget-changes | budget-changes |
| 1 | content | 56 | 57 | 6 | 119612 | 7471104 | legacy-change-limit | legacy-change-limit |
| 2 | position | 0 | 65 | 4 | 115565 | 8388608 | budget-changes | budget-changes |
| 2 | content | 41 | 45 | 24 | 86538 | 5767168 | legacy-change-limit | legacy-change-limit |
| 3 | position | 0 | 33 | 16 | 122400 | 4390912 | budget-changes | budget-changes |
| 3 | content | 30 | 30 | 19 | 118494 | 3997696 | budget-changes | budget-changes |
| 4 | position | 1 | 50 | 1 | 111639 | 6750208 | budget-changes | budget-changes |
| 4 | content | 50 | 49 | 2 | 110425 | 6619136 | legacy-change-limit | legacy-change-limit |
| 5 | position | 3 | 43 | 1 | 128614 | 5898240 | budget-changes | budget-changes |
| 5 | content | 43 | 40 | 4 | 121569 | 5505024 | legacy-change-limit | legacy-change-limit |
| 6 | position | 14 | 16 | 5 | 93825 | 3145728 | budget-cas-bytes | budget-record-bytes |
| 6 | content | 26 | 12 | 9 | 81331 | 2621440 | budget-changes | budget-changes |
| 7 | position | 1 | 41 | 21 | 88292 | 5570560 | budget-changes | budget-changes |
| 7 | content | 14 | 13 | 49 | 31285 | 1835008 | admissible | budget-record-bytes |
| 8 | position | 3 | 54 | 12 | 101970 | 7405568 | budget-changes | budget-changes |
| 8 | content | 9 | 6 | 60 | 10268 | 983040 | admissible | budget-record-bytes |
| 9 | position | 0 | 1 | 48 | 2908 | 131072 | admissible | budget-record-bytes |
| 9 | content | 1 | 1 | 48 | 2908 | 131072 | admissible | budget-record-bytes |
| 10 | position | 0 | 26 | 25 | 71450 | 3538944 | budget-cas-bytes | budget-record-bytes |
| 10 | content | 26 | 26 | 25 | 71450 | 3538944 | budget-changes | budget-changes |
| 11 | position | 0 | 42 | 3 | 138125 | 5570560 | budget-changes | budget-changes |
| 11 | content | 32 | 33 | 12 | 116839 | 4325376 | budget-changes | budget-changes |
| 12 | position | 0 | 39 | 8 | 81488 | 3538944 | budget-changes | budget-changes |
| 12 | content | 9 | 35 | 12 | 70100 | 3014656 | budget-changes | budget-changes |

### gear

| 阶段 | 规则 | 删 | 增/改 | 重绑定 | 下界记录B | 下界CAS B | range门槛 | 完整父门槛 |
|---|---|---|---|---|---|---|---|---|
| 1 | position | 3 | 62 | 1 | 123456 | 20792710 | budget-changes | budget-changes |
| 1 | content | 56 | 57 | 6 | 119612 | 19102565 | legacy-change-limit | legacy-change-limit |
| 2 | position | 0 | 65 | 4 | 115565 | 6188408 | budget-changes | budget-changes |
| 2 | content | 41 | 45 | 24 | 86538 | 4028974 | legacy-change-limit | legacy-change-limit |
| 3 | position | 0 | 33 | 16 | 122400 | 3367960 | budget-changes | budget-changes |
| 3 | content | 30 | 30 | 19 | 118494 | 2936957 | budget-changes | budget-changes |
| 4 | position | 1 | 50 | 1 | 111639 | 8617293 | budget-changes | budget-changes |
| 4 | content | 50 | 49 | 2 | 110425 | 8446616 | legacy-change-limit | legacy-change-limit |
| 5 | position | 3 | 43 | 1 | 128614 | 18785683 | budget-changes | budget-changes |
| 5 | content | 43 | 40 | 4 | 121569 | 17515618 | legacy-change-limit | legacy-change-limit |
| 6 | position | 14 | 16 | 5 | 93825 | 10171124 | budget-cas-bytes | budget-record-bytes |
| 6 | content | 26 | 12 | 9 | 81331 | 8376888 | budget-changes | budget-changes |
| 7 | position | 1 | 41 | 21 | 88292 | 14368576 | budget-changes | budget-changes |
| 7 | content | 14 | 13 | 49 | 31285 | 4673996 | budget-cas-bytes | budget-record-bytes |
| 8 | position | 3 | 54 | 12 | 101970 | 5206497 | budget-changes | budget-changes |
| 8 | content | 9 | 6 | 60 | 10268 | 851174 | admissible | budget-record-bytes |
| 9 | position | 0 | 1 | 48 | 2908 | 72586 | admissible | budget-record-bytes |
| 9 | content | 1 | 1 | 48 | 2908 | 72586 | admissible | budget-record-bytes |
| 10 | position | 0 | 26 | 25 | 71450 | 4605458 | budget-cas-bytes | budget-record-bytes |
| 10 | content | 26 | 26 | 25 | 71450 | 4605458 | budget-changes | budget-changes |
| 11 | position | 0 | 42 | 3 | 138125 | 19150091 | budget-changes | budget-changes |
| 11 | content | 32 | 33 | 12 | 116839 | 14997311 | budget-changes | budget-changes |
| 12 | position | 0 | 39 | 8 | 81488 | 10669529 | budget-changes | budget-changes |
| 12 | content | 9 | 35 | 12 | 70100 | 8949381 | budget-changes | budget-changes |

## 解析与资源代价

| 模式 | 18文件wall中位s | CPU中位s | 含启动进程wall中位s | 进程峰值MiB |
|---|---|---|---|---|
| whole | 0.056982 | 0.062500 | 0.185232 | 37.14 |
| position | 0.271182 | 0.265625 | 0.409997 | 49.35 |
| content | 0.272789 | 0.281250 | 0.410452 | 49.38 |

| 分块 | 候选 | 全部历史CAS B | 13状态未压缩定位候选 B | 全部RKV源一次B | 原生库一次B |
|---|---|---|---|---|---|
| fixed | whole | 919792 | 20904 | 362137 | 0 |
| fixed | position | 919792 | 1114496 | 362137 | 0 |
| fixed | content | 919792 | 1631278 | 362137 | 0 |
| gear | whole | 885123 | 20904 | 362137 | 124419 |
| gear | position | 885123 | 1114496 | 362137 | 124419 |
| gear | content | 885123 | 1631278 | 362137 | 124419 |

metadata去text逐条canonical JSON求和，完整父上下文可由已计CAS快照关联；content
键的64hex文本SHA全额收费。未计实际FTS/Memory清单/overlay/运行时/pyc/安装/文件
系统成本，不能与v0.23完整系统算净压缩率。所有51模块/HTML源计一次，Gear加完整
旧实测库/元数据。解析含双遍XML与描述/SHA生成，输入预加载，启动另列；CPU为
本机计时分辨率，RSS含输入/输出，未测query或科学质量。

## 数据支持的结论与下一门槛

fixed：内容锚的v4 range乐观通过3/12，位置键1/12，当前完整父校验0/12。这些是同一批数据的必要条件计数，不能称实际增量索引收益。

gear：内容锚的v4 range乐观通过2/12，位置键1/12，当前完整父校验0/12。这些是同一批数据的必要条件计数，不能称实际增量索引收益。


固定/Gear只多出2/1个乐观可行转换，仍有9/10个不通过，父上下文读取也未解决；
内容键没有提供足够证据支持生产集成。暂缓片段Memory新格式与局部解码开发，
保留整篇默认及原预算。后续优先扩大离线科学检索任务/上下文覆盖评测，定位
实际任务瓶颈；不再在这六篇上调门槛或追加键规则追求正结果。若未来独立工作负载
显示更大潜力，再以可信父上下文、同粒度重建、完整索引/清单/CAS/资源与整个
查询成本为新验收门槛。现有审计API及负结果仍保留，便于复核。

所有数字见原始plans/parser-trials/identity-audit及核验JSON。仅本机温缓存；无新
科学QA、E3、多跳、长期会话、冷缓存、跨机器、掉电/并发/GC或普遍数学证明结论。
