# RKV-1 实验路线

依据 2026-10-14 用户确认的对话和三份本地研究报告整理。RKV-1 是项目名，
不是已存在的标准，也不声称全局最优或突破信息论界限。

固定决策：公开科学数据集；本地 CPU；压缩与科学推理共同优化；Python 原型、
经性能分析后迁移 Rust 核心。先交付可运行 E0/E1，后续阶段分别发布版本。

| 阶段 | 内容 | 验收门槛 | v0.64.0 状态 |
|---|---|---|---|
| E0 | Zstd、Brotli、LZMA、Zlib、去重对照 | 固定数据哈希，重复测量体积、时间、RAM、随机读 | 同容器对照；新增十个查询种子、读取器生命周期、打开阶段与配对波动；冷缓存/跨机器未测 |
| E1 | 分块、内容寻址、校验、增量编码复用、解码 | 逐字节恢复；损坏必须失败 | 两个独立家族各三次真实发布；同格式IO消融与冻结v0.8对照；240次正式恢复/92,160次正式范围读取一致。IO收益混合，默认reference/link不变；全量读源/校验保留；归档恢复默认文件同步、198条故障审计，80次正式恢复一致；目录/掉电未测 |
| E2 | 科学 CSV、数值、代码、数学表达式的类型编码 | 完整成本下可重复净收益；精确恢复 | 已补FITS类型分流/区域分块，规则先冻结、再测新float64/32。500次恢复/96,000次范围读一致，新记录0/8联合通过；整体字节重排仍更有依据，默认不切换。新增SAC/DCD领域复测，240次同步恢复/43,520次范围读一致，现有重排2/8同后端联合通过；文本仅作负对照，v0.32代码/数学四通道词法候选0/36净空间通过、不集成；语义候选仍待研究 |
| E3 | 神经预测 + 熵编码 + 精确残差 | 解码确定性；权重、字典、推理成本全部计入 | CPU神经与有界在线候选均可恢复原字节，但对普通codec完整净空间/联合收益未通过；v0.36–39负结果保留，不默认集成 |
| E4 | 语义/图检索、动态记忆、证据回溯、形式化验证 | 科学问答、多跳推理、反例保持与可验证证据收益 | 原文/历史SID/词法和公共批查询可运行；v0.50首次question-only封存dev对照，graph质量/时间联合False，ID覆盖与literal分开；生成回答提升、语义蕴含、多跳与真实长期会话/形式证明未完成 |

按用户选择，已完成本机多轮读取评测，冷缓存/跨机器明确未测。E2 已扩大独立数值
数据和反变换诊断；v0.5 引入独立校验单元并计入索引成本。v0.6 在同归档下完成
Python/Rust 配对，保留全部校验，单列 DLL+元数据 121,747 bytes；归档本身不变。
v0.7 已完成 QASPER 三个原始发布的固定/Gear、独立/共享 CAS 对照；共享对象真实
只存一份，同表示下快照ID与对象字节并集一致。共享 Gear 相对独立 Gear 减少
32.37%逻辑字节，但Python扫描和对象IO成本较高。v0.8剖析冻结v0.7源码，确认Gear
逐字节循环为主要诊断热点；只迁移该循环到Rust，保留同表/递推/切点/全部SHA校验。
本机五轮提交配对与整份库成本见results/v0.8.0。默认仍为Python，不声称原生CAS
解码收益。v0.9完成对象发布/访问消融及Evidence Inference第二个真实版本家族，
所有同表示存储字节一致。bounded/Windows rename没有稳定全面提速，保留显式候选；
不再仅凭减少系统调用推断性能。各家族整份实测库成本124,419 bytes，固定数据范围
与不变整文件背景均披露。v0.9后转入E2数组/数值类型：先固定公开数据及字节真值，
建立普通codec对照，再测类型变换与精确残差的净成本；代码/数学类型随后。
v0.10已实现上述首批数值原型：EEG/ECG原字节、头和注释均保留，全部同v4容器。
同安装归档与专用源模块全额成本分别报告；不把变换payload节省冒充完整收益。
重排有净空间收益，Python XOR有明显反变换成本；随机噪声回退仍有标签与编码开销。
独立归档与CAS未组合测量，不把两者比例叠加。下一步补真实浮点数组、类型/通道
布局与专业科学压缩器对照，再按热点证据决定数值核心原生化。代码/数学类型随后。
E3/E4尚未开始实测；不由精确字节恢复直接推断推理或无限上下文收益。

v0.12补FITS白名单与区域边界布局，两个新增验证输入的全部预定工作点未同时胜过
普通固定与整文件重排。分段归档小幅节省没有覆盖专用源成本，读取也没有全面收益；
保留显式候选，不把复杂度增加视为进步。新增样本仍是同域/同托管项目，后续须扩域。
校对实现同时发现既有归档解包没有逐文件fsync，此前部分说明过强，现行规范已校正。
下一优先项明确并测量恢复持久性语义，之后继续类型候选筛选、代码/数学与按热点原生化。

v0.11已补真实float32/64与专业字节压缩基线，保留FITS头/填充/特殊位模式，不经过
数值转换。专业后端的完整恢复包括首次导入，暖范围读另测；共享一次整个Blosc
发行包的成本情景也与已安装场景分别报告。没有把专业库快于Python循环直接解释为
本项目Rust内核收益，也不以小样本归档节省抵消未分配的部署成本。下一步先根据
本轮同后端消融与读取工作点筛选策略，补类型/布局分流与成本适用范围；只有热点
证据足够时再迁移自有数值内核。冷缓存/跨机器按用户选择继续记未测，E3/E4仍待开展。

v0.20完成基于计数/原记录/CAS解码工作的确定性重放预算；默认用于新库，旧v3
显式启用。已见回归得到修复，但并非所有阶段更快，且大记录/分块增加保留空间。
下一优先项分离QASPER论文检索投影与原始路径/标注变化，再扩独立真实论文修订；
科学问答仍需新API预算和独立任务设计。E3、长期对话、多跳与形式化验证仍未完成。

v0.21已分离QASPER投影与原路径/标注，保留全部精确原文与历史；同源官方发布
固定/Gear计入空间分别省34.63%/39.94%，但当前定位重绑定查询更慢。v4需新读取器，
保留显式候选，默认v3不变。下一优先项减少v4查询定位准备，再补独立真实论文正文
修订；既有三次数据集发布正文相同，不满足该验收。模型预算/长期对话/多跳仍待定。

v0.22已补v4批量核验/命中投影与纯定位免复制，同原封库对照实际v0.21发布模块
及强制复制消融，保留所有校验。官方全体重绑定阶段有读时延/RSS改善，小基础
免复制无额外稳定收益，v4仍显式。下一项转向独立真实论文正文修订，避免继续只
用正文相同的数据集发布代表修订；继续计全部原文、定位、索引和读取成本。

v0.23已接入独立eLife真实正文修订：六篇/三版本，12转换。整篇XML记录每次
因旧新合计>256KiB检查点，无增量索引优势。下一优先项定义细粒度证据来源身份与
精确范围，再验证成本，不能直接放宽预算掩盖粒度问题。原始字节保持，模型仍未
新增调用，E3/多跳/长期对话未开展。

## 从研究报告落到工程

