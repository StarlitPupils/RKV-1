# Shared CAS draft 0.1 / v0.7 protocol

这是独立于 RKV 归档 v1/v2/v3 的可选目录存储。原有 pack/read/unpack 默认与格式
保持不变。CAS 保留原始普通文件相对路径和字节，不保存权限、时间、链接或空目录。

## 目录与格式

```
vault/
  config.rkvc
  objects/ab/<remaining 62 lowercase hex digits>
  snapshots/<64 lowercase hex digits>.rkvs
```

config/snapshot：8-byte magic（RKVCAS1\n / RKVSNP1\n）、u64 little-endian JSON
长度、32-byte SHA-256(JSON)、UTF-8 canonical JSON。JSON 按键排序、紧凑分隔、
不转义 Unicode，拒绝重复键/非规范表示。长度最多64MiB；config最多64KiB。
摘要检查损坏，不建立来源身份。snapshot ID 是其 canonical JSON SHA-256。

config 固定 version=1、compression（raw/Zlib6/Zstd3，单帧、无字典）和 chunker。
Snapshot 包含 version=1、config_sha256、label、files；每个文件有 path、size、
原始文件 sha256、按原始字节顺序的 chunks=[{id,size},...]。对象 id 是原始块 SHA-256，
由内容决定，不含路径。因此保留原始版本文件名也可跨版本复用同一对象。

对象头固定84bytes，Python struct `<8sBBHII32s32s`：magic=RKVOBJ1\n，codec u8
（0raw/1zlib/2zstd）、flags u8=0、reserved u16=0、raw_size u32、stored_size u32、
原始 SHA-256、存储 payload SHA-256，随后唯一 payload。压缩不比原文小则用raw。
大小/codec/摘要/尾部均验证；受限解压后再次核对原始 SHA。完整恢复还核对文件 SHA。
局部读取仅核对触及对象，未触及损坏需对应完整 snapshot verify 检出。

快照最多2GiB原文、100000文件、500000引用；读取范围最多64MiB。对象不超过分块
配置最大值，所有非尾块满足配置最小值。内部路径拒绝软链接/junction/reparse point。
调用者选择的根目录与父目录必须可信；不支持源目录和 store 重叠。

## 分块与提交语义

fixed：固定 size，4096..8MiB，尾块可更短。
gear-v1：size 为2的幂，4096..2MiB；min=size/4、max=4*size。
表项为 SHA256(b"RKV1-GEAR-V1\0" + byte) 的前8字节按 little-endian 解释。
每字节 `h=((h<<1)+table[b]) mod 2^64`，长度达min且`h&(size-1)==0`，或达max时
切块；每块重置h。size是mask scale，**不保证实际平均块大小**，必须报告观测分布。
这是简单 Gear CDC，不是 FastCDC 复现；背景参考
[FastCDC 原论文](https://www.usenix.org/conference/atc16/technical-sessions/presentation/xia)。

只新增不可变对象和快照。新文件先在同目录写临时文件、flush/fsync，再用不覆盖
的原子 link 发布。对象全部发布后才发布快照；同ID重复提交不新增对象/快照。
已有对象复用前须解码核对，不能用损坏旧对象继续提交。同调用内重复对象在校验
后复用。源文件仍全量读取/哈希，不是避免扫描的增量系统。

中断提交可留下未引用对象，存储账本包含它们；无GC/删除功能。已发布快照不被
回滚或改写。原子名称发布不等于断电耐久性保证；没有目录fsync/故障注入电源测试。
统计须在无活动写入时进行；恢复逐个对象打开，不缓存已解码字节。

## 执行

```powershell
python -m rkv1 store-init data/vault --codec zstd --chunker gear-v1 --chunk-size 65536
python -m rkv1 store-add data/vault data/qasper-versions/v0.1 --label v0.1
python -m rkv1 store-add data/vault data/qasper-versions/v0.2 --label v0.2
python -m rkv1 store-stat data/vault
# 用 store-add 输出的 snapshot_id：
python -m rkv1 store-verify data/vault SNAPSHOT_ID
python -m rkv1 store-unpack data/vault SNAPSHOT_ID data/restored-v0.1
python -m rkv1 store-read data/vault SNAPSHOT_ID qasper-train-v0.1.json --offset 4090 --length 100 --out data/excerpt.bin
python -m scripts.run_versions --out results/local-versions
python -m scripts.summarize_versions results/local-versions --plot
```

## 冻结实验

QASPER 官方原始 train/dev v0.1→v0.2→v0.3，原文件名/字节均保留，不解析后重写。
归档/成员 SHA 在 version_data.py 和 dataset-provenance.json 固定。来源及许可见
[官方数据卡](https://huggingface.co/datasets/allenai/qasper)。这是一个语料家族的三次
真实发布，不当作三个独立科学数据集，也不把差异自动解释为单一编辑操作。

八条件：独立 RKV 固定64KiB/1MiB；独立 CAS 固定64KiB/1MiB/Gear scale64KiB；
共享 CAS 同三种边界。全部 Zstd3、无 CSV/模型/外部字典/原生后端。
同边界的独立/共享 CAS 快照ID相同、object文件字节集合相同，仅存储份数不同。
它们用于隔离共享效果；旧 RKV 与 CAS 的格式/对象校验不同，不声称是单变量对照。

每条件一次预热完整序列，再五次正式完整序列；序列内部必须按版本顺序提交。
条件/重复编号打乱。每个快照单独新进程恢复，全部路径/字节比较。每轮完整存储
树哈希必须一致；读取前后树不变。提交含压缩、复用验证、fsync与发布，独立 CAS
的初始化计入每版提交；共享初始化单记并计入完整序列总耗时。

每版五个种子、每类别64正式查询/4预热、常驻/重开分别测。全条件实际请求哈希
匹配，固定64KiB跨边界窗口仅定义查询位置，不保证每次跨过变量块。计时前预读
选定快照记录及触及对象集合，或完整旧归档。范围工作账本不是物理磁盘IO计数。

完整账本累计所有 config、snapshot、object 头/摘要/payload、未引用对象；对比每版
新增写入与最终总文件字节数。Windows 额外读取 FILE_STANDARD_INFO.AllocationSize，
POSIX用st_blocks*512。它们是已分配文件数据空间，未包含目录/MFT resident属性/
日志等全部文件系统成本；报告文件数，不称为完整物理卷占用。参考
[Microsoft FILE_STANDARD_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_standard_info)。
分配空间/完整树扫描在提交计时外；编码进程RSS仍包含这些未计时账本操作。
范围RSS额外包含真值、预读对象清单/元数据与独立工作账本，不能当作生产读取器RAM。

全部控制共享相同 v0.7 Python 部署；codec/系统/公共运行时未全额分配每个归档。
只报告本机温缓存、五轮描述统计；冷缓存/跨机器/跨日/推理质量均未测。
