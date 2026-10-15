# RKV1-FORMAT · Draft 0.6

v0.12新增显式 **v6布局扩展**：顶层layout=fixed/fits-segments-v1，允许较短区域块并
记录实际数值变换，分段读取器构建原始长度前缀数组做范围定位。默认格式不变。
布局规则、引用上限、v6严格校验及v1–v5兼容见[LAYOUT.md](LAYOUT.md)。

v0.11新增显式专业codec的 **v5平块扩展**。字段沿用v4，允许原有none/数值变换，
另允许九个 `blosc-zstd-{none,shuffle,bitshuffle}-{2,4,8}` codec（只许外层transform=none）。
专业codec自动写v5；也可显式选择v5做普通/数值对照。v4拒绝专业codec，v5拒绝
CSV/独立单元。默认none仍写v2，普通数值策略自动写v4，单元仍v3，CAS格式1不变。
Blosc固定参数、16-byte帧头、解码上界/结构验证及兼容规则见
[SCIENTIFIC.md](SCIENTIFIC.md)。v0.10及更早读取器拒绝v5；新读取器继续读v1–v4。

v0.10新增显式数值策略的**v4平块扩展**，字段/限制与兼容说明见
[NUMERIC.md](NUMERIC.md)。v4只允许none及数值字节策略；旧读取器拒绝v4。
默认写入、既有CSV v2和独立单元v3语义保持不变，以下历史v1/v2/v3规范仍有效。

v0.5.0 读取器支持 manifest version=1/2/3。默认写 version=2；显式指定 unit_size
才写 version=3。v0.4.0 及更早读取器不能读 v3；升级后仍恢复 v1/v2，默认 v2
归档字节保持兼容。发布前验证 v1 实际归档与 v0.4 core 生成的 v2 固定归档。
[v1 规范](FORMAT-v1.md)、[v2 规范](FORMAT-v2.md) 保留，旧 Release/tag 不改写。

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

## Version 3：父块与独立单元

文件仍按 chunk_size 切父块，files/chunks 与父块 SHA-256 的意义不变。顶层字段
沿用 v2 并增加 `unit_size`；大小至少 4096 bytes、不超过 chunk_size，须整除
chunk_size。块内按 unit_size 分单元，末单元可短；每个单元独立压缩、反变换和校验。
默认外层块 1 MiB；实验扫描 16/64 KiB 单元，参数不代表通用最优。

```json
{
  "version": 3, "chunk_size": 1048576, "unit_size": 65536,
  "compression": "zstd", "deduplicate": true, "transform": "csv-columns-v1",
  "files": [{"path": "data.csv", "size": 120000, "sha256": "<file hash>", "chunks": ["<parent id>"]}],
  "blocks": {"<parent id>": {
    "offset": 0, "stored_size": 50000, "raw_size": 120000, "codec": "units-v1",
    "unit_count": 2, "index_size": 96, "index_sha256": "<index hash>"
  }}
}
```

示例大小/hash 仅说明字段；真实归档必须符合全部大小关系。每父块 body 为固定宽度
二进制单元索引，随后是顺序排列的单元 payload。索引长 `ceil(raw_size/unit_size)*48`。
`index_sha256` 由顶层清单校验链约束；首次使用索引时验 SHA-256，再检查全部条目。
每条目为 little-endian `<IIIBBH32s>`：

| 字段 | 大小 / 意义 |
|---|---|
| raw_size | u32；除末单元外为完整 unit_size |
| stored_size | u32；1–raw_size，payload 中无间隙 |
| coded_size | u32；反变换前长度，1–2*raw_size+256 |
| codec | u8；0=raw、1=Zlib 6、2=Zstd 3 |
| transform | u8；0=none、1=CSV-COLUMNS-V1 |
| reserved | u16；必须为 0 |
| raw_sha256 | 32 bytes 原始单元摘要 |

单元偏移由前面 stored_size 的前缀和得出；原文偏移由序号*unit_size 得出。不存
外部指针或可执行代码，不依赖外部字典/模型。raw 单元要求 stored=coded=raw 且
transform=none；压缩单元 codec 须等于顶层策略、stored<raw；none 要求 coded=raw。
变换仅在顶层允许时使用，CSV 候选比普通 payload 小才选用；索引两种标志成本相同。

父块 stored_size 包含索引和所有单元 payload，可能比 raw_size 大；合法范围为
`index_size+unit_count <= stored_size <= index_size+raw_size`。索引校验后要求全部
单元 stored_size 总和恰好覆盖父块 body。全局父块仍无重叠/间隙/尾随数据。

### 校验范围与缓存

部分范围请求只恢复触及的单元，验证索引和这些单元的原始 SHA-256；没有宣称验证
未触及单元或整个父块。完整父块恢复另验父块 SHA-256；完整文件读取/verify/unpack
继续验文件 SHA-256。未触及单元损坏可不影响局部读取，但完整 verify 必须失败。
哈希链仍只处理完整性，不能证明来源身份。

