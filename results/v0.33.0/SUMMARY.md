# v0.33.0 实验报告：单写入 / 多读取的快照一致性

## 结论与适用范围

冻结的三轮门槛 **0/3** 通过。正式审计查询
2689 次，其中当前 HEAD 2415 次、显式初始快照 274 次；
原句/位置绑定 10756 条。当前查询与实际 add 区间重叠 1930 次。
观察到的 worker/父进程/历史审计错误共 6 条。所有错误均在 JSON 中保留，不重试失败操作。

这项结果只覆盖本机、合成资料、单 writer / 四 reader 的三个有界调度样本。
它不估计生产错误率，也不证明任意并发顺序、多个 writer、断电恢复或无限上下文可行。
没有模型调用，不能据此声称回答质量、多跳推理或长期会话收益。冷缓存/跨机器未测。

## 背景与冻结假设

v0.32 的代码/数学词法通道科学净空间 0/36、联合 0/36，不能用原生化改变该表示输出的字节数。
因此本版没有继续在这些源文件上搜索规则，而是检查动态证据记忆尚未直接覆盖的并发读取边界。
假设是：默认 search 在一次调用开始选定 HEAD 后，应绑定到一个不可变 SID；writer 提交新的 SID
不应让同一次结果混入其他 epoch。显式指定旧 SID 则须继续读旧内容。

运行库共 57 模块，除版本字符串外与实际 v0.32 标签逐字节相同；本版添加实验 driver、独立
审计测试、分析脚本和协议，没有给写入/读出路径打并发修复补丁。冻结提交 `148b5f4`。
协议与 driver SHA、全部运行库 SHA 和所有 81 个合成源 SHA 在 environment.json 保存并于分析时核对。

## 数据、流程与审计方法

每轮新建独立源目录及 Memory，默认 compact-budget-v3 / fixed / Zlib，原 replay budget 不变。
每个源文件 277446B、2048 条 JSONL，4 条 sentinel 每版同时改变四位 epoch，
其余 2044 条背景不变。使用排序键、固定分隔符、ASCII 转义和 CRLF，包含雪字与引号转义。
这是可按 corpus() 再生的合成结构，未将它包装成公开科学任务质量数据。

每轮四个 reader 先用初始 SID 各执行一次排除的预热/审计；共 12 次，
不计正式查询。全部 READY 后才释放 START，writer 连续提交 80 次更新。
reader 每十次有一次显式初始 SID，其他读取当前 HEAD；STOP 后再完成 20 次并要求最后当前读到80。
独立进程清除模型配置环境，所有循环和超时预先固定，失败不重试，不因结果改变预算。

每个查询要求完整 sentinel 集合、四个相同结果 SID、正确原始 key/path/offset/length/SHA，
title 和 sentences 必须等于该 SID 的原 JSONL；再从 CAS 读完整源并验证预生成完整源 SHA。
显式旧 SID 必须保持 epoch0，当前读 epoch 不得倒退。审计时间独立记账，未伪装成免费验证。
查询结束后不再次使用可变 HEAD 决定本次预期版本，避免把正常更新误判为不一致。

writer 停止后，全部成功提交历史 SID 再做完整源与四 locator 审计。
独立于正式 reader 的历史复查共 144 次 / 576 条记录绑定。
原始 Memory 中除 HEAD.json 外所有文件要求仍存在且 SHA 不变，answers 必须为空。
下述区间重叠使用同机 perf_counter：只说明操作持续区间重叠，不证明任何特定指令恰好同时访问。

## 逐轮结果与真实成本

|轮|成功更新|历史复查|门槛|add中位ms|add P95 ms|初始B|保留全部历史B|
|---|---:|---:|---|---:|---:|---:|---:|
|1|80|81|False|30.693|43.590|371538|863971|
|2|48|49|False|30.372|35.673|371538|673144|
|3|13|14|False|33.171|35.463|371538|457707|

|轮/reader|正式审计|旧SID|当前|当前不同epoch|重叠|最后epoch|search中位ms|search P95 ms|额外审计中位ms|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|1/0|447|45|402|81|349|80|5.444|8.587|1.909|
|1/1|392|40|352|74|321|73|5.406|8.567|1.865|
|1/2|239|24|215|39|184|38|5.316|6.475|1.822|
|1/3|156|16|140|24|117|23|5.322|6.679|1.838|
|2/0|58|6|52|6|32|5|2.770|6.526|1.714|
|2/1|311|32|279|49|226|48|5.250|6.435|1.754|
|2/2|307|31|276|49|220|48|5.276|6.418|1.786|
|2/3|312|32|280|49|229|48|5.266|6.511|1.728|
|3/0|117|12|105|14|63|13|5.437|7.233|1.857|
|3/1|117|12|105|14|65|13|5.349|6.963|1.797|
|3/2|117|12|105|14|62|13|5.258|7.354|1.822|
|3/3|116|12|104|14|62|13|5.332|7.643|1.884|

## 异常与部分完成的解释

add尝试143次，成功141次；query尝试2693次，完成审计2689次。
原始异常如下；后续未执行的操作不能算作通过，不重跑失败轮来替换这些结果。