证据层保存原始字节；认知层的摘要、图谱、embedding、神经状态均是辅助表示。
语义检索只负责定位证据，不能由摘要生成原文来冒充恢复。当前全部对象为 EXACT，
不启用有损层，不按重要性删掉原始数据。

后续可融合的思想：固定/内容定义分块、共享字典、类型变换与精确残差、
联想索引、可重建语义缓存、动态重要性和重放。每个方法先写可证伪假设，
做对照和消融，再决定是否进入默认流水线。研究报告对未来模型的描述是候选方向，
不等于本项目已经复现或验证。

## 实验账本

`B_total = encoded_payload + manifest + index + dictionary + model + decoder/runtime allocation`

v3 的兼容统计 payload_bytes 已经包含二进制索引；使用 encoded_payload_bytes 才能
独立加 index，避免重复计费。默认 v2 的 payload 与 encoded payload 相同。

归档压缩实验报告容器总字节，模型、外部字典、语义索引为零；v0.15记忆实验另计非零词法索引和未知远程模型成本。公共运行时和
codec 实现未摊入每个归档，不能将归档体积称为完整部署占用。E2/E3 若引入专属
资源，必须同时报告对象条件码长、资源全额成本与明确对象数量下的摊销成本。

存储恢复率、检索召回率和推理质量分别记录，未运行的指标保持 null。
只有在指定语料上的实验观察才能称为结果；不把测试覆盖率当作普遍无损的数学证明。

## 版本制度

每个可复现里程碑：代码与测试 → 原始结果 JSON → README 总述 →
`docs/releases/vX.Y.Z.md` → Git tag → 通过 CI 后发布 GitHub Release。
不改写已发布 tag，不覆盖旧实验结果。格式更改必须记录兼容性。

v0.13完成恢复文件同步的显式策略与成本对照；80次正式恢复全一致，单文件科学输入
的配对耗时约3倍，130文件合成对照约13.72倍，不能跨设备推广。强杀审计说明发布
边界和残留，不能当作掉电证明。v0.12分段工作量账本另行更正，原延迟/成本及0/8
联合验收计算不变。下一优先项回到E2：扩展科学领域/代码数学候选，先计完整成本、
再决定热点原生化；不由这次可靠性改进推导压缩或推理收益。

v0.14复测现有字节重排在SAC/DCD两个新领域例子中的适用范围，计源最小归档分别
净省26.16%/15.56%，共享一次专用源合计15.79%。八个新科学工作点2个联合通过，
只涉及DCD/Zlib同后端/块对照，编码仍更慢，不能称全流程或跨codec支配。SAC无
联合通过；源码/TeX/噪声重排全部回退，顶层标签与尝试仍收费。新证据不是新算法。
同v4、同文件同步边界、逐阶段日志和发布重试等待计时；不与历史close批次算加速。
下一轮回到代码/数学的可逆候选及明确工作负载；再按计算热点决定数值原生化。
原始词法/换行/空白/注释必须精确保留，不能由等价表达式重建冒充字节恢复。

## v0.15：先打通证据记忆能力闭环

按用户继续推进首个演示的选择，先实现E4最小基线，E2未视为全部完成，E3仍待研究。
原始证据逐字节保存，索引只用于定位；模型回答单独派生写回，不能自升格为证据。
SciFact 188条gold文档宏平均召回@5 88.34%；12条预定主张两条件共24次真实API调用，
有检索判定正确10/12，空证据4/12。只作小样本基线，不作通用推理或无限上下文结论。
本机CPU负责存储/检索，用户指定DeepSeek API负责远程模型计算。

初始含索引2.325倍原文；保留两快照后4.301倍，未达整个记忆系统净压缩目标。
后续优先扩大独立问题，区分模型弃答/判定、引用选择与检索误差，降低索引重复成本，
再测长会话、语义/图检索与多跳。E3另需确定性预测/熵编码/精确残差及全部权重成本。
历史段落描述各版当时进度；当前状态以上表及本节为准。

## v0.16：记忆索引的空间、查询与更新成本

contentless FTS5定位表去除正文副本，基础索引＋增量重放保留全库BM25；检查点按固定
25%定位变化或8层增量触发。三策略三轮4,275查询、1,764旧快照查询全部匹配原策略。
追加88B并保留两快照时，计源8.44MB对35.69MB净省76.34%；查询配对中位快1.393倍，
但比紧凑完整索引慢、RSS更高。大幅定位改变需完整建检查点，不宣称所有更新恒定成本。
初始计源仍大于原文1.5%，公共运行时未全额分配。E4局部成本改善，不是新模型质量
或E3神经压缩结果。先缩单份索引和定位元数据，扩负载/独立问题，再做长期记忆。

## v0.17：分离CAS重写与定位重放成本

固定/Gear × v2/v3，加已有Rust Gear控制，5条件三轮各11快照。13B插入由127新CAS
对象降至1，索引由5.456MB降至385B差异；8070查询/1815旧快照检查排序与来源一致，
165历史快照整源SHA重读通过。计三份源码和完整实测库后，Gear Rust/v3最终8.78MB
对固定/v2 39.29MB净省77.66%，总提交4.097对6.923s；查询定位重放却更慢。Python
Gear扫描亦更慢。保留成本/提交/查询/RSS各自报告，尚无全流程或全负载支配。
新建库默认固定/v3，Gear可选；下步剖析查询重放并扩真实更新家族。E3/长期记忆/
多跳和更大独立问答仍待验证。正式测量使用冻结旧库，Release保留精确二进制和元数据。

## v0.18：查询内复用和延后定位

复用每次请求已验证的快照/overlay；v3先验证全部位移范围，再只换算命中定位，
完整FTS改写与全库BM25不变。固定/Gear、五阶段三计划三轮，17190正式查询全部
匹配v0.17，22个历史快照整源重读和持久树逐文件SHA不变。短插入固定/Gear配对快
1.543/1.515倍；无跨查询缓存，RSS未全面下降，两份专用源增加3801B一次。
不产生新压缩/提交/模型质量结论，记忆v1-v3/CAS1/归档v1-v6兼容。下步扩真实更新
和更长历史、压基础索引成本；独立问答与长期记忆仍须新实验，E3仍未开展。

## v0.19：真实发布与长历史的负结果边界

QASPER三次dev原始发布各281论文，保留版本文件名；仅投影论文文本，qas标注不
进入FTS。正文相同、原成员变化281/9条，每次完整检查点，两策略最终同为15.40MB。
独立合成2048记录、初始＋100更新，计源/原生后83.43→8.86MB，但42次512变化
恰为25%时查询462.80ms对完整重建2.10ms；43/80因超记录/区间门槛重建后回落。
1800正式/2496历史身份查询一致，606未来探针阴性，624历史快照全源验证；0模型。
当前记录占比策略不能约束读延迟，优先优化检查点成本与投影/来源定位耦合，再扩
论文真正内容修订。QASPER新来源类型需v0.19，旧文本/SciFact和物理格式保持兼容。

## v0.24：片段身份先行，暂不接入默认

两种片段键规则1854范围审计通过，但927投影单元均无id；v4乐观下界仅1/12修订可过，
完整父校验0/12。见results/v0.24.0/SUMMARY.md。位置键级联/版本路径重绑定与CAS读放大
优先于局部解码：下一轮独立测内容锚定键/重复段落，仍保留原预算，不把预检作实际索引收益。

