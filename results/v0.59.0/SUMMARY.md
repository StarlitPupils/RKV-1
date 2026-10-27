# v0.59.0 实验报告：索引加载观察器成本与精确调用诊断

## 结论及用途

**H1观察器开销≤10%：False；H2 instrumented inverse+varint self-time占比每轮≥50%：False**。18 fresh worker全部恢复完全相同原JSON与consumer-ready对象；9ON精确read_uvar调用数/全部function self-time守恒、9OFF计数null及追加18实际frame独立decode通过。本版测观察器和调用热点，未实现任何算法提速/原生核心/生产接入；不能把instrumented函数份额当未剖析CPU份额，也不能拿它计算可靠的Rust/Amdahl速度上界。

v058 typed/Zstd预定空间/时间/联合仍False。其完整矩阵中typed/LZMA虽净少60122/527350B，但加载更慢；本版固定这三个旧typed/LZMA frame作为工程诊断输入，不重编码、不调整level/训练/问题预算。两真实旧索引不是LLM参数权重；人工control是结构随机postings，非白噪声。

准备阶段两个真实frame各1次cProfile已经看过，实际profile-probes.json的B/SHA及2次数见measurement-context。因此阈值和重复量度是透明的已见输入探索性诊断，不称封存未知科学验证或独立域。本版正式18worker与此前2探针分开，无覆盖/补轮。

## 精确调用及恢复契约

| 数据 | token T | posting P | read_uvar预期4+2T+2P | ON精确符合轮数 |
|---|---:|---:|---:|---|
| entailmentbank | 5822 | 61534 | 134716 | 3/3 |
| scifact | 35664 | 534805 | 1140942 | 3/3 |
| synthetic_control | 1024 | 8192 | 18436 | 3/3 |

由原JSON独立计T/P。每typed payload有metadata长度1次、doc/token/pair头3次、每token字节长度和posting个数2次、每pair doc delta/TF2次。ON原inverse恰1次，read_uvar primitive与总calls均等预期，无漏计。self-time逐function相加与pstats.total_tt以严格容差守恒，不能相加cumulative重复统计。

所有18worker按原frame三SHA/长度/EOF/规范uvarint/UTF8/TF/doc范围和重建JSON size预算恢复，原decode、transform源码逐字节同v058，仅运行库版本号改变。模型对象再canonical重建比原bytes完全相同，源/frame事后SHA复核未变。OFF函数列表及profiler total为null，绝不写零伪装观测。异常finally关闭观察器、损坏必须拒绝，未绕过校验。

## 有/无观察器的实测成本

| 数据 | 模式 | ready wall中位s | ready CPU中位s | parent全wall中位s | 观察peak RSS三轮最大B |
|---|---|---:|---:|---:|---:|
| entailmentbank | off | 0.234862 | 0.234375 | 0.387182 | 62263296 |
| entailmentbank | on | 0.347565 | 0.343750 | 0.521298 | 62435328 |
| scifact | off | 0.741768 | 0.718750 | 0.964755 | 96980992 |
| scifact | on | 1.430377 | 1.437500 | 1.643783 | 96849920 |
| synthetic_control | off | 0.017536 | 0.015625 | 0.118793 | 29782016 |
| synthetic_control | on | 0.031648 | 0.031250 | 0.137239 | 29585408 |

ready区间固定原decode(frame)+json.loads(raw)，ON启停cProfile开销计入该段；pstats转换/输出序列化在ready外，仍计worker与parent。OFF导入相同模块/函数，有相同计时点；没有预先构建model绕掉解码。原输入与frame read/SHA在ready前，完整原字节/JSON/SHA重查在ready后，均计parent。父时间启动至进程退出，includes解释器与全部准备/核验/report I/O，不是ready的小段时间。

| 数据 | ON/OFF ready wall中位配对比 | CPU比 | parent比 | H1≤1.10 | 三轮instrumented inverse+varint份额 | H2每轮≥.50 |
|---|---:|---:|---:|---|---|---|
| entailmentbank | 1.482313236811558 | 1.4 | 1.3392922196510946 | False | [0.3565039313478554, 0.356263297292459, 0.3546376356610754] | False |
| scifact | 1.9337832762821379 | 1.9574468085106382 | 1.7038350361273034 | False | [0.6582694306786592, 0.6597790297929916, 0.6573776581852027] | True |
| synthetic_control | 1.7829277824430976 | 2.0 | 1.1593884816635924 | False | [0.582809278102562, 0.5721030151709102, 0.5775961523348475] | True |

