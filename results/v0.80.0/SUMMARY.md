# v0.80.0 实验报告：迟到成员请求的 RAM/CPU 取舍

## 预定门槛结果

H1原bytes、全部exactpacket、96控制、时间线和费用记录 **True**；H2主4096额外常驻状态初始/最终<=原完整树一半 **True**；H3主4096完整算法phase wall/CPU和整个parent wall均不回退 **False**；联合 **False**。固定24freshworker/192packet/384成员、96负控制，另24fresh根、28086叶metadata、28110所有原文件恢复和384原bytes成员通过，无正式重跑或选最佳轮。

本版研究保留全树与收到path后重算的已见owned机制。RAM状态下降不代表端到端速度/总RAM/生产压缩改善。v079固定8metadata计入完整index后的净增340600B不回填；本版没有靠删diagnostic index.json宣称新算法或磁盘净收益，也未新增科学NLI/自然语言/逻辑DAG/回答任务。

## 冻结和相同工作量

496检查495pass/1权限skip，freeze `3cb3269f8a89cb6234c3e5dee99318ed75e4c790`，exactCI `40810650479`成功后唯一执行。9/64/512/4096×3轮×A/B=24。Roleorders AB/BA/AB，固定8迟到双path请求，600秒/0retry。先source/Store/完整Scope初始化，再A完整Catalogue或B无path初始anchor_only全扫描；A/B同SID/Scope生命周期，关闭后拒绝，finally显式关闭prover释放字段。

Child constructor和RAM状态计量完成后才发READY；父任务观测READY、从fresh实际Store独立认证root后，才生成请求（j%N和(N-1-j)%N，重合第二+1mod N），写exclusive SHA/时间线，stdin给child。每case父/child请求一致、生成时间>=constructor完成，真实报告SHA与DONE一致；不预生成path帮B缓存。协议可预测，不能称未知自然语言检索或新科学。

## 所有配对与阶段边界

| round |eligible |算法wall B/A |算法CPU B/A |完整parent wall B/A |额外常驻状态 B/A |完整child peakRSS B/A |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 9 | 1.265469580496623 | 0.0 | 1.0218687274597107 | 0.20580947136563876 | 1.0001443209698369 |
| 1 | 64 | 1.3528221627090649 | None | 0.9715982754830912 | 0.03938563675641499 | 0.9967058149527356 |
| 1 | 512 | 3.0093716302310916 | None | 1.0681006878368762 | 0.005053304759908872 | 0.9944079407241717 |
| 1 | 4096 | 5.525679305263881 | 6.0 | 1.0119661524539716 | 0.0006225540289448063 | 0.9377219076864025 |
| 2 | 9 | 1.1296429714417755 | 0.0 | 1.0010833741767433 | 0.20580947136563876 | 1.0125273124544791 |
| 2 | 64 | 1.4075796049128906 | 1.0 | 0.9506179442258759 | 0.03938563675641499 | 1.0015788718243146 |
| 2 | 512 | 2.9267999665907705 | 1.0 | 1.0385408043284778 | 0.005053304759908872 | 1.0004188774085452 |
| 2 | 4096 | 5.4378159069535075 | 6.5 | 1.0262239055523052 | 0.0006225540289448063 | 0.9414201753540804 |
| 3 | 9 | 0.9897355490992029 | 0.0 | 0.986692610003827 | 0.20580947136563876 | 1.0040462427745664 |
| 3 | 64 | 1.5352119573335783 | None | 1.041521185292219 | 0.03938563675641499 | 0.9997127674852794 |
| 3 | 512 | 2.817104818950422 | None | 1.037150408573886 | 0.005053304759908872 | 0.9937664496467655 |
| 3 | 4096 | 5.58934580252802 | 7.0 | 1.065344536160138 | 0.0006225540289448063 | 0.9460268417495413 |

算法phase=完整初始tree/anchor constructor +8次issue/原bytes读取和独立verify/canonical/写实际packet。共同Scope初始化、source生成/ingest、等待父数据及额外状态观察在该phase外，仍单列并进入完整worker/parent。父独立root认证和请求生成wall/自身CPU另记。H3同时要求phase wall/CPU和parent都<=1；不能用共同大ingest掩盖phase变慢。0CPU分母为null不能pass。其余count为完整diagnostic，不替换primary。

## RAM与 observer

A保存全部records/nodes/positions，B保存初始anchor，收到path重新排序/遍历并生成必要siblings。额外常驻图按真实实例/__dict__/tree字段去重sys.getsizeof，先扣共同scope.files和SID的同对象引用；不是全系统allocator核算。两方法初始/最终状态相等且额外状态计量自身wall/CPU单记，置算法phase外但仍进入worker/parent/RSS。A图遍历更贵，不能把观察成本差异当算法加速；H3 phase不含该观察。

初始全量O(N)Snapshot/Scope metadata和每次排序keylist仍存在并另外记费，B不是全流程O(logN)RAM。全部RSS是进程峰值，可能受GC/allocator历史影响，不能把常驻对象图比例当同幅总RAM节省。输出packet/日志不属于prover长期状态但全部落盘费用保留。Scope完整metadata对象图、构建/请求/观察/父阶段详见raw/derived。

## 原证据、完整费用与信任

全部192实际落盘packet以fresh原Store重算root/每leafmetadata、原文件逐byte恢复和独立成员checker复核。A/B同query/SID/requestSHA/packet bytes/返回payload B守恒。额外分析应用读取2748228B单列，非worker/SSD全系统IO。Checker独立接收父认证的可信anchor SHA/SID/path；仅SID或消息自报anchor不能自认证。成员不是全eligible覆盖、原文科学真理或逻辑DAG。损坏CAS由原read_range拒绝，元信息成员本身不是存储健康证明。

整库实际67Python+HTML 429612B，全部scripts保守1712044B，所有专用源/测试/协议/input逐SHA。完整worker source/CAS/snapshot/请求/packet残留9169386B，outer raw/stdio/parent3570495B、私有准备79363B。原v079 index及所有旧science/human/train/model/帧/恢复/下载cache/失败费用保留。当前model0/新训练0/新API0不抹除旧成本。完整分析finally/parenttimer另附，未知OS/目录/物理IO不当0。

## 复现与发行

```powershell
python -m unittest discover -s tests
```

scripts.run_late_membership.execute_case负责真实父子协议，直接worker需父输入READY后的认证请求，不能伪造空stdin跑完整实验。正式controller/input保存exact role/countorder和独占路径，无重跑覆盖。

![迟到请求内存与完整阶段时间](late-membership.png)

图须实际视觉检查。详报告/rawparent/标准图/README/release→localinitialbuild0→物理外actualwheel/currentnative/actualsdist新旧smoke→finalbuild源码审计0→tagReleaseCI→实际7资产SHA/递归全source/外actualpublished安装/proof8全齐才交付。本版init版本metadata用bytes.replace保留255B原行尾，formal前raw/Git/manifest全量一致；不重复v079包装换行差异。

原科学、模型、frames/restored、私研、课程模板个人报告和密钥不公开。E3净收益/E4整体/真实长期会话/科学NLI/回答/无限上下文仍未完成，冷缓存/跨机/物理SSD/全系统IO未测。下一项必须据RAM/CPU真实取舍决定，不增加请求/改阈值追联合正结果。


实际图已视觉检查。当前主4096三轮额外状态比0.000622554，完整child peakRSS比0.93772/0.94142/0.94603；算法wall比5.52568/5.43782/5.58935，CPU比6/6.5/7，parent比1.01197/1.02622/1.06534。重算省的是额外常驻对象图，不能据此声称总RAM省99.94%。
