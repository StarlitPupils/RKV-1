# 精确 CSV Rust 内核与配对实验

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