H1须两个真实索引上三指标都满足；人工控制另列。CPU零分母保持null并失败，不加epsilon。H2只描述剖析状态中的self-time分布，不能外推未剖析CPU或原生可省时间。观察器使高频小函数多次付出记录成本，profile偏置不能用profile内部扣一笔费用消除；后续Rust若做，必须新鲜无profiler配对并计DLL加载/ffi/整个二进制/元数据/源码。

## 函数级定位（全部原始rows保留）

### entailmentbank instrumented self-time前12项

| 文件/函数 | self中位s | 三轮调用数 |
|---|---:|---|
| scripts/postings_transform.py/inverse | 0.068595 | [1, 1, 1] |
| encoder.py/iterencode | 0.065174 | [2, 2, 2] |
| scripts/postings_transform.py/read_uvar | 0.055195 | [134716, 134716, 134716] |
| decoder.py/raw_decode | 0.042213 | [2, 2, 2] |
| ~/<method 'decompress' of '_lzma.LZMADecompressor' objects> | 0.035604 | [1, 1, 1] |
| ~/<built-in method builtins.len> | 0.022210 | [326760, 326760, 326760] |
| __init__.py/dumps | 0.013173 | [17345, 17345, 17345] |
| scripts/postings_transform.py/_unique | 0.008145 | [17720, 17720, 17720] |
| scripts/postings_transform.py/canonical | 0.007710 | [17345, 17345, 17345] |
| ~/<method 'encode' of 'str' objects> | 0.004635 | [28866, 28866, 28866] |
| encoder.py/encode | 0.004244 | [17345, 17345, 17345] |
| ~/<built-in method _hashlib.openssl_sha256> | 0.003522 | [3, 3, 3] |
### scifact instrumented self-time前12项

| 文件/函数 | self中位s | 三轮调用数 |
|---|---:|---|
| scripts/postings_transform.py/inverse | 0.510518 | [1, 1, 1] |
| scripts/postings_transform.py/read_uvar | 0.430791 | [1140942, 1140942, 1140942] |
| ~/<built-in method builtins.len> | 0.163626 | [2449973, 2449973, 2449973] |
| decoder.py/raw_decode | 0.087164 | [2, 2, 2] |
| encoder.py/iterencode | 0.085136 | [2, 2, 2] |
| ~/<method 'decompress' of '_lzma.LZMADecompressor' objects> | 0.040963 | [1, 1, 1] |
| __init__.py/dumps | 0.033529 | [40849, 40849, 40849] |
| scripts/postings_transform.py/canonical | 0.019341 | [40849, 40849, 40849] |
| encoder.py/encode | 0.010835 | [40849, 40849, 40849] |
| ~/<method 'decode' of 'bytes' objects> | 0.008767 | [35666, 35666, 35666] |
| ~/<method 'encode' of 'str' objects> | 0.008617 | [46032, 46032, 46032] |
| encoder.py/__init__ | 0.007750 | [40849, 40849, 40849] |
### synthetic_control instrumented self-time前12项

| 文件/函数 | self中位s | 三轮调用数 |
|---|---:|---|
| scripts/postings_transform.py/read_uvar | 0.009774 | [18436, 18436, 18436] |
| scripts/postings_transform.py/inverse | 0.008300 | [1, 1, 1] |
| ~/<built-in method builtins.len> | 0.003529 | [52764, 52764, 52764] |
| encoder.py/iterencode | 0.002593 | [2, 2, 2] |
| ~/<method 'decompress' of '_lzma.LZMADecompressor' objects> | 0.001957 | [1, 1, 1] |
| decoder.py/raw_decode | 0.001524 | [2, 2, 2] |
| __init__.py/dumps | 0.001058 | [1282, 1282, 1282] |
| scripts/postings_transform.py/canonical | 0.000600 | [1282, 1282, 1282] |
| encoder.py/encode | 0.000347 | [1282, 1282, 1282] |
| ~/<built-in method _json.encode_basestring> | 0.000319 | [1280, 1280, 1280] |
| encoder.py/__init__ | 0.000239 | [1282, 1282, 1282] |
| ~/<method 'encode' of 'str' objects> | 0.000236 | [1538, 1538, 1538] |

