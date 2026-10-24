# v0.20 重放预算策略对照

同源码比较全量重建、旧25%/256策略、32变化数＋宽字节限消融、新三预算策略。
新默认预算32变化/256KiB重放原记录/2MiB逐次CAS解码工作；旧比例/位移上限仍保留。
限制工作量而非wall/RSS，所有来源校验与全库BM25保留，无新缓存或模型调用。

四组合成控制、各四策略三轮：已见100更新的Gear回归及默认固定64KiB复测；新增
96KiB大记录和固定1MiB块放大控制各5状态，均为定向试验而非盲测/真实科学数据。
Gear的旧策略/重建每阶段持久字节匹配v0.19，避免改变输入掩盖原问题；同轮四策略
共享代码，不直接把整版v0.19/v0.20历史耗时相除。

## 保留全部历史成本与提交

| 控制 | 策略 | 最终计入B | 总提交wall中位s | 各轮基础数 |
|---|---|---|---|---|
| regression-gear | rebuild | 83738870 | 10.806 | [101, 101, 101] |
| regression-gear | legacy | 9161975 | 8.503 | [3, 3, 3] |
| regression-gear | count-only | 9140293 | 7.603 | [3, 3, 3] |
| regression-gear | bounded | 9140288 | 7.560 | [3, 3, 3] |
| regression-fixed | rebuild | 81950222 | 10.168 | [101, 101, 101] |
| regression-fixed | legacy | 7373302 | 8.640 | [3, 3, 3] |
| regression-fixed | count-only | 7351642 | 7.479 | [3, 3, 3] |
| regression-fixed | bounded | 7351637 | 7.183 | [3, 3, 3] |
| large-record | rebuild | 3762424 | 0.632 | [5, 5, 5] |
| large-record | legacy | 1159069 | 0.458 | [1, 1, 1] |
| large-record | count-only | 1159173 | 0.464 | [1, 1, 1] |
| large-record | bounded | 2461028 | 0.563 | [3, 3, 3] |
| cas-amplification | rebuild | 16333513 | 0.701 | [5, 5, 5] |
| cas-amplification | legacy | 5620067 | 0.545 | [1, 1, 1] |
| cas-amplification | count-only | 5620171 | 0.544 | [1, 1, 1] |
| cas-amplification | bounded | 10977073 | 0.623 | [3, 3, 3] |

## 逐阶段读写与预算

