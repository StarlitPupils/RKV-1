# v0.32 实验报告：代码/数学词法字节通道的完整成本

## 冻结问题与方法

E2代码/数学表示仍有空缺。本轮只测一个原始字节重排：ASCII标识符、十进制
拼写、ASCII空白和其他字节四通道，control逐token记类型与canonical长度。
不执行输入代码，不做AST/表达式等价化，所有原字节(含注释/字符串/CRLF/Unicode)
都保存。类型是字节词法，不是完整语言tokenizer或语义压缩。

独立RKVTEXT1实验帧66B header，原样/通道共享同一框架、原SHA/长度及单codec流。
通道输入为40B长度头+control+四pool，全部再压缩。对Zlib6/Zstd3/LZMA6分别测
plain/lanes/auto，auto实际计算两者并选完整帧较小者、同分plain，双尝试全部收费。
不是主RKV归档v7，不改变旧Archive/Memory/CAS，也不产生随机范围读/推理收益。

全部57模块/驱动/协议/输入清单冻结`d6d7c21`；218测试运行、217通过、1权限跳过。格式/边界/门槛见[TEXT-LANES](../../docs/TEXT-LANES.md)。

## 结论及架构决策

科学候选净空间0/36、联合0/36通过；噪声联合0/6。所有189次实际恢复正确，但正确性不等于压缩收益。

- zlib六科学文件共享专用源一次：plain 157405B，lanes 232204B（增47.52%），auto 159919B。
- zstd六科学文件共享专用源一次：plain 167086B，lanes 263084B（增57.45%），auto 169600B。
- lzma六科学文件共享专用源一次：plain 141149B，lanes 198907B（增40.92%），auto 143663B。

自动模式21/21个输入/codec条件都回退plain（含噪声；三轮共63正式auto编码），
帧字节与plain完全相同，而双尝试/变换成本和候选源码仍收费。强制lanes连不计
源码的帧也更大，不能把问题解释为只需摊薄decoder。结果否定当前四通道表示
在这些工作点的优势，不否定所有代码/数学表示；没有分离control与跨类统计损失
的消融，不能将失败精确归因给某一原因。

当前格式的输出比特数不因搬到Rust而改变，还要增加实际库成本，因此不追加该
表示的原生化/主格式集成，默认继续普通codec。后续回到动态证据记忆工程缺口，
优先冻结一个单writer/多reader快照一致性实验；它属于机械正确性验证，不当作
生产并发、模型推理或长期会话收益。E3神经预测仍需独立设计和完整模型成本。

## 数据与可复现范围

| 家族 | 固定ref | 原路径 | 原字节B |
|---|---|---|---|
| scipy/scipy | v1.14.1 | scipy/optimize/_linprog.py | 29756 |
| scipy/scipy | v1.14.1 | scipy/linalg/_basic.py | 69168 |
| sympy/sympy | 1.13.3 | sympy/core/expr.py | 142171 |
| sympy/sympy | 1.13.3 | sympy/integrals/integrals.py | 64861 |
| latex3/latex2e | release-2024-11-01 | required/amsmath/amsmath.dtx | 233049 |
| latex3/latex2e | release-2024-11-01 | base/ltmath.dtx | 42287 |

六文件来自SciPy/SymPy/LaTeX2e三个项目，不当六个独立科学领域或抽样总体；版本
是固定历史基准而非最新软件推荐。原commit/SHA256/Git blob SHA/官方URL/许可证
见dataset-provenance.json，源代码和可逆帧/恢复文件不发布。另262144B固定SHAKE
噪声仅作负对照，不当真实科学来源。没有在看压缩率后挑文件、级别、类规则或扩大N。

189编码/恢复对、378个独立新进程阶段、378次实际文件fsync；无warmup。全部恢复
逐字节与原SHA相等，三轮每条件帧SHA/大小/选择/control账本全同，源/协议不变。
每阶段记录codec是否已由公共模块预载；首次lazy导入若发生在计算中则收费，
整个进程wall/RSS也列出。不把codec已预载说成首次导入，冷缓存/跨机器未测。

## 成本口径及联合门槛

