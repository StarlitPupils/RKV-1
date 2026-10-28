# v0.77.0 实验报告：有限批次的固定快照元数据复用

## 预定门槛与实测结果

H1证明/原source读取/计量一致：**True**；H2主4096/meterOFF批wall、CPU和完整parent<=1各轮：**True**；H3主4096/meterOFF peakRSS<=1.25各轮：**True**；联合 **True**。48freshworker/384query无重跑，另384实际证明用全新realStore元数据/原DAG审计、56220全部owned原文件逐byte恢复通过。

主4096OFF三轮batchwall比0.04158–0.04188，含初始setup的8query批次约23.9–24.1倍；整进程parent比0.3312–0.3358，约3倍；peakRSS比0.7608–0.7698，低约23%–24%。缓存tracked metadata5923451B（约5.65MiB），含所有proxy backingdict，低于16MiB保留图门槛。RSS反映当前Python对象分配/保留和GC，不推断所有环境缓存都会减少内存。

这只是已见owned规则证据的元数据组件实验。没有更改逻辑推导、sourcepayload读取/验证、全catalogue证明表示、默认SDK/UI；没有byte/压缩收益，也不能说明科学NLI/长期对话/回答或无限上下文完成。v076精确模板在新308句0key/532题全拒答的负结果保留，更强模型资源选择未获新授权，0模型API/下载。

## 冻结、固定工作量与2x2计量

472检查471pass/1权限skip，source/protocol/input freeze `b0880d9581ea3034588de652ac57dda28cdcf4fd`，exactCI `40639479254`成功后唯一执行。已见owned sourcecounts9/64/512/4096，两个固定selected source、四groundquery各重复2次、work100000、global_verdict永null。3roundcountorders与roleorders见[协议](../../docs/PINNED-METADATA.md)与input manifest，2method fresh/pinned ×meterOFF/ON ×4count ×3round=48，每worker600s/0retry，完整8query/384分母。没有以最好轮、meterON或较小规模替换primary4096OFF。

所有method/query/SID/fullcanonical证明SHA在同count上完全相同。Pinnedscope对真实原Snapshot构造校验一次，保留深只读metadata表，然后producer/旧独立source-DAGchecker共用这个initialmetadata信任；不称二者元数据校验完全独立。原CAS/source read_range路径逐次调用，未缓存decodedsource，实际返回B不减。复用单SID/8query生命周期，拒绝wrongSID/新HEAD/reentry/关闭后新read，初始manifest损坏及新scope损坏拒绝，active scope内actualCAS损坏仍拒绝。原对象和已验证metadata在scope关闭后释放引用，之前用户取出的只读metadata值不等于可撤销权限，不声称内存安全隔离。

## OFF主速度/RSS与所有轮次