## v0.25：内容键仍不足，暂缓片段集成

新增显式content锚，固定/Gear的v4乐观可过3/12、2/12，对位置1/12；完整父校验仍0。
新增SHA键和重复身份成本全计，已有API与真实v0.24发行包36描述一致。报告
results/v0.25.0/SUMMARY.md。暂缓片段Memory新格式/局部解码；下一轮扩大离线科学
检索任务与上下文覆盖评测，不在这六篇调预算或追加键规则追求正结果。

## v0.26：扩大离线科学任务，召回与上下文损失分离

固定281篇/1005实例，948种问题文本，比旧64新增884种；目标论文@5=44.28%，
24KB完整参考232/927=25.03%，134已召回可映射题受预算遗漏。0模型请求，非官方QA
F1。下一轮冻结问题相关选择器，在相同检索/正文预算下配对，并新增独立数据验证；
不将覆盖提升冒充模型质量。报告results/v0.26.0/SUMMARY.md。

## v0.27：显式段落选择有预算边界

同检索同预算，dev/train 8KB完整参考107→179、176→305；24KB为232→260、445→471，
论文组区间跨零；48KB train570→559。新增排序约4–5ms、有输题及非单调回归。
保留显式候选，默认不换；下一版CLI/API显式选择、本地fixture核验原句绑定/请求
字节和默认兼容，不花新模型预算。报告results/v0.27.0/SUMMARY.md。

## v0.28：显式CLI/API接入，默认不变

支持source-order/lexical及三body预算；HTTP v2显式能力、旧v1默认兼容。13正式
loopback fixture请求、0远程模型，实际POST/原句引用/拒绝路径/旧默认逐字节核验；
195测试通过/1权限跳过。下一轮区分来源已知与开放检索；模型质量需新授权预算。

## v0.29：来源条件分解，优先修复开放检索瓶颈

Memory.lookup显式读取已知来源，原字节/索引校验共享search；不自动接入原回答API。
三轮10794问题对，194292选句绑定；open全分数复现v0.27。24KB lexical下dev/train
open260/471，known764/1728，oracle-if-recalled352/674；分母927/2240。额外来源
信息不算检索器收益。已知来源仍有未映射/预算损失；8KB lexical仍有60/154输题，
24KB dev论文区间跨零，默认不改。下一项冻结不读目标身份的开放检索候选，计辅助
索引、构建/校验/查询成本，不调既有gold参数。报告results/v0.29.0/SUMMARY.md。

## v0.30：开放单元检索收益有限，迁移与成本阻止默认切换

新增显式快照绑定辅助FTS；12进程12873题对，原基线/身份/原句核验全通过。
@5 QASPER dev/train44.28→45.87、39.03→42.00%；SciFact dev/train88.34→81.12、
89.17→82.94%，迁移失败。24KB lexical覆盖dev+24、train+16，train论文区间跨零。
候选空间和查询均增，计入aux后QASPER两库大于原JSON；默认不换、不调gold权重。
下一项固定同规则验证新来源任务、精确成员定位及标注隔离；明确自定义来源检索
不等于官方QA/模型质量，0新增模型调用。报告results/v0.30.0/SUMMARY.md。

## v0.31：新来源迁移无稳健收益，回到E2代码/数学

PubMedQA PQA-L原1000成员/3358 CONTEXTS条目精确支持，问题/答案/预测不投影。
保持v0.30排序规则，@1 957→950、@5 984→986、@20 994→992，MRR下降，候选更贵/
更慢，默认不换。来源定位非官方QA；0新模型调用。v0.24–v0.30物理外部安装范围
补测/更正已追加Release，原tag和实验不变。下一项回到E2代码/数学可逆类型候选，
先计完整控制/字典/源解码器成本、同codec/精确恢复，不再调这些gold检索权重。
报告results/v0.31.0/SUMMARY.md。E3/推理质量/多跳/长期对话未完成。

## v0.32：代码/数学可逆词法候选失败，不追加原生化

六公开源文件/三项目及噪声，三codec/三条件/三轮，189恢复和378文件fsync全一致。
强制分流更大，科学净空间/联合均0/36；auto全部回退plain但CPU/源成本仍收。
保持独立实验帧，不改变主归档/Memory或默认；原生化不能改善同表示的输出B，
不追加DLL费用。下一项机械测试动态证据记忆单writer/多reader快照一致性，明确
非生产并发或模型/长期会话收益。报告results/v0.32.0/SUMMARY.md，E3仍待独立设计。

## v0.33：并发负结果，先修正HEAD共享访问

单writer/四reader、三新目录各计划80更新，默认预算不变。提交80/48/13次成功，
4次reader读HEAD和2次writer替换HEAD PermissionError；0/3门槛通过。
2689查询/10756绑定、144已提交历史复查通过，不能把部分正确解释为并发可用。
下一版做Windows共享删除句柄最小修正、定向测试、同负载复测；不重跑覆盖旧失败。
之后才研究单writer固定提交边界进程中断，不等于断电。报告results/v0.33.0/SUMMARY.md。

## v0.34：修正Windows HEAD读/发布，本机原负载通过

READ/WRITE/DELETE共享读取和POSIX名称替换，其他Memory方法/预算/旧driver不改，
3新目录各80更新、5462查询/21848绑定及243历史复查全部通过，0错误。
不支持API的旧Windows/FS仅兼容原单次os.replace，不保证该降级并发；无权限重试。
不是生产并发、多writer、吞吐或推理收益。v0.33遗漏4子模块源码成本已追加更正，
本版完整393969B。下一项固定提交边界进程中断恢复（非断电），再回到E3小型预测
候选的确定性/完整成本设计。报告results/v0.34.0/SUMMARY.md；模型新预算仍未授权。

## v0.35：固定硬退出边界恢复通过，残留照实收费

原v0.34运行库不改逻辑，7硬退出点+1控制，3轮24新目录全部通过；
192源/位置审计、768绑定、72历史SID复查。每case单次恢复e1和未来e2更新，旧资料保持。
发布前HEAD临时文件每轮94B残留，不自动清理，完整树383915B对原stats383821B；
用递归账本计入，原格式/预算不改。不等于断电/任意时刻崩溃/生产或模型收益。
报告results/v0.35.0/SUMMARY.md。下一项回E3确定性小型预测器+熵编码CPU可行性，
先冻结训练验证分离及权重/字典/源/运行库/训练编解码完整成本，不引入新模型API调用。

## v0.36：首个E3机械原型通过，神经候选净成本失败

代码/协议a0c34fb先冻，95292B训练一次后模型SHA于7b865bb先冻，再测固定前缀。
3科学8192B/噪声、4方法3轮，48对恢复/96fsync及三轮帧一致；科学净空间/联合0/9。
神经payload在9/9比较已大于普通codec，再付每帧4878B权重及专用源码；不集成/原生化。
训练NumPy52666902B与CPU/RSS独立记账，解码纯整数无NumPy；主Archive/Memory/default不变。
下一项固定unigram+同码器廉价统计诊断，区分条件预测与权重成本，不把已见前缀当新验证。
报告results/v0.36.0/SUMMARY.md；E3净收益、长期对话/多跳/回答质量仍未验收，0新模型API。

## v0.37：廉价统计控制分离了神经预测和权重成本

