# v0.65.0 实验报告：词序碰撞反例与显式规则来源证明

## 本轮结论与项目位置

H1受限形式机制 **True**，H2自造词序碰撞诊断 **True**。72/72主查询完成独立原文DAG与有限闭包核验，3/3预算控制保持incomplete，6/6篡改被拒；历史SID的24份certificate SHA与最初相同。64个旧模型方向预测暴露同词袋表示限制：每模型8/16判对，固定50%。**这是预期的人工反例与受限机制验收，不是科学NLI准确率改善或回答收益。**

上一版真实检索论文上的pair弱分类质量失败（97/146低于多数类101/146），本版不在已见dev调参，不把人工题当新科学验证。模型吃自然语言字符串，形式验证器吃人工显式结构化公理，两者输入信息不同，不能据此把形式结果当更好的语义模型。E3净收益、E4整体、可靠证据关系、真实长期会话、回答质量和无限上下文均未完成。

## 冻结、次数与数据

代码/协议/owned-input/modelSHA清单冻结 `78218038d9a6ab1675c5eef63e54160bb175844e`；exact候选CI `40455963796`成功后，唯一1fresh worker，timeout600s、重试0。完整357检查356通过/1既有Windows权限跳过。0新科学问题、0新训练、0模型API。已训练的四模型逐byte SHA和长度检查后加载，未改变训练参数或权重；旧训练1campaign/3fit/多数类及全部产物仍计历史费用。

owned fixture初始19facts+7rules=26records，更新追加1明确负fact=27records。8种predicate的正向有明确正事实、反向有明确负事实，不能从未出现推断为假。16方向题+8链/循环/负前提/未知/非默认否定/不爆炸/重复变量/常量题，初始、更新、更新后读旧SID三阶段各24题=72证书。完整预算100000逻辑工作单位，3预算控制0单位，6篡改均留分母。人工query期望在协议之前固定，不称盲测。

| 阶段 |24主查询verdict分布 |
|---|---|
| initial | {'supported': 11, 'refuted': 9, 'unknown': 4} |
| updated | {'supported': 9, 'refuted': 9, 'inconsistent': 2, 'unknown': 4} |
| historical | {'supported': 11, 'refuted': 9, 'unknown': 4} |

新负influence(c0,c2)使该查询及经规则传播的connected变为inconsistent；原正证明保留，不擅自选胜负，也不推出任意unrelated结论。无显式正负推导且独立固定点完整才可称unknown。预算中止为incomplete，即使局部已有witness也不升级为完整判别。

## 格式、算法与独立证明

仅自定义RKVLOGIC1 signed binary Horn JSONL，无函数项/等式理论/默认否定/NL抽取。每规则1..3前提、最多3变量、head变量必须在premises出现；1024records/64rules/1MiB源上限，读取前先检查源metadata大小。正负通道独立；递归循环计算有限闭包，矛盾不触发经典爆炸。

主引擎前向匹配，按稳定recordID/atom顺序选首个proof，记录事实/规则原SID/path/offset/length/SHA、变量替换和前提拓扑索引。独立审计器单独解析原source并逐record通过实际Store重新读字节，独立验证每步和完整有限grounding固定点。独立grounding上限100000，超过时VerificationCapacityExceeded，不当unknown或科学反例。独立验证的结论只在给定公理正确的前提下成立，CAS来源真实不代表公理来自可靠语言理解或科学上为真。

