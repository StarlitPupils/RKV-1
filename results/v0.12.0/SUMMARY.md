# v0.12.0 FITS 类型分流与区域分块

规则/矩阵/验收在新验证输入压缩结果之前固定，见 docs/LAYOUT.md（协议提交38473b2）。
Spitzer为已见开发记录；M13 float64与ROSAT float32为新增验证记录。
它们仍是同一托管项目的天文示例，不称跨领域或严格盲测。ECG和噪声为未识别格式对照。
所有原文件头/数据/填充原样恢复，不解析或重写数值。规则只识别完整单一2D浮点主图像。

每组20条件：Zlib6/Zstd3 ×64KiB/1MiB ×五种方法，全同v6。
普通固定块；整文件字节重排；固定块仅对完全位于图像中的块重排；仅分段；分段且仅图像重排。
全量归档计prefix/JSON/路径/块/文件SHA与实际配方；分段读取器另建前缀偏移数组，逻辑字节和RSS分别报告。
候选分配完整layouts.py一次，配置数值策略另分配完整numeric.py一次，包括未识别格式回退。
公共Python/core/Zstd和pyc未全额分配，不称完整部署成本；无专用DLL/模型/字典。

一次完整预热+五轮正式，条件/轮次打乱；分阶段新进程测wall/CPU/RSS，范围请求跨条件/模式匹配。
本机温OS缓存；重开读取器不是冷磁盘。p95指各轮p95的中位，配对速度是逐轮baseline/candidate再取中位。
持久性口径：归档编码flush/fsync后发布；归档解包关闭文件并校验后发布目录，未逐文件fsync。
此前部分说明对恢复文件fsync描述过强，本版校正，不将未执行的操作计入结果或承诺掉电持久性。

## spitzer32

Development；原始 2,113,920 B。

BITPIX -32，FITS轴 [1025, 513]，头/图像/填充 8,640/2,103,300/1,980 B；NaN 3，正零 0/525,825（0.0000%）。

| 配置 | 归档 B | 专用源一次 B | 偏移数组 B | 编码 ms | 恢复 ms | 常驻p95 ms | 重开p95 ms |
|---|---|---|---|---|---|---|---|
| zlib/64KiB/ordinary | 1853090 | 0 | 0 | 65.638 | 12.059 | 0.236 | 0.968 |
| zlib/64KiB/global-shuffle | 1655910 | 1431 | 0 | 109.692 | 9.321 | 0.175 | 0.668 |
| zlib/64KiB/typed-fixed | 1661295 | 4824 | 0 | 104.679 | 9.236 | 0.228 | 0.759 |
| zlib/64KiB/segmented-none | 1853131 | 3393 | 288 | 67.604 | 12.269 | 0.452 | 0.917 |
| zlib/64KiB/typed-segmented | 1654670 | 4824 | 288 | 102.043 | 9.505 | 0.252 | 0.840 |
| zstd/64KiB/ordinary | 1845184 | 0 | 0 | 14.396 | 9.176 | 0.093 | 0.874 |
| zstd/64KiB/global-shuffle | 1662023 | 1431 | 0 | 16.967 | 8.784 | 0.126 | 0.692 |
| zstd/64KiB/typed-fixed | 1666672 | 4824 | 0 | 15.925 | 8.851 | 0.124 | 0.686 |
| zstd/64KiB/segmented-none | 1845252 | 3393 | 288 | 14.547 | 9.071 | 0.167 | 0.596 |
| zstd/64KiB/typed-segmented | 1660725 | 4824 | 288 | 16.700 | 9.646 | 0.149 | 0.752 |
| zlib/1024KiB/ordinary | 1845778 | 0 | 0 | 74.183 | 12.668 | 4.664 | 5.252 |
| zlib/1024KiB/global-shuffle | 1631970 | 1431 | 0 | 119.871 | 10.969 | 3.696 | 4.170 |
| zlib/1024KiB/typed-fixed | 1739659 | 4824 | 0 | 96.012 | 11.338 | 5.009 | 4.876 |
| zlib/1024KiB/segmented-none | 1845802 | 3393 | 48 | 77.230 | 13.285 | 4.918 | 4.849 |
| zlib/1024KiB/typed-segmented | 1630773 | 4824 | 48 | 118.284 | 10.961 | 3.345 | 4.585 |
| zstd/1024KiB/ordinary | 1838188 | 0 | 0 | 15.193 | 9.334 | 1.899 | 2.361 |
| zstd/1024KiB/global-shuffle | 1644778 | 1431 | 0 | 19.157 | 9.919 | 2.723 | 2.765 |
| zstd/1024KiB/typed-fixed | 1741901 | 4824 | 0 | 17.684 | 9.848 | 2.986 | 2.831 |
| zstd/1024KiB/segmented-none | 1838160 | 3393 | 48 | 14.399 | 9.382 | 2.011 | 2.514 |
| zstd/1024KiB/typed-segmented | 1643579 | 4824 | 48 | 18.179 | 10.108 | 2.712 | 2.997 |

### 同后端/块大小消融

倍率为逐轮配对中位，大于1更快，括号为更快轮数；完整CPU/RSS/原始样本保留于JSON。