| round |eligible |meter |batch wall ratio |batch CPU ratio |parent full wall ratio |peakRSS ratio |pinned tracked metadata B |
|---|---:|---|---:|---:|---:|---:|---:|
| 1 | 9 | off | 0.5595267411030447 | 0.6666666666666666 | 0.8318098844298224 | 0.9986560781918143 | 15844 |
| 1 | 9 | on | 0.537180016626636 | 0.3333333333333333 | 0.8782425958938196 | 1.002577952369261 | 15844 |
| 1 | 64 | off | 0.22595302445550752 | 0.25 | 0.6412971962811653 | 0.9789775441949355 | 95227 |
| 1 | 64 | on | 0.21934259631685202 | 0.2222222222222222 | 0.6667959275479528 | 0.9818857965451055 | 95227 |
| 1 | 512 | off | 0.06877898060021358 | 0.08 | 0.40512852270252453 | 0.9215091066782307 | 743371 |
| 1 | 512 | on | 0.07173157768464775 | 0.06 | 0.3999056155427561 | 0.9282985921641383 | 743371 |
| 1 | 4096 | off | 0.04187946593021539 | 0.04415584415584416 | 0.33122027660527065 | 0.7608055009823183 | 5923451 |
| 1 | 4096 | on | 0.041940822997804966 | 0.03926701570680628 | 0.3392611987705376 | 0.7301188903566711 | 5923451 |
| 2 | 9 | off | 0.5138397558255541 | 0.3333333333333333 | 0.8641604141153024 | 1.003798088703749 | 15844 |
| 2 | 9 | on | 0.557599516446078 | 0.3333333333333333 | 0.9338254382174053 | 0.9980449657869013 | 15844 |
| 2 | 64 | off | 0.24270481688617798 | 0.2222222222222222 | 0.6723357789175439 | 0.9802843828414386 | 95227 |
| 2 | 64 | on | 0.2414694022261658 | 0.25 | 0.6873664472311206 | 0.9826803631151457 | 95227 |
| 2 | 512 | off | 0.07179837609330418 | 0.058823529411764705 | 0.4107136189325255 | 0.9281659388646288 | 743371 |
| 2 | 512 | on | 0.07332800223349355 | 0.08163265306122448 | 0.40672277186020195 | 0.9225428509438056 | 743371 |
| 2 | 4096 | off | 0.04157518240318798 | 0.042105263157894736 | 0.3337453131537742 | 0.7698089350941275 | 5923451 |
| 2 | 4096 | on | 0.04284001941767717 | 0.04415584415584416 | 0.3445696043554652 | 0.7350860803416522 | 5923451 |
| 3 | 9 | off | 0.5337273699855098 | 0.3333333333333333 | 0.8768340391979026 | 1.0009791921664626 | 15844 |
| 3 | 9 | on | 0.5562763123469461 | 0.6666666666666666 | 0.8735834461168067 | 1.005152109911678 | 15844 |
| 3 | 64 | off | 0.217769583104727 | 0.25 | 0.6554869577989806 | 0.9732302201070792 | 95227 |
| 3 | 64 | on | 0.23607458168904394 | 0.2222222222222222 | 0.6105271784521455 | 0.9772700226109723 | 95227 |
| 3 | 512 | off | 0.07131014012896575 | 0.06 | 0.40100442039709533 | 0.9318156944292437 | 743371 |
| 3 | 512 | on | 0.07220758661254657 | 0.04 | 0.41261485814052345 | 0.9177098073364537 | 743371 |
| 3 | 4096 | off | 0.04163657638690514 | 0.041666666666666664 | 0.3358407144891751 | 0.7612704199677487 | 5923451 |
| 3 | 4096 | on | 0.04372195227122825 | 0.04461942257217848 | 0.3537136204874436 | 0.7244333157617291 | 5923451 |

主4096OFF每轮batchwall（含setup/8query/证明写入/close）、batchCPU与完整parentwall均<=1才H2True；peakRSS<=1.25才H3True。Zero clock denominator为null不能pass，其他规模/计量ON均作为完整diagnostic。源创建/导入另在raw记录，worker/parent整体仍包含，不能只展示查询内一小段加速。无额外重跑挑时间。

## Observer影响与读取守恒

| round |eligible |method |ON/OFF batch wall |ON/OFF batch CPU |
|---|---:|---|---:|---:|
| 1 | 9 | fresh | 1.0357650990021545 | 1.0 |
| 1 | 9 | pinned | 0.9943980729257035 | 0.5 |
| 1 | 64 | fresh | 0.9886599361242641 | 1.125 |
| 1 | 64 | pinned | 0.9597359353189369 | 1.0 |
| 1 | 512 | fresh | 1.0028257323362215 | 1.0 |
| 1 | 512 | pinned | 1.0458758082119068 | 0.75 |
| 1 | 4096 | fresh | 1.0021982648327852 | 0.9922077922077922 |
| 1 | 4096 | pinned | 1.0036665726372822 | 0.8823529411764706 |
| 2 | 9 | fresh | 0.9870757802853508 | 1.0 |
| 2 | 9 | pinned | 1.0711373955455528 | 1.0 |
| 2 | 64 | fresh | 1.005428240821142 | 0.8888888888888888 |
| 2 | 64 | pinned | 1.0003104157848008 | 1.0 |
| 2 | 512 | fresh | 0.9900238638191547 | 0.9607843137254902 |
| 2 | 512 | pinned | 1.011115794638608 | 1.3333333333333333 |
| 2 | 4096 | fresh | 1.002681943773496 | 1.013157894736842 |
| 2 | 4096 | pinned | 1.0331864217561937 | 1.0625 |
| 3 | 9 | fresh | 0.9790906918345459 | 1.0 |
| 3 | 9 | pinned | 1.0204553675441603 | 2.0 |
| 3 | 64 | fresh | 1.005044168100335 | 1.125 |
| 3 | 64 | pinned | 1.089524892230689 | 1.0 |
| 3 | 512 | fresh | 1.00954165856535 | 1.0 |
| 3 | 512 | pinned | 1.0222468588337732 | 0.6666666666666666 |
| 3 | 4096 | fresh | 1.006333370334796 | 0.9921875 |
| 3 | 4096 | pinned | 1.0567357694798372 | 1.0625 |

