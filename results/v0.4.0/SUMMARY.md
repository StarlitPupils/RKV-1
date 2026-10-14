# v0.4.0 E2 独立数值数据与 CSV 反变换优化

3 组语料、18 个条件；**90 次正式完整恢复 + 18 次预热恢复**，
**15,360 次正式范围读取 + 1,920 次预热范围读取**全部逐字节一致。
同一 CSV 归档在旧/新反变换条件间复用，原文数值、换行和文件哈希保持一致。

增加 HTRU2 脉冲星候选与 Superconductivity 两个原始公开数据集；Wine 作为已有对照。
HTRU2 使用 CR-only 换行，当前 CSV v1 不适用，必须回退且不规范化。Superconductivity
保留 train.csv 与含化学式的 unique_m.csv，混合非数值数据也可回退；不筛选只报正结果。

优化只把按单元索引的 Python 生成器替换为列切片 + zip 重建，保留词法、维度、长度
和最终块 SHA-256 校验。无格式变化、无新模型或字典，默认 CSV 仍关闭。

## 空间与完整恢复

同 codec、1 MiB；耗时为记录轮次中位数。旧基线是冻结的 v0.3 CSV 反变换，其余代码
共享本版实现，因此不是把两次历史整机运行直接比较。

| 数据 | codec | 普通 bytes | CSV bytes | 空间节省 | 变换块/全部块 | 旧 CSV 恢复 ms | 新 CSV 恢复 ms | 旧/新耗时 | 更快轮数 | 新 CSV/普通耗时 |
|---|---|---|---|---|---|---|---|---|---|---|
| wine | zlib | 93493 | 89174 | 4.620% | 2/2 | 33.879 | 28.100 | 1.21× | 5/5 | 6.68× |
| wine | zstd | 98417 | 98019 | 0.404% | 1/2 | 13.096 | 11.965 | 1.09× | 4/5 | 2.17× |
| htru2 | zlib | 781993 | 782003 | -0.001% | 0/2 | 9.688 | 9.427 | 无变换 | — | 0.95× |
| htru2 | zstd | 788646 | 788656 | -0.001% | 0/2 | 8.473 | 8.261 | 无变换 | — | 0.96× |
| superconductivity | zlib | 8258627 | 7284903 | 11.790% | 23/28 | 791.358 | 687.129 | 1.15× | 5/5 | 7.17× |
| superconductivity | zstd | 7548059 | 7442705 | 1.396% | 14/28 | 496.877 | 429.114 | 1.16× | 5/5 | 6.94× |

HTRU2 的回退没有 CSV 算法收益；微小时间差属于对照波动。启用策略的头部会有少量固定成本。

## 跨 codec 的体积对照

仅在本轮 Zlib/Zstd 中，分别选择普通与 CSV 条件的最小归档；不代表全部成熟方法的最优。

| 数据 | 普通最小体积 codec | 普通 bytes | 普通恢复 ms | CSV 最小体积 codec | CSV bytes | CSV 恢复 ms | 净空间节省 | CSV/普通恢复耗时 |
|---|---|---|---|---|---|---|---|---|
| wine | zlib | 93493 | 4.206 | zlib | 89174 | 28.100 | 4.620% | 6.68× |
| htru2 | zlib | 781993 | 9.940 | zlib | 782003 | 9.427 | -0.001% | 0.95× |
| superconductivity | zstd | 7548059 | 61.856 | zlib | 7284903 | 687.129 | 3.486% | 11.11× |

## 加权范围读取与内存

延迟为各轮 p95 中位数；每轮每类别请求数见 protocol，样本量较小，不替代 v0.3 读取矩阵。

| 数据 | codec | 条件 | 常驻 p95 ms | 重开 p95 ms | 恢复峰值 MiB |
|---|---|---|---|---|---|
| wine | zlib | plain | 0.820 | 1.031 | 26.14 |
| wine | zlib | legacy_csv | 23.950 | 24.930 | 29.89 |
| wine | zlib | current_csv | 20.327 | 20.302 | 29.88 |
| wine | zstd | plain | 0.432 | 0.661 | 26.12 |
| wine | zstd | legacy_csv | 7.814 | 7.740 | 26.88 |
| wine | zstd | current_csv | 6.081 | 6.495 | 26.97 |
| htru2 | zlib | plain | 3.828 | 4.144 | 28.03 |
| htru2 | zlib | legacy_csv | 3.812 | 4.107 | 28.06 |
| htru2 | zlib | current_csv | 3.789 | 4.343 | 27.87 |
| htru2 | zstd | plain | 2.027 | 2.285 | 27.49 |
| htru2 | zstd | legacy_csv | 1.955 | 2.188 | 27.67 |
| htru2 | zstd | current_csv | 1.931 | 2.393 | 27.61 |
| superconductivity | zlib | plain | 3.283 | 3.885 | 28.79 |
| superconductivity | zlib | legacy_csv | 39.134 | 38.585 | 36.54 |
| superconductivity | zlib | current_csv | 33.314 | 33.071 | 38.43 |
| superconductivity | zstd | plain | 1.686 | 2.285 | 28.06 |
| superconductivity | zstd | legacy_csv | 36.700 | 37.613 | 36.73 |
| superconductivity | zstd | current_csv | 31.570 | 32.044 | 38.18 |

## 诊断与解释边界

- wine/zlib：取一个 84,199 bytes 的变换块，分别诊断旧/新反变换三次；全部函数计数/时间在 JSON。
- wine/zstd：取一个 84,199 bytes 的变换块，分别诊断旧/新反变换三次；全部函数计数/时间在 JSON。
- htru2/zlib：没有实际变换块，反变换 profile=null。
- htru2/zstd：没有实际变换块，反变换 profile=null。
- superconductivity/zlib：取一个 1,048,576 bytes 的变换块，分别诊断旧/新反变换三次；全部函数计数/时间在 JSON。
- superconductivity/zstd：取一个 1,048,576 bytes 的变换块，分别诊断旧/新反变换三次；全部函数计数/时间在 JSON。


cProfile 的累计时间有嵌套重叠且受 instrumentation 影响；不能相加成总 CPU 占比，
也不能用它替代独立 worker 的耗时对照。列切片会增加引用存储，必须同时看 RSS。
词法正则验证仍保留，是后续 Rust/解析优化候选；本版没有 Rust 加速结果。

范围读取仍重建完整变换块，局部循环优化不能保证随机访问的综合收益。体积和耗时
应分别验收；保持可选策略。单机、温缓存、五轮默认样本，不声称通用最优或显著性。
归档字节包含所有元数据，运行时账本另记实验源码；冻结旧解码器是共享实验资源，
不是每个归档的模型/字典。完整 Python/共享原生依赖仍未全额分摊。

下一步：依据诊断结果改善类型表示和块内访问，再开展真实版本序列/共享块存储；
数组、代码、数学文本和 E3/E4 尚待推进。见 [CSV-TRIALS.md](../../docs/CSV-TRIALS.md)。
