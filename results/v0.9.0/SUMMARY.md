# v0.9.0 同格式CAS对象IO消融与独立版本家族

分别测QASPER三个原始发布和Evidence Inference三个官方发布的两张原始主CSV表。
全部Zstd3，Gear使用相同冻结v0.8 Rust库；无CSV变换/模型。默认reference/link保持不变。
八条件包括旧独立1MiB、共享固定64KiB、独立/共享冻结v0.8 Gear、当前reference/link、
bounded/link、reference/Windows rename及组合。逐新文件flush/fsync、全部复用验证保留。

logical计全部对象84-byte头/双摘要/payload、配置/快照及未引用对象；本表原生库另计。
allocated为正式第0轮文件数据extent，不含完整目录/MFT/日志。提交含初始化、库首次
身份检查/加载、全量扫描、压缩、旧对象验证与发布。恢复为三次独立进程耗时之和，
再取轮次中位。范围为最后版本byte_weighted组各轮p95的中位。原始wall/CPU/RSS均保留。
所有同kind/profile条件完整存储树、快照和对象账本相同，读取前后存储树不变。

## qasper

原文合计128,076,252 bytes，8条件、5轮。

| 条件 | logical bytes | allocated数据 bytes | 文件数 | 提交 s | 恢复 s | 常驻p95 ms | 重开p95 ms |
|---|---|---|---|---|---|---|---|
| archive-fixed-1024 | 31519475 | 31522816 | 3 | 0.671 | 0.260 | 1.673 | 2.287 |
| isolated-gear-v08 | 35408908 | 38224616 | 1436 | 3.084 | 0.518 | 0.551 | 3.746 |
| shared-fixed-v08 | 35981908 | 39780480 | 1928 | 4.502 | 0.579 | 0.409 | 4.533 |
| shared-gear-bounded | 23946864 | 25759992 | 914 | 2.491 | 0.511 | 0.510 | 3.814 |
| shared-gear-combined | 23946864 | 25759992 | 914 | 2.124 | 0.511 | 0.528 | 3.822 |
| shared-gear-reference | 23946864 | 25759992 | 914 | 2.397 | 0.515 | 0.532 | 3.801 |
| shared-gear-rename | 23946864 | 25759992 | 914 | 2.632 | 0.517 | 0.548 | 3.853 |
| shared-gear-v08 | 23946864 | 25759992 | 914 | 2.463 | 0.518 | 0.525 | 3.773 |

### 相同框架的配对

倍率=reference/candidate，每轮比值后取中位；范围是描述统计，不是置信区间。

| reference | candidate | 指标 | 配对加速中位 | 逐轮范围 | candidate更快轮数 |
|---|---|---|---|---|---|
| reference | v08 | add | 0.973× | 0.669–1.271× | 2/5 |
| reference | bounded | add | 0.889× | 0.649–1.549× | 1/5 |
| reference | rename | add | 0.760× | 0.657–1.388× | 2/5 |
| reference | combined | add | 0.974× | 0.854–1.466× | 2/5 |
| reference | bounded | restore | 1.008× | 0.989–1.047× | 3/5 |
| reference | bounded | open_reader | 1.103× | 0.919–1.138× | 4/5 |
| reference | bounded | open_and_read | 0.991× | 0.967–1.166× | 2/5 |
| rename | combined | restore | 1.017× | 1.007–1.547× | 5/5 |
| rename | combined | open_reader | 1.021× | 0.922–1.038× | 4/5 |
| rename | combined | open_and_read | 1.001× | 0.921–1.054× | 3/5 |

组合提交配对中位0.974×，2/5轮更快。逐轮波动跨过1；不从两个耗时中位之比推算配对收益。

同表示共享节省32.371%；本家族单独部署加整份库后24,071,283bytes，对独立1MiB减少23.630%。

原文件整文件复用背景（不等同于块复用）：v1 0/41,339,485原文字节来自早期相同文件, v2 0/43,368,694原文字节来自早期相同文件, v3 0/43,368,073原文字节来自早期相同文件。

## evidence

原文合计18,747,243 bytes，8条件、5轮。