ON记录实际原Snapshot构造次数/时间与read_range返回path/B，pinned每8query批次构造恰1。OFF observer与observed calls全部null，不是0；OFF速度用于primary，避免callback减少冒充算法收益。On两方法每query选中原sourcepayload与旧auditor所有重复source返回守恒一致。Audit API自报返回数与On观测对齐，不把Off非观测项伪称已测。应用source返回B不是SSD/全系统IO/CASdecode；metadata读取并未被选取payload上限限定，全catalogue和proof大小仍随N增长。

## 语义、内存上限和故障边界

Pinned接受初始完整原Snapshot验证结果后，active scope中即使磁盘manifest副本被外部损坏仍继续使用先前合法inmemory数据，fresh新scope再验证并拒绝。此语义和已有持有Snapshot一致，但区别于每次重开fresh构造立即发现manifest后来损坏的策略。Formal批次无并发写/损坏；不能将本结果外推为同等热故障探测或生产无条件替换。旧SID固定，新HEAD不改变已缓存世界，不会隐式跟随新知识。

Tracked metadata cap16MiB包括header/filetable/offsets/只读proxy及其**backingdict表**的去重Python对象图，按sys.getsizeof，排除callerStore/OS/GC/allocator；保留图大小在初次构造后检查。不是初始加载/构造峰值上限，不是总RSS承诺，不是indexed或streamingmetadata验证。完整processRSS实测独立gate。初始小原型遗漏proxy背后dict table计量已在正式前纠正；原CAS损坏测试曾因误找分片filename失败，修用实际Store.object_path，原日志保留。无4096pinned性能/容量预检来调cap。

## 原文件、全部费用与后置独立复核

所有384实际落盘canonicalproof再次以fresh realStore metadata核原file/SID/range/SHA/闭包，与worker共享pinned视图分开。每worker所有source（含notes）完整恢复，共56220文件 =4*14055，逐文件不是去重块或抽样；追加analysis应用返回7047876B单列，不混为worker读全源或物理IO。分析内部finally和父驱动完整计时另附，失败也保留，不将恢复报告阶段冒充全审核CPU。

整库实际递归66Python+HTML 426112B，全部scripts保守1682238B；所有专用code/tests/protocol/input逐SHA。完整worker源/CAS/snapshot/证明/元数据残留30253944B，outer raw/parent/log 7400849B，private准备27000B。所有旧science/human/model/train/source/frames/restored/下载失败与cache历史费用保留。当前model0不抹除旧训练模型，未知OS/allocator/目录分配不当0。无coldcache/crossmachine/SSD/fullIO实测。

## 运行、交付与下一步

```powershell
python -m unittest discover -s tests
python -m scripts.run_pinned_metadata --work fresh-work --count 9 --round 1 --method pinned --meter off --report exclusive-report.json
```

![元数据复用主计量与完整内存](pinned-metadata.png)

图已实际视觉检查，OFF时间/RSS与ON48次降为1次的构造记录一致。实验/报告不是发行完成：本地initialbuild退出0、物理仓库外actualwheel/currentnative+新旧actualsdist、finalbuild/sourceaudit，再commitpush/tagReleaseCI、实际7资产SHA/递归PythonHTML/allsource/物理外actualpublishedinstall/proof8全齐才交付。原science/human/train/models/帧/恢复副本/私研/课程模板个人报告/密钥不公开。

若time/RAM门槛未过，保留，不调seengeometry/cap或改primary追positive。即便组件通过，初始O(N)manifest验证/全catalogue通信体积/多并发/持久索引/跨设备与真实长会话仍未解决，不叫总体目标实现。旧24API预算已用完无新模型资源授权，继续纯CPU离线。E3净收益/E4整体/开放NL科学NLI/可靠回答/无限上下文未完成。