A为实际完整帧66+compressed payload；40+control+pool是压缩前结构，不在A上
再次加一遍。B为A加专用帧模块源码(含编/解码)，候选再加通道模块正/反变换；
C为A加实际整个RKV57模块/HTML一次。B/C是替代场景，不能叠加重复计源。
codec/Python/OS/安装/pyc/文件系统未全额分配，任何场景都不是完整部署成本。

每单文件各自全收B，若严格净省且三轮纯encode/decode wall中位都不慢才联合
通过；六科学文件固定N=6共享源码一次另报空间，不混噪声、不当所有单文件通过。
重复轮只是相同输入计时，不当独立样本或统计因果证明。全部原样本在trials.json。

公共帧模块4037B、候选通道模块2514B、整个RKV源391113B。字典/模型/本实验专属原生库0B；已安装codec实现成本仍是未全额分配的公共部分。

## 逐输入完整帧/源成本与联合结果

![净成本比](text-lanes-net-cost.png)

| 输入 | codec | 条件/实际选择 | A帧B | B帧+专用源B | 空间通过 | 编码中位ms | 解码中位ms | 联合 |
|---|---|---|---|---|---|---|---|---|
| scipy__scipy__optimize___linprog.py | zlib | plain/plain | 8850 | 12887 | baseline | 0.653 | 0.133 | baseline |
| scipy__scipy__optimize___linprog.py | zlib | lanes/lanes | 12624 | 19175 | False | 7.154 | 6.108 | False |
| scipy__scipy__optimize___linprog.py | zlib | auto/plain | 8850 | 15401 | False | 7.762 | 0.133 | False |
| scipy__scipy__optimize___linprog.py | zstd | plain/plain | 9398 | 13435 | baseline | 1.356 | 1.138 | baseline |
| scipy__scipy__optimize___linprog.py | zstd | lanes/lanes | 14267 | 20818 | False | 7.786 | 7.358 | False |
| scipy__scipy__optimize___linprog.py | zstd | auto/plain | 9398 | 15949 | False | 7.142 | 1.322 | False |
| scipy__scipy__optimize___linprog.py | lzma | plain/plain | 8502 | 12539 | baseline | 7.308 | 0.416 | baseline |
| scipy__scipy__optimize___linprog.py | lzma | lanes/lanes | 11018 | 17569 | False | 17.111 | 6.496 | False |
| scipy__scipy__optimize___linprog.py | lzma | auto/plain | 8502 | 15053 | False | 23.730 | 0.413 | False |
| scipy__scipy__linalg___basic.py | zlib | plain/plain | 19469 | 23506 | baseline | 1.555 | 0.269 | baseline |
| scipy__scipy__linalg___basic.py | zlib | lanes/lanes | 27973 | 34524 | False | 18.251 | 16.168 | False |
| scipy__scipy__linalg___basic.py | zlib | auto/plain | 19469 | 26020 | False | 19.741 | 0.259 | False |
| scipy__scipy__linalg___basic.py | zstd | plain/plain | 20380 | 24417 | baseline | 1.420 | 1.188 | baseline |
| scipy__scipy__linalg___basic.py | zstd | lanes/lanes | 32444 | 38995 | False | 15.965 | 17.035 | False |
| scipy__scipy__linalg___basic.py | zstd | auto/plain | 20380 | 26931 | False | 16.166 | 1.265 | False |
| scipy__scipy__linalg___basic.py | lzma | plain/plain | 17622 | 21659 | baseline | 12.259 | 0.803 | baseline |
| scipy__scipy__linalg___basic.py | lzma | lanes/lanes | 23750 | 30301 | False | 39.414 | 16.626 | False |
| scipy__scipy__linalg___basic.py | lzma | auto/plain | 17622 | 24173 | False | 51.542 | 0.784 | False |
| sympy__sympy__core__expr.py | zlib | plain/plain | 35501 | 39538 | baseline | 3.201 | 0.466 | baseline |
| sympy__sympy__core__expr.py | zlib | lanes/lanes | 52571 | 59122 | False | 33.954 | 28.326 | False |
| sympy__sympy__core__expr.py | zlib | auto/plain | 35501 | 42052 | False | 37.331 | 0.456 | False |
| sympy__sympy__core__expr.py | zstd | plain/plain | 38389 | 42426 | baseline | 1.826 | 1.295 | baseline |
| sympy__sympy__core__expr.py | zstd | lanes/lanes | 60134 | 66685 | False | 27.788 | 29.446 | False |
| sympy__sympy__core__expr.py | zstd | auto/plain | 38389 | 44940 | False | 28.183 | 1.385 | False |
| sympy__sympy__core__expr.py | lzma | plain/plain | 31682 | 35719 | baseline | 26.187 | 1.283 | baseline |
| sympy__sympy__core__expr.py | lzma | lanes/lanes | 44434 | 50985 | False | 71.937 | 30.077 | False |
| sympy__sympy__core__expr.py | lzma | auto/plain | 31682 | 38233 | False | 97.817 | 1.325 | False |
| sympy__sympy__integrals__integrals.py | zlib | plain/plain | 17140 | 21177 | baseline | 1.401 | 0.251 | baseline |
| sympy__sympy__integrals__integrals.py | zlib | lanes/lanes | 25217 | 31768 | False | 14.799 | 12.479 | False |
| sympy__sympy__integrals__integrals.py | zlib | auto/plain | 17140 | 23691 | False | 15.858 | 0.237 | False |
| sympy__sympy__integrals__integrals.py | zstd | plain/plain | 18421 | 22458 | baseline | 1.489 | 1.448 | baseline |
| sympy__sympy__integrals__integrals.py | zstd | lanes/lanes | 29329 | 35880 | False | 13.062 | 13.952 | False |
| sympy__sympy__integrals__integrals.py | zstd | auto/plain | 18421 | 24972 | False | 13.171 | 1.233 | False |
| sympy__sympy__integrals__integrals.py | lzma | plain/plain | 15958 | 19995 | baseline | 13.006 | 0.704 | baseline |
| sympy__sympy__integrals__integrals.py | lzma | lanes/lanes | 21658 | 28209 | False | 32.437 | 13.258 | False |
| sympy__sympy__integrals__integrals.py | lzma | auto/plain | 15958 | 22509 | False | 45.613 | 0.696 | False |
| latex3__required__amsmath__amsmath.dtx | zlib | plain/plain | 62191 | 66228 | baseline | 5.518 | 0.746 | baseline |
| latex3__required__amsmath__amsmath.dtx | zlib | lanes/lanes | 91471 | 98022 | False | 63.728 | 53.722 | False |
| latex3__required__amsmath__amsmath.dtx | zlib | auto/plain | 62191 | 68742 | False | 68.389 | 0.745 | False |
| latex3__required__amsmath__amsmath.dtx | zstd | plain/plain | 65239 | 69276 | baseline | 2.292 | 1.568 | baseline |
| latex3__required__amsmath__amsmath.dtx | zstd | lanes/lanes | 102020 | 108571 | False | 50.240 | 56.222 | False |
| latex3__required__amsmath__amsmath.dtx | zstd | auto/plain | 65239 | 71790 | False | 51.917 | 1.472 | False |
| latex3__required__amsmath__amsmath.dtx | lzma | plain/plain | 53642 | 57679 | baseline | 40.320 | 1.998 | baseline |
| latex3__required__amsmath__amsmath.dtx | lzma | lanes/lanes | 77790 | 84341 | False | 127.925 | 55.861 | False |
| latex3__required__amsmath__amsmath.dtx | lzma | auto/plain | 53642 | 60193 | False | 175.986 | 2.008 | False |
| latex3__base__ltmath.dtx | zlib | plain/plain | 10217 | 14254 | baseline | 0.755 | 0.173 | baseline |
| latex3__base__ltmath.dtx | zlib | lanes/lanes | 15797 | 22348 | False | 10.894 | 9.515 | False |
| latex3__base__ltmath.dtx | zlib | auto/plain | 10217 | 16768 | False | 11.448 | 0.178 | False |
| latex3__base__ltmath.dtx | zstd | plain/plain | 11222 | 15259 | baseline | 1.337 | 1.167 | baseline |
| latex3__base__ltmath.dtx | zstd | lanes/lanes | 18339 | 24890 | False | 10.341 | 10.743 | False |
| latex3__base__ltmath.dtx | zstd | auto/plain | 11222 | 17773 | False | 10.591 | 1.254 | False |
| latex3__base__ltmath.dtx | lzma | plain/plain | 9706 | 13743 | baseline | 8.575 | 0.478 | baseline |
| latex3__base__ltmath.dtx | lzma | lanes/lanes | 13706 | 20257 | False | 23.467 | 10.077 | False |
| latex3__base__ltmath.dtx | lzma | auto/plain | 9706 | 16257 | False | 31.576 | 0.473 | False |
| control_noise_256k.bin | zlib | plain/plain | 262296 | 266333 | baseline | 4.088 | 0.389 | baseline |
| control_noise_256k.bin | zlib | lanes/lanes | 290161 | 296712 | False | 84.482 | 70.747 | False |
| control_noise_256k.bin | zlib | auto/plain | 262296 | 268847 | False | 89.882 | 0.371 | False |
| control_noise_256k.bin | zstd | plain/plain | 262229 | 266266 | baseline | 1.611 | 1.313 | baseline |
| control_noise_256k.bin | zstd | lanes/lanes | 298650 | 305201 | False | 64.838 | 70.841 | False |
| control_noise_256k.bin | zstd | auto/plain | 262229 | 268780 | False | 66.457 | 1.363 | False |
| control_noise_256k.bin | lzma | plain/plain | 262282 | 266319 | baseline | 36.846 | 0.422 | baseline |
| control_noise_256k.bin | lzma | lanes/lanes | 276622 | 283173 | False | 156.090 | 78.965 | False |
| control_noise_256k.bin | lzma | auto/plain | 262282 | 268833 | False | 194.275 | 0.436 | False |