原模型不变、同训练95292B只构建一次静态频数表。神经3/3科学payload更小，完整B0/3更小；
两模型对普通codec的科学净空间/联合都0/9。噪声sourceB下NN小169B而帧大899B，分配敏感性保留。
60恢复对/120fsync全精确，原48条件帧SHA复现；同前缀诊断不是新独立验证，不改默认或原生化。
报告results/v0.37.0/SUMMARY.md。后续必须新假设/新数据并先冻协议，不能在这些gold上继续调训练参数。

## v0.38：固定CDF独立码长账本通过，压缩收益仍未完成

24原帧身份/8独特条件的L-I仅0.25–1.72位，预定[-1,4]门槛8/8；3合成恢复/2 uniform golden通过。
相对普通codec科学逻辑payload差距至少10892位；没有新增科学编码/恢复，不是新压缩验证。
233测试232通过/1跳过，原运行库与模型不改逻辑，只有发行版本标识变更。报告results/v0.38.0/SUMMARY.md。
下一项冻结不依赖外置训练权重的有界在线统计候选及新留出输入，完整计状态/CPU/源码，
先保证确定性和字节恢复，再判断净收益；不调旧gold、0新模型API。长期对话/多跳/无限上下文未验收。

## v0.39：有界在线统计新段验证，状态和CPU不免费

冻结候选/CI后另冻新固定段SHA，75对/150新codec阶段/150fsync全精确，25条件三轮SHA一致。
order0/order1科学净B分别0/9、0/9，联合0/9、0/9；不隐藏132612B一阶逻辑状态和全部CPU/RSS。
旧模块除版本字面量不变，独立实验帧不改默认；报告results/v0.39.0/SUMMARY.md。新段不等于新项目，
0模型API。下一项须读完整结果后另冻假设，不调已见区段；推理/长期会话/无限上下文未验收。

## v0.40：E4显式路径机械通过，资源协议有缺项

288主问题=279完成+9预期缺证/循环，12控制/6篡改负审计、855绑定及39完整历史源通过。
known-root/指定SID/合成语法仅为证据基础设施，非真实多跳或回答收益；每轮memory1171964B。
父测完整process wall漏记，资源记录false、整份协议未全满足；物理IO/解压B原定null。
下一项独立协议补父测进程时间/CAS块工作量，已见fixture复测不当新科学验证，不调入证预算。
报告results/v0.40.0/SUMMARY.md；0模型请求，E3净收益与E4整体/长期会话/无限上下文未验收。

## v0.41：新批次父测完整时间与CAS应用放大通过核验

6 fresh worker、600 proof与v0.40一致，576/24/12/1710合同通过，6parent sidecar有完整计时/SHA。
ON入证156426B，对应应用CAS返回2444100B（15.62×）和解码56426496B（360.72×）；非SSD/全系统IO。
observer开销和全部memory/sidecar/源码计账，原v0.40漏项不回填。报告results/v0.41.0/SUMMARY.md。
下一项先冻单trace内有界已验证块复用，保持原证据合同，新增RAM/源码/CPU不能免费，默认不改。
0新模型调用；已见合成fixture的计量修复不等于真实推理验证，E3净收益/E4整体未验收。

## v0.42：有界单trace缓存完整factorial

12worker/1200proof/3420绑定和文件一致，工作量门槛True、无仪表时间联合True，原值/RAM/源码/sidecar收费。已见同块有利fixture非真实推理验证，不改默认。下一项先冻跨块负控制，不调cap。报告results/v0.42.0/SUMMARY.md。

## v0.43：同原记录跨文件布局控制

24worker/2400proof/6840绑定/624历史文件与6组完整树通过。clustered工作量/时间True/False，separated True/False；固定cap不调，全部负方向/CPU/文件/RAM收费，非真实推理验证。报告results/v0.43.0/SUMMARY.md。下一步须另冻假设，不默认集成。

## v0.44：原CAS工作量调用角色归因

6worker/600proof/1710绑定/156源/12795event与v043原值一致且守恒，80%归因假设门槛True。重仪表只计诊断成本，没有优化/提速验证。下一项另冻请求内验证/视图复用及安全/RAM合同。报告results/v0.44.0/SUMMARY.md。

## v0.45：固定SID单trace已验证视图候选

24worker/2400proof/6840绑定/624源与旧v043一致。机制联合True，两布局时间联合True/True，分散decoded少61.49%；新请求重验/每selected原record SHA保持，但不承诺每hop重验所有未选中源。RAM/源码和完整费用计账，默认不集成，非真实推理收益。报告results/v0.45.0/SUMMARY.md；下一项先冻独立安全/负载转移，不调旧参数。

## v0.46：既有SciFact指定三key批查询迁移

24worker/768bundle/2304绑定/24全源恢复通过，无原文公共JSON及全树一致。两负载base-only CAS计数相等，时间联合True/True，全部费用与负方向见results/v0.46.0/SUMMARY.md。旧QueryView不改，默认不集成，非未知数据/科学问答或长期收益；下一项另冻假设，不改本次selector追正。

## v0.47：可选公共固定SID批查询接口

Memory.lookup_many最多32显式key、原record入证预算不等于I/O/RAM上限。126case=66返回/60预期预算拒绝、666绑定/36历史源恢复通过；65递归Python+HTML和全部成本计账。仅合成机械验收，performance_gain_gate=null，不外推旧科学速度；默认lookup/CLI/UI不改。报告results/v0.47.0/SUMMARY.md，E3净收益/E4整体/真实长会话未验收，下一项须另冻假设。

## v0.48：公共批查询固定size成本范围

36worker/1152bundle/13824原record绑定/36全源恢复通过，1/3/32时间联合1key: False / 3key: True / 32key: True，CAS全部计数相等无字节收益，全部负方向/费用保留。原公共API不改、默认不切换，既有科学数据和3key不称新独立科学验证。报告results/v0.48.0/SUMMARY.md；下一优先项另冻未知问题证据定位/检索假设，无新模型API，E4整体/真实长会话未验收。

## v0.49：训练标注原始来源就绪诊断

3worker/16533实际成员绑定/3全源恢复通过；单轮253未解、3369 UUID改写保留，严格全可解/全literal均False，不能当语义等价或检索收益。开发集未解析、图/模型训练0，报告results/v0.49.0/SUMMARY.md；后续冻结train-only检索/图方法与modelSHA后再揭dev，不补gold进原source。

## v0.50：封存开发集question-only来源定位

一次train/modelSHA冻结后揭dev，3方法9worker，质量门槛True，时间门槛False，质量与时间联合False；187原行/评分187/排除0重叠。固定12/4096、ID与literal口径分开、未解/改写负分母保留，原证/9全源恢复通过。报告results/v0.50.0/SUMMARY.md；不当NLI/生成回答/真实长会话，不能在此dev调参追正，E3净收益/E4整体仍待验收。

## v0.51：原模型封存官方test复现

旧model/candidate逐字不变/新训练0，340原行/评分339/排除1，固定9worker与12/4096；源ID质量True / 时间True / 联合True。ID/literal分开、逐题负方向和完整旧模型/训练成本保留，报告results/v0.51.0/SUMMARY.md。后续先另冻失败来源诊断，不在此test调参追正；E4整体/真实长会话未验收。

## v0.52：已见漏证账本和诊断上界