| 条件 | logical bytes | allocated数据 bytes | 文件数 | 提交 s | 恢复 s | 常驻p95 ms | 重开p95 ms |
|---|---|---|---|---|---|---|---|
| archive-fixed-1024 | 3760981 | 3764224 | 3 | 0.083 | 0.049 | 1.381 | 1.731 |
| isolated-gear-v08 | 4370481 | 4715240 | 177 | 0.285 | 0.083 | 0.492 | 1.371 |
| shared-fixed-v08 | 2768755 | 3100800 | 181 | 0.281 | 0.095 | 0.343 | 1.495 |
| shared-gear-bounded | 2608262 | 2818296 | 104 | 0.291 | 0.081 | 0.492 | 1.366 |
| shared-gear-combined | 2608262 | 2818296 | 104 | 0.214 | 0.080 | 0.492 | 1.427 |
| shared-gear-reference | 2608262 | 2818296 | 104 | 0.223 | 0.083 | 0.511 | 1.451 |
| shared-gear-rename | 2608262 | 2818296 | 104 | 0.256 | 0.081 | 0.565 | 1.366 |
| shared-gear-v08 | 2608262 | 2818296 | 104 | 0.216 | 0.083 | 0.500 | 1.524 |

### 相同框架的配对

倍率=reference/candidate，每轮比值后取中位；范围是描述统计，不是置信区间。

| reference | candidate | 指标 | 配对加速中位 | 逐轮范围 | candidate更快轮数 |
|---|---|---|---|---|---|
| reference | v08 | add | 1.003× | 0.937–1.569× | 3/5 |
| reference | bounded | add | 0.766× | 0.666–1.597× | 2/5 |
| reference | rename | add | 0.929× | 0.476–1.599× | 1/5 |
| reference | combined | add | 1.026× | 0.976–1.584× | 4/5 |
| reference | bounded | restore | 1.034× | 0.994–1.116× | 4/5 |
| reference | bounded | open_reader | 1.081× | 0.773–1.149× | 3/5 |
| reference | bounded | open_and_read | 1.036× | 0.988–1.174× | 4/5 |
| rename | combined | restore | 1.013× | 0.974–1.070× | 4/5 |
| rename | combined | open_reader | 1.149× | 1.057–1.173× | 5/5 |
| rename | combined | open_and_read | 0.996× | 0.831–1.095× | 2/5 |

组合提交配对中位1.026×，4/5轮更快。逐轮波动跨过1；不从两个耗时中位之比推算配对收益。

同表示共享节省40.321%；本家族单独部署加整份库后2,732,681bytes，对独立1MiB减少27.341%。

原文件整文件复用背景（不等同于块复用）：v1 0/6,248,459原文字节来自早期相同文件, v2 1,119,110/6,249,392原文字节来自早期相同文件, v3 1,119,110/6,249,392原文字节来自早期相同文件。

## 验证、资源与范围

两家族共240次正式完整恢复、92,160次正式范围读取，
另48次恢复预热、5,760次查询预热，全部逐字节一致。
DLL 123,904bytes + 原始元数据515bytes = 124,419bytes，
每家族单独部署上表全额加一次。两个独立仓库共用同一份库时，总逻辑成本
26,679,545bytes，对各自独立归档之和35,280,456bytes减少
24.379%；这是资源摊销情景，未做跨家族CAS去重。

候选不改编码，默认reference/link不变。rename只有Windows发布路径变化，read路径
与reference相同；不把其读取波动解释为rename解码加速。bounded仍检查对象路径和
完整EOF、全部SHA与受限解压。每个新文件仍flush/fsync，不以减少同步次数换速度。
Gear scale64KiB不保证实际均值一致，不是FastCDC。本机温缓存五轮，不做统计显著
或全局最优结论；冷缓存、跨机器、跨日和推理质量未测。范围RSS含真值和账本，
编码RSS含树审计，不当作生产内存。无GC或断电耐久性证明。

Evidence Inference只测两张官方原始主表，prompts三版完全相同；不能把此家族较高
共享收益推广至论文全文或独立科学数据。来源范围、固定commit/SHA见DATASETS/IO协议。