六科学输入候选工作点36个，专用源净空间通过0/36、联合通过0/36；噪声6点联合0/6。门槛不因结果而调整。

## 固定六文件共享源一次的空间情景

| codec | 条件 | 原科学字节B | 完整帧合计B | 共享专用源后B | 全部RKV源后B |
|---|---|---|---|---|---|
| zlib | plain | 581292 | 153368 | 157405 | 544481 |
| zlib | lanes | 581292 | 225653 | 232204 | 616766 |
| zlib | auto | 581292 | 153368 | 159919 | 544481 |
| zstd | plain | 581292 | 163049 | 167086 | 554162 |
| zstd | lanes | 581292 | 256533 | 263084 | 647646 |
| zstd | auto | 581292 | 163049 | 169600 | 554162 |
| lzma | plain | 581292 | 137112 | 141149 | 528225 |
| lzma | lanes | 581292 | 192356 | 198907 | 583469 |
| lzma | auto | 581292 | 137112 | 143663 | 528225 |

这是明确N=6的空间账本，不把六次冷进程导入/写盘相加称单个部署批处理耗时，也不扩大对象数摊薄decoder获得正结果。B与C不相加。

## 控制/回退、I/O与资源

每个attempt原长度、变换长度、tokens/control长度、四pool长度、40B结构头、
compressed payload和66B帧头均在原始JSON。auto回退plain也收费变换和两次codec，
并在B分配候选源码；实际帧可以等于plain，不能因此声称编码/部署成本免费。

