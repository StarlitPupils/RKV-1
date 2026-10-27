# v0.60.0 实验报告：既有typed/LZMA frame的Rust批量规范varint读取

## 结论与归因边界

**H1相对typed Python加载时间：True；H2相对plain完整空间/加载联合：False**。27 fresh worker全部原byte/model一致，独立追加27次原Python actual frame decode及9次实际native decode通过。所有A/B/C都用v058原actual frame，未重编码/量化/删字段/训练，原header、规范uvarint、长度/三SHA/重建JSONsize/UTF8/TF/doc范围/EOF均保留。

A plain/Python/LZMA，B typed/Python/LZMA，C typed/native/LZMA。H1仅C/B，是同一种typed表示下的实现时间；H2 C/A须两个真实索引完整活动路径空间及ready wall/CPU/parent都过，不能用内核变快代替完整路径通过。C与B frame逐字节相同，Rust自身字节收益为0；C/A体积差来自旧typed布局，须再扣全部native费用，不能称Rust发明了新压缩收益。

同typed表示下，EntailmentBank ready wall比0.924075（少7.59%）、SciFact 0.761005（少23.90%）；但相对plain仍3.244992倍/3.758885倍，不能称完整方案已更快。C/A完整净空间少38981B/506209B，人工控制反而多17987B，所有方向保留。

原EntailmentBank/SciFact模型和LZMA空间点已见，属于工程实现探索，不是独立未知科学验证。v058原主typed/Zstd联合False不因改看LZMA而改写，v059观察器1.48x/1.93x开销及H2负结果保留；本版完全无profiler，不拿profile份额当未剖析CPU或本轮速度预测。

## 完整活动路径空间与费用

| 数据 | 模式 | 原actual frame B | 额外专用源码/二进制/metadata B | frame+实际恢复JSON+整库/源码完整B |
|---|---|---:|---:|---:|
| entailmentbank | plain | 930794 | 0 | 5990770 |
| entailmentbank | typed | 864534 | 6138 | 5930648 |
| entailmentbank | native | 864534 | 27279 | 5951789 |
| scifact | plain | 1657218 | 0 | 12240358 |
| scifact | typed | 1123730 | 6138 | 11713008 |
| scifact | native | 1123730 | 27279 | 11734149 |
| synthetic_control | plain | 56470 | 0 | 840765 |
| synthetic_control | typed | 47178 | 6138 | 837611 |
| synthetic_control | native | 47178 | 27279 | 858752 |

共同全部66递归Python+1HTML 426112B，共同frame wrapper 4196B；B/C收费整个旧typed transform 6138B。C另加完整native Python/Rust src/Cargo 10686B、整个被测DLL 9728B和完整native metadata 727B，共native premium **21141B**。不只算导出函数或压缩后DLL，不把已放在电脑里当免费。

完整B中的恢复JSON是v058已经真实写盘并本轮逐字节复核的文件，不是虚构未来删除后的费用。默认PaperRetriever仍需原JSON路径，新CLI可显式解包；尚无透明压缩SDK加载整合。本轮无新frame/恢复副本编码写盘，但既有原模型与历史artifact不删除。所有old frame/restore480473583B继续保留；本轮选中6组frame/restored是其中子集，不与旧全campaign重复相加冒充新数据。

| 数据 | C完整B-A完整B | C/A空间胜 | C/A空间加载联合 |
|---|---:|---|---|
| entailmentbank | -38981 | True | False |
| scifact | -506209 | True | False |
| synthetic_control | 17987 | False | False |

上述完整性范围是实际活动artifact、整个RKV源码/HTML和专用源码/被测DLL/metadata，不是全系统TCO。CI编译CPU未提供，保持null；工具链/平台/解释器/依赖二进制/pycache未全额归因，不声称包含编译或所有基础设施的端到端成本已通过。

## 无profiler的加载时间与资源

