# 精确 CSV / Gear Rust 内核与配对实验

## v0.8 Gear 边界扫描

v0.7 的冻结Python源码经cProfile诊断后，逐字节Gear循环是主要热点。v0.8新增显式
`store-add --chunker-backend rust --native-library ...`，只迁移边界扫描。Python仍组装
原文字节、计算全部SHA-256、压缩、验证旧对象、fsync并发布对象和快照。
默认仍为Python；固定边界不接受Rust扫描后端。CAS config和快照均不写后端名称，
两个后端产生相同切点、对象、快照ID和完整存储树，CAS格式仍为version=1。

```powershell
python -m rkv1 store-init vault --chunker gear-v1 --chunk-size 65536 --codec zstd
python -m rkv1 store-add vault data/qasper-versions/v0.1 --label v0.1 --chunker-backend rust --native-library .tools/native-v0.8-measured/rkv1_core.dll
python -m scripts.run_gear --native-library .tools/native-v0.8-measured/rkv1_core.dll --out results/local-gear
python -m scripts.profile_store --backend rust --native-library .tools/native-v0.8-measured/rkv1_core.dll --out results/local-gear/profiling-native.json
python -m scripts.summarize_gear results/local-gear
```

API：`Store(root).add(source, label="...", chunker_backend="rust", native_library=library)`；
`chunks(stream, settings, backend="rust", native_library=library)`也可直接使用。
旧CSV ABI=1不变，Gear使用额外的`rkv1_gear_abi_version() == 1`及`rkv1_gear_scan`。
库元数据必须声明`gear_abi=1`和features中的`gear-v1`，否则在加载DLL前拒绝。
加载后还检查导出ABI；任何失败直接报错，不自动回退或跳过数据。

Gear C ABI接受本缓冲区的字节、256项u64表、scale、rolling/count输入输出状态，
返回缓冲区内从1开始的切点位置数组。h按u64溢出保持原递推，边界后h/count清零；
Python跨短读取保留原文缓冲区与状态，最终残余字节不丢弃。缓冲区上限8MiB，
scale仍为4096..2MiB的二次幂。输出容量不足或状态/尺寸不合法时不更新状态。
FFI只检查声明的尺寸，调用者仍必须提供有效、互不重叠、存活的指针与缓冲区。

本机测量使用通过Windows/Linux CI的冻结Windows二进制，源提交
`96be8d0361407d6970bcb1101e2770151951483d`，DLL SHA-256
`7736879b67377038fdc2211fbdadfc12c71983ba96257dbb8a18c33c660196e2`。
DLL 123,904 bytes + 原始native.json 515 bytes，整份库全额计费124,419 bytes。
发布资产`rkv1-native-measured-v0.8.0-windows-x86_64.zip`保留该库和元数据原字节；
本机时序必须用此资产复现，不假定新Release构建与它二进制相同。源码内核指纹、
编译器、完整树一致性及配对样本见[本轮记录](../results/v0.8.0/SUMMARY.md)。

主实验六条件：旧独立1MiB RKV、共享固定64KiB CAS、独立/共享Gear × Python/Rust。
一次完整序列预热，再五轮正式新进程序列；条件/轮次打乱，每序列依次添加三版。
计时包含首次库身份检查/加载、FFI和复制，实际读源、压缩、复用验证与发布全部保留。
每个版本均独立恢复，再比较全部文件名和原字节；各后端的所有轮次存储树和账本必须
完全一致。范围请求指纹匹配，恢复/读取仍使用同一Python CAS实现；相应计时波动不能
解释为原生解码收益。cProfile诊断与主实验分离，仪器化占比不视作正常运行CPU比例。

共享原生资源全额加一次，不按符号大小推算所谓Gear专属成本。文件数据allocation、
逻辑存储、文件数分别报告；目录/MFT/日志和公共Python/codec/OS未全额分配。
本机温缓存、一个家族三版；冷缓存、跨机器、跨日与推理质量未测。

## CSV 后端

默认后端仍为 Python。Rust 只迁移 CSV v1 的数值字面量检查与列到行的精确反变换，
不解析浮点数，不改写编码、codec、哈希、归档格式或完整性规则。它不是整个归档
的原生解码器；CSV 仍须显式启用。v1/v2/v3 均可用这个读取后端。

## 使用