| 控制 | 阶段 | 策略 | 检查点原因（三轮） | 新索引B（三轮） | 查询中位/p95 ms | 对旧策略配对加速 | 对重建配对加速 | 查询进程峰值MiB |
|---|---|---|---|---|---|---|---|---|
| regression-gear | 0 | rebuild | ['initial', 'initial', 'initial'] | [761856, 761856, 761856] | 2.18/8.30 | 1.064× | 1.000× | 32.14 |
| regression-gear | 0 | legacy | ['initial', 'initial', 'initial'] | [761856, 761856, 761856] | 2.11/8.56 | 1.000× | 0.940× | 32.28 |
| regression-gear | 0 | count-only | ['initial', 'initial', 'initial'] | [761856, 761856, 761856] | 2.17/8.56 | 0.971× | 0.976× | 32.33 |
| regression-gear | 0 | bounded | ['initial', 'initial', 'initial'] | [761856, 761856, 761856] | 2.02/8.74 | 1.070× | 1.008× | 32.32 |
| regression-gear | 1 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.10/8.85 | 2.603× | 1.000× | 32.21 |
| regression-gear | 1 | legacy | [None, None, None] | [317, 317, 317] | 5.42/12.37 | 1.000× | 0.384× | 33.61 |
| regression-gear | 1 | count-only | [None, None, None] | [317, 317, 317] | 5.69/11.49 | 0.960× | 0.369× | 33.87 |
| regression-gear | 1 | bounded | [None, None, None] | [317, 317, 317] | 5.72/11.89 | 0.950× | 0.372× | 33.30 |
| regression-gear | 40 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.33/8.13 | 2.881× | 1.000× | 32.19 |
| regression-gear | 40 | legacy | [None, None, None] | [515, 515, 515] | 6.82/12.93 | 1.000× | 0.347× | 33.85 |
| regression-gear | 40 | count-only | [None, None, None] | [515, 515, 515] | 6.85/12.94 | 0.995× | 0.347× | 34.00 |
| regression-gear | 40 | bounded | [None, None, None] | [515, 515, 515] | 6.54/12.51 | 1.027× | 0.367× | 33.36 |
| regression-gear | 41 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.34/9.66 | 2.055× | 1.000× | 32.33 |
| regression-gear | 41 | legacy | [None, None, None] | [372, 372, 372] | 4.84/11.11 | 1.000× | 0.487× | 33.77 |
| regression-gear | 41 | count-only | [None, None, None] | [372, 372, 372] | 4.38/10.91 | 1.086× | 0.542× | 33.95 |
| regression-gear | 41 | bounded | [None, None, None] | [372, 372, 372] | 4.37/10.27 | 1.120× | 0.535× | 33.50 |
| regression-gear | 42 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.31/8.48 | 247.920× | 1.000× | 32.23 |
| regression-gear | 42 | legacy | [None, None, None] | [24791, 24791, 24791] | 589.44/780.32 | 1.000× | 0.004× | 36.14 |
| regression-gear | 42 | count-only | ['budget-changes', 'budget-changes', 'budget-changes'] | [761856, 761856, 761856] | 2.31/8.83 | 256.550× | 0.973× | 32.24 |
| regression-gear | 42 | bounded | ['budget-changes', 'budget-changes', 'budget-changes'] | [761856, 761856, 761856] | 2.19/9.03 | 275.832× | 1.040× | 32.20 |
| regression-gear | 43 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.22/8.52 | 1.037× | 1.000× | 32.17 |
| regression-gear | 43 | legacy | ['legacy-change-limit', 'legacy-change-limit', 'legacy-change-limit'] | [761856, 761856, 761856] | 2.37/8.63 | 1.000× | 0.964× | 32.18 |
| regression-gear | 43 | count-only | [None, None, None] | [247, 247, 247] | 5.05/11.27 | 0.456× | 0.431× | 33.91 |
| regression-gear | 43 | bounded | [None, None, None] | [247, 247, 247] | 5.11/11.16 | 0.471× | 0.444× | 33.99 |
| regression-gear | 79 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.27/9.02 | 1.128× | 1.000× | 32.33 |
| regression-gear | 79 | legacy | [None, None, None] | [0, 0, 0] | 2.70/9.05 | 1.000× | 0.886× | 32.30 |
| regression-gear | 79 | count-only | [None, None, None] | [247, 247, 247] | 5.19/11.92 | 0.537× | 0.442× | 33.42 |
| regression-gear | 79 | bounded | [None, None, None] | [247, 247, 247] | 5.19/10.95 | 0.534× | 0.441× | 33.64 |
| regression-gear | 80 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [765952, 765952, 765952] | 2.42/9.31 | 0.959× | 1.000× | 32.23 |
| regression-gear | 80 | legacy | ['relocation-limit', 'relocation-limit', 'relocation-limit'] | [765952, 765952, 765952] | 2.44/8.92 | 1.000× | 1.043× | 32.23 |
| regression-gear | 80 | count-only | ['relocation-limit', 'relocation-limit', 'relocation-limit'] | [765952, 765952, 765952] | 2.66/9.63 | 0.928× | 0.952× | 32.16 |
| regression-gear | 80 | bounded | ['relocation-limit', 'relocation-limit', 'relocation-limit'] | [765952, 765952, 765952] | 2.27/8.50 | 1.020× | 1.072× | 32.26 |
| regression-gear | 100 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.47/9.49 | 2.322× | 1.000× | 32.18 |
| regression-gear | 100 | legacy | [None, None, None] | [317, 317, 317] | 6.27/11.84 | 1.000× | 0.431× | 33.98 |
| regression-gear | 100 | count-only | [None, None, None] | [317, 317, 317] | 6.13/11.75 | 1.023× | 0.405× | 33.48 |
| regression-gear | 100 | bounded | [None, None, None] | [317, 317, 317] | 5.90/11.93 | 1.039× | 0.435× | 33.80 |
| regression-fixed | 0 | rebuild | ['initial', 'initial', 'initial'] | [761856, 761856, 761856] | 1.95/8.16 | 0.991× | 1.000× | 32.16 |
| regression-fixed | 0 | legacy | ['initial', 'initial', 'initial'] | [761856, 761856, 761856] | 2.00/7.96 | 1.000× | 1.009× | 32.23 |
| regression-fixed | 0 | count-only | ['initial', 'initial', 'initial'] | [761856, 761856, 761856] | 1.99/7.81 | 1.003× | 1.002× | 32.21 |
| regression-fixed | 0 | bounded | ['initial', 'initial', 'initial'] | [761856, 761856, 761856] | 2.06/8.29 | 0.959× | 0.954× | 32.16 |
| regression-fixed | 1 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.10/7.47 | 2.463× | 1.000× | 32.28 |
| regression-fixed | 1 | legacy | [None, None, None] | [316, 316, 316] | 5.19/10.80 | 1.000× | 0.406× | 33.43 |
| regression-fixed | 1 | count-only | [None, None, None] | [316, 316, 316] | 5.11/10.31 | 1.010× | 0.419× | 33.26 |
| regression-fixed | 1 | bounded | [None, None, None] | [316, 316, 316] | 5.41/11.03 | 1.026× | 0.420× | 33.23 |
| regression-fixed | 40 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.32/7.92 | 2.679× | 1.000× | 32.14 |
| regression-fixed | 40 | legacy | [None, None, None] | [514, 514, 514] | 6.21/11.35 | 1.000× | 0.373× | 33.87 |
| regression-fixed | 40 | count-only | [None, None, None] | [514, 514, 514] | 5.86/11.46 | 1.056× | 0.403× | 33.93 |
| regression-fixed | 40 | bounded | [None, None, None] | [514, 514, 514] | 6.33/11.25 | 1.024× | 0.395× | 33.41 |
| regression-fixed | 41 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.23/8.22 | 1.943× | 1.000× | 32.18 |
| regression-fixed | 41 | legacy | [None, None, None] | [372, 372, 372] | 4.42/9.93 | 1.000× | 0.515× | 33.75 |
| regression-fixed | 41 | count-only | [None, None, None] | [372, 372, 372] | 4.66/9.86 | 0.979× | 0.490× | 33.55 |
| regression-fixed | 41 | bounded | [None, None, None] | [372, 372, 372] | 4.44/9.31 | 0.990× | 0.518× | 33.23 |
| regression-fixed | 42 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.45/7.96 | 201.137× | 1.000× | 32.20 |
| regression-fixed | 42 | legacy | [None, None, None] | [24787, 24787, 24787] | 534.47/684.67 | 1.000× | 0.005× | 35.97 |
| regression-fixed | 42 | count-only | ['budget-changes', 'budget-changes', 'budget-changes'] | [761856, 761856, 761856] | 2.21/7.80 | 229.971× | 1.062× | 32.06 |
| regression-fixed | 42 | bounded | ['budget-changes', 'budget-changes', 'budget-changes'] | [761856, 761856, 761856] | 2.36/8.18 | 218.302× | 0.976× | 32.20 |
| regression-fixed | 43 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.15/8.12 | 1.029× | 1.000× | 32.19 |
| regression-fixed | 43 | legacy | ['legacy-change-limit', 'legacy-change-limit', 'legacy-change-limit'] | [761856, 761856, 761856] | 2.31/7.40 | 1.000× | 0.972× | 32.26 |
| regression-fixed | 43 | count-only | [None, None, None] | [248, 248, 248] | 4.49/9.81 | 0.518× | 0.484× | 33.58 |
| regression-fixed | 43 | bounded | [None, None, None] | [248, 248, 248] | 4.61/9.87 | 0.513× | 0.482× | 33.50 |
| regression-fixed | 79 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.24/8.40 | 1.193× | 1.000× | 32.16 |
| regression-fixed | 79 | legacy | [None, None, None] | [0, 0, 0] | 2.77/8.39 | 1.000× | 0.838× | 32.18 |
| regression-fixed | 79 | count-only | [None, None, None] | [247, 247, 247] | 4.65/10.37 | 0.576× | 0.474× | 33.28 |
| regression-fixed | 79 | bounded | [None, None, None] | [247, 247, 247] | 4.80/9.94 | 0.587× | 0.468× | 33.85 |
| regression-fixed | 80 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [765952, 765952, 765952] | 2.26/8.54 | 1.033× | 1.000× | 32.23 |
| regression-fixed | 80 | legacy | ['relocation-limit', 'relocation-limit', 'relocation-limit'] | [765952, 765952, 765952] | 2.25/8.50 | 1.000× | 0.968× | 32.18 |
| regression-fixed | 80 | count-only | ['relocation-limit', 'relocation-limit', 'relocation-limit'] | [765952, 765952, 765952] | 2.42/7.58 | 1.018× | 0.999× | 32.23 |
| regression-fixed | 80 | bounded | ['relocation-limit', 'relocation-limit', 'relocation-limit'] | [765952, 765952, 765952] | 2.25/7.66 | 1.044× | 0.980× | 32.16 |
| regression-fixed | 100 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [761856, 761856, 761856] | 2.27/8.41 | 2.382× | 1.000× | 32.21 |
| regression-fixed | 100 | legacy | [None, None, None] | [318, 318, 318] | 5.97/11.93 | 1.000× | 0.420× | 33.30 |
| regression-fixed | 100 | count-only | [None, None, None] | [318, 318, 318] | 5.80/10.77 | 1.036× | 0.439× | 33.71 |
| regression-fixed | 100 | bounded | [None, None, None] | [318, 318, 318] | 6.20/12.14 | 0.953× | 0.405× | 33.84 |
| large-record | 0 | rebuild | ['initial', 'initial', 'initial'] | [651264, 651264, 651264] | 2.54/11.62 | 0.978× | 1.000× | 34.46 |
| large-record | 0 | legacy | ['initial', 'initial', 'initial'] | [651264, 651264, 651264] | 2.53/12.36 | 1.000× | 1.022× | 34.45 |
| large-record | 0 | count-only | ['initial', 'initial', 'initial'] | [651264, 651264, 651264] | 2.82/12.58 | 0.944× | 0.987× | 34.46 |
| large-record | 0 | bounded | ['initial', 'initial', 'initial'] | [651264, 651264, 651264] | 2.64/12.33 | 0.980× | 0.984× | 34.39 |
| large-record | 1 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [651264, 651264, 651264] | 2.73/13.28 | 2.565× | 1.000× | 34.37 |
| large-record | 1 | legacy | [None, None, None] | [245, 245, 245] | 7.06/17.64 | 1.000× | 0.390× | 34.79 |
| large-record | 1 | count-only | [None, None, None] | [245, 245, 245] | 7.05/16.70 | 0.982× | 0.380× | 35.06 |
| large-record | 1 | bounded | [None, None, None] | [245, 245, 245] | 7.02/18.14 | 1.001× | 0.386× | 35.06 |
| large-record | 2 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [651264, 651264, 651264] | 2.75/12.44 | 4.071× | 1.000× | 34.48 |
| large-record | 2 | legacy | [None, None, None] | [298, 298, 298] | 11.14/21.66 | 1.000× | 0.246× | 34.99 |
| large-record | 2 | count-only | [None, None, None] | [298, 298, 298] | 11.30/21.15 | 0.994× | 0.243× | 35.04 |
| large-record | 2 | bounded | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | [651264, 651264, 651264] | 2.61/13.49 | 4.120× | 0.979× | 34.57 |
| large-record | 3 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [651264, 651264, 651264] | 2.78/13.31 | 5.079× | 1.000× | 34.36 |
| large-record | 3 | legacy | [None, None, None] | [345, 345, 345] | 14.29/24.20 | 1.000× | 0.197× | 34.83 |
| large-record | 3 | count-only | [None, None, None] | [345, 345, 345] | 14.15/24.42 | 0.983× | 0.198× | 35.36 |
| large-record | 3 | bounded | [None, None, None] | [246, 246, 246] | 7.10/16.36 | 1.925× | 0.401× | 35.07 |
| large-record | 4 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [651264, 651264, 651264] | 2.61/12.46 | 1.159× | 1.000× | 34.38 |
| large-record | 4 | legacy | [None, None, None] | [0, 0, 0] | 2.98/13.71 | 1.000× | 0.863× | 34.44 |
| large-record | 4 | count-only | [None, None, None] | [0, 0, 0] | 2.87/12.87 | 1.012× | 0.875× | 34.21 |
| large-record | 4 | bounded | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | [651264, 651264, 651264] | 2.65/12.47 | 1.150× | 1.000× | 34.21 |
| cas-amplification | 0 | rebuild | ['initial', 'initial', 'initial'] | [2678784, 2678784, 2678784] | 7.67/44.33 | 1.033× | 1.000× | 33.82 |
| cas-amplification | 0 | legacy | ['initial', 'initial', 'initial'] | [2678784, 2678784, 2678784] | 8.05/46.18 | 1.000× | 0.968× | 33.86 |
| cas-amplification | 0 | count-only | ['initial', 'initial', 'initial'] | [2678784, 2678784, 2678784] | 7.67/44.67 | 1.042× | 1.006× | 33.88 |
| cas-amplification | 0 | bounded | ['initial', 'initial', 'initial'] | [2678784, 2678784, 2678784] | 7.82/44.13 | 1.032× | 0.992× | 33.95 |
| cas-amplification | 1 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [2678784, 2678784, 2678784] | 7.81/44.32 | 2.616× | 1.000× | 34.00 |
| cas-amplification | 1 | legacy | [None, None, None] | [244, 244, 244] | 20.53/56.65 | 1.000× | 0.382× | 39.15 |
| cas-amplification | 1 | count-only | [None, None, None] | [244, 244, 244] | 20.48/57.32 | 0.992× | 0.390× | 39.11 |
| cas-amplification | 1 | bounded | [None, None, None] | [244, 244, 244] | 20.25/55.72 | 1.004× | 0.387× | 39.17 |
| cas-amplification | 2 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [2678784, 2678784, 2678784] | 7.67/43.93 | 3.868× | 1.000× | 34.08 |
| cas-amplification | 2 | legacy | [None, None, None] | [293, 293, 293] | 29.77/66.21 | 1.000× | 0.259× | 39.15 |
| cas-amplification | 2 | count-only | [None, None, None] | [293, 293, 293] | 29.54/66.18 | 1.009× | 0.264× | 39.20 |
| cas-amplification | 2 | bounded | ['budget-cas-bytes', 'budget-cas-bytes', 'budget-cas-bytes'] | [2678784, 2678784, 2678784] | 7.91/45.90 | 3.740× | 0.972× | 33.95 |
| cas-amplification | 3 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [2678784, 2678784, 2678784] | 7.93/45.93 | 4.877× | 1.000× | 33.88 |
| cas-amplification | 3 | legacy | [None, None, None] | [340, 340, 340] | 39.36/75.54 | 1.000× | 0.205× | 39.21 |
| cas-amplification | 3 | count-only | [None, None, None] | [340, 340, 340] | 38.73/78.25 | 1.005× | 0.211× | 39.13 |
| cas-amplification | 3 | bounded | [None, None, None] | [243, 243, 243] | 20.71/56.75 | 1.855× | 0.389× | 39.13 |
| cas-amplification | 4 | rebuild | ['full-profile', 'full-profile', 'full-profile'] | [2678784, 2678784, 2678784] | 7.65/44.87 | 1.024× | 1.000× | 33.89 |
| cas-amplification | 4 | legacy | [None, None, None] | [0, 0, 0] | 7.94/45.50 | 1.000× | 0.977× | 33.90 |
| cas-amplification | 4 | count-only | [None, None, None] | [0, 0, 0] | 8.02/43.15 | 1.022× | 0.983× | 33.95 |
| cas-amplification | 4 | bounded | ['budget-cas-bytes', 'budget-cas-bytes', 'budget-cas-bytes'] | [2678784, 2678784, 2678784] | 7.79/44.86 | 1.029× | 0.993× | 33.91 |

