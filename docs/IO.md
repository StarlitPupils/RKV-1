# v0.9 CAS 对象 IO 消融协议

在v0.8已定位的对象发布/读取成本上做同格式实验。CAS version=1、84-byte对象头、
原文/存储双摘要、文件摘要、逐对象复用解码验证和逐新文件flush/fsync均保留。
Gear仍选v0.8冻结Windows库；没有迁移新的Rust IO代码，也没有CSV变换或模型。

## 候选与控制

- frozen v0.8：`store_v0_8.py`与v0.8.0的store.py原字节相同，SHA-256
  `89213a7f3d95d13f0005bc9e8fb1c42fee11b0e5f27e4887750f0e1e6ec9afc4`。
- current reference/link：当前实例参数框架，采用原读取和硬链接发布，检测框架本身影响。
- bounded/link：仍每次检查分片目录和对象普通文件/reparse属性；仅在分片缺失时mkdir。
  对象头校验后读取`stored_size+1`以内字节，长度必须恰好等于stored_size，以已打开
  流的精确EOF替代单独的路径size stat。截断、任意尾随字节先失败；双摘要和解压照常。
- reference/rename：仅Windows，临时同目录文件关闭前flush/fsync，然后`os.rename`。
  Windows遇到已存在目标会失败；绝不使用replace，也不在POSIX上运行此策略。
  成功后无需再删临时名字；失败清理临时文件，已有对象/快照不覆盖。
- bounded/rename：组合上述两项，读取和发布效果分开对照。

另保留旧独立RKV 1MiB、共享固定64KiB、独立Gear控制。Windows共八条件。
默认仍是reference/link；候选须通过`--io-backend bounded`、`--publisher rename`
显式选择。选项仅属于当前Store实例，不写入配置、对象或快照。
所有同kind/profile的条件，完整目录树字节、快照ID和新增对象账本必须一致。

参见[Python 3.13 os.rename](https://docs.python.org/3.13/library/os.html#os.rename)、
[二进制缓冲读取](https://docs.python.org/3.13/library/io.html#io.BufferedReader.read)。
名称发布成功不构成断电耐久性证明；仍无目录fsync、GC或掉电故障测试。

## 数据与测量

分别独立评测两个语料家族：QASPER官方三次发布，以及Evidence Inference官方
v1.2/v1.3/v1.4的两个主CSV表。后者按commit URL和每文件SHA固定，原始相对路径、
换行、引号和字节均保留。完整选择范围及官方来源见[DATASETS.md](DATASETS.md)。

每家族一次完整序列预热，再五轮正式新进程序列；内部按发布顺序添加，条件/轮次
打乱。发布各新文件的同步、旧对象验证、压缩、库首次身份检查/加载均计时。树扫描/
allocation审计在提交计时外，但编码RSS仍包含这些审计操作。
每个版本独立进程完整恢复；在计时外比较所有原始路径和字节。候选读取器按该条件
的io_backend选择；rename只改发布，不把读取时序波动解释为rename解码收益。

每版/轮/类别64正式范围请求、4预热，常驻与重开模式分别测。实际请求指纹跨所有
条件和生命周期匹配，固定64KiB窗口不保证跨变量块边界。读取前预读快照与所引用
对象，仍为本机温OS缓存；无已解码数据缓存。工作账本不是物理磁盘IO计数。

配对倍率按同轮比值再取中位；各轮p95的中位与配对比值中位不是同一统计量。
五轮范围只描述观察波动，不是置信区间。每家族单独报告结果，不混作六份独立语料。

## 完整资源与复现

每条件统计全部对象头、payload、双摘要、配置、快照及未引用对象。allocated只计
文件数据extent，目录/MFT/日志未完整计入；报告文件数，不称为完整物理卷成本。
各家族可单独加一次整份冻结DLL+native.json，两个独立仓库共用一份库的情景另列，
不把资源重复算入每版本，也不宣称已经做跨家族CAS去重。公共Python/codec/OS未全额分配。
全部候选仍扫描所有原文、验证全部复用对象；冷缓存、跨机器、跨日和推理质量未测。

```powershell
python -m rkv1 store-init vault --chunker gear-v1 --codec zstd
python -m rkv1 store-add vault data/qasper-versions/v0.3 --label v0.3 --chunker-backend rust --native-library native/rkv1_core.dll --io-backend bounded --publisher rename
python -m rkv1 store-verify vault SNAPSHOT_ID --io-backend bounded
python -m rkv1 store-unpack vault SNAPSHOT_ID restored --io-backend bounded
python -m rkv1 store-read vault SNAPSHOT_ID FILE --offset 4090 --length 100 --out range.bin --io-backend bounded
python -m scripts.run_io --native-library native/rkv1_core.dll --out results/local-io
python -m scripts.summarize_io results/local-io
```

先解压Release的`rkv1-native-measured-v0.9.0-windows-x86_64.zip`到`native/`。
性能复现使用该冻结实测库资产，保留原始native.json；新通用平台构建只按
自己的构建身份使用，不假定二进制相同。旧v0.7/v0.8读取器可读取本版同字节CAS。