从受信任的 GitHub Release 下载对应 Windows x86_64 或 Linux x86_64 原生 ZIP，
解压出 DLL/SO 与相邻的 native.json。路径是用户明确选择的可执行库；哈希校验
检查文件身份，不能自行建立发布者身份。Python 会核对大小、SHA-256、源提交和
ABI=1，再加载。失败直接报错，不默默回退。库使用期间应保持不变。

```powershell
python -m rkv1 verify snapshot.rkv --decoder-backend rust --native-library .tools/native-v0.5/rkv1_core.dll
python -m rkv1 unpack snapshot.rkv restored --decoder-backend rust --native-library .tools/native-v0.5/rkv1_core.dll
python -m rkv1 read snapshot.rkv table.csv --offset 4090 --length 100 --out excerpt.bin --decoder-backend rust --native-library .tools/native-v0.5/rkv1_core.dll
```

API：`Archive(path, decoder_backend="rust", native_library=path_to_library)`；`verify`
和 `unpack` 接受相同关键字参数。选择属于读取器实例，不更改全局 Python 反变换。
Python 的受限解压、单元/父块/文件 SHA-256 都继续执行。

## v0.6 实验冻结条件

为避免边测边编译，本机使用 v0.5.0 Release 的 Windows 原生候选，固定
源提交 `5418b305172d349a864f64f123070e3ee949d301` 与 DLL SHA-256
`13bd00bb7eeb5ac3f9a62cbe7e416a10b52e1ff04a1ad3815649745f06a73217`。
二进制 121,344 bytes。完整编译器、元数据大小/哈希保存在 native-provenance.json。
v0.6 内核源文件与该版本相同；新 Release 库须按自己的元数据核验，不能假设不同
构建二进制哈希相同。冻结 v0.5 元数据里的“性能未测”描述是构建时状态。

Wine/超导材料：Zlib/Zstd × 1 MiB 整块、64/16 KiB 两层单元 × none/CSV ×
Python/Rust；HTRU2 为 CR-only 负对照：Zstd/1 MiB × none/CSV × 两种后端。
共 26 份归档、52 个读取条件。每份归档编码两次检查确定性、完整 verify；两个
后端直接读取同一个归档文件。

每条件一次新进程预热恢复，再五次正式新进程恢复；预热阶段在正式阶段之前。
正式条件/轮次全部打乱，恢复记录 wall/CPU/RSS，并在计时外比较全部路径/字节。
恢复 wall 包括读取器构建、库哈希/加载、FFI、内存复制、codec 和所有校验。
两后端以同轮编号比较；编号是匹配重复观测，不代表同时执行。

范围阶段条件/轮次/读取器生命周期交错打乱，五个查询种子，每类每轮 64 条正式
请求、4 条预热。固定 64 KiB 边界，实际请求哈希必须全部匹配。范围计时前预读
归档；库按进程缓存，已预热查询不含首次加载。常驻模式 initial_open_s 另记首次
构建，重开模式首次加载发生在查询预热中。短请求不等同于应用首次启动速度。

所有归档大小包含完整元数据/索引。Rust 不改归档大小；另报 DLL+native.json
全额部署成本，正空间收益时计算分摊到 N 份同样大小归档后的成本，不能声称单份
小语料净省空间。公共 Python/操作系统/链接库未完整分配，不是完整部署大小。

源码、输入、归档、库与库元数据在实验前后校验。范围 RSS 含真值和工作账本，
不当作生产读取器内存。仅本机温缓存；冷缓存、跨机器、跨日与推理质量未测。
五轮配对方向/范围不属于显著性检验，保留普通编码和无变换负对照。

```powershell
$env:RKV_NATIVE_LIBRARY = (Resolve-Path .tools/native-v0.5/rkv1_core.dll).Path
python -m unittest discover -s tests -v
python -m scripts.run_native --native-library .tools/native-v0.5/rkv1_core.dll --out results/local-native
python -m scripts.summarize_native results/local-native
```

最后一条在数据完整后生成对比表与科学图。Linux CI 验证正确性，不提供本机或
跨机器的性能复测结论。后续根据测得热点决定更广的 Rust 迁移。

上述v0.6完整测试命令对应v0.6.0 tag。当前v0.8完整原生测试应将
`RKV_NATIVE_LIBRARY`设为v0.8 measured库，覆盖CSV和Gear两个内核；重跑v0.6
CSV性能矩阵时仍通过`run_native --native-library`明确选择冻结v0.5库。