1578旧题方法记录/6204源ID组分类与DP oracle核验通过，前12字节排除占多数假设False。oracle知道gold不是可部署成绩，新增science/训练/原source-range绑定均0，不用诊断改旧分数；报告results/v0.52.0/SUMMARY.md。下一项另冻独立数据/候选，不在旧test调预算追正，E4整体/回答质量未验收。

## v0.53：已见SciFact论文来源迁移

固定方法/12篇/4096原整行B，新训练一次，300原行/298检索/188有gold/110无gold/2重叠排除，9worker。论文来源质量True / 时间False / 联合False，graph多1篇gold/完整仍139题，不能称稳健领域迁移或回答收益。全部成本、负门槛、原paper绑定/恢复保留，报告results/v0.53.0/SUMMARY.md。后续先做可调用且严格原证校验的实验接口或另冻诊断，不能调此dev预算追正；E4整体仍未验收。

## v0.54：已见SciFact入证拒绝/图暴露诊断

3诊断worker，894记录/627组，新科学试次/训练/原source绑定0。H1 byte拒绝≥半数漏证=True、H2≥半数有gold主张seed触图=False；不是干预收益。原v053仅多1篇gold、完整139/188、联合失败不变。完整成本/实际扫描而非first12口径在results/v0.54.0/SUMMARY.md；E4整体未验收，后续另冻实验API或新假设。

## v0.55：显式SID/modelSHA的实验论文证据API

新增wheel内PaperRetriever，默认Memory/CLI/UI不改，原BM25/图/12篇4096B；3worker894已见proof机制调用全部一致，2559正式+2559独立审计绑定/完整恢复，非新科学质量或速度收益。285检查284pass/1skip，66runtime+HTML 426112B，原模型及训练/全部文件成本保留。报告results/v0.55.0/SUMMARY.md；E4整体/生成回答/真实长期会话未完成。

## v0.56：原整论文gold-aware容量诊断

唯一1诊断worker/188gold主张/209组，贪心/独立DP同值，H1=False(9/49)、H2=False(4/62)。上界完整179/188非部署成绩，0新科学试次/训练/原source绑定。报告results/v0.56.0/SUMMARY.md，后续另冻新检索/证据单位候选，原E3及v053联合失败不改。

## v0.57：最佳abstract句匹配重排原整论文

9worker，原12篇/4096整recordB不变、新索引一次构造另冻SHA；来源质量False / 时间False / 联合False。完整109/188/macro 0.588209，新index 35012961B及全部CPU/RAM/逐题退步保留。只是已见开发数据探索，不称泛化/回答/净压缩收益，研究方法不默认集成。报告results/v0.57.0/SUMMARY.md。

## v0.58：canonical索引postings逐字节可逆格式

2原index+人工随机结构控制，72worker/72恢复+72实际frame审计通过，typed/zstd预定完整空间/加载/联合均False。完整矩阵typed/LZMA空间净少60122B/527350B，但恢复明显慢，不能当推理或总收益。新frame实验脚本/CLI不默认SDK集成，原source/model/质量不改；报告results/v0.58.0/SUMMARY.md，后续先profile再另冻优化/可选加载方案，完整源码/二进制费用继续计。

## v0.59：加载观察器成本与规范varint调用诊断

H1观察器开销≤10%：False；H2 instrumented inverse+varint self-time占比每轮≥50%：False。原3typed/LZMA frame18 OFF/ON worker逐字节通过、9ON调用/时间守恒与9OFF null、追加18实际解码审计；工具偏置不能当未剖析CPU份额/原生收益。原v058主联合失败保留，下一版另冻小型Rust批量候选与完整二进制费用再测。详见results/v0.59.0/SUMMARY.md。

## v0.60：原frame同表示Rust批量u64读取

H1相对typed Python加载时间：True；H2相对plain完整空间/加载联合：False。原LZMA frame不重编码，27无profiler worker原byte/model和追加27Python/9native audit通过，完整DLL/metadata/Python+Rust/Cargo费用计入；被测CI binary SHA与当前发行binary功能proof分开。保持v058/v059负结果，不由内核时间推断问答/无限上下文。详见results/v0.60.0/SUMMARY.md。

## v0.61候选实验（发行核验待办）

来源质量True / 时间False / 联合False。一次train另冻sidecarSHA、9worker/独立排名和来源audit，known-dev单域，原12/4096未改；详细报告results/v0.61.0/SUMMARY.md。尚未完整发布，不能称E4/回答/无限上下文完成。

补记v0.61 actual发行收尾：ReleaseCI40446749549、7base实际下载SHA/全源码/物理外wheel与currentnative及新旧sdist功能/第8proof重下载通过，proof SHA e94f7a210f551e41f58bc24e54e284342d26e566e6f87194985467a59a8a55d5。原tag前报告状态不覆写，实际发行proof为完成证据。

## v0.62：既有增益与训练问题字面相似度

H1至少一半正增益在近似训练问题组：False；H2非近似组仍有来源质量提升：True。固定4/5、1诊断worker/298问题/188annotated/110null，独立integerJaccard/2682已有proof与exactdelta守恒；非semantic leakage或泛化证明，原v061时间/联合失败保持。详见results/v0.62.0/SUMMARY.md。

## v0.63：源SciFact关联无重训迁移目标EntB

来源ID质量False / literal质量False / 时间False / 全联合False。既有3model输入SHA不改，9worker/独立ref/source/gold/oldbaselineaudit，ID/literal反例与完整加载/历史成本保留；已见目标非未知科学验证。详见results/v0.63.0/SUMMARY.md。

## v0.64：实际原source上的弱词面关系分类

H1关系分类质量False / H2局部CPU与model可行性True / 本probe联合False。1训练campaign3fit+多数类，4modelSHA后12worker，明确gold/unknown/missing/conditional与allgold分母分开、独立source/oldproof/feature/logit/成本audit；科学verified仍False，不称可靠NLI或回答/E4完成。详见results/v0.64.0/SUMMARY.md。

## v0.65：显式规则证明与旧词袋方向反例

72主/3预算/6篡改机制通过；64owned方向预测旧4model各8/16，不是新科学验证。显式axioms/SID/逐record证书和独立有限闭包不等于自然语言抽取或科学真理，0新训练/API。E3净收益/E4整体/回答/无限上下文未完成。详见results/v0.65.0/SUMMARY.md。

## v0.66：有限规则变形与独立原证机制

1296主/972一致性/36跨源拒绝/48历史恢复通过；人工3constant/3predicate有限域，不是科学NLI或自然语言解析证明。旧signedengine/checker不改，0新训练/API。E3净收益/E4整体/回答/无限上下文未完成，详见results/v0.66.0/SUMMARY.md。

## v0.67：eligible来源集合字节覆盖边界

36case/12完整/24incomplete/12history/10无效完整proof拒绝。只做StageA字节覆盖，sourcegrammar/logic/science flagsFalse，跨文件推导和自然语言NLI未实现，0新训练/API。E3净收益/E4整体/回答/无限上下文未完成，详见results/v0.67.0/SUMMARY.md。

## v0.68：多来源显式规则原fileDAG

216case/36fullclosure/144sourceincomplete/36workincomplete/72history/12tamper/7恢复通过，原tuple与独立closure，不代表NL或科学真理，0新训练/API。E3净收益/E4整体/回答/无限上下文未完成，详见results/v0.68.0/SUMMARY.md。

