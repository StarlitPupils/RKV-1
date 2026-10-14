# 独立校验单元实验（v0.5.0）

目的：减少 CSV 范围读取的整块重建成本，同时计入全部索引，和直接小块方案比较。
先推进类型表示/块内访问；Rust 性能迁移和真实版本序列/共享块存储仍是后续任务。

## 使用与复现

```powershell
python -m pip install -e ".[zstd]"
python -m rkv1 pack data/superconductivity data/super-units.rkv --codec zstd --transform csv-columns-v1 --unit-size 65536
python -m rkv1 verify data/super-units.rkv
python -m rkv1 read data/super-units.rkv train.csv --offset 65530 --length 4096 --out data/range.bin
python scripts/run_units.py --out results/local-units
python scripts/summarize_units.py results/local-units --plot
```

绘图另需 .[plots]。输出目录必须不存在；默认 pack 不指定 unit-size 时仍是 v2。
v3 需要 v0.5+ 读取器，旧格式可继续读。[格式与校验范围](FORMAT.md)。

## 假设与对照

1. 独立子单元将短请求的逻辑解码放大从约 1 MiB 降到约 16/64 KiB。
2. 外层保持 1 MiB，可以使顶层清单较小；首次读取父块的二进制索引仍有成本。
3. 若普通小块已有同样收益，必须在总大小、打开成本、逐轮延迟上比较，而非只对
   整块 CSV 宣称胜出。空间节省不能忽略单元索引中的摘要和结构字段。

Wine、Superconductivity：flat 1 MiB/64 KiB/16 KiB、1 MiB 父块+64/16 KiB 单元，
各配 Zlib/Zstd 与 none/CSV，共各20条件；Superconductivity 另加一个关闭索引缓存
的 Zstd/CSV/64 KiB 单元控制。QASPER 只测 Zstd/none 五种布局及无缓存控制；
HTRU2 为回退对照，Zstd、flat1MiB/flat64KiB/units64KiB × none/CSV。

所有条件使用同源码部署、路径/原文/哈希、flush/fsync/原子发布和归档摘要。
v2 验触及块；v3 验索引和触及单元；完整恢复都验父块与文件。完整归档字节包含
所有索引、JSON、摘要、标志和 payload。v3 比 v2 小块的 CSV 接受阈值可略不同：
二进制索引标志是固定成本，JSON transform 标签可变，不假定 payload 完全相同。

## 测量

每条件一次编码/完整恢复预热、五次正式记录；独立编码/恢复进程，外部目录比较
在计时外。归档字节在重复编码间必须相同，再生成同 SHA-256 的归档做范围测试。
配置顺序随机；编码/恢复按配置成组执行，范围配置/轮次/模式交错随机执行。

范围每轮两种模式、每种可用类别64次请求、4次查询预热、最多4096 bytes。类别为
字节加权、独立大小文件、cross_unit。最后一组固定在64KiB网格边界，全部布局使用
同一组请求；不把它称为每个1MiB父块的跨块请求。每轮所有请求指纹必须完全一致。

常驻读取器按需缓存索引；重开时每次读首次索引。无缓存控制仅作用于范围读取，
完整恢复仍使用普通默认读取器。每次计时前预读归档，OS 温缓存；独立进程不代表
冷磁盘。冷缓存、跨机器、跨日继续明确未测。

主要延迟为五轮各自 nearest-rank p95 的中位数，并保留范围、配对比值与更快轮数。
范围不是置信区间，不提出显著性结论。原始请求/阶段跨度/执行顺序全部保存。
逻辑工作账本根据实际触及单元计算，referenced_index_bytes 是引用的索引大小，
不是缓存未命中或物理 IO 量。账本有独立未计时读取器，范围 RSS 含其缓存与查询
真值；完整恢复 RSS 单独测量，不把范围峰值称为生产读取器内存。

## 验收边界

每次完整恢复与每次范围读取逐字节一致；重复归档确定性；实现、输入及归档前后
哈希不变。格式测试包含索引损坏、重算索引摘要后的非法条目、触及/未触及单元
损坏、父块哈希、部分尾单元、跨父/子边界、缓存淘汰和 v1/v2 兼容。

算法只提供独立单元，未改变科学数值精度、删除原文或增加神经表示。默认配置
不会由一轮结果自动替换；若两层索引不产生净收益，也要保留负结果。
