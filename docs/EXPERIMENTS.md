# 复现实验

Python 3.10+。Zlib 核心只依赖标准库；Zstd 安装固定版本的可选依赖。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[bench]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/run_controlled.py --out results/local-controlled
```

Linux/macOS 使用 `.venv/bin/python`。下载器复用 SHA-256 匹配的文件。重新实验使用
新输出目录，保留已发布记录。

## 操作命令

```powershell
python -m rkv1 fetch data/scifact --dataset scifact
python -m rkv1 pack data/scifact data/scifact-v2.rkv --codec zstd
python -m rkv1 verify data/scifact-v2.rkv
python -m rkv1 unpack data/scifact-v2.rkv data/restored-v2
python -m rkv1 compare data/scifact data/restored-v2
python -m rkv1 read data/scifact-v2.rkv corpus.jsonl --offset 1048570 --length 128 --out data/range.bin
python -m rkv1 pack data/scifact data/no-dedup.rkv --codec zstd --no-dedup
python -m rkv1 fetch data/wine --dataset wine
python -m rkv1 pack data/wine data/wine-columns.rkv --codec zstd --transform csv-columns-v1
python -m rkv1 bench-controlled data/scifact --out results/local-controlled/scifact.json
```

默认拒绝覆盖已有归档，恢复目录必须不存在。增量 --base 必须同块大小、codec、
transform。旧归档可继续验证/恢复；新归档需 v0.2.0+ 读取器。

## v0.2.0 受控协议

每个方法使用同一个 RKV1 v2 容器、同一套 manifest/块/文件 SHA-256、相同临时文件
写入、flush、fsync、原子替换和归档摘要。可变量为 codec、块大小、去重与可逆变换。

64 KiB、256 KiB、1 MiB × raw/Zlib 6/Zstd 3 × 去重开/关，共 18 配置。
UCI 与 Wine 另加两 codec × 三块大小的 CSV 列重排，各 24 配置。执行顺序以种子
20261014 打乱；每配置 1 次预热、5 次记录。每次归档字节必须相同，每次恢复由父进程
在计时外逐字节比较源目录。

`runtime-footprint.json` 记录共享 RKV/transform 源码以及本机可选 Zstd distribution
占用。所有 v2 条件部署同一份源码；codec 的安装开销须结合归档数量摊销，归档字节
不能视为完整部署成本。Python 与共享原生依赖仍未全额分配到单个归档。

编码、恢复、随机读取各用新 Python 进程，分别测峰值 RSS，包含解释器、codec 和
缓冲；恢复内存不含编码进程持有的原文。不计子进程启动时间；编码计时含归档摘要，
恢复含内部哈希校验。

随机读取每种可用类别 128 次：按文件字节加权、独立小文件/大文件组、跨块窗口。
请求最多 4096 bytes。open_reader 已打开清单；open_and_read 计入每次打开/关闭。
两者均温 OS 缓存，重新打开不等于冷磁盘。记录全部样本、median、样本标准差与
nearest-rank p95；不存在的类别为空。

真实数据为原 UCI、SciFact、QASPER train/dev v0.3、Wine Quality red/white。
合成重复仅做去重对照。来源与固定哈希随结果保存。受控实现支持 2 GiB 输入；
旧 bench 的历史 TAR 基准仍为 64 MiB。

## 增量场景

SciFact 最大文件 corpus：尾部追加、中间插入、等长替换、重命名；另测最小文件删除。
Zstd/1 MiB 下比较完整编码与旧块复用，1 次预热 + 5 次测量，每次逐字节比较恢复。
所有新快照独立，源文件仍全量读取。固定分块中间插入可能改变后续块地址，必须同时
报告复用比例、完整写出量与时间。

## 边界与发布

单机器、温缓存、后台负载未隔离；尚无能耗或推理质量结果。CSV 仅覆盖受支持数值
表格，净收益按完整归档字节比较，负结果也保存。受控对照不能代表所有成熟 seekable
系统。v0.1.0 方法与结果在其 tag 保留，两版协议不同，不直接比较耗时作因果结论。

本地测试、恢复验证、JSON、规范、README 和 Release 说明完成后打 tag。CI 运行
Windows/Linux、Python 3.10/3.13 的核心与 Zstd 测试，以及 Rust 骨架测试；通过后发布
wheel、源码包与实验记录 ZIP。

摘要和图形可从 JSON 重新生成（绘图依赖另装）：

```powershell
python -m pip install -e ".[plots]"
python scripts/summarize_controlled.py results/local-controlled --plot
```
