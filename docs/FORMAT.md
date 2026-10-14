# RKV1-FORMAT · Draft 0.2

首次实现于软件 v0.2.0。新写入器产生 manifest version=2；读取器支持 version=1/2。
旧版 v0.1.0 不能读取新版，升级后仍可直接恢复旧归档。发布前使用 v0.1.0 实际生成
的固定归档测试兼容性。[旧版规范](FORMAT-v1.md) 保留，旧 Release/tag 不改写。

## 保真与布局

恢复普通文件相对路径和全部原始字节，不保留空子目录、权限、时间戳、ACL、扩展属性
或链接关系。源目录在打包时必须保持稳定，输出父目录由调用方管理。

| 偏移 | 长度 | 内容 |
|---:|---:|---|
| 0 | 8 | Magic `52 4b 56 31 0d 0a 1a 0a` |
| 8 | 8 | manifest 字节长度 H，unsigned little-endian |
| 16 | 32 | SHA-256(manifest 原始 UTF-8 字节) |
| 48 | H | UTF-8 JSON manifest |
| 48+H | 其余 | 连续块 payload |

JSON 不接受重复键/未知字段。写入器排序键、紧凑 UTF-8 序列化。清单先验哈希再解析。
SHA-256 检测损坏、定位内容，不提供来源身份认证。

## Version 2 清单

```json
{
  "version": 2, "chunk_size": 1048576,
  "compression": "zstd", "deduplicate": true, "transform": "none",
  "files": [{"path": "data.bin", "size": 3, "sha256": "<file hash>", "chunks": ["<block id>"]}],
  "blocks": {"<block id>": {
    "offset": 0, "stored_size": 3, "raw_size": 3, "codec": "raw",
    "coded_size": 3, "transform": "none"
  }}
}
```

占位 hash 不是有效归档。实际 SHA-256 为 64 位小写十六进制。

- compression 为 raw/zlib/zstd；固定 Zlib 6 / Zstd 3。Zstd 帧含 content size 和
  checksum，不使用外部字典或额外线程。
- deduplicate=true 时 block id 为原始块 SHA-256；重复引用共用 payload。
  false 时 id 为 `<SHA-256>@<8位小写十六进制occurrence index>`，index 从 0 连续编号，
  每块恰好引用一次。两模式均计算和验证原始哈希。
- 顶层 transform 为 none/csv-columns-v1，表示允许的策略；每块记录实际采用的变换。
  不符合条件或收益不足时回退 none。
- raw_size 为原始块长；coded_size 为变换后、压缩前长度。none 时两者相等；
  变换结果上限 `2*raw_size+256`。
- offset 相对 payload 起点。所有范围无重叠、无间隙、无尾随数据，全部块均被引用。
  文件除尾块外必须为完整 chunk_size；空文件不引用块。
- stored_size 不大于 raw_size，压缩不缩小时保留原始字节。

CSV 策略先做普通压缩，再尝试列重排压缩，仅当块 payload 的节省足以抵消更长的
transform/coded_size 字段才选择变换。完整归档总大小仍需实测，顶层策略和后续偏移
等开销无法仅靠单块估算完全预测。策略默认关闭。

## CSV-COLUMNS-V1

保留字节的列重排，不转换 float，不规范化字符串/换行。接受逗号/分号分隔且列数一致
的数值行；支持整数、小数、正负号、科学计数法、空格/tab。带引号的数据、空值、
NaN/Inf、混合列数等回退普通编码。

块内第一行和最后一个 LF 后的尾部按原样保存，保留表头与跨块不完整行；中间完整行
按列重排，逐行保存 LF/CRLF。所有恢复仅依赖本块。

| 字段 | 编码 |
|---|---|
| Magic | 8 bytes `RKVCSV1\n` |
| delimiter / flags | 各 1 byte；flags=0 |
| columns | u16 little-endian |
| rows / prefix_size / suffix_size / original_size | 各 u32 little-endian |
| prefix / suffix | 原始边界字节 |
| endings | rows bytes，0=LF、1=CRLF |
| cells | 列优先数值原文，以 LF 分隔，共 rows*columns 个单元 |

最多 65,536 行、256 列、262,144 单元。解码器检查维度、语法、换行表与完整输出长度
后重建原块，继续检查原始 SHA-256。

## 解码、增量与限制

清单验证后按 codec 恢复 coded_size，必要时反变换至 raw_size，验证块/文件哈希。
Zlib 限制输出、拒绝剩余输入和未结束流；Zstd 拒绝错误长度、过大窗口、外部字典、
额外帧或尾随数据。inspect 只验清单；range read 验触及块，完整文件读也验文件；
verify/unpack 验全部引用。

写入同目录临时文件，flush/fsync 后原子发布；恢复在私有目录全部验证后发布。
增量 base 需同块大小、compression、transform；v1 base 按 Zlib/none 解释。
复用前验证块，输出完整独立快照，仍全量读取源数据并写新容器。

限制：清单 64 MiB、100,000 文件、500,000 块、2 GiB 恢复总量、块 1 byte–8 MiB、
单次 range read 64 MiB。拒绝越界/特殊路径、文件名冲突、链接/reparse point 和
特殊文件。未承诺生产级多写者事务、掉电目录持久性、纠错或备份。
