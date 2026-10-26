# v0.42 冻结协议：仅单trace的有界已验证块复用

成本机制候选，不是新科学/真实推理。v0.41实际发行已核验，旧64 runtime只变版本，旧worker/fixture/gold/4096B入证/3跳及cas_traffic计量器不改。新评测脚本不集成默认Memory/Archive路径。已见fixture链节点集中同块，有利复用，不推广至跨块或自然任务。

## 规则

QueryBlockCache仅在一个目标SID trace中临时包装该Store实例block方法，退出/异常恢复并清空。key=(content hash,expected_size)，容量固定65536 decoded payload B，LRU。miss调用原block，保留stored/raw hash/EOF/长度/codec核验；能容纳时在解码前按expected_size淘汰；超cap块正常解码但不入cache。hit必须重新核key/整数正size、len和raw SHA，不重新读取对象文件/stored SHA。后续record仍经原Memory校验原record SHA和成员。请求内复用已验证内容，不承诺hit重新检查磁盘；新trace重新验证。内部replay同hash可以共用，不能把缓存带去另一次目标SID请求。

65536只限制保留的decoded payload，不是全部RAM/IO；metadata、Python对象、瞬态解码和RSS另计。peak_retained_graph_bytes只统计实例/映射/引用key与bytes的浅层图，不是增量分配或所有patch bookkeeping。scope退出retained payload必须0。无权重/字典/训练/模型API。

## 完整2×2

cache OFF/ON × traffic meter OFF/ON各3轮，共12新worker。同轮源/问题seed均沿v0.40，A=cacheOFF/meterOFF，B=cacheON/meterOFF，C=cacheOFF/meterON，D=cacheON/meterON；固定ABCD、BADC、CDAB三轮顺序。每worker96主问题（93完成/2missing/1cycle）+4控制+2负审计，总1152主问题=1116完成/24missing/12cycle、48控制、24负审计、3420接受绑定。所有1200 proof须与v0.40逐case相等，同轮4条件的全memory文件集合/字节/SHA相等；原source/HEAD保持，派生记录继续收费。

meter ON600 trace记录应用CAS read返回B、解码输出B，沿v0.41守恒；meter OFF600计数null，非0。cache OFF600 cache计数null；cache ON600 requests=hits+misses、payload峰值≤65536、scope后payload0；正式请求无oversize/失败，meter ON时decode_successes=cache misses。物理SSD/全系统IO/缓存冷态未测为null，不用应用B冒充物理B。

每worker原始报告不回写，meter/cache sidecar独立，父perf_counter紧包subprocess.run至退出，exclusive+fsync独立parent记录退出码/实际报告SHA/完整process wall。timeout600s，失败不重试覆盖。worker内RSS沿原观察点，非完整生命周期外部RSS。

## 先验门槛

必要真实CAS检查：重复读只miss调用原函数；hit raw哈希、wrong size、LRU两块淘汰、oversize不入cache、异常恢复、下次trace损坏源拒绝。完整测试后冻结代码/协议、CI成功再唯一12worker计划，不根据结果改容量/次数。

机械与全部父记录/计数/源/证明/文件合同全通过才认为候选正确。工作量门槛：meter ON每轮cache ON的应用CAS read B和解码输出B均严格小于OFF。时间联合门槛只用meter OFF：3轮cache ON/OFF成对比率的中位数在trace wall、trace CPU、parent完整wall三项都≤1；OFF CPU若0则该比率null且联合不通过，不加epsilon/追加轮数。RSS与完整费用独立列，时间通过不叫生产联合净收益；任何负方向保留。

meter ON的时间和observer×cache交互只作诊断，不用于算法速度门槛，避免少触发仪表被当作缓存加速。三轮为重复机械任务，不是独立科学样本。额外RAM/缓存源码/计量源码、旧快照/派生文件/sidecar与全部CPU计账；平台TCO未分配不当免费。

原始child/meter/parent JSON、报告/标准图实际视觉检查、源码账本、README/release说明，CI后Release并实际资产SHA/全部递归Python+HTML/物理仓库外实际wheel+sdist候选检查/current native/既有兼容/proof重下载后完成。未通过完整门槛仍保留负结果，不默认集成。0新模型API，E3净收益/E4整体/真实长对话与回答质量仍未验收。
