# v0.13 归档恢复文件同步与发布边界

从v0.13起，归档API `unpack`、`Archive.process(output_dir=...)` 和CLI `unpack`
默认sync_policy=files：完整块/文件原始SHA验证通过后，依次flush、os.fsync、close。
空文件同样同步；全部文件完成后再重命名暂存目录为目标。任何同步异常直接失败，
不静默降级。显式close策略保留关闭文件的对照边界。verify不写出文件，也不fsync。
策略只改变恢复I/O语义，不改归档格式/编码/压缩率；CAS恢复路径保持既有实现。

Python参考[os.fsync文档](https://docs.python.org/3.13/library/os.html#os.fsync)：
缓冲文件先flush再fsync，Windows调用MS `_commit`。本版没有新增原生库/模型/字典。
**文件同步请求不等于目录或掉电持久性证明**：没有目录/卷级同步、设备断电实验、
控制器缓存保证或多写者事务。父目录须可信。强杀后的私有暂存目录可能残留，
没有自动恢复/GC；发布之后进程被杀，完整目标可存在而客户端未收到成功返回。

## 预定成本实验

冻结后运行十轮正式，每个案例/策略一次完整预热；所有案例/策略/轮次打乱。
每次恢复新进程，close/files使用**同一个归档、相同SHA**及相同其余校验/发布路径。
计时含unpack、SHA、同步、关闭、目录发布和内部暂存清理；排除Python进程启动、
外部逐字节真值比较及输出删除。使用工作区scratch目录，记录实际卷，不混用TEMP卷。

四个案例：

- 原始PTB ECG三文件，v4/Zlib1MiB/byte-shuffle2。
- 原始M13 float64单文件，v4/Zstd1MiB/整文件byte-shuffle8。
- 同一M13，v6/Zstd64KiB/FITS分段类型重排，作为不同解码路径的同步对照。
- 合成文件数控制：固定262,147-byte噪声连续切成129份，每份<=2048B，再加一个空文件，
  共130个文件；v2/Zlib64KiB。不是新科学语料，不将它的开销推广到真实科学目录。

共80次正式恢复、8次预热。输出均对原始源逐字节比较，归档前后SHA保持不变。
记录wall、CPU、峰值RSS、每轮策略与完成fsync文件数。配对差值为每轮files-close，
配对倍率为files/close后取中位，不用两个中位之比冒充配对结果。
归档哈希预读，温OS缓存，后台负载未隔离；不测冷缓存/跨机器/跨日/功耗/推理质量。
同步成本依文件数、设备与缓存变化，不预设统一百分比；不会为更好时序删除同步。
同代码close对照用于隔离同步开销，不能将历史v0.12与本版独立批次直接作因果比较。

## 故障审计

v1固定历史归档，加v2–v6合成小样本；每格式11情形、重复3次，共198个审计记录。
正常files/close；首次写/flush/fsync/关闭失败、末次fsync失败、发布前失败；
首次成功同步后、发布前、发布后三个明确检查点强制终止子进程。
故障注入只存在于实验模块，不通过生产环境变量启用；fsync的正常路径实际调用OS。
核对正常路径flush→fsync→close→publish顺序、空文件同步、目标状态、返回计数，
以及强杀残留。模拟异常/杀进程不等于真实断电或覆盖所有故障交错。

## v0.12工作量账本更正

v0.12的v6分段数据读取是正确的，但分析性touched_bytes仍按固定块偏移计算，导致
部分decoded/stored字节及放大率不正确。v0.13改用真实前缀偏移，并以实际被解码块
的单元测试和独立线性重叠扫描核对。旧tag和原始结果不覆盖。
使用原始输入重编码全部100个v0.12归档，要求完整SHA和存储账本逐项相同，再对
原96,000次请求重算工作量，写独立更正记录。它不是新的读取性能实验，不替换延迟。
原0/8验收用归档成本及延迟，未使用这些工作量字段，因此其计算结论不变。

## 执行

```powershell
python -m pip install -e ".[scientific]"
python -m scripts.run_sync --out results/local-sync
python -m scripts.correct_v012_work --out results/local-sync/v012-work-ledger-correction.json
python -m rkv1 unpack evidence.rkv restored
python -m rkv1 unpack evidence.rkv historical-close --sync-policy close
```

输出目录须不存在；完整实验需要v0.12输入已下载及历史结果随源码保留。
scientific extra用于v5故障格式覆盖；正式同步计时的四个案例不使用Blosc/RKV Rust。
本机测试和CI执行异常/中断检查，但不是跨机器性能复测。