## v0.69：官方OWA给定形式representation

固定64theory/allquestion，原JSON→derivedsource独立审计和closure，H1=True/H2=True，不称English/NLI/回答；0新训练/API。E3净收益/E4整体/无限上下文未完，详见results/v0.69.0/SUMMARY.md。

## v0.70：受限controlledEnglish预测与后置reference对齐

固定officialtest64全部题，English唯一预测源，givenrepresentation后置audit，H1=True/H2=True。不称开放NL/科学NLI，0训练/API；E3净收益/E4整体/回答/无限上下文未完成，详见results/v0.70.0/SUMMARY.md。

## v0.71：已见证明可逆共享布局与ordinarycodec

12worker/768root恢复/actualframe独立审计，primaryZstd保守空间H1=False/整process时间H2=False/joint=False；全部source/deps/metadata/旧新残留成本保留，不称新科学NLI/推理收益，详见results/v0.71.0/SUMMARY.md。

## v0.72：冻结grammar在实际NatLang human source上的边界

同32theory规范control与实际sentences分开，H1human=False/H2=False，unsupported全分母、0适配/训练/API，非开放NL/科学NLI。E3净收益/E4整体/回答/无限上下文未完，详见results/v0.72.0/SUMMARY.md。

## v0.73候选：部分选集单调证据，禁止全局结论

78case/36preflight/9oldstrict/30tamper/24history通过，追加78原DAG/63原文件恢复；global_verdict永null，真实全目录先验。427检查426pass1skip，不称NLI/回答/全库完整或性能收益。发行安装/资产核验尚未完成，详见results/v0.73.0/SUMMARY.md。

## v0.74：固定证据的全目录放大诊断

12worker/96query、96actualDAG/14055file恢复，H1True，但4096/9wall214–243x、证书25.84x，H2/H3/jointFalse；CPU零base保留null，observerON非生产速度，完整成本与负结果保留。下一步应分别研究紧凑catalogue绑定与pinned metadata复用，不能混两个改动解释收益。发行核验待完成，详见results/v0.74.0/SUMMARY.md。

## v0.75：原Store依赖的紧凑证书

1152byte/原DAG通过，主Zstd完整列明B H1True（净-42136至-42177B），时间H2False（1.44–1.51x），jointFalse；不是通用压缩或E3/NLI/回答收益。postanalysis完整计时因builtin-zlib收尾失败未知null保留，formal计时齐。发行核验待完成，详见results/v0.75.0/SUMMARY.md。

## v0.76：train-only人类结构模板泛化

一次1681train/1099模板，NatLangtest32/532Q三role全拒答；308新句key命中0，测试实体全在train词表。H1/H2False/H3True/jointFalse，source实际审核/恢复0不冒充prefixSHA恢复，负结果全保留，禁止测试后补规则。更强语义模型资源待用户选择，当前只纯CPU离线元数据实验授权。发行核验待完成，详见results/v0.76.0/SUMMARY.md。

## v0.77：单SID有限批次metadata复用

48worker/384query与384freshDAG/56220file恢复，H1/H2/H3True；primary4096meterOFF批wall约.042、parent约.333、RSS约.765，原sourceB不变。保留初始metadata语义/初始O(N)/tracked cap不等于峰值RAM，未集成默认SDK/不称生产或语义收益。发行核验待完成，详见results/v0.77.0/SUMMARY.md。


## v0.78 候选：显式 SDK 同快照读取作用域

在 v0.77 组件验证后新增 opt-in Store.read_scope，不改默认 snapshot 或磁盘格式。固定 12 worker 做 SDK/旧实验接口逐字节、范围、全验证、证据与生命周期一致性；旧实际 v0.77 wheel 兼容性必须仓库外安装后才记通过。478 本机测试 477 pass/1 skip；无新速度、压缩或语义收益声明。冻结协议见 docs/SDK-READ-SCOPE.md；正式实验尚未执行。

状态更正：v0.73–v0.77 以上历史段落中的“发行核验待完成”或“尚未完成”均已在各版后续实际资产/安装/proof 核验中收尾；最新已完整交付版本为 v0.77.0，各原始实验门槛及负结果不变。


v0.78补充：固定12worker全部正确性/生命周期控制通过，追加192实际fresh原DAG与14055file恢复；actual旧v0.77 wheel仓库外兼容通过，H1/H2/H3/joint=True。新公开SDK显式启用，默认snapshot仍旧路径；原v0.77组件速度不是本版新测。最终发行核验仍待完成。


## v0.79 候选：选中原文件的短成员证明

v0.78已完整发行核验。下一项针对v0.74的全eligible目录通信放大，初始完整可信manifest派生anchor，独立接收端用显式外部可信anchor SHA/SID/path验选中文件成员。不是仅凭SID自认证、逻辑DAG或科学证明；保留同SID伪anchor反例。固定12worker/24成员/96控制/12历史与重绑定控制，primary4096短packet与固定8消息完整索引+新增源码费用分开检验，不能以packet节省代替完整净收益。485检查484pass/1skip，正式尚未执行。协议docs/CATALOG-MEMBERSHIP.md。


v0.79实验补充：固定12worker完成且独立14043叶/14055file恢复通过。H1/H2=True，但完整index+新代码+固定8消息H3=False/joint=False；仅消息小不能代替净收益，不变更复用次数追正。详实报告results/v0.79.0/SUMMARY.md；发行核验待完成。


## v0.80候选：迟到成员请求的RAM/CPU取舍

v0.79全部发行核验已通过，原固定8消息净增340600B负结果不改。新候选同held Scope/初始完整metadata与可信anchor，A保留全树/B每迟到请求重遍历；24worker/8双path/192packet/384成员，RAM与完整算法phase CPU/wall/parent gate分开，不用删除诊断文件声称压缩。必要owned测试已过，全回归/精确CI后才能正式。协议docs/LATE-MEMBERSHIP.md，当前尚未正式或发布。


v0.80实测：24case/192packet384member、fresh24根/28086叶/28110file恢复和96控制通过，H1/H2True，但算法phase5.4–5.6x/CPU6–7x，parent回退，H3/jointFalse。额外状态比.00062255不是RSS，RSS比.938–.946；无生产速度/压缩/NLI收益。报告results/v0.80.0/SUMMARY.md，发行核验待完成。


## v0.81候选：64KiB metadata subtree cache

v080已全部发行核验，其省状态但phase慢5.4–5.6x负结果保持。候选固定完整cache-owned graph操作后上界65536B，provisional/全prover/Scope/RSS另列；36worker ABC/BCA/CAB，同8迟到请求，正确性、C/A常驻RAM和完整phase CPU/wall/parent联合门槛先冻结。不得以删index/只限hash payload隐藏费用。协议docs/BOUNDED-MEMBERSHIP.md；尚未正式/发布。


v081实测补充：36worker和独立fullaudit通过，H1/H2True，主4096 C cache0 hits、73719 hash nodes与9次完整树相同，LRU反复淘汰，phasewall15.9–18.5x/CPU13.3–22x，H3/jointFalse。操作后保守max65272B，provisional70552B另列；额外prover60474B不是全RSS。报告results/v0.81.0/SUMMARY.md，发行核验待完成。


## v0.82候选：v081缓存0命中的只读事后诊断