pack source_load含输入pin SHA/读取，纯encode(含原SHA)、帧写入/flush/fsync分别
测；pack phase排除source_load。restore真值读取是独立基准前提，不属于实际
decoder；真实phase含帧读取、decode(含原SHA)、恢复写入fsync，逐字节读回审计
另计。不能把纯encode/decode当完整pack/restore或省略新codec首次导入。每阶段
新进程，实际模块预载状态、CPU样本、进程wall和峰值RSS完整留存。RSS包含输入/
真值/输出/元数据/公共模块，不能解释为codec独占RAM。没有目录fsync/掉电证明。

| 输入 | codec | 条件 | pack阶段中位ms | restore阶段中位ms | encode/restore进程RSS中位MiB |
|---|---|---|---|---|---|
| scipy__scipy__optimize___linprog.py | zlib | plain | 1.312 | 0.924 | 30.13/30.02 |
| scipy__scipy__optimize___linprog.py | zlib | lanes | 7.844 | 6.858 | 30.31/30.18 |
| scipy__scipy__optimize___linprog.py | zlib | auto | 8.504 | 0.904 | 30.45/30.08 |
| scipy__scipy__optimize___linprog.py | zstd | plain | 1.998 | 1.862 | 30.71/30.31 |
| scipy__scipy__optimize___linprog.py | zstd | lanes | 8.455 | 8.116 | 30.82/30.41 |
| scipy__scipy__optimize___linprog.py | zstd | auto | 8.177 | 2.174 | 30.79/30.27 |
| scipy__scipy__optimize___linprog.py | lzma | plain | 8.041 | 1.237 | 46.61/30.09 |
| scipy__scipy__optimize___linprog.py | lzma | lanes | 17.890 | 7.314 | 47.13/30.18 |
| scipy__scipy__optimize___linprog.py | lzma | auto | 24.489 | 1.179 | 47.00/30.10 |
| scipy__scipy__linalg___basic.py | zlib | plain | 2.263 | 0.990 | 30.25/30.23 |
| scipy__scipy__linalg___basic.py | zlib | lanes | 18.981 | 16.994 | 30.52/30.31 |
| scipy__scipy__linalg___basic.py | zlib | auto | 20.472 | 0.929 | 30.48/30.16 |
| scipy__scipy__linalg___basic.py | zstd | plain | 2.062 | 1.903 | 30.77/30.41 |
| scipy__scipy__linalg___basic.py | zstd | lanes | 16.656 | 17.824 | 30.96/30.56 |
| scipy__scipy__linalg___basic.py | zstd | auto | 16.917 | 2.035 | 31.18/30.44 |
| scipy__scipy__linalg___basic.py | lzma | plain | 12.983 | 1.615 | 46.96/30.27 |
| scipy__scipy__linalg___basic.py | lzma | lanes | 40.223 | 17.571 | 47.88/30.47 |
| scipy__scipy__linalg___basic.py | lzma | auto | 52.313 | 1.728 | 47.78/30.31 |
| sympy__sympy__core__expr.py | zlib | plain | 3.952 | 1.260 | 30.45/30.60 |
| sympy__sympy__core__expr.py | zlib | lanes | 34.794 | 29.276 | 30.76/30.93 |
| sympy__sympy__core__expr.py | zlib | auto | 38.079 | 1.239 | 30.81/30.49 |
| sympy__sympy__core__expr.py | zstd | plain | 2.538 | 2.121 | 30.88/30.77 |
| sympy__sympy__core__expr.py | zstd | lanes | 28.549 | 30.425 | 31.55/31.27 |
| sympy__sympy__core__expr.py | zstd | auto | 29.038 | 2.231 | 31.76/30.74 |
| sympy__sympy__core__expr.py | lzma | plain | 26.884 | 2.075 | 47.73/30.59 |
| sympy__sympy__core__expr.py | lzma | lanes | 72.895 | 30.943 | 48.98/30.95 |
| sympy__sympy__core__expr.py | lzma | auto | 98.667 | 2.209 | 49.09/30.48 |
| sympy__sympy__integrals__integrals.py | zlib | plain | 2.211 | 0.966 | 30.36/30.27 |
| sympy__sympy__integrals__integrals.py | zlib | lanes | 15.645 | 13.375 | 30.38/30.42 |
| sympy__sympy__integrals__integrals.py | zlib | auto | 16.609 | 0.983 | 30.39/30.23 |
| sympy__sympy__integrals__integrals.py | zstd | plain | 2.155 | 2.194 | 30.84/30.41 |
| sympy__sympy__integrals__integrals.py | zstd | lanes | 13.724 | 14.840 | 31.09/30.58 |
| sympy__sympy__integrals__integrals.py | zstd | auto | 14.016 | 1.938 | 31.22/30.41 |
| sympy__sympy__integrals__integrals.py | lzma | plain | 13.696 | 1.391 | 46.93/30.26 |
| sympy__sympy__integrals__integrals.py | lzma | lanes | 33.408 | 14.168 | 47.72/30.57 |
| sympy__sympy__integrals__integrals.py | lzma | auto | 46.535 | 1.486 | 47.77/30.26 |
| latex3__required__amsmath__amsmath.dtx | zlib | plain | 6.284 | 1.532 | 30.54/30.91 |
| latex3__required__amsmath__amsmath.dtx | zlib | lanes | 64.595 | 54.649 | 31.47/31.57 |
| latex3__required__amsmath__amsmath.dtx | zlib | auto | 69.218 | 1.729 | 31.70/30.82 |
| latex3__required__amsmath__amsmath.dtx | zstd | plain | 2.978 | 2.453 | 31.16/30.95 |
| latex3__required__amsmath__amsmath.dtx | zstd | lanes | 50.956 | 57.131 | 32.00/31.84 |
| latex3__required__amsmath__amsmath.dtx | zstd | auto | 52.859 | 2.249 | 32.04/31.03 |
| latex3__required__amsmath__amsmath.dtx | lzma | plain | 41.096 | 2.902 | 48.77/30.98 |
| latex3__required__amsmath__amsmath.dtx | lzma | lanes | 128.856 | 56.846 | 50.82/31.61 |
| latex3__required__amsmath__amsmath.dtx | lzma | auto | 176.808 | 2.889 | 50.84/30.86 |
| latex3__base__ltmath.dtx | zlib | plain | 1.449 | 0.884 | 30.32/30.19 |
| latex3__base__ltmath.dtx | zlib | lanes | 11.644 | 10.305 | 30.23/30.16 |
| latex3__base__ltmath.dtx | zlib | auto | 12.132 | 0.917 | 30.29/30.16 |
| latex3__base__ltmath.dtx | zstd | plain | 1.992 | 1.915 | 30.71/30.29 |
| latex3__base__ltmath.dtx | zstd | lanes | 11.020 | 11.636 | 30.85/30.57 |
| latex3__base__ltmath.dtx | zstd | auto | 11.372 | 1.962 | 30.86/30.27 |
| latex3__base__ltmath.dtx | lzma | plain | 9.431 | 1.197 | 46.60/30.17 |
| latex3__base__ltmath.dtx | lzma | lanes | 24.315 | 11.067 | 47.19/30.29 |
| latex3__base__ltmath.dtx | lzma | auto | 32.717 | 1.331 | 47.17/30.10 |
| control_noise_256k.bin | zlib | plain | 4.896 | 1.285 | 30.66/31.16 |
| control_noise_256k.bin | zlib | lanes | 85.401 | 71.778 | 31.63/31.83 |
| control_noise_256k.bin | zlib | auto | 90.819 | 1.239 | 32.15/31.16 |
| control_noise_256k.bin | zstd | plain | 2.372 | 2.192 | 31.26/31.19 |
| control_noise_256k.bin | zstd | lanes | 65.658 | 71.883 | 32.18/32.15 |
| control_noise_256k.bin | zstd | auto | 67.386 | 2.319 | 32.65/31.20 |
| control_noise_256k.bin | lzma | plain | 37.790 | 1.330 | 49.23/31.49 |
| control_noise_256k.bin | lzma | lanes | 157.295 | 80.069 | 51.90/32.07 |
| control_noise_256k.bin | lzma | auto | 195.305 | 1.333 | 52.40/31.42 |

## 格式拒绝、决策与后续

测试拒绝未知magic/codec/method、错长度/SHA、非canonical或越界/未耗尽通道、
压缩后额外字节/串接流及伪造小长度解压；Zstd要求声明内容长度/受限window/无
外部字典，LZMA memlimit256MiB。原样与通道均做原SHA验证。实验帧由主Archive
明确拒绝，旧v1–v6归档及所有旧来源/默认仍经回归，不把新prototype当生产格式。

保留全部负结果和对象/codec适用范围；默认不集成。只有明确净空间、真实热点及
包含完整原生库成本的工作负载才考虑Rust，不从Python慢推导综合收益。本轮没有
模型/检索/推理收益，远程模型调用0；E3神经预测、语义压缩、多跳、长期会话、
形式证明、冷缓存/跨机器/并发/掉电等未测。具体后续应依据上述门槛，不在既有
语料调规则/级别或改变对象数追求正结果。