| 数据 | 模式 | ready wall中位s | ready CPU中位s | parent全wall中位s | 观察peak RSS三轮最大B |
|---|---|---:|---:|---:|---:|
| entailmentbank | plain | 0.067639 | 0.062500 | 0.219647 | 59297792 |
| entailmentbank | typed | 0.236983 | 0.234375 | 0.387330 | 62148608 |
| entailmentbank | native | 0.218990 | 0.203125 | 0.370123 | 62529536 |
| scifact | plain | 0.148199 | 0.140625 | 0.361948 | 98410496 |
| scifact | typed | 0.737686 | 0.734375 | 0.947800 | 95711232 |
| scifact | native | 0.562322 | 0.562500 | 0.775374 | 96899072 |
| synthetic_control | plain | 0.004318 | 0.000000 | 0.103780 | 29409280 |
| synthetic_control | typed | 0.016990 | 0.015625 | 0.117312 | 29782016 |
| synthetic_control | native | 0.014001 | 0.000000 | 0.114705 | 29605888 |

ready为decode(frame)+json.loads成旧consumer同对象。C同时包含native模块导入、读取/核DLL SHA、CDLL/ABI验证、Python caller u64buffer分配和每posting list批量FFI；未将库初始化放到计时外。固定全新进程/顺序，仍为本机OS cache条件，不能称真正冷缓存。

原source/frame读取与SHA在ready前、完整原bytes/canonical/model/实际恢复文件和source/frame未变复核在ready后，都在worker/parent内。C还在ready后核DLL未变。parent从启动至退出完整wall，不能只把小内核循环当应用端耗时。每轮原指标与配对比见27child/parent JSON；CPU零分母保留null并失败，不补轮或epsilon。

| 数据 | C相对baseline | ready wall配对中位比 | CPU比 | parent比 | 时间门槛≤1 |
|---|---|---:|---:|---:|---|
| entailmentbank | typed | 0.9240746901700715 | 0.8666666666666667 | 0.955415148360466 | True |
| entailmentbank | plain | 3.244991889973785 | 3.25 | 1.6814077158679632 | False |
| scifact | typed | 0.7610051816143389 | 0.7659574468085106 | 0.8153830994643889 | True |
| scifact | plain | 3.7588850953001303 | 4.0 | 2.1291957365752605 | False |
| synthetic_control | typed | 0.8117823106015838 | 0.0 | 0.9777730235685187 | True |
| synthetic_control | plain | 3.2433126236166263 | None | 1.1052698010224113 | False |

H1两个真实索引C/B三指标均≤1才True；H2两个真实索引C/A同时间标准并严格完整空间胜才True。人工控制完整保留，3轮是同数据的机械/时间重复，不当27独立科学域。未运行检索问题、NLI、答案或真实长期会话。

## 实现与内存

唯一迁移段是posting doc-delta/TF规范u64读取。旧Python每pair两次read_uvar改为每list一次Rust batch，Python仍循环构造原postings、TF/doc正值和范围/原JSONsize预算验证；metadata及token varint仍由原Python读取。原scripts/index_frame.py和postings_transform.py逐字节同v058，独立auditor按Git核对，默认SDK/Memory/UI/主归档不改。

独立no_std cdylib零第三方crate、Rust内部不分配，release opt3/lto/codegen1/panicabort/strip固定在看正式结果前。C ABI1输入/输出为caller valid不重叠缓冲区、count/cap/长度；null/对齐/count边界、每byte有界、最多10byte/u64、溢出/截断/非最小表示拒绝。出错partial输出必须忽略。Python只接受显式path/SHA/ABI1，不静默fallback或读取默认隐含模型服务。

Rust无分配不等于零RAM。Python持payload、metadata/词表/新posting与旧/新JSON对象及caller输出buffer；增长时旧values引用可与新buffer短暂并存。由已验证最大posting长度推得精确最大owned u64payload和保守双buffer瞬态上界如下，allocator/object/codec内存另计在RSS观察中，不声称精确总峰值：

| 数据 | 最大单owned u64payload B | 增长瞬态payload保守上界B |
|---|---:|---:|
| entailmentbank | 40912 | 81824 |
| scifact | 55024 | 110048 |
| synthetic_control | 128 | 256 |

64/65MiB输入cap和2m值batch cap不等于总RSS cap。观察RSS不是纯增量或常驻精确RAM，FFI释放GIL不代表已验证并发安全/吞吐。SSD物理/全系统IO/冷缓存/跨机均未测。

## 冻结顺序、实际二进制与检查