v081发行资产/外部安装/proof已齐。对原全部12Ccase/96请求192成员冻结原输入SHA，replay要求initial/final trace及全部packet字节保真，观察原cache key是否在使用前被淘汰。observer CPU/RSS独立，不回填旧性能，不测新策略/不称新科学。507检查待通过，freeze/CI后才能唯一replay。协议docs/CACHE-REPLAY.md。

## v0.82.0 · 已见缓存事后诊断

12case/96请求保真；主4096每query初始142相关节点均在查找前丢失，H1/H2通过。独立12根/14043叶/14055file/192成员原bytes通过。没有新策略/科学/提速，旧负结果保持，完整发行待核验。

### v0.82 完整交付确认（2026-10-29）

前述“候选/待完成”记录为冻结时状态。现ReleaseCI 40821635891、7实际资产SHA、全部源码、仓库外actualwheel/currentnative及新旧actualsdist、最终第8份proof重下载全部通过。tag ac5a9f6cc182ba19abaacc78f065bc8c5389877c，proof SHA256 e1cd3c0645a061c7cc6dcb0ed93e308511dc8b56c89380294ef0065cdb691a24；不改旧tag/原测量。

## v0.83实验结果（发行待核验）

固定span>=64四法48worker/384packet768成员192控制、fresh48root56172leaf56220file通过。D主4096每轮80命中/0淘汰/10311hashnode；初末状态45634/45690B、cache max49368B，D/A额外状态约1.90%，RSS约.941–.956。wall仍1.74–2.00x/CPU1.33–2.50x，H3/jointFalse；完整本地/实际发行资产安装proof仍待收尾，不称交付或生产/推理收益。

### v0.83完整交付确认

tag4f3264fd66dbe7a71b350eaf995a904317e133a4、ReleaseCI40829377990、finalproof d67e7b67861a98e2c043a5ee15dd89902e22a2a5fa45fa2d9ae528648f5df0e9，实际7SHA/67Python+HTML/allsource/外actualwheel-currentnative/newspan/alllegacyactualsdist/proof8通过；旧实验不变。

## v0.84候选：API证据干预

用户授权新48call×512out、失败0retry，密钥只用户环境。16已见SciFact题×empty/retrieved/固定环rotated，排除旧API12题和train重复；source/citation/annotation分开核验。当前13owned机制检查通过，真实API调用0；源码协议输入freeze/全CI后才正式，未发布。不把byte绑定当NLI，不把unannotated当无证据证明。

## v0.84实测（完整发行待核验）

唯一48次真实API全部完成、原文与引用独立audit通过：empty4/16、retrieved9/16、rotated4/16；annotated判定+完整rationale为0/12、5/12、0/12，H1/H2True。仅16已见题，p=.125，SUPPORT1/6，5gold论文未取回，2已取回但判定错，不能称科学NLI已解决或普遍收益。新48call已用完，禁止额外付费调用。

### v0.84完整交付确认

tag506dd5e1cc3d15400e30c79707154d8d72ceaa33，proofd6fe01703d81a2cd0033c41b32eed6d17ebbe8631bf6d2a5a654e63b9beb0b7e，actual7SHA/67Python+HTML/allsource/物理外actualwheel-currentnative/newAPI fake和alllegacyactualsdist/proof8齐。旧48调用不再执行。

## v0.85候选：旧API漏检的排名/原记录准入审计

0新API/训练/检索方法；只独立复算原16已见问题的冻结词法排序与12/4096whole-record准入，匹配43旧返回记录和12gold，检验5缺gold论文中原记录自身>4096B是否严格过半。精确一次worker16case，parent/worker/finally/分析全程计时；本版未冻结或正式，不能当新科学验证。

## v0.85实测（发行待核验）

H1原排序/选集/字节与计量通过，H2原单record自身体积>4096B多数命题False（0/5）。5漏选rank2/2/4/7/225，都是当时剩余不足，不应混称结构性超长或纯预算因果。原16case/43selected+12gold、worker与独立analysis各48binding/fullcorpus1均核，0新API。图已实际看，完整发行待收尾。

### v0.85完整交付

tagaca19bfb3598c787ae3a9da941122defde3c592b，原proofbf3479d10dae42fe30ce68f5bca4f4498827878bebcb51629cdc5e114e0fe7f4，actual7SHA/全源码/外actualwheel-currentnative/owned-new/alllegacyactualsdist/proof8通过；随后追加scope人工文案更正资产，现共9asset，原proof/科学结果不变。

## v0.86候选：固定预算的原记录分数密度

三角色旧lexical/精确Fraction score_per_byte/length_only，原12wholepaper4096B不改；primary270问题168annotated/102质量null，排除旧API28题和train重合但仍是已见dev。9freshworkers/2430本机query、0新API/训练，严格先freeze/CI再评分；当前8必要owned通过，真实结果未知，未发布。

## v0.86固定预算来源选择实测（发行待核验）

9worker/2430查询、270已见问题中168annotated和102质量null；独立11244原记录绑定与完整corpus恢复通过。旧词法/分数密度/长度控制宏paperrecall为76.24%/57.86%/1.19%，完整126/95/2题。H1True、H2False、H3False、jointFalse；密度候选完整算法wall4.54–4.74x，0新API/训练。图已实际检查，不继续调此旧集合参数追正；当前只收尾本版实际包/CI/外安装/proof核验。

### v0.86完整交付确认

tag5c91df742af503252e9c874dd961865abf6696f2、ReleaseCI40842671596、finalproof4294d006e7a1f3cdccce7571dcaffa92c0efcd461fcf20b4f57844da02c3fa6d。7份实际资产SHA、67Python+HTML/全部源码、仓库外实际发行wheel/current native及新cost-aware三方法owned与所有旧sdist smoke通过，最终第8份proof重下载通过。原负结果、协议、原始JSON及图保持冻结；本段为核验完成后的主分支状态更新，不移动tag。

## v0.87候选：第二批16题API证据干预复测

用户明确新增授权48次/512out/0retry。新16题以SHA分层6/6/4、排除所有旧API28题及train重合，固定原提示/模型alias/三条件/12篇4096B。新call0；先必要测试、源码/协议/输入SHA与exactCI，再唯一正式。数据仍项目已见dev，不称未知科学泛化。

### v0.87完整交付

tagdcb7be19c281117da844a11ac1bcb3c67b10ef41/ReleaseCI40854945377/finalproofcbb747cc31af15c7d0033abd7bd9beba2cca12b7a9aefdf496567e36d5f56c6d，actual7SHA/67Python+HTML/全部源码/物理外actualwheel-currentnative/newselector+alllegacyactualsdist/proof8通过。

## v0.88候选：两批原96回答的证据可得性与失败定位

0新API/训练/检索，32问题×三条件原输出，主24有标注retrieved，互斥区分缺标注论文/有来源判定错/判定对依据不全/grounded正确；按每批保留多数假设和零分母null。已见事后诊断，先冻代码/协议/输入SHA和exactCI再唯一正式。当前仅准备，无实测结果。

### v0.88实测（发行待核验）

96原输出/32问题/24主有标注retrieved，worker及独立source/citation/audit各89绑定、125625应用B通过；H1True，H2两批True。缺来源5/7及3/5为grounded失败多数；已有来源仍判定错各2，保留。0新API/训练/检索，先前已见结果的定位不称新的科学或因果验证。

