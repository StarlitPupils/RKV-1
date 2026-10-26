# v0.41 冻结协议：完整进程时间和trace范围CAS应用流量

这是已见v0.40合成fixture的成本仪表复测，不是新科学验证或推理提升。v0.40父测完整process wall漏记保持null/资源协议false，原轮不覆盖。本版只修复独立评测驱动；旧64 runtime模块除版本字面量保持逐字节不变，不调4096B入证、3跳、fixture、gold或正常失败分母。

## 范围和计数

scripts/cas_traffic.py只在单线程trace调用scope中包装Path.open返回的read与rkv1.store.decompress；其他函数仍调用原函数，无代码复制/替换解码/跳过原哈希、大小、EOF、codec校验。作用域退出即恢复函数；不计ingest、独立audit、ledger或派生写的CAS流量。

只有该memory.store.root/objects/内binary read累计object_opens、read_calls、application_CAS_file_bytes（Python read实际返回的header+payload字节）。不是SSD物理读B，也不覆盖metadata、stat、buffer预取、SQLite C层或全系统I/O。缓存状态未控制，physical_SSD_bytes/all_system_file_bytes为null。

包store.decompress原函数累计decode_attempts/successes、成功输入payload B、CAS_decoded_output_bytes；另分raw codec输出和压缩codec输出。它是CAS算法解码工作量，不等于峰值内存/新增信息/真实磁盘读取。任何原函数异常原样传播，失败解码不记成功输出。

计数守恒（正式trace全部无损坏情况下）：decode_attempts=decode_successes=object_opens，read_calls=2*object_opens；application_CAS_file_bytes=payload_input_bytes+OBJECT.size*object_opens；decoded总B=raw_codec_output_bytes+compressed_decode_output_bytes。0对象的未知key合法，分母为0的每题放大率记null。OFF计数必须null，不可记成0流量。

## 配对和冻结

3配对轮，每轮OFF/ON各一fresh worker与全新memory目录，6进程。奇轮OFF→ON，偶轮ON→OFF；相同轮使用v0.40 seed=20261026+轮号。二者都用同一sidecar recorder，计算proof SHA；OFF只是不包CAS，不是完全无记录器开销的原v0.40代码。

worker复用冻结scripts/run_evidence_paths.worker及evidence_path_fixture/gold，保持docs/evidence-path-inputs.json的13源SHA和原v0.40源准备/worker/fixture字节身份；新wrapper只替换legacy.trace绑定，原proof不加入计数字段。每worker100trace（96主问题+4控制）、2负审计。总576主问题=558complete+12missing+6cycle，24控制、12篡改负审计、1710接受绑定；ON流量300trace，OFF300trace计数null。

每对所有proof SHA、源SHA、问题SHA与按case_id配对的v0.40 proof保持一致。保留每轮全memory文件ledger，对OFF/ON文件集合/字节/SHA做完整比较；不硬改SQLite字节来强求相等，差异照实报告为一致性失败。

父进程perf_counter紧包subprocess.run直至child退出/timeout，exclusive+flush/fsync另写parent sidecar，含返回码、完整process wall与实际child/meter report SHA。child原report不回写父字段。超时600s，保留失败，不失败重试或覆写。完整process wall不从mtime/worker内计时估计。

## 先验验收和费用

必要单元检查用真实tiny CAS raw+zlib对象检验read返回B=实际对象文件B、decoded B=原长度；损坏对象仍拒绝、proof ON/OFF相等、scope外audit不累计。完整测试后提交冻结本协议/代码，CI通过再执行唯一六worker正式计划；无新源挑选或模型训练。

验收：6worker原机械/gold/控制/负审计/旧文件/HEAD合同保持；576主问题、24控制、12负审计/1710绑定通过；6份完整parent timing/身份记录；3对proof/源/问题/全memory集合及SHA完全相等；300ON trace计数守恒，300OFF计数null。任何失败保留，不调次数/预算追通过。

报告应用CAS file B / verified record B / admitted record B，以及decoded output / admitted B；聚合分母明确是同300trace而非只成功题。每题0分母保持null，不加epsilon。报告ON/OFF成对trace wall/CPU、parent完整wall的每轮原值和三轮中位数比率，量化observer开销，不把它说成算法加速。Windows CPU量化0值保留，不作显著性宣称。

全memory源/旧快照/索引/derived/残留文件、评测sidecar B/源码/协议metadata均计账；runtime整库与计量评测程序分别列，避免重复相加。worker内peakRSS沿用旧采样点（最终report序列化前），没有新的完整生命周期外部RSS；这是事先声明的观测边界，不补造。父测wall修复不消除physical I/O、冷缓存/跨机等未测限制。

源码冻结期间保持runtime及旧worker/fixture/准备器/输入清单不变；独立analyzer/plotter费用与实验分开，原始worker/meter/parent JSON完整保存。报告/标准图+视觉核验/README/release说明，CI后Release，并实际资产SHA/递归Python+HTML/外部wheel/current native安装/既有路径和计量检查/proof重下载后才能下一版。0模型API，真实QA/长会话/自然语言多跳、全系统或SSD物理I/O未测，E3净收益仍未通过。
