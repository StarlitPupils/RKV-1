# v0.82.0 实验报告：已见cache失效的只读诊断replay

## 诊断结果与分母

H1原initial/final cache trace、96原packet SHA/192原bytes、输入文件及observer恢复/集合/计数守恒 **True**；H2主4096的全部24原query，初始相关key非空、全被真实lookup且均在使用前已丢失 **True**。12旧Ccase全部replay，不排失败；新科学问题0、新训练0、新API0、新policy/cap试验0。旧v081时钟/RAM/代码/数据和H3/jointFalse不回填。

本版是观察到端点0hits后的事后诊断，不是独立新科学验证或新的生产速度/压缩收益。对应olddata的12根、14043 metadata叶、14055所有原文件及192成员另以fresh真实Store独立复核；原source/CAS只读。Observer key列表显式保存，后置逐range/set/histogram核算。

## 冻结与保真

507检查506pass/1权限skip，最终freeze `9ae7b6ad6b5fc5f49730241406487ccc510c97d0`，exactCI `40820409589`成功后唯一12replay。最初仅等待CI时发现只聚合计数不足独立key审计，于真实replay0/output目录不存在时停止等待，补四个key集合后另冻结/CI，原日志保留；没有重跑真实样本、没有改cache参数。

固定v081全部3轮×9/64/512/4096 Ccase及原8请求。每case fresh进程600秒、0replay retry，先全source恢复against旧owned fixture，重建相同Scope/cache，再逐旧请求比较canonicalpacket与旧SHA、独立原bytes验证；原首末trace完全相同才允许解读观察。旧报告与v081 tag逐byte相同、所有旧输入和旧算法源SHA被冻结且复盘前后未变。旧请求本来已知，未声称新迟到问题实验。

## 逐case记录与观察成本

| round |eligible |hits |misses |query开始相关key总数 |使用前已丢失key总数 |replay全wall s |replay全CPU s |replay peakRSS B |parent全wall s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 9 | 36 | 0 | 76 | 0 | 0.011684499913826585 | 0.015625 | 27320320 | 0.12064530001953244 |
| 1 | 64 | 80 | 0 | 912 | 0 | 0.026825499953702092 | 0.03125 | 27750400 | 0.1297850999981165 |
| 1 | 512 | 0 | 8032 | 1160 | 1160 | 0.2079896000213921 | 0.21875 | 29667328 | 0.3154777002055198 |
| 1 | 4096 | 0 | 65328 | 1136 | 1136 | 1.5506806999910623 | 1.53125 | 44601344 | 1.6611405001021922 |
| 2 | 64 | 80 | 0 | 912 | 0 | 0.02582450001500547 | 0.03125 | 27713536 | 0.13477280014194548 |
| 2 | 9 | 36 | 0 | 76 | 0 | 0.012425699969753623 | 0.015625 | 27381760 | 0.115728999953717 |
| 2 | 4096 | 0 | 65328 | 1136 | 1136 | 1.5710972999222577 | 1.5625 | 44441600 | 1.6754531001206487 |
| 2 | 512 | 0 | 8032 | 1160 | 1160 | 0.20907859993167222 | 0.1875 | 29736960 | 0.31453000009059906 |
| 3 | 512 | 0 | 8032 | 1160 | 1160 | 0.20403510006144643 | 0.203125 | 29556736 | 0.3102202999871224 |
| 3 | 4096 | 0 | 65328 | 1136 | 1136 | 1.5606053001247346 | 1.5625 | 44498944 | 1.6680989998858422 |
| 3 | 9 | 36 | 0 | 76 | 0 | 0.010794700123369694 | 0.015625 | 27418624 | 0.11624730005860329 |
| 3 | 64 | 80 | 0 | 912 | 0 | 0.026128399884328246 | 0.03125 | 27660288 | 0.1342714000493288 |

每query初始key、相关key（不包含requested leaf）、真实asked key及lost-before-lookup key均保存range列表；独立核lost⊆asked⊆relevant⊆initial，重算span histogram、unique计数和not-asked数。get调用hits+misses等于lookups且精确对齐cache计数器增量。NodeLRU原方法按原规则执行，故初始存在而lookup时miss的key已在同query遍历中丢失；本诊断没有另行删除或policy变更。小规模全保留作为行为对照，不能因其不符合largest症状排除。

CacheProbe只在当前target/query局部包装原get，先调用原方法再记数；nested/concurrent observer拒绝、finally恢复。观察器额外持有旧key引用、收集集合，影响存活/RSS/CPU，以上replay成本独立，不得替换/比较旧phase来推加速。完整内部finally与父wall/自身CPU/RSS记录齐，不能只报局部收尾。原始阶段的速度/RAM结果仍只在v081报告。

## 可解释范围和后续

如果H2成立，它具体支持“有用的初始cache项在真正访问前已因当前遍历过程丢失”的解释；不证明任何替代策略必然更快。v081的0hits与9次完整hash、evictions是旧实测，本版增加查询内部key位置证据，仍是同一已见owned任务。n>=64 admission只是由树节点数预算推导的后续假设，未在本版实现/测量，也不扫描参数、改64KiB或8请求追正。

## 全部资源与发行

额外后置应用读取1374114B，和replay进程读取分别记录，不是物理SSD/全系统IO。整库实际67Python+HTML 429612B；全部scripts保守1735758B及所有新源/测试/协议/input SHA列明。replay raw/parent/finally/log残留388850B、私有准备12762B单列；旧v081源/CAS/snapshot/packet/模型/旧science/human/train/frame/restored/缓存/失败均保留非零，复用不是免费删除。未知OS/物理分配不当0。

```powershell
python -m unittest discover -s tests
```

scripts.replay_cache使用独立old-work/old-report和exclusive新report；公开v081代码可重建owned输入，但不得重建旧时钟填入原结果。标准图须实际视觉看：

![cache使用前淘汰诊断](cache-replay.png)

详报告/README/release与完整localinitialbuild0→物理仓库外actualwheel/currentnative/actualsdist新诊断+所有旧机制→finalbuild/sourceaudit0→tagReleaseCI→实际7资产SHA/全递归source/外actualpublished安装/proof8齐才交付。原science/models/frame/restored/私研/模板课程个人报告密钥不外发。E3净收益/E4整体/真实长会话/科学NLI/回答/无限上下文未完，coldcache/crossmachine/SSD物理全系统IO未知；无新模型/API/下载授权，CPU离线。