### v0.88完整交付确认

tagd07671b6826aa4a0130146914df9aa5e8e5dc853、ReleaseCI40860126424、finalproof48d6ad9965e14e0a98826eb07908d2d3a147fd1128b9fb6a79f2acd954513554。实际7资产SHA/67Python+HTML/全部源码/物理仓库外实际发行wheel-currentnative与96owned响应诊断和所有旧sdist/proof8通过。原科学结果、tag、资产、计时不变；仅更新主分支核验状态。

## v0.89候选：实际检索与标注论文对照的同批干预

用户明确新增批准48次512out/0retry，24有标注原问题×实际检索/annotation-aware整论文控制，重测两条件而不拿新oracle对旧服务回答。固定12/4096不调，oracle不是可部署检索器。新API0；先代码/协议/inputSHA/exactCI冻结再唯一正式，H1全48机械接受，H2oracle在24总分母的判定及依据均严格提高，否则False。

### v0.89原正式轮未完成（发行待核验）

第7预留请求URLError，7attempted/6response/41missing，按协议停止且0重试。H1/H2False，不能从缺失不对称推断检索或oracle效能。原slot/source/响应和原48分母独立审计通过，分析前quota接口暂时失败恢复后仅补未开始的audit，未重发API。剩余41授权名额未使用但本轮已关闭。

### v0.89软件交付确认（科学轮保持未完成）

tag23f7eee03d86b3bdbc4c3724918eeecdc1a513af/ReleaseCI40866699127/finalprooff5480b3889387c13805208082db68be280d332251a98ecc5c95c3ea51eaa5ec2，actual7SHA/67Python+HTML/全部源码/外实际发行安装与paired48owned及alllegacyactualsdist/proof8通过。科学7attempt/6responses/41missing原轮冻结不变，不补发。

## v0.90候选：只读活动检查与report-only恢复

纯离线owned进程硬退出7边界+成功控制各3轮24child、4篡改负控制，0实时HTTP；所有动作model_send_allowedFalse。先冻代码协议和exactCI再跑完整矩阵，测原文件不变/预留不重发/计数一致与完整parent计时；不叫断电或科学推理提升。当前准备，无正式结果。

### v0.90实测（发行待核验）

唯一24child/3round/4tamper正式与独立原bytes/源请求及响应SHA/完整parent计数通过，H1/H2True。总162reserved/156raw/153result/159owned-send marker，inspector/report额外发送0，真实HTTP0。21硬退出childfinally缺失CPU/RSS保持null，非断电或科学质量验证。原v089失败轮保持关闭。

### v0.90完整软件交付确认

tag58411a4d58b2b9850045f464b0bc0cb2889ffb0d、ReleaseCI40874134052、finalproofb64c5bfd6bc17eb54b5b4a76d42d8f44a13c37b0ffaabec5a3646c54fff26b6b，实际7资产SHA/67Python+HTML/全部源码/仓库外实际发行wheel-currentnative/新生命周期owned和全部旧sdist/proof8通过。原实验、tag、资产、计时不改，本段仅更新主分支核验状态。v089科学7/6/41继续关闭，机械通过不当推理收益。

## v0.91候选：固定静态源HEAD的访问路径观测

用户在新实际窗口1793298289明确继续。一个fresh worker、system/direct三轮固定6次HEAD/15s/0retry，仅https://api.deepseek.com/根路径、无密钥/认证/正文/redirect/模型调用；H1请求与原计时/隐私字段守恒，H2direct少于system非HTTP响应失败仅描述当前小样本。不能回溯解释v089或保证生成服务。先freeze/exactCI再正式。

### v0.91实测（发行待核验）

固定6HEAD/3对无认证根路径，system/direct各3/3观测401HTTP、0非响应错误，H1True/H2False，0模型调用。过去v089原因、认证有效、模型生成可用性均未证明；不把相近小样本墙钟当可靠提速。独立metadata/计数/原始时钟audit通过，图已实际看。

### v0.91完整软件交付确认

tag80d8179a2328bea5bc5be105b24a1aa40fb21f61、ReleaseCI40885089220、finalproof36cca54492ad8bc01a255da2ae3a20120dd4f873f92601a98c9f9bf7d95b4f6f，实际7资产SHA/67Python+HTML/全部源码/仓库外实际发行wheel-currentnative/新6FAKE HEAD及全部旧sdist/proof8通过。仅更新主分支交付状态，原协议、6次观测、源码、tag、资产和计时不变；401不表示认证成功或生成可用，也不解释v089旧失败。

## v0.92候选：精确句子token与原Store来源绑定

固定18fresh ownedStore worker，3/17/65记录×两编码×三轮，510record/1020选中token/108拒绝/18旧SID。原SID/path/fullfileSHA/recordrangeSHA/显式abstract或sentences与独立原JSONL行边界/byte-token参考核验，原完整record读取、UTF8offsetmap/metadata/hexpacket成本计费。H1完整机械保真，H2六primary完整packet<=原record；不叫净压缩/检索/推理收益。无科学数据/gold/模型/API；先冻结协议输入源码与exactCI再正式。11必要owned检查已通过，正式0。详见docs/SOURCE-SPANS.md。

### v0.92实测（发行待核验）

18freshworker/510record/1020token/108控制/18旧SID均通过独立原JSONL边界/byte-token/完整source与packetSHA/全文件不变audit，H1True；主65record完整packet/record为5.402235和4.948228，三轮完全一致，H2False。包含完整定位信息与hex开销，不以选中token小替代整个packet净收益。0科学数据/模型/API/HEAD，所有18parent/child与独立audit完整时钟保留；图已实际看。正式和audit不重跑，下一步完整local/CI/实际资产安装proof。

### v0.92完整软件交付确认

tage28fbcd145a4f04e6ceaca5dd3b58663e6dacc4f、ReleaseCI40900556305、finalproof684ebfea5651372d73dd68d0c7ed8db5ecdc5a3c93866932d349371f4015c6b3，实际7资产SHA/67Python+HTML/全部源码/仓库外实际发行wheel-currentnative/新source-span owned与全部旧sdist/proof8通过。本段仅更新主分支交付状态，原协议/18case/510record/1020token/108控制/计时/source/tag/资产不改；完整packet放大4.95–5.40倍的H2False保持，不当净压缩或语义收益。

## v0.93候选：当前实验发行包与历史结果分离

完整runtime/HTML/scripts/tests/fixtures/docs/Rust保留；sdist只含当前结果，历史仍在原Git/tag/Release，旧分析需对应历史目录。冻结后唯一build和独立完整成员/SHA/历史树不变audit，H2压缩文件<=旧实际asset10%，这是改变发行内容，不是科学压缩或推理收益。现有证据视图5项private准备暂不公共采用；本版先消除164MB重复历史传输瓶颈。正式0，详见SCOPED-SDIST.md。

### v0.93正式构建与独立审计（发行待核验）

1次冻结构建1401293B，对旧actual164035251B约0.854%；711必要源/currentseed文件、719实际成员与92历史目录Git树不变通过独立参考，H1/H2True。改变发行内容，不是科学压缩/速度收益。5个旧checkout文本行尾差异明确记录，formal本地raw与实际CI Git字节各自核验，不隐藏SHA差异；所有旧结果/成本留存。图已实际看，完整local/actual发行源范围/外安装/proof尚待。