v059全部实际资产/外部安装/finalproof完成后采用。source/protocol/input freeze `34726ce87e424e324d6e04b4d8884ad6985bcb42`，exact candidateCI `40435920805`成功后，只下载该Windows CI artifact一次，核其official digest（若API提供）、ZIP实际SHA、source commit/ABI/features/whole DLL SHA；先本机actual full320再单独commit二进制身份 `e8c19db41d87a7b981f6ca51cf7ea30968ca3c86`，最后唯一正式27worker。被测DLL SHA **e128f5510a287f3dc29f76e65e0c6e8331d7689820dc5c0a4f3888f89d138553**，编译器 `rustc 1.99.1 (58cf8f9c3 2026-10-13)`；actual measured artifact ZIP SHA `a35387607f7934c5acc4824b60daa409622bb4a1feb0a30668a3479ffcb2b3d8`。

首次实际Actions artifact GET用了错误Accept而HTTP415，失败日志B/SHA及恢复说明在transport-recovery.json；按[GitHub官方artifact API](https://docs.github.com/en/rest/actions/artifacts#download-an-artifact)改为标准JSON Accept后下载同一个CI artifact，原code/CI/DLL未重编，首次失败前正式worker为0，未重跑或覆盖实验。

本机未装新Rust工具链，编译发生于exact CI；初始320检查315pass/5skip明确其中4native未执行。CI Win/Linux各4Rust+6Python native全部通过，取actual Windows DLL后本机完整320检查319pass/1Windows权限skip。新增golden含u64max与2000固定seed随机数、prefix/trailing消费边界/输出复用、截断/非最小/溢出、null/对齐/count/cap/sentinel、4codec+空/Unicode/opaque metadata、plain拒绝、三SHA/重建size拒绝、显式SHA/ABI选择、CLI不覆盖输出；不是只测happy path。

3数据×3模式×3轮=27，ABC/BCA/CAB固定，600s/worker、0retry/重编/改level/换source。actual source/frame/restored SHA/size/旧report SHA在docs/native-postings-inputs.json。独立audit核全部27child/parent、3data对象/原bytes/保留恢复文件、actualDLL/metadata和source/tag，额外27Python+9native实际decode。追加审计wall 10.576025s、CPU 8.687500s、peak RSS 135856128B独立记账。

current Release CI按最终tag重建的Win/Linux native可能SHA不同；**当前发行binary只获功能核验，不继承被测binary的时间**。actual measured Windows ZIP另作为Release asset发布并重下载核SHA，外部安装后同时functional测current与measured，两者scope分开。此区别不是跨机器复测；性能仅本机actual指定DLL和两个已见索引。

## 产物、复现与下一步

27 raw child/parent JSON 32106B，三shared原JSON 15136487B；选择的旧frame/restore真实B 34952898B为v058480MB子集。源码/HTML、Rust/Cargo和assessment/test/protocol/input逐文件B/SHA见source-resource，原训练/字典/graph/科学CAS/旧快照/句索引失败/观察器记录继续保留。private原文/model/frame/恢复不随发布。

```text
python -m scripts.native_postings MODEL.rkvpost recovered.json --library DLL_PATH --library-sha256 EXACT_SHA
python -m scripts.run_native_postings --manifest docs/native-postings-inputs.json --binary-manifest docs/native-postings-binary.json --out NEW_PRIVATE_DIRECTORY
```

新CLI限长read/exclusive输出/fsync，不覆盖已有。formal复现需取得原model/frame并核固定SHA，public不分发真实科学索引。操作原byte/model正确，不意味着证据蕴含或生成回答提升。

![同frame空间、加载与原生配对](native-postings.png)

图实际打开核验、0轴/三data和整DLL费用，不以截断轴夸大收益。代码/冻结协议/rawJSON/标准图/本详实报告/README/release，CI后8实际base资产SHA（原5+2current postings+actual measured ZIP）、递归66+HTML/新Rust和scripts、物理仓库外actualwheel+currentGear+currentpostings+measuredpostings/实际sdist新native与全部旧smoke、最终第9proof重下载后完整交付。

下一步只按H1/H2与完整成本结论决定停止该内核或实现显式可选SDK加载；不能重复调已见数据/预算追正结果。0新编码/训练/科学问题/模型API（旧24耗尽），E3净收益失败/E4整体/NLI/回答/真实长会话/无限上下文未完成。
