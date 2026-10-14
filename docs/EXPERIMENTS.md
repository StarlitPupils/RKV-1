# 复现实验

Python 3.10+。核心只依赖标准库；完整 E0 对照安装锁定版本的可选依赖。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[bench]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/run_experiments.py --out results/local
```

Linux/macOS 将解释器路径替换为 `.venv/bin/python`。无网络时可预先放入与固定
SHA-256 一致的数据文件；下载器会验明后复用。首次运行需从官方源获取数据。

单独执行：

```powershell
python -m rkv1 fetch data/uci
python -m rkv1 fetch data/scifact --dataset scifact
python -m rkv1 pack data/uci data/uci.rkv
python -m rkv1 verify data/uci.rkv
python -m rkv1 unpack data/uci.rkv data/restored
python -m rkv1 compare data/uci data/restored
python -m rkv1 read data/uci.rkv winequality-red.csv --offset 0 --length 128 --out data/range.bin
python -m rkv1 pack data/uci data/uci-next.rkv --base data/uci.rkv
python -m rkv1 bench data/scifact --repeats 3 --warmups 1 --queries 32 --out results/local/scifact.json
```

目标归档默认不能存在；已恢复目录也必须不存在。参数 `--chunk-size` 单位是字节，
增量 base 必须使用相同块大小。`python rkv1.py` 兼容原对话命令。

## 测量定义

每个方法在独立 Python 子进程执行，1 次预热、3 次记录、种子 20261014。
报告原始样本、median、min/max、样本标准差；随机读取 32 个最多 4096 字节的窗口，
报告 median 和 nearest-rank p95。顺序固定，不模拟冷缓存或独占 CPU。

编码时间包含打包、压缩和写盘；恢复包含读盘、解码和写出文件。基线额外对 TAR
字节流比较，RKV 内部验 SHA-256。所有方法在计时后再对恢复目录逐字节比较。
因此不是纯 codec microbenchmark；RKV 含哈希/fsync，而 TAR baseline 没有相同校验语义。

TAR 方法用规范化 PAX TAR（mtime/uid/gid=0，mode=0644），统一存储文件组织信息。
RKV 使用含哈希和引用的 JSON manifest；容器总开销都计入大小。两个容器不同，
不能直接将差值归因为某一个编码器。随机读为温缓存模式：RKV 保持 manifest 打开，
仅解码触及的块；传统整流 TAR 每次完整解码。seekable-Zstd、分块 TAR 等更强对照
尚未加入，结果只说明这组具体实现的取舍。

峰值 RAM 使用 Windows PeakWorkingSetSize / POSIX ru_maxrss；它是工作进程整个
生命周期峰值，包含解释器、输入、预热、校验、读写缓冲，不是纯 codec 内存，也不含
操作系统文件缓存或所有外部进程。当前没有 GPU、能耗和科学推理质量指标。

增量实验追加一个固定探针到排序第一份文件，比较完整重压与验证后复用块。单次测量，
仅做机制诊断，不用于宣称统计显著速度优势。两种方式都重新读源并写完整独立快照。

## 发布前检查

单元测试、真实数据 bytewise compare、所有可选基线、格式文档、原始 JSON 和结果
解释都完成后再打 tag。CI 在 Windows/Linux、Python 3.10/3.13 上运行核心测试，
Linux 运行 Rust 骨架测试；Release 工作流只在这些测试通过后发布 wheel、源码包与
实验记录 ZIP。首次实验格式使用 prerelease 标记。