完整计入所有RKV Python源码及打包HTML一次，Gear组另计整个实测DLL/元数据；固定
组没有原生依赖。Python/SQLite/OS、pyc、安装/文件系统元数据未全额分配，非完整
部署净压缩；此口径与v0.19的四模块不同，不直接计算版本压缩升级百分比。

4032正式、10176历史身份查询与重建的key顺序、BM25（绝对差<=1e-10）、原文/完整
定位摘要一致；2544原始快照未来探针阴性，2544历史快照实例全源大小/SHA重读，
当前源逐字节一致。同表示CAS树相同，查询前后持久树不变。实例含多轮/多策略重复。
336新查询进程，各一次预热排除统计。query计整个search与清理，启动另列；commit
包含预算估计/验证/HEAD发布，源生成不计。RSS含整个进程/输入，配对比值逐问题/
轮计算后取中位。仅本机温缓存；四组控制不增加科学问题或模型质量证据。

新建库默认compact-budget-v3；旧v3库不自动切换，memory-budget只原子更新未来
writer策略，不重建旧视图/改HEAD，旧高代价快照仍可能慢。旧v0.19读取器可读新
v3视图，旧writer不能写新profile。物理归档/CAS/清单不变，无迁移或GC。定向控制
不能证明所有负载更优，预算不限制索引SHA、SQLite复制/排序、位移扫描与实际命中
读取等总耗时；空间、提交、查询和RSS分别判断。无E3、冷缓存/跨机器、掉电、并发
写入、长期对话或新模型调用。原始科学输入/私有研究不进入Release。