|轮|执行者|异常|
|---|---|---|
|1|reader 1|PermissionError：[Errno 13] Permission denied: 'E:\\memorystorage\\.tools\\memory-concurrency-v033-work\\round-1\\memory\\HEAD.json'|
|1|reader 2|PermissionError：[Errno 13] Permission denied: 'E:\\memorystorage\\.tools\\memory-concurrency-v033-work\\round-1\\memory\\HEAD.json'|
|1|reader 3|PermissionError：[Errno 13] Permission denied: 'E:\\memorystorage\\.tools\\memory-concurrency-v033-work\\round-1\\memory\\HEAD.json'|
|2|reader 0|PermissionError：[Errno 13] Permission denied: 'E:\\memorystorage\\.tools\\memory-concurrency-v033-work\\round-2\\memory\\HEAD.json'|
|2|writer|PermissionError：[WinError 5] 拒绝访问。: 'E:\\memorystorage\\.tools\\memory-concurrency-v033-work\\round-2\\memory\\.memory-head-i12mi9d0' -> 'E:\\memorystorage\\.tools\\memory-concurrency-v033-work\\round-2\\memory\\HEAD.json'|
|3|writer|PermissionError：[WinError 5] 拒绝访问。: 'E:\\memorystorage\\.tools\\memory-concurrency-v033-work\\round-3\\memory\\.memory-head-3q6xkqo9' -> 'E:\\memorystorage\\.tools\\memory-concurrency-v033-work\\round-3\\memory\\HEAD.json'|

本轮三个门槛均未达到；已返回结果与历史复查没有发现混合epoch或绑定错误，观察到的HEAD访问冲突仍使并发可用性失败。

独立历史审计144次；初始不可变文件保持的轮数3/3。

失败 add 可能已留下 CAS/索引/manifest 但 HEAD 未前移，其实际空间仍计入；没有清理这些文件
来美化大小，未承诺失败写入是无副作用的事务。没有观察到内容错误不能证明不存在其他一致性问题。

下一版先考察 HEAD 的 Windows 读取共享方式：微软文档说明 FILE_SHARE_DELETE 允许其他
句柄进行 rename/delete；其技术文章说明普通 C runtime 的读写共享不等于共享删除，
并可能在 rename 窗口引发 sharing violation。本实验错误位置与该机制相符，仍是机制推断，
需定向句柄测试和同负载正式复测才能验证；本版未加入修正或重试。
参考：[CreateFileW官方文档](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
和[微软关于重命名共享冲突的说明](https://devblogs.microsoft.com/oldnewthing/20211022-00/?p=105822/)。


![快照实验操作数量、区间重叠、写入延迟与保留空间](snapshot-concurrency.png)

查询频率与具体交错由 OS 调度决定，不要求三轮次数相同，也不将较多查询当质量提升。
所有延迟是含同机争用的观测值，没有串行基线或因果隔离，不能据此声称并行加速。
保留空间包含实际 CAS、全部历史索引/manifest、HEAD 和 answers；分目录原数见 derived-metrics.json。
没有删除历史版本或不收费的隐式全量副本来降低成本。源文件和数据生成/审计/协调的额外 CPU、
工作盘空间不属于 Memory 的目录统计；OS/Python/SQLite/Zlib/硬件不是零成本。
source-resource.json 单列全部运行库源码与 HTML，未将它称为完整部署占用。

## 验证、可复现执行与边界

本版完整单元套件 220 项，219 通过、1 Windows 权限项跳过，0 失败。
新增审计测试不仅覆盖有效结果，还故意损坏投影/位置/SID/记录集合及完整源身份，确认验证器拒绝。
原测试仍覆盖旧归档 v1–v6、Memory 历史、来源格式、预算和显式候选边界。
本实验没有使用 Gear 原生库；发布库只作为兼容功能资产，不能冒充本次性能依据。

```powershell
python -m unittest discover -s tests -v
python -m scripts.run_memory_concurrency --work <不存在的工作目录> --out <不存在的结果目录>
python -m scripts.analyze_memory_concurrency --out <结果目录> --freeze <冻结提交> --test-log <完整测试日志>
```

environment.json 记录 Python/OS/CPU 数与计时器，round-1/2/3.json 公开逐次查询、writer、
完整 SID/源 SHA、历史复查、错误、子进程状态和目录字节。它们都是合成身份和运行记录，
不含真实科学语料、私有文档或模型密钥。Release CI/实际资产和仓库外安装记录随发行资产另附。

未覆盖多 writer、删除/GC、进程被杀、磁盘满、文件系统损坏、远程共享盘、断电、冷缓存、
异机与不同解释器/文件系统。零观察错误不是全局线性一致性的形式证明；本次重叠不是对每个
publication 指令的穷举调度。E3 神经预测、推理质量、多跳与长期对话目标仍未完成。

## 后续路线

若三轮门槛通过，下一项冻结单 writer 的故障注入：在固定提交边界终止子进程，检查可见 HEAD
与历史证据，再独立恢复写入；明确区分进程中断与真正断电。若不通过，保留本版原始失败，
下一版依据具体错误提出最小修正及固定复测，不能把失败重新运行后覆盖成通过。
不调整已评估科学任务预算，不因本次正确性结果默认切换检索或压缩表示。