| 基线 | 候选 | 计源净省 | 编码配对 | 恢复配对 | 常驻配对 | 重开配对 |
|---|---|---|---|---|---|---|
| zlib/64KiB/ordinary | zlib/64KiB/global-shuffle | 10.563% | 0.604× (0/5) | 1.331× (5/5) | 1.642× (5/5) | 1.334× (4/5) |
| zlib/64KiB/ordinary | zlib/64KiB/typed-fixed | 10.090% | 0.648× (0/5) | 1.321× (5/5) | 1.085× (4/5) | 1.188× (4/5) |
| zlib/64KiB/ordinary | zlib/64KiB/segmented-none | -0.185% | 0.977× (2/5) | 0.975× (2/5) | 0.660× (1/5) | 1.040× (3/5) |
| zlib/64KiB/segmented-none | zlib/64KiB/typed-segmented | 10.613% | 0.646× (0/5) | 1.278× (5/5) | 1.631× (5/5) | 1.102× (4/5) |
| zlib/64KiB/typed-fixed | zlib/64KiB/typed-segmented | 0.398% | 0.951× (2/5) | 0.970× (2/5) | 0.906× (2/5) | 0.787× (2/5) |
| zlib/64KiB/global-shuffle | zlib/64KiB/typed-segmented | -0.130% | 1.070× (3/5) | 0.968× (1/5) | 0.656× (0/5) | 0.790× (2/5) |
| zlib/64KiB/ordinary | zlib/64KiB/typed-segmented | 10.447% | 0.632× (0/5) | 1.281× (5/5) | 0.974× (2/5) | 1.146× (4/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/global-shuffle | 11.506% | 0.614× (0/5) | 1.185× (5/5) | 1.264× (5/5) | 1.219× (5/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/typed-fixed | 5.488% | 0.767× (0/5) | 1.116× (5/5) | 0.977× (2/5) | 1.109× (4/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/segmented-none | -0.185% | 0.967× (1/5) | 0.953× (1/5) | 0.948× (2/5) | 1.083× (4/5) |
| zlib/1024KiB/segmented-none | zlib/1024KiB/typed-segmented | 11.551% | 0.643× (0/5) | 1.219× (5/5) | 1.428× (5/5) | 1.087× (4/5) |
| zlib/1024KiB/typed-fixed | zlib/1024KiB/typed-segmented | 6.242% | 0.789× (0/5) | 1.044× (4/5) | 1.406× (5/5) | 1.088× (4/5) |
| zlib/1024KiB/global-shuffle | zlib/1024KiB/typed-segmented | -0.134% | 1.006× (3/5) | 1.004× (4/5) | 1.183× (5/5) | 1.016× (3/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/typed-segmented | 11.387% | 0.627× (0/5) | 1.209× (5/5) | 1.457× (5/5) | 1.148× (4/5) |
| zstd/64KiB/ordinary | zstd/64KiB/global-shuffle | 9.849% | 0.887× (0/5) | 1.057× (4/5) | 1.073× (3/5) | 1.488× (3/5) |
| zstd/64KiB/ordinary | zstd/64KiB/typed-fixed | 9.413% | 0.945× (1/5) | 1.022× (3/5) | 0.972× (1/5) | 1.332× (3/5) |
| zstd/64KiB/ordinary | zstd/64KiB/segmented-none | -0.188% | 0.990× (2/5) | 1.042× (3/5) | 0.718× (1/5) | 1.520× (4/5) |
| zstd/64KiB/segmented-none | zstd/64KiB/typed-segmented | 9.904% | 0.830× (0/5) | 0.906× (2/5) | 1.080× (4/5) | 0.764× (0/5) |
| zstd/64KiB/typed-fixed | zstd/64KiB/typed-segmented | 0.356% | 0.957× (0/5) | 0.975× (1/5) | 0.955× (2/5) | 0.815× (1/5) |
| zstd/64KiB/global-shuffle | zstd/64KiB/typed-segmented | -0.126% | 0.988× (2/5) | 0.911× (0/5) | 0.949× (2/5) | 0.901× (2/5) |
| zstd/64KiB/ordinary | zstd/64KiB/typed-segmented | 9.735% | 0.906× (0/5) | 0.950× (2/5) | 0.821× (2/5) | 1.123× (3/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/global-shuffle | 10.444% | 0.863× (1/5) | 0.941× (1/5) | 0.753× (0/5) | 0.876× (0/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/typed-fixed | 4.976% | 0.810× (2/5) | 0.961× (2/5) | 0.640× (0/5) | 0.921× (0/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/segmented-none | -0.183% | 1.082× (3/5) | 0.996× (2/5) | 0.944× (2/5) | 0.936× (2/5) |
| zstd/1024KiB/segmented-none | zstd/1024KiB/typed-segmented | 10.488% | 0.777× (0/5) | 0.928× (1/5) | 0.700× (1/5) | 0.731× (1/5) |
| zstd/1024KiB/typed-fixed | zstd/1024KiB/typed-segmented | 5.629% | 1.003× (3/5) | 0.974× (2/5) | 1.096× (4/5) | 0.928× (0/5) |
| zstd/1024KiB/global-shuffle | zstd/1024KiB/typed-segmented | -0.133% | 1.045× (3/5) | 0.955× (1/5) | 0.887× (2/5) | 0.923× (1/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/typed-segmented | 10.325% | 0.836× (2/5) | 0.921× (1/5) | 0.699× (0/5) | 0.741× (0/5) |

### 预定联合验收

须同时胜过同codec/块的ordinary与global-shuffle的预定门槛；编码独立披露，非综合支配判定。

| 分段类型配置 | 通过 |
|---|---|
| zlib/64KiB/typed-segmented | False |
| zlib/1024KiB/typed-segmented | False |
| zstd/64KiB/typed-segmented | False |
| zstd/1024KiB/typed-segmented | False |

### 每种方法事后最小归档

限本矩阵的体积选参，不是预先固定的部署配置或速度最优；不替代上面的同配置验收。

| 方法 | 最小配置 | 归档 B | 加源后净省 |
|---|---|---|---|
| ordinary | zstd/1024KiB/ordinary | 1838188 | 0.000% |
| global-shuffle | zlib/1024KiB/global-shuffle | 1631970 | 11.141% |
| typed-fixed | zlib/64KiB/typed-fixed | 1661295 | 9.361% |
| segmented-none | zstd/1024KiB/segmented-none | 1838160 | -0.183% |
| typed-segmented | zlib/1024KiB/typed-segmented | 1630773 | 11.021% |

## m13_64

New record validation; not used to choose routing rules or compression parameters；原始 11,586,240 B。

BITPIX -64，FITS轴 [1392, 1040]，头/图像/填充 2,880/11,581,440/1,920 B；NaN 0，正零 1/1,447,680（0.0001%）。

| 配置 | 归档 B | 专用源一次 B | 偏移数组 B | 编码 ms | 恢复 ms | 常驻p95 ms | 重开p95 ms |
|---|---|---|---|---|---|---|---|
| zlib/64KiB/ordinary | 2682144 | 0 | 0 | 469.982 | 32.568 | 0.230 | 1.822 |
| zlib/64KiB/global-shuffle | 1888621 | 1431 | 0 | 655.397 | 35.864 | 0.261 | 1.828 |
| zlib/64KiB/typed-fixed | 1896259 | 4824 | 0 | 651.397 | 35.963 | 0.261 | 1.829 |
| zlib/64KiB/segmented-none | 2682708 | 3393 | 1440 | 469.480 | 33.346 | 0.234 | 1.928 |
| zlib/64KiB/typed-segmented | 1888917 | 4824 | 1440 | 660.088 | 36.265 | 0.261 | 1.932 |
| zstd/64KiB/ordinary | 2815434 | 0 | 0 | 53.335 | 33.294 | 0.223 | 1.805 |
| zstd/64KiB/global-shuffle | 1802707 | 1431 | 0 | 63.686 | 28.475 | 0.158 | 1.748 |
| zstd/64KiB/typed-fixed | 1812412 | 4824 | 0 | 63.650 | 27.423 | 0.161 | 1.791 |
| zstd/64KiB/segmented-none | 2815670 | 3393 | 1440 | 54.817 | 33.742 | 0.225 | 1.791 |
| zstd/64KiB/typed-segmented | 1803350 | 4824 | 1440 | 63.850 | 27.666 | 0.163 | 2.002 |
| zlib/1024KiB/ordinary | 2599278 | 0 | 0 | 501.447 | 32.500 | 2.271 | 2.685 |
| zlib/1024KiB/global-shuffle | 1701177 | 1431 | 0 | 734.972 | 38.638 | 2.942 | 3.395 |
| zlib/1024KiB/typed-fixed | 1785491 | 4824 | 0 | 710.991 | 37.792 | 3.003 | 3.406 |
| zlib/1024KiB/segmented-none | 2599713 | 3393 | 120 | 499.847 | 33.059 | 2.439 | 2.824 |
| zlib/1024KiB/typed-segmented | 1701455 | 4824 | 120 | 733.137 | 38.341 | 2.925 | 3.451 |
| zstd/1024KiB/ordinary | 2753841 | 0 | 0 | 53.832 | 32.337 | 2.168 | 2.512 |
| zstd/1024KiB/global-shuffle | 1669954 | 1431 | 0 | 65.757 | 28.650 | 1.905 | 2.245 |
| zstd/1024KiB/typed-fixed | 1771666 | 4824 | 0 | 64.439 | 29.811 | 1.983 | 2.334 |
| zstd/1024KiB/segmented-none | 2754165 | 3393 | 120 | 52.716 | 30.792 | 2.063 | 2.507 |
| zstd/1024KiB/typed-segmented | 1670183 | 4824 | 120 | 67.908 | 29.888 | 1.921 | 2.307 |

### 同后端/块大小消融

倍率为逐轮配对中位，大于1更快，括号为更快轮数；完整CPU/RSS/原始样本保留于JSON。

| 基线 | 候选 | 计源净省 | 编码配对 | 恢复配对 | 常驻配对 | 重开配对 |
|---|---|---|---|---|---|---|
| zlib/64KiB/ordinary | zlib/64KiB/global-shuffle | 29.532% | 0.717× (0/5) | 0.914× (0/5) | 0.890× (1/5) | 1.042× (3/5) |
| zlib/64KiB/ordinary | zlib/64KiB/typed-fixed | 29.121% | 0.721× (0/5) | 0.899× (0/5) | 0.890× (1/5) | 1.072× (4/5) |
| zlib/64KiB/ordinary | zlib/64KiB/segmented-none | -0.148% | 0.999× (2/5) | 0.978× (0/5) | 0.983× (1/5) | 0.949× (1/5) |
| zlib/64KiB/segmented-none | zlib/64KiB/typed-segmented | 29.499% | 0.712× (0/5) | 0.922× (0/5) | 0.873× (1/5) | 0.976× (2/5) |
| zlib/64KiB/typed-fixed | zlib/64KiB/typed-segmented | 0.386% | 0.985× (0/5) | 1.008× (3/5) | 1.060× (3/5) | 0.908× (1/5) |
| zlib/64KiB/global-shuffle | zlib/64KiB/typed-segmented | -0.195% | 0.994× (1/5) | 0.981× (1/5) | 1.019× (3/5) | 0.918× (0/5) |
| zlib/64KiB/ordinary | zlib/64KiB/typed-segmented | 29.395% | 0.711× (0/5) | 0.901× (0/5) | 0.862× (0/5) | 0.978× (2/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/global-shuffle | 34.497% | 0.683× (0/5) | 0.838× (0/5) | 0.777× (0/5) | 0.835× (0/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/typed-fixed | 31.123% | 0.706× (0/5) | 0.850× (0/5) | 0.756× (0/5) | 0.802× (0/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/segmented-none | -0.147% | 0.998× (2/5) | 0.983× (2/5) | 0.904× (1/5) | 0.946× (2/5) |
| zlib/1024KiB/segmented-none | zlib/1024KiB/typed-segmented | 34.452% | 0.679× (1/5) | 0.862× (0/5) | 0.851× (0/5) | 0.818× (0/5) |
| zlib/1024KiB/typed-fixed | zlib/1024KiB/typed-segmented | 4.694% | 0.969× (0/5) | 0.997× (2/5) | 1.021× (3/5) | 1.013× (3/5) |
| zlib/1024KiB/global-shuffle | zlib/1024KiB/typed-segmented | -0.216% | 1.003× (3/5) | 1.010× (3/5) | 0.973× (2/5) | 0.980× (1/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/typed-segmented | 34.356% | 0.681× (0/5) | 0.847× (0/5) | 0.770× (0/5) | 0.803× (0/5) |
| zstd/64KiB/ordinary | zstd/64KiB/global-shuffle | 35.920% | 0.841× (0/5) | 1.150× (5/5) | 1.464× (5/5) | 1.046× (3/5) |
| zstd/64KiB/ordinary | zstd/64KiB/typed-fixed | 35.454% | 0.831× (0/5) | 1.214× (5/5) | 1.378× (5/5) | 1.005× (3/5) |
| zstd/64KiB/ordinary | zstd/64KiB/segmented-none | -0.129% | 0.978× (2/5) | 0.963× (0/5) | 0.966× (2/5) | 1.018× (4/5) |
| zstd/64KiB/segmented-none | zstd/64KiB/typed-segmented | 35.859% | 0.847× (0/5) | 1.240× (5/5) | 1.404× (5/5) | 0.926× (1/5) |
| zstd/64KiB/typed-fixed | zstd/64KiB/typed-segmented | 0.499% | 0.998× (2/5) | 0.992× (2/5) | 1.002× (3/5) | 0.906× (0/5) |
| zstd/64KiB/global-shuffle | zstd/64KiB/typed-segmented | -0.224% | 0.985× (2/5) | 1.007× (3/5) | 0.969× (0/5) | 0.897× (0/5) |
| zstd/64KiB/ordinary | zstd/64KiB/typed-segmented | 35.776% | 0.824× (0/5) | 1.204× (5/5) | 1.380× (5/5) | 0.939× (2/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/global-shuffle | 39.307% | 0.820× (0/5) | 1.123× (5/5) | 1.107× (4/5) | 1.192× (4/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/typed-fixed | 35.490% | 0.838× (0/5) | 1.100× (4/5) | 1.055× (4/5) | 1.094× (4/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/segmented-none | -0.135% | 1.032× (3/5) | 1.036× (4/5) | 0.980× (2/5) | 1.002× (3/5) |
| zstd/1024KiB/segmented-none | zstd/1024KiB/typed-segmented | 39.258% | 0.795× (0/5) | 1.044× (4/5) | 1.113× (4/5) | 1.100× (5/5) |
| zstd/1024KiB/typed-fixed | zstd/1024KiB/typed-segmented | 5.713% | 0.957× (0/5) | 0.997× (2/5) | 0.982× (2/5) | 1.021× (3/5) |
| zstd/1024KiB/global-shuffle | zstd/1024KiB/typed-segmented | -0.217% | 0.991× (2/5) | 0.977× (1/5) | 0.952× (2/5) | 0.960× (1/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/typed-segmented | 39.176% | 0.786× (0/5) | 1.087× (5/5) | 1.017× (3/5) | 1.102× (4/5) |

### 预定联合验收

须同时胜过同codec/块的ordinary与global-shuffle的预定门槛；编码独立披露，非综合支配判定。

| 分段类型配置 | 通过 |
|---|---|
| zlib/64KiB/typed-segmented | False |
| zlib/1024KiB/typed-segmented | False |
| zstd/64KiB/typed-segmented | False |
| zstd/1024KiB/typed-segmented | False |

### 每种方法事后最小归档

限本矩阵的体积选参，不是预先固定的部署配置或速度最优；不替代上面的同配置验收。

| 方法 | 最小配置 | 归档 B | 加源后净省 |
|---|---|---|---|
| ordinary | zlib/1024KiB/ordinary | 2599278 | 0.000% |
| global-shuffle | zstd/1024KiB/global-shuffle | 1669954 | 35.698% |
| typed-fixed | zstd/1024KiB/typed-fixed | 1771666 | 31.654% |
| segmented-none | zlib/1024KiB/segmented-none | 2599713 | -0.147% |
| typed-segmented | zstd/1024KiB/typed-segmented | 1670183 | 35.559% |

## rosat32

New record validation; not used to choose routing rules or compression parameters；原始 478,080 B。

BITPIX -32，FITS轴 [480, 240]，头/图像/填充 17,280/460,800/0 B；NaN 0，正零 26,100/115,200（22.6562%）。

| 配置 | 归档 B | 专用源一次 B | 偏移数组 B | 编码 ms | 恢复 ms | 常驻p95 ms | 重开p95 ms |
|---|---|---|---|---|---|---|---|
| zlib/64KiB/ordinary | 324664 | 0 | 0 | 15.197 | 4.515 | 0.222 | 0.569 |
| zlib/64KiB/global-shuffle | 296975 | 1431 | 0 | 24.903 | 4.522 | 0.259 | 0.601 |
| zlib/64KiB/typed-fixed | 297043 | 4824 | 0 | 24.848 | 4.581 | 0.353 | 0.605 |
| zlib/64KiB/segmented-none | 324408 | 3393 | 80 | 14.916 | 4.633 | 0.393 | 0.666 |
| zlib/64KiB/typed-segmented | 295427 | 4824 | 80 | 24.659 | 4.686 | 0.376 | 0.627 |
| zstd/64KiB/ordinary | 323578 | 0 | 0 | 7.567 | 5.193 | 0.098 | 0.418 |
| zstd/64KiB/global-shuffle | 298836 | 1431 | 0 | 8.761 | 5.111 | 0.119 | 0.380 |
| zstd/64KiB/typed-fixed | 298839 | 4824 | 0 | 8.713 | 5.111 | 0.128 | 0.392 |
| zstd/64KiB/segmented-none | 323366 | 3393 | 80 | 7.651 | 5.249 | 0.166 | 0.390 |
| zstd/64KiB/typed-segmented | 297604 | 4824 | 80 | 8.901 | 5.310 | 0.149 | 0.431 |
| zlib/1024KiB/ordinary | 322751 | 0 | 0 | 15.526 | 4.461 | 1.881 | 1.984 |
| zlib/1024KiB/global-shuffle | 291817 | 1431 | 0 | 27.292 | 4.848 | 2.112 | 2.240 |
| zlib/1024KiB/typed-fixed | 322767 | 4824 | 0 | 15.590 | 4.622 | 1.781 | 2.016 |
| zlib/1024KiB/segmented-none | 322529 | 3393 | 24 | 15.545 | 4.554 | 1.669 | 2.028 |
| zlib/1024KiB/typed-segmented | 290415 | 4824 | 24 | 26.656 | 4.756 | 1.856 | 2.200 |
| zstd/1024KiB/ordinary | 321984 | 0 | 0 | 7.803 | 4.894 | 0.824 | 1.107 |
| zstd/1024KiB/global-shuffle | 294301 | 1431 | 0 | 9.042 | 5.236 | 1.199 | 1.465 |
| zstd/1024KiB/typed-fixed | 322000 | 4824 | 0 | 7.381 | 4.941 | 0.856 | 1.253 |
| zstd/1024KiB/segmented-none | 321680 | 3393 | 24 | 8.098 | 5.236 | 0.808 | 1.102 |
| zstd/1024KiB/typed-segmented | 292840 | 4824 | 24 | 9.214 | 5.379 | 1.114 | 1.458 |

### 同后端/块大小消融

倍率为逐轮配对中位，大于1更快，括号为更快轮数；完整CPU/RSS/原始样本保留于JSON。

| 基线 | 候选 | 计源净省 | 编码配对 | 恢复配对 | 常驻配对 | 重开配对 |
|---|---|---|---|---|---|---|
| zlib/64KiB/ordinary | zlib/64KiB/global-shuffle | 8.088% | 0.604× (0/5) | 0.975× (1/5) | 1.009× (3/5) | 1.043× (3/5) |
| zlib/64KiB/ordinary | zlib/64KiB/typed-fixed | 7.022% | 0.622× (0/5) | 0.995× (2/5) | 1.014× (3/5) | 0.940× (0/5) |
| zlib/64KiB/ordinary | zlib/64KiB/segmented-none | -0.966% | 1.050× (3/5) | 0.974× (1/5) | 0.842× (2/5) | 0.850× (1/5) |
| zlib/64KiB/segmented-none | zlib/64KiB/typed-segmented | 8.404% | 0.606× (0/5) | 0.995× (2/5) | 1.045× (4/5) | 1.062× (4/5) |
| zlib/64KiB/typed-fixed | zlib/64KiB/typed-segmented | 0.535% | 1.010× (3/5) | 0.978× (0/5) | 0.893× (1/5) | 0.996× (1/5) |
| zlib/64KiB/global-shuffle | zlib/64KiB/typed-segmented | -0.618% | 1.004× (3/5) | 0.944× (2/5) | 0.878× (1/5) | 0.921× (1/5) |
| zlib/64KiB/ordinary | zlib/64KiB/typed-segmented | 7.519% | 0.613× (0/5) | 0.973× (1/5) | 0.759× (1/5) | 0.921× (0/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/global-shuffle | 9.141% | 0.569× (0/5) | 0.923× (0/5) | 0.940× (1/5) | 0.893× (0/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/typed-fixed | -1.500% | 1.006× (3/5) | 0.963× (2/5) | 1.137× (3/5) | 0.996× (2/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/segmented-none | -0.982% | 0.980× (2/5) | 0.980× (1/5) | 1.127× (5/5) | 0.989× (2/5) |
| zlib/1024KiB/segmented-none | zlib/1024KiB/typed-segmented | 9.414% | 0.584× (0/5) | 0.924× (2/5) | 0.904× (0/5) | 0.911× (1/5) |
| zlib/1024KiB/typed-fixed | zlib/1024KiB/typed-segmented | 9.876% | 0.582× (0/5) | 0.940× (0/5) | 0.894× (1/5) | 0.899× (0/5) |
| zlib/1024KiB/global-shuffle | zlib/1024KiB/typed-segmented | -0.679% | 1.018× (4/5) | 1.008× (3/5) | 1.138× (5/5) | 1.025× (3/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/typed-segmented | 8.524% | 0.583× (0/5) | 0.953× (0/5) | 1.017× (3/5) | 0.902× (1/5) |
| zstd/64KiB/ordinary | zstd/64KiB/global-shuffle | 7.204% | 0.853× (0/5) | 1.016× (3/5) | 1.030× (3/5) | 1.099× (4/5) |
| zstd/64KiB/ordinary | zstd/64KiB/typed-fixed | 6.155% | 0.859× (0/5) | 1.006× (3/5) | 1.044× (3/5) | 1.028× (3/5) |
| zstd/64KiB/ordinary | zstd/64KiB/segmented-none | -0.983% | 0.968× (2/5) | 0.981× (2/5) | 0.931× (2/5) | 1.010× (3/5) |
| zstd/64KiB/segmented-none | zstd/64KiB/typed-segmented | 7.446% | 0.836× (0/5) | 1.012× (3/5) | 1.091× (3/5) | 0.947× (1/5) |
| zstd/64KiB/typed-fixed | zstd/64KiB/typed-segmented | 0.407% | 0.928× (2/5) | 0.969× (1/5) | 0.948× (1/5) | 0.938× (1/5) |
| zstd/64KiB/global-shuffle | zstd/64KiB/typed-segmented | -0.720% | 0.970× (0/5) | 0.988× (2/5) | 0.833× (0/5) | 0.856× (1/5) |
| zstd/64KiB/ordinary | zstd/64KiB/typed-segmented | 6.536% | 0.797× (0/5) | 0.973× (1/5) | 0.974× (1/5) | 1.015× (3/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/global-shuffle | 8.153% | 0.856× (0/5) | 0.983× (2/5) | 0.659× (0/5) | 0.805× (1/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/typed-fixed | -1.503% | 1.066× (3/5) | 1.000× (3/5) | 0.962× (2/5) | 0.884× (2/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/segmented-none | -0.959% | 0.934× (1/5) | 0.943× (0/5) | 1.028× (4/5) | 1.036× (3/5) |
| zstd/1024KiB/segmented-none | zstd/1024KiB/typed-segmented | 8.432% | 0.885× (0/5) | 0.979× (1/5) | 0.741× (0/5) | 0.762× (0/5) |
| zstd/1024KiB/typed-fixed | zstd/1024KiB/typed-segmented | 8.922% | 0.811× (0/5) | 0.919× (0/5) | 0.715× (0/5) | 0.826× (0/5) |
| zstd/1024KiB/global-shuffle | zstd/1024KiB/typed-segmented | -0.653% | 0.936× (1/5) | 0.959× (0/5) | 1.103× (5/5) | 1.079× (4/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/typed-segmented | 7.553% | 0.833× (0/5) | 0.923× (0/5) | 0.743× (0/5) | 0.821× (1/5) |

### 预定联合验收

须同时胜过同codec/块的ordinary与global-shuffle的预定门槛；编码独立披露，非综合支配判定。

| 分段类型配置 | 通过 |
|---|---|
| zlib/64KiB/typed-segmented | False |
| zlib/1024KiB/typed-segmented | False |
| zstd/64KiB/typed-segmented | False |
| zstd/1024KiB/typed-segmented | False |

### 每种方法事后最小归档

限本矩阵的体积选参，不是预先固定的部署配置或速度最优；不替代上面的同配置验收。

| 方法 | 最小配置 | 归档 B | 加源后净省 |
|---|---|---|---|
| ordinary | zstd/1024KiB/ordinary | 321984 | 0.000% |
| global-shuffle | zlib/1024KiB/global-shuffle | 291817 | 8.925% |
| typed-fixed | zlib/64KiB/typed-fixed | 297043 | 6.248% |
| segmented-none | zstd/1024KiB/segmented-none | 321680 | -0.959% |
| typed-segmented | zlib/1024KiB/typed-segmented | 290415 | 8.306% |

## ecg

Unrecognized-format control；原始 1,154,687 B。

| 配置 | 归档 B | 专用源一次 B | 偏移数组 B | 编码 ms | 恢复 ms | 常驻p95 ms | 重开p95 ms |
|---|---|---|---|---|---|---|---|
| zlib/64KiB/ordinary | 869176 | 0 | 0 | 39.344 | 9.729 | 0.362 | 0.917 |
| zlib/64KiB/global-shuffle | 635362 | 1431 | 0 | 57.953 | 7.330 | 0.185 | 0.685 |
| zlib/64KiB/typed-fixed | 869192 | 4824 | 0 | 40.563 | 9.879 | 0.317 | 0.866 |
| zlib/64KiB/segmented-none | 869187 | 3393 | 184 | 40.488 | 9.910 | 0.427 | 1.069 |
| zlib/64KiB/typed-segmented | 869203 | 4824 | 184 | 40.033 | 9.866 | 0.372 | 0.909 |
| zstd/64KiB/ordinary | 882277 | 0 | 0 | 10.370 | 7.583 | 0.106 | 0.624 |
| zstd/64KiB/global-shuffle | 659231 | 1431 | 0 | 12.032 | 7.706 | 0.105 | 0.559 |
| zstd/64KiB/typed-fixed | 882293 | 4824 | 0 | 9.526 | 7.752 | 0.097 | 0.544 |
| zstd/64KiB/segmented-none | 882288 | 3393 | 184 | 9.827 | 7.807 | 0.106 | 0.580 |
| zstd/64KiB/typed-segmented | 882304 | 4824 | 184 | 10.039 | 7.319 | 0.115 | 0.563 |
| zlib/1024KiB/ordinary | 865406 | 0 | 0 | 43.216 | 9.961 | 4.649 | 4.864 |
| zlib/1024KiB/global-shuffle | 627728 | 1431 | 0 | 62.546 | 7.649 | 2.615 | 2.773 |
| zlib/1024KiB/typed-fixed | 865422 | 4824 | 0 | 42.654 | 9.588 | 4.518 | 4.845 |
| zlib/1024KiB/segmented-none | 865417 | 3393 | 48 | 43.056 | 9.701 | 4.416 | 4.761 |
| zlib/1024KiB/typed-segmented | 865433 | 4824 | 48 | 43.240 | 9.892 | 4.559 | 5.198 |
| zstd/1024KiB/ordinary | 874083 | 0 | 0 | 12.125 | 8.073 | 1.736 | 2.180 |
| zstd/1024KiB/global-shuffle | 632643 | 1431 | 0 | 14.533 | 7.985 | 2.087 | 2.604 |
| zstd/1024KiB/typed-fixed | 874099 | 4824 | 0 | 12.401 | 8.147 | 1.730 | 2.086 |
| zstd/1024KiB/segmented-none | 874094 | 3393 | 48 | 12.152 | 7.821 | 1.789 | 2.176 |
| zstd/1024KiB/typed-segmented | 874110 | 4824 | 48 | 12.670 | 8.606 | 1.851 | 2.245 |

### 同后端/块大小消融

倍率为逐轮配对中位，大于1更快，括号为更快轮数；完整CPU/RSS/原始样本保留于JSON。

| 基线 | 候选 | 计源净省 | 编码配对 | 恢复配对 | 常驻配对 | 重开配对 |
|---|---|---|---|---|---|---|
| zlib/64KiB/ordinary | zlib/64KiB/global-shuffle | 26.736% | 0.687× (0/5) | 1.294× (5/5) | 1.945× (4/5) | 1.315× (5/5) |
| zlib/64KiB/ordinary | zlib/64KiB/typed-fixed | -0.557% | 0.946× (1/5) | 0.979× (1/5) | 1.123× (3/5) | 1.094× (3/5) |
| zlib/64KiB/ordinary | zlib/64KiB/segmented-none | -0.392% | 0.981× (1/5) | 0.986× (2/5) | 0.882× (2/5) | 0.988× (2/5) |
| zlib/64KiB/segmented-none | zlib/64KiB/typed-segmented | -0.166% | 1.014× (3/5) | 1.016× (3/5) | 1.093× (3/5) | 1.176× (3/5) |
| zlib/64KiB/typed-fixed | zlib/64KiB/typed-segmented | -0.001% | 1.015× (3/5) | 1.013× (4/5) | 0.858× (1/5) | 1.015× (3/5) |
| zlib/64KiB/global-shuffle | zlib/64KiB/typed-segmented | -37.254% | 1.460× (5/5) | 0.750× (0/5) | 0.494× (1/5) | 0.753× (0/5) |
| zlib/64KiB/ordinary | zlib/64KiB/typed-segmented | -0.558% | 1.002× (3/5) | 0.985× (1/5) | 0.961× (0/5) | 1.047× (3/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/global-shuffle | 27.299% | 0.691× (0/5) | 1.276× (5/5) | 1.813× (5/5) | 1.802× (5/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/typed-fixed | -0.559% | 0.996× (2/5) | 0.992× (2/5) | 1.029× (4/5) | 1.019× (4/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/segmented-none | -0.393% | 0.992× (2/5) | 1.022× (4/5) | 1.060× (4/5) | 0.974× (2/5) |
| zlib/1024KiB/segmented-none | zlib/1024KiB/typed-segmented | -0.167% | 0.983× (0/5) | 0.982× (1/5) | 0.958× (0/5) | 0.933× (1/5) |
| zlib/1024KiB/typed-fixed | zlib/1024KiB/typed-segmented | -0.001% | 0.991× (1/5) | 0.989× (2/5) | 1.010× (3/5) | 0.898× (1/5) |
| zlib/1024KiB/global-shuffle | zlib/1024KiB/typed-segmented | -38.321% | 1.443× (5/5) | 0.749× (0/5) | 0.569× (0/5) | 0.558× (0/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/typed-segmented | -0.561% | 0.974× (1/5) | 0.978× (2/5) | 1.037× (3/5) | 0.908× (2/5) |
| zstd/64KiB/ordinary | zstd/64KiB/global-shuffle | 25.119% | 0.867× (1/5) | 0.953× (2/5) | 1.024× (4/5) | 1.139× (4/5) |
| zstd/64KiB/ordinary | zstd/64KiB/typed-fixed | -0.549% | 1.089× (5/5) | 0.978× (2/5) | 1.004× (3/5) | 1.126× (4/5) |
| zstd/64KiB/ordinary | zstd/64KiB/segmented-none | -0.386% | 1.064× (4/5) | 0.992× (2/5) | 0.978× (2/5) | 1.097× (4/5) |
| zstd/64KiB/segmented-none | zstd/64KiB/typed-segmented | -0.163% | 0.983× (2/5) | 1.054× (4/5) | 1.009× (3/5) | 1.040× (4/5) |
| zstd/64KiB/typed-fixed | zstd/64KiB/typed-segmented | -0.001% | 0.966× (1/5) | 1.048× (3/5) | 0.973× (1/5) | 1.010× (3/5) |
| zstd/64KiB/global-shuffle | zstd/64KiB/typed-segmented | -34.279% | 1.208× (5/5) | 1.026× (3/5) | 0.929× (1/5) | 0.998× (2/5) |
| zstd/64KiB/ordinary | zstd/64KiB/typed-segmented | -0.550% | 1.054× (4/5) | 1.016× (3/5) | 0.950× (1/5) | 1.137× (4/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/global-shuffle | 27.458% | 0.829× (0/5) | 0.976× (2/5) | 0.823× (0/5) | 0.814× (0/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/typed-fixed | -0.554% | 0.993× (2/5) | 0.989× (2/5) | 1.016× (4/5) | 1.018× (3/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/segmented-none | -0.389% | 0.985× (2/5) | 0.988× (2/5) | 1.011× (3/5) | 1.024× (3/5) |
| zstd/1024KiB/segmented-none | zstd/1024KiB/typed-segmented | -0.165% | 0.957× (1/5) | 0.938× (0/5) | 0.948× (1/5) | 0.977× (1/5) |
| zstd/1024KiB/typed-fixed | zstd/1024KiB/typed-segmented | -0.001% | 0.949× (2/5) | 0.947× (1/5) | 0.947× (1/5) | 0.997× (2/5) |
| zstd/1024KiB/global-shuffle | zstd/1024KiB/typed-segmented | -38.617% | 1.212× (5/5) | 0.914× (2/5) | 1.157× (5/5) | 1.160× (4/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/typed-segmented | -0.555% | 1.015× (3/5) | 0.927× (1/5) | 0.949× (1/5) | 0.948× (1/5) |

### 预定联合验收

须同时胜过同codec/块的ordinary与global-shuffle的预定门槛；编码独立披露，非综合支配判定。

| 分段类型配置 | 通过 |
|---|---|
| zlib/64KiB/typed-segmented | False |
| zlib/1024KiB/typed-segmented | False |
| zstd/64KiB/typed-segmented | False |
| zstd/1024KiB/typed-segmented | False |

### 每种方法事后最小归档

限本矩阵的体积选参，不是预先固定的部署配置或速度最优；不替代上面的同配置验收。

| 方法 | 最小配置 | 归档 B | 加源后净省 |
|---|---|---|---|
| ordinary | zlib/1024KiB/ordinary | 865406 | 0.000% |
| global-shuffle | zlib/1024KiB/global-shuffle | 627728 | 27.299% |
| typed-fixed | zlib/1024KiB/typed-fixed | 865422 | -0.559% |
| segmented-none | zlib/1024KiB/segmented-none | 865417 | -0.393% |
| typed-segmented | zlib/1024KiB/typed-segmented | 865433 | -0.561% |

## noise

Unrecognized-format control；原始 262,147 B。

| 配置 | 归档 B | 专用源一次 B | 偏移数组 B | 编码 ms | 恢复 ms | 常驻p95 ms | 重开p95 ms |
|---|---|---|---|---|---|---|---|
| zlib/64KiB/ordinary | 263640 | 0 | 0 | 8.629 | 3.016 | 0.034 | 0.266 |
| zlib/64KiB/global-shuffle | 263653 | 1431 | 0 | 12.739 | 3.220 | 0.036 | 0.260 |
| zlib/64KiB/typed-fixed | 263656 | 4824 | 0 | 8.579 | 3.022 | 0.039 | 0.229 |
| zlib/64KiB/segmented-none | 263651 | 3393 | 48 | 9.151 | 3.185 | 0.038 | 0.234 |
| zlib/64KiB/typed-segmented | 263667 | 4824 | 48 | 8.537 | 3.211 | 0.035 | 0.253 |
| zstd/64KiB/ordinary | 263640 | 0 | 0 | 5.827 | 3.045 | 0.037 | 0.309 |
| zstd/64KiB/global-shuffle | 263653 | 1431 | 0 | 6.342 | 3.293 | 0.035 | 0.272 |
| zstd/64KiB/typed-fixed | 263656 | 4824 | 0 | 6.163 | 3.101 | 0.038 | 0.282 |
| zstd/64KiB/segmented-none | 263651 | 3393 | 48 | 5.952 | 3.102 | 0.038 | 0.250 |
| zstd/64KiB/typed-segmented | 263667 | 4824 | 48 | 6.197 | 3.086 | 0.065 | 0.349 |
| zlib/1024KiB/ordinary | 262694 | 0 | 0 | 9.060 | 3.177 | 0.116 | 0.400 |
| zlib/1024KiB/global-shuffle | 262707 | 1431 | 0 | 13.204 | 3.093 | 0.120 | 0.274 |
| zlib/1024KiB/typed-fixed | 262710 | 4824 | 0 | 8.366 | 3.051 | 0.121 | 0.318 |
| zlib/1024KiB/segmented-none | 262705 | 3393 | 16 | 8.734 | 2.935 | 0.124 | 0.376 |
| zlib/1024KiB/typed-segmented | 262721 | 4824 | 16 | 8.435 | 2.881 | 0.123 | 0.304 |
| zstd/1024KiB/ordinary | 262694 | 0 | 0 | 6.303 | 2.897 | 0.125 | 0.304 |
| zstd/1024KiB/global-shuffle | 262707 | 1431 | 0 | 6.686 | 2.840 | 0.117 | 0.320 |
| zstd/1024KiB/typed-fixed | 262710 | 4824 | 0 | 6.098 | 2.918 | 0.121 | 0.370 |
| zstd/1024KiB/segmented-none | 262705 | 3393 | 16 | 6.260 | 3.172 | 0.141 | 0.341 |
| zstd/1024KiB/typed-segmented | 262721 | 4824 | 16 | 6.070 | 2.957 | 0.119 | 0.369 |

### 同后端/块大小消融

倍率为逐轮配对中位，大于1更快，括号为更快轮数；完整CPU/RSS/原始样本保留于JSON。

| 基线 | 候选 | 计源净省 | 编码配对 | 恢复配对 | 常驻配对 | 重开配对 |
|---|---|---|---|---|---|---|
| zlib/64KiB/ordinary | zlib/64KiB/global-shuffle | -0.548% | 0.695× (0/5) | 0.919× (0/5) | 0.954× (0/5) | 1.099× (5/5) |
| zlib/64KiB/ordinary | zlib/64KiB/typed-fixed | -1.836% | 1.018× (3/5) | 1.014× (3/5) | 0.908× (2/5) | 1.193× (4/5) |
| zlib/64KiB/ordinary | zlib/64KiB/segmented-none | -1.291% | 0.968× (0/5) | 0.933× (1/5) | 0.939× (2/5) | 1.132× (4/5) |
| zlib/64KiB/segmented-none | zlib/64KiB/typed-segmented | -0.542% | 1.047× (4/5) | 1.053× (3/5) | 1.030× (3/5) | 1.003× (3/5) |
| zlib/64KiB/typed-fixed | zlib/64KiB/typed-segmented | -0.004% | 1.047× (3/5) | 0.941× (2/5) | 1.008× (3/5) | 0.881× (2/5) |
| zlib/64KiB/global-shuffle | zlib/64KiB/typed-segmented | -1.285% | 1.458× (5/5) | 0.981× (2/5) | 1.043× (4/5) | 1.027× (3/5) |
| zlib/64KiB/ordinary | zlib/64KiB/typed-segmented | -1.840% | 1.017× (3/5) | 0.952× (1/5) | 0.991× (1/5) | 1.051× (4/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/global-shuffle | -0.550% | 0.677× (0/5) | 1.027× (3/5) | 0.958× (0/5) | 1.413× (4/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/typed-fixed | -1.842% | 1.086× (4/5) | 1.046× (3/5) | 0.967× (1/5) | 1.179× (5/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/segmented-none | -1.296% | 1.043× (4/5) | 1.032× (3/5) | 0.953× (0/5) | 1.017× (5/5) |
| zlib/1024KiB/segmented-none | zlib/1024KiB/typed-segmented | -0.544% | 1.023× (4/5) | 1.026× (3/5) | 1.034× (3/5) | 1.270× (4/5) |
| zlib/1024KiB/typed-fixed | zlib/1024KiB/typed-segmented | -0.004% | 0.983× (2/5) | 1.022× (3/5) | 1.013× (3/5) | 0.993× (2/5) |
| zlib/1024KiB/global-shuffle | zlib/1024KiB/typed-segmented | -1.290% | 1.556× (5/5) | 1.008× (3/5) | 1.004× (3/5) | 0.869× (1/5) |
| zlib/1024KiB/ordinary | zlib/1024KiB/typed-segmented | -1.847% | 1.067× (4/5) | 1.082× (4/5) | 0.949× (2/5) | 1.339× (5/5) |
| zstd/64KiB/ordinary | zstd/64KiB/global-shuffle | -0.548% | 0.990× (2/5) | 0.935× (0/5) | 1.018× (4/5) | 1.058× (4/5) |
| zstd/64KiB/ordinary | zstd/64KiB/typed-fixed | -1.836% | 1.018× (3/5) | 0.954× (1/5) | 1.037× (3/5) | 1.084× (4/5) |
| zstd/64KiB/ordinary | zstd/64KiB/segmented-none | -1.291% | 1.014× (3/5) | 0.954× (2/5) | 0.997× (2/5) | 0.963× (2/5) |
| zstd/64KiB/segmented-none | zstd/64KiB/typed-segmented | -0.542% | 0.942× (1/5) | 0.976× (2/5) | 0.928× (2/5) | 0.671× (2/5) |
| zstd/64KiB/typed-fixed | zstd/64KiB/typed-segmented | -0.004% | 1.002× (3/5) | 1.032× (3/5) | 0.972× (1/5) | 0.809× (2/5) |
| zstd/64KiB/global-shuffle | zstd/64KiB/typed-segmented | -1.285% | 1.017× (3/5) | 1.067× (3/5) | 0.923× (1/5) | 0.856× (1/5) |
| zstd/64KiB/ordinary | zstd/64KiB/typed-segmented | -1.840% | 0.976× (2/5) | 0.991× (1/5) | 1.014× (3/5) | 1.032× (3/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/global-shuffle | -0.550% | 0.900× (1/5) | 1.012× (3/5) | 1.050× (3/5) | 0.953× (0/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/typed-fixed | -1.842% | 0.988× (2/5) | 1.038× (3/5) | 0.997× (2/5) | 0.873× (2/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/segmented-none | -1.296% | 0.956× (2/5) | 0.985× (0/5) | 0.888× (1/5) | 0.851× (2/5) |
| zstd/1024KiB/segmented-none | zstd/1024KiB/typed-segmented | -0.544% | 1.033× (4/5) | 1.108× (4/5) | 1.121× (5/5) | 0.835× (2/5) |
| zstd/1024KiB/typed-fixed | zstd/1024KiB/typed-segmented | -0.004% | 0.975× (2/5) | 1.023× (3/5) | 1.036× (4/5) | 1.031× (3/5) |
| zstd/1024KiB/global-shuffle | zstd/1024KiB/typed-segmented | -1.290% | 1.095× (4/5) | 0.961× (1/5) | 1.000× (2/5) | 0.908× (2/5) |
| zstd/1024KiB/ordinary | zstd/1024KiB/typed-segmented | -1.847% | 1.038× (3/5) | 1.020× (3/5) | 1.052× (4/5) | 0.866× (1/5) |

### 预定联合验收

须同时胜过同codec/块的ordinary与global-shuffle的预定门槛；编码独立披露，非综合支配判定。

| 分段类型配置 | 通过 |
|---|---|
| zlib/64KiB/typed-segmented | False |
| zlib/1024KiB/typed-segmented | False |
| zstd/64KiB/typed-segmented | False |
| zstd/1024KiB/typed-segmented | False |

### 每种方法事后最小归档

限本矩阵的体积选参，不是预先固定的部署配置或速度最优；不替代上面的同配置验收。

| 方法 | 最小配置 | 归档 B | 加源后净省 |
|---|---|---|---|
| ordinary | zlib/1024KiB/ordinary | 262694 | 0.000% |
| global-shuffle | zlib/1024KiB/global-shuffle | 262707 | -0.550% |
| typed-fixed | zlib/1024KiB/typed-fixed | 262710 | -1.842% |
| segmented-none | zlib/1024KiB/segmented-none | 262705 | -1.296% |
| typed-segmented | zlib/1024KiB/typed-segmented | 262721 | -1.847% |

## 两份新增验证输入合计，专用源共用一次

这是独立归档加总，无CAS；每组事后选最小归档，不按速度选，M13大文件主导合计。

| 方法 | 合计归档 B | 源一次 B | 净省 |
|---|---|---|---|
| ordinary | 2921262 | 0 | 0.000% |
| global-shuffle | 1961771 | 1431 | 32.796% |
| typed-fixed | 2068709 | 4824 | 29.019% |
| segmented-none | 2921393 | 3393 | -0.121% |
| typed-segmented | 1960598 | 4824 | 32.720% |

共500次正式完整恢复、96,000次正式范围读取，另100次恢复预热、12,000次查询预热，全部逐字节一致。

新float64文件约11.6MB，ROSAT约22.66%正零，不能外推全部浮点科学数据。未识别ECG保守回退普通编码，会错过人工声明int16重排的收益；没有自动推断其通道/类型。五轮为描述统计，不给显著性或跨机器承诺。全部精确恢复不等于推理收益，无冷缓存/跨机器/跨日、数值Rust、CAS+布局或E3/E4结果。默认策略保持不变。
