# 多轮读取协议（v0.3.0）

本轮先推进 E0 读取评测，再进入 E2 性能分析。按用户选择，只使用当前 Windows
本机；冷缓存和跨机器数据明确未测，不将重新打开文件当作冷磁盘。

## 复现

```powershell
python -m pip install -e ".[zstd]"
python scripts/run_reading.py --out results/local-reading
python scripts/summarize_reading.py results/local-reading
# 绘图另需 .[plots]
python scripts/summarize_reading.py results/local-reading --plot
# 单语料，报告输出路径必须不存在
python -m rkv1 bench-reads data/scifact --out results/scifact-reading.json
```

Python 3.10+；数据下载器复用固定 SHA-256 的 SciFact/QASPER 文件。输出目录/报告
默认拒绝覆盖。历史受控压缩实验仍使用 run_controlled.py，v0.1/v0.2 记录不改写。

## 可证伪假设

1. 常驻读取器时，较小块通过降低解码放大改善短范围读取。
2. 每次重新打开时，小块带来的清单开销可能抵消解码收益；打开阶段必须单独计时。
3. 单批查询的排序能否在不同种子和交错执行后保持，须报告逐轮方向与波动。

本轮只观察原参数，不根据结果挑选种子，不自动改变生产默认值。

## 矩阵与配对

SciFact、QASPER × raw/Zlib 6/Zstd 3 × 64 KiB/256 KiB/1 MiB，18 个配置。
归档仍是 RKV v2，去重开启，变换关闭；相同 SHA-256 和 pack 持久化流程。
每个归档只编码一次并完整校验；本轮不是新的编码/恢复速度实验。

每配置两个连续批次，每批五轮，每轮每个可用类别 128 次正式请求、8 次查询预热。
类别为按文件字节加权、独立小文件/大文件和跨块窗口，请求最多 4096 bytes。
空类别保留空值。每批交错打乱配置、轮次、模式；类别顺序也按轮打乱。

轮种子由主种子、批次、轮号的 SHA-256 派生，存入 JSON。非跨块请求在不同 codec、
块大小与模式之间完全相同，并检查请求指纹；跨块窗口取决于分块位置，不能当成
跨块大小的完全配对请求。实际请求与执行顺序全部保存。

## 生命周期、计时与缓存

- open_reader：同一 worker 保持读取器打开；请求延迟排除首次打开和最后关闭。
- open_and_read：每个请求打开、读取、关闭；总延迟包含全部阶段，并分别保存跨度。

每个模式/轮次使用新 Python worker，启动时间不计入请求延迟。预先读取源文件的
目标范围作为真值；随后预读完整归档，将 OS 缓存置于温缓存条件。真值准备、查询
预热、外部字节比较和逻辑工作账本均不计入请求时间，内部块哈希照常计入。

常驻模式另记一次 initial_open_s。分析账本另用一个未计时读取器获取清单。预热
只控制本次读取的条件，不隔离后台负载、CPU 频率或硬盘内部缓存。fresh process
只重置解释器状态，不能代表 OS 冷缓存。

打开阶段包括文件打开、清单读取/哈希/JSON 解析/结构检查以及路径索引建立。
阶段计时使用 perf_counter，额外测量开销在两模式/全部配置中采用相同方式；非常
短的请求仍可能受到计时开销影响。[Python 时间文档](https://docs.python.org/3/library/time.html#time.perf_counter)。

## 汇总与完整性

每轮 nearest-rank p95 为排序后 ceil(0.95*n) 对应值。主要表格报告十轮 p95 的
中位数、最小/最大值及原始十个值；不把查询合并后冒充独立重复，也不声称该范围
是置信区间。相同种子逐轮计算基线 p95 / 候选 p95，记录更快轮数。
中位数和标准差为描述统计。[Python 统计文档](https://docs.python.org/3/library/statistics.html)。

每个请求逐字节比较；归档先完整校验，末尾核对归档 SHA-256。整个矩阵前后核对
源文件哈希和实现源码指纹；输入或实现变化时失败，不能沿用正式结果。
逻辑解码放大 = 触及块原始字节 / 请求字节；另记触及压缩 payload 字节与块次数。
它们不等于物理磁盘流量。RSS 含解释器、codec、预先准备的查询真值和临时块，
不能直接与旧版恢复进程内存比较。

两个批次在同一轮实验中连续执行，不能称为跨日或跨机器复现。冷 OS 缓存、跨机器、
跨日、成熟 seekable 系统对照和推理质量均保持 null；后续有环境再单独开展。
原始结果 schema_version=3，归档 manifest 仍为 version=2。