表只文件/函数符号、self-time/调用数；全部行在9ON rawJSON。没有原索引token、原文、题目、答案或fullhits。builtin/C函数统计受profiler支持范围影响，不将缺少Python调用当免费CPU。cProfile占比是工具输出，非底层CPU指令采样。

## 冻结、次数和独立审计

runtime/protocol/input freeze `f0825a5c5cce5208f12563c83aea2ada771befb3`，exact CI `40434075005`成功后，唯一3数据×OFF/ON×3轮=18。顺序AB/BA/AB，各轮manifest数据顺序固定，A OFF B ON，600s/worker、0retry。输入为v058 round1实际typed/LZMA stored frame，source/frame B/SHA及原child report SHA见docs/index-profile-inputs.json。

独立analyzer核18child/parent SHA和状态、9ON function非负/次数/守恒、9OFF null、18次真实frame无profiler额外decode原bytes、全部runtime/protocol/test/manifest对Git freeze。额外审计wall 8.155354s/CPU 6.453125s/peak RSS 126164992B单列，不当新的正式worker或算法加速试次。

314检查313通过/1Windows权限跳过；新4项包含OFF byte/null、ON调用/守恒、坏frame拒绝及异常关闭、fresh synthetic OFF/ON和原SHA拒绝。未编译新Rust，没有新模型训练或问题评分。原Gear DLL仅既有完整测试/发行功能验证，不是本轮热点原生实现。

## 完整费用与局限

66递归Python+1HTML 426112B，原frame wrapper/transform和新assessment/test/protocol/input逐文件B/SHA见source-resource，assessment合计42498B；18 raw child/parent JSON 81639B，图/analysis/context/package记录另计。9ON记录更多函数行带来输出和内存费用，parent包含处理，不隐去。

三原shared model 15136487B、三旧stored frame 2035442B复用，未新建frame/恢复raw文件，0新编码；既有v058全部frame+restore480473583B仍保留，旧训练/源码/字典/graph/source CAS/快照/句索引负结果等沿历史账本不删除。该诊断不产生存储节省，不因私有模型不发布而视为零成本。

RSS为观测峰值，不等于增量常驻或预算上限；平台/解释器/依赖二进制/pycache未全额归因，源码不是全系统TCO。SSD物理/全系统IO/冷缓存/跨机仍null。3轮是机械/时间重复，真实索引2个不是18个独立科学域。

![观察器成本及带偏置的self份额](index-profile.png)

图实际打开核验，左为ON/OFF观察器开销比（不是优化速度），右为instrumented self份额，0轴/比值/百分比语义明确，全部三数据保留。

## 复现、交付与下一步

```text
python -m scripts.run_index_profile --manifest docs/index-profile-inputs.json --out NEW_PRIVATE_DIRECTORY
python -m scripts.analyze_index_profile --manifest docs/index-profile-inputs.json --out NEW_PRIVATE_DIRECTORY --freeze FROZEN_COMMIT --test-log TEST_LOG
```

需先取得对应输入并核SHA，public repo不含原model/frame；输出exclusive不覆盖。公开代码/冻结协议/raw无原文JSON/图/详实报告/README/release，CI后5实际资产SHA/66+HTML/物理外actualwheel+current native/actualsdist合成ON-OFF及所有旧smoke/finalproof重下载才完整交付。

下一步可将已定位高频规范varint读取迁移为小型批量Rust候选，但必须保留原Python比较、原frame/全部校验，另冻二进制/编译选项与整个DLL/metadata/代码费用，新鲜无profiler配对实测。不能因本轮热点/调用次数就宣布收益。0新科学问题/训练/模型API（旧24已耗尽）；E3净收益失败、E4整体/NLI/生成回答/真实长会话/无限上下文仍未验收。