逻辑工作单位只统计候选atom统一比较和新增推导，不含排序、原文I/O、全部CPU/RAM，不是完整资源上限或抗拒绝服务保证。[Souffle第一手教程](https://souffle-lang.github.io/tutorial)仅作有限域递归规则背景，本实现自定义语法、不声称Souffle兼容或复现其性能。

## 词序信息丢失的可证伪反例

8组上下文同时明确陈述正向并否认反向，两条claim交换主客体但词袋完全相同，gold分别SUPPORT/CONTRADICT。389维旧特征（claim/document/sharedTF+否定/覆盖标量+bias）逐float完全相同；claim-only也相同，四既有model预测同一分数/标签，所以每组最多判对1/2。正式32个pair×2claim=64预测全满足该碰撞，4model各8/16。它指出表示无法分辨这类输入，不证明每个旧科学错误都由词序造成，也不支持把规则接口当自动NLI。

| 原模型 |完整加载B |固定SHA |
|---|---:|---|
| claim_only | 4211 | 25ffc7eb96bd69ef8360fae01a7f77c70281b10464e4cc13fed0425c6a856fd7 |
| majority | 488 | e4f8d05a688935f476b846751185c58fbc4a5ac9d73ce2c2abe94ed01cb02996 |
| pair | 8545 | aad660b51b3361177311212e920a52b08115afa047c3af6aa911b8781bdc9961 |
| permuted_pair | 8563 | fe6ed6235947995c1c56fbeba0b4682e3b3e827f20c0e0b90b29abf73a9e3870 |

## 原source与资源账本

所有阶段读原SID，查询前后CAS账本不变，2完整原source恢复通过。成功证书原record绑定 **1833**；成功constructor/auditor加完整恢复的应用层源返回 **506666B**。拒绝篡改时的应用read B未装计量，为null而非0；全系统SQLite/metadata/OS读、SSD物理IO、冷缓存、跨机未测。该B不能叫物理读取。

| 阶段 |constructor+infer+独立audit wall s |CPU s |CAS查询期不变 |
|---|---:|---:|---|
| initial | 0.636005 | 0.640625 | True |
| updated | 0.659219 | 0.656250 | True |
| historical | 0.654085 | 0.640625 | True |

完整worker wall **2.226713s** / CPU **2.046875s** / process peakRSS **36818944B**；父进程完整subprocess wall **2.331723s**，单轮机械运行不称性能增益。模型加载 `{'all_model_bytes': 21807, 'cpu_s': 0.0, 'wall_s': 0.0011400999501347542}`，owned预测 `{'cpu_s': 0.0, 'wall_s': 0.004657299956306815}`；ingest逐项在raw-worker.json，未剔除训练/source/observer费用以制造收益。

整库递归66Python+1HTML完整源码 **426112B**；所有新程序/测试/协议/input清单 **41286B**。完整4模型加载 **21807B**；本轮source、所有旧新快照/CAS、private完整certificate和independent审计记录等全部工作文件 **1395277B**，逐文件size/SHA见source-resource/raw-worker，未只记最终HEAD。旧真实科学训练和模型目录/原语料/检索source等保留在v0.64及历史账本，不用0新训练冒充0模型费用。依赖/系统二进制、OS/allocator开销不能从这些源码B推出，未分配项明确保留。

## 可运行交付、图与后续

```powershell
python -m unittest discover -s tests
```

scripts/signed_logic.py与audit_signed_logic.py可通过实际Store+显式SID/path调用，logic_fixture.py提供owned示例，run_signed_logic.py是冻结1worker驱动。正式CLI需清单中的本地既有model文件及冻结commit，缺失SHA/模型会拒绝；不把私有科学权重打包。scripts为sdist/experiment源，不默认进wheel SDK；运行库66模块仅版本变化、HTML相同，既有SDK/UI/归档无新默认规则行为。

![受限机制与词序碰撞](signed-logic.png)

图已实际视觉检查（坐标、比例、标签与三阶段分母清楚）；该图不是科学分类比较或推理质量提升。报告编写时尚待最终本地package与GitHub Release实际核验，完成状态以最终published-verification.json为准，不回写原实验。下一项应另冻受限规则输入边界/变形与拒绝测试，或另行选择真正带组合顺序信息的语义候选和独立数据；不能继续调旧词袋参数来追这个反例正分。没有新增远程模型授权。

补充完整实验脚本费用：除整库66Python+HTML外，保守计入当前全部173份scripts Python源码，共1477763B，包括共享依赖和未执行的历史脚本；不声称它们全被本worker实际import。清单见source-resource.json，与冻结tag逐byte核对。训练/source历史费用保持原账本。Windows CPU计时有粒度限制，模型载入和小型碰撞预测记录0.0s不代表无CPU成本，完整worker CPU和RSS已保留。