索引按需加载，读取器缓存已校验的索引及偏移；默认计费预算 1 MiB、最多 128 个
父块，LRU 淘汰。计费为二进制字节+每偏移40 bytes+每项256 bytes，属于保守的实现
估算，并非操作系统 RSS 硬限制。不缓存恢复后的单元，payload 每次仍读取和校验。
读取器假设打开期间归档不可变，已缓存索引不会反复读取原地修改的文件内容。

### 成本和复用

`stored_bytes = metadata_bytes + unit_index_bytes + encoded_payload_bytes`。
metadata_bytes 为 prefix+JSON；兼容字段 payload_bytes 指整个 body，已经含二进制
索引，不能再重复加索引成本。total_metadata_bytes 为 JSON/prefix 与单元索引之和。
共享 decoder/runtime 另记，不把归档大小当作完整部署占用。

去重和 base 复用仍以整个父块为粒度。单元 SHA-256 用于校验，不代表实现跨父块
单元去重、追加式多版本 CAS 或 CDC。base 需同父块大小、单元大小、codec、transform，
复用前恢复并验证父块，输出完整独立快照。

## 解码、增量与限制

v1/v2 清单验证后按 codec 恢复 coded_size，必要时反变换至 raw_size，验证块/文件哈希；
v3 按上面的独立单元协议读取。
Zlib 限制输出、拒绝剩余输入和未结束流；Zstd 拒绝错误长度、过大窗口、外部字典、
额外帧或尾随数据。inspect 只验清单；range read 验触及块，完整文件读也验文件；
verify/unpack 验全部引用。

写入同目录临时文件，flush/fsync 后原子发布；恢复在私有目录全部验证后发布。
从v0.13起，归档解包默认sync_policy=files，每个完整原始文件SHA验证后执行
flush→fsync→close（含空文件），全部文件完成后再发布目录。同步错误直接失败；
显式close保留历史关闭边界。verify不写文件，不同步。发布rename仅对Windows
5/32/33错误有界尝试4次；永久失败传播，不重试fsync，不覆盖既有目标。
没有目录/卷同步、真实掉电或多写者事务保证；发布后强杀可留下完整目标但没有成功
返回，发布前强杀可能残留私有暂存。CAS恢复保持既有语义。策略不改变归档字节。
v0.12及以前归档解包没有逐文件fsync，历史时序不包含该成本；详见PERSISTENCE.md。
增量 base 需同块大小、compression、transform；v1 base 按 Zlib/none 解释。
复用前验证块，输出完整独立快照，仍全量读取源数据并写新容器。

限制：清单 64 MiB、100,000 文件、500,000 块、2 GiB 恢复总量、块 1 byte–8 MiB、
单次 range read 64 MiB。拒绝越界/特殊路径、文件名冲突、链接/reparse point 和
特殊文件。未承诺生产级多写者事务、掉电目录持久性、纠错或备份。

## v0.14兼容说明

本版没有新格式，跨域实验全部显式v4平块，仅用既有none/byte-shuffle策略。默认
none仍写v2，既有v1–v6读取、CAS1与v0.13归档恢复files语义保持不变。SAC/DCD
结构扫描只作计时外provenance，不影响编码路由，解码不需要ObsPy/MDAnalysis。
新增scratch/JSONL是评测选项，不是归档字段。输入源码/TeX不执行或语义规范化。

## v0.15应用层记忆元数据

原始证据沿用CAS1，归档v1–v6无变更。memory/目录的SQLite FTS5索引、版本1清单、
HEAD及派生answers是应用层元数据，详见[MEMORY.md](MEMORY.md)。每个清单绑定
CAS快照、源文件和索引SHA；句子引用绑定原记录定位与句子SHA，不是科学蕴含证明。

## v0.16应用层记忆清单v2

归档v1–v6和CAS1未改。新索引为contentless FTS5与原记录定位表，清单v2绑定基础
索引SHA/基础CAS快照、不可变增量链和当前完整来源树；HEAD仍在验证完当前视图后
发布。增量含父/新快照、删除key和新定位，Zlib压缩并绑定SHA/原长度。查询在内存
复制/重放以保持全库BM25，不存完整查询视图。详见[MEMORY-INDEX.md](MEMORY-INDEX.md)。
v0.16兼容旧v1应用清单；v0.15不读新v2清单。无自动迁移、GC或掉电验证。

## v0.17应用层记忆清单v3

归档v1–v6/CAS1不变；索引库schema仍为contentless FTS5与定位表。新v3清单最多一份
基础相对overlay，删除/改写/新增定位与位置区间分开。overlay绑定基础/当前CAS快照、
压缩SHA和原长度；仅位置变化不算FTS记录改写。区间以基础坐标统一选rowid后移动，
避免交叉重复移动。超过25%非位置变化或256区间建检查点，保留全部旧文件。v0.16
拒绝v3，新读取器兼容v1/v2；源索引策略/分块模式不自动迁移。详见MEMORY-UPDATES.md。
