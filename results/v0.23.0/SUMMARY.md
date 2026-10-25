# v0.23 独立真实正文修订：整篇JATS记录基线

eLife固定官方提交中按数值ID前六篇三版本论文，18原文件，12次投影确实变化。
不是QASPER标注发布，也不是人工科学QA。六篇v1后逐篇v2/逐篇v3，13状态。
固定/Gear×完整重建/预算v3/投影v4，各三轮，全部原文和历史保留，无GC。

**粒度负结果：旧+新整篇记录全部超过256KiB，预算v3/v4每次都检查点，没有
增量索引收益。v4指纹表还有额外字节。Gear CAS复用与索引收益分开报告。**

## 全历史成本与提交

| 分块 | 策略 | 最终计入B | 总提交wall中位s | 基础数（三轮） |
|---|---|---|---|---|
| fixed | rebuild | 3556231 | 0.943 | [13, 13, 13] |
| fixed | budget-v3 | 3556330 | 0.900 | [13, 13, 13] |
| fixed | projection-v4 | 3663389 | 0.999 | [13, 13, 13] |
| gear | rebuild | 3645981 | 0.860 | [13, 13, 13] |
| gear | budget-v3 | 3646080 | 0.863 | [13, 13, 13] |
| gear | projection-v4 | 3753139 | 0.923 | [13, 13, 13] |

## 每阶段索引与查询

| 分块 | 阶段 | 策略 | 新索引B（三轮） | 检查点原因 | 查询中位/p95 ms | 对重建配对加速 | 进程峰值MiB |
|---|---|---|---|---|---|---|---|
| fixed | 0 | rebuild | [172032, 172032, 172032] | ['initial', 'initial', 'initial'] | 25.97/29.56 | 1.000× | 36.79 |
| fixed | 0 | budget-v3 | [172032, 172032, 172032] | ['initial', 'initial', 'initial'] | 25.83/28.93 | 1.016× | 36.70 |
| fixed | 0 | projection-v4 | [180224, 180224, 180224] | ['initial', 'initial', 'initial'] | 27.54/30.60 | 0.943× | 37.56 |
| fixed | 1 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 27.02/31.58 | 1.000× | 37.11 |
| fixed | 1 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 25.95/28.89 | 1.034× | 36.78 |
| fixed | 1 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 28.43/30.63 | 0.962× | 37.41 |
| fixed | 2 | rebuild | [176128, 176128, 176128] | ['full-profile', 'full-profile', 'full-profile'] | 27.68/29.90 | 1.000× | 36.98 |
| fixed | 2 | budget-v3 | [176128, 176128, 176128] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.04/31.13 | 1.019× | 37.09 |
| fixed | 2 | projection-v4 | [184320, 184320, 184320] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.02/31.69 | 0.949× | 37.47 |
| fixed | 3 | rebuild | [176128, 176128, 176128] | ['full-profile', 'full-profile', 'full-profile'] | 26.87/29.57 | 1.000× | 36.69 |
| fixed | 3 | budget-v3 | [176128, 176128, 176128] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.09/30.61 | 0.989× | 36.93 |
| fixed | 3 | projection-v4 | [184320, 184320, 184320] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 28.99/39.10 | 0.916× | 37.34 |
| fixed | 4 | rebuild | [176128, 176128, 176128] | ['full-profile', 'full-profile', 'full-profile'] | 27.21/30.25 | 1.000× | 36.77 |
| fixed | 4 | budget-v3 | [176128, 176128, 176128] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.23/29.93 | 0.995× | 36.84 |
| fixed | 4 | projection-v4 | [184320, 184320, 184320] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.72/32.39 | 0.920× | 37.78 |
| fixed | 5 | rebuild | [180224, 180224, 180224] | ['full-profile', 'full-profile', 'full-profile'] | 28.92/30.81 | 1.000× | 37.14 |
| fixed | 5 | budget-v3 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.06/31.63 | 0.988× | 37.20 |
| fixed | 5 | projection-v4 | [188416, 188416, 188416] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 30.85/33.13 | 0.937× | 37.72 |
| fixed | 6 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 29.43/32.14 | 1.000× | 36.85 |
| fixed | 6 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.48/32.90 | 0.997× | 36.91 |
| fixed | 6 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 31.07/33.84 | 0.946× | 37.37 |
| fixed | 7 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 28.86/32.19 | 1.000× | 36.86 |
| fixed | 7 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.03/34.09 | 0.999× | 36.62 |
| fixed | 7 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 30.92/34.71 | 0.943× | 37.47 |
| fixed | 8 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 28.82/31.34 | 1.000× | 36.93 |
| fixed | 8 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 28.61/32.30 | 1.004× | 37.14 |
| fixed | 8 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 31.26/37.04 | 0.923× | 37.62 |
| fixed | 9 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 28.65/31.10 | 1.000× | 36.98 |
| fixed | 9 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 28.47/31.30 | 1.002× | 36.97 |
| fixed | 9 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 30.67/33.05 | 0.931× | 37.41 |
| fixed | 10 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 28.59/31.34 | 1.000× | 36.83 |
| fixed | 10 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 28.66/31.24 | 0.999× | 36.93 |
| fixed | 10 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 30.60/34.14 | 0.938× | 37.26 |
| fixed | 11 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 27.95/30.17 | 1.000× | 37.08 |
| fixed | 11 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.85/30.21 | 1.007× | 37.12 |
| fixed | 11 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 30.16/32.77 | 0.925× | 37.57 |
| fixed | 12 | rebuild | [180224, 180224, 180224] | ['full-profile', 'full-profile', 'full-profile'] | 27.44/35.48 | 1.000× | 37.26 |
| fixed | 12 | budget-v3 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.70/29.62 | 0.994× | 37.14 |
| fixed | 12 | projection-v4 | [188416, 188416, 188416] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.34/31.97 | 0.939× | 37.59 |
| gear | 0 | rebuild | [172032, 172032, 172032] | ['initial', 'initial', 'initial'] | 24.35/27.41 | 1.000× | 37.02 |
| gear | 0 | budget-v3 | [172032, 172032, 172032] | ['initial', 'initial', 'initial'] | 24.31/26.54 | 0.993× | 36.88 |
| gear | 0 | projection-v4 | [180224, 180224, 180224] | ['initial', 'initial', 'initial'] | 26.07/29.52 | 0.931× | 37.66 |
| gear | 1 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 25.02/28.51 | 1.000× | 37.27 |
| gear | 1 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 25.21/27.51 | 0.997× | 36.97 |
| gear | 1 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 26.79/30.36 | 0.934× | 37.42 |
| gear | 2 | rebuild | [176128, 176128, 176128] | ['full-profile', 'full-profile', 'full-profile'] | 25.84/28.76 | 1.000× | 37.29 |
| gear | 2 | budget-v3 | [176128, 176128, 176128] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 25.75/29.36 | 1.002× | 37.46 |
| gear | 2 | projection-v4 | [184320, 184320, 184320] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 28.07/31.54 | 0.922× | 37.86 |
| gear | 3 | rebuild | [176128, 176128, 176128] | ['full-profile', 'full-profile', 'full-profile'] | 25.52/27.84 | 1.000× | 37.21 |
| gear | 3 | budget-v3 | [176128, 176128, 176128] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 25.63/29.38 | 0.985× | 37.06 |
| gear | 3 | projection-v4 | [184320, 184320, 184320] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.57/30.60 | 0.926× | 37.54 |
| gear | 4 | rebuild | [176128, 176128, 176128] | ['full-profile', 'full-profile', 'full-profile'] | 26.05/28.90 | 1.000× | 37.28 |
| gear | 4 | budget-v3 | [176128, 176128, 176128] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 26.23/29.05 | 0.995× | 37.09 |
| gear | 4 | projection-v4 | [184320, 184320, 184320] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 28.26/31.17 | 0.921× | 37.55 |
| gear | 5 | rebuild | [180224, 180224, 180224] | ['full-profile', 'full-profile', 'full-profile'] | 27.65/29.87 | 1.000× | 37.16 |
| gear | 5 | budget-v3 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.40/31.11 | 1.000× | 37.23 |
| gear | 5 | projection-v4 | [188416, 188416, 188416] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.70/32.79 | 0.928× | 37.36 |
| gear | 6 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 27.69/30.14 | 1.000× | 36.82 |
| gear | 6 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.46/30.80 | 1.012× | 37.27 |
| gear | 6 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.55/32.96 | 0.934× | 37.40 |
| gear | 7 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 27.54/29.56 | 1.000× | 36.89 |
| gear | 7 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.50/30.29 | 0.996× | 36.86 |
| gear | 7 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.53/32.71 | 0.927× | 37.80 |
| gear | 8 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 27.55/30.52 | 1.000× | 36.83 |
| gear | 8 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.97/35.96 | 0.987× | 36.79 |
| gear | 8 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.77/32.18 | 0.933× | 37.17 |
| gear | 9 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 27.29/29.93 | 1.000× | 36.67 |
| gear | 9 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.48/30.59 | 0.995× | 37.06 |
| gear | 9 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.16/31.96 | 0.937× | 36.95 |
| gear | 10 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 27.56/29.95 | 1.000× | 36.74 |
| gear | 10 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 27.21/30.89 | 1.001× | 36.73 |
| gear | 10 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 29.44/33.12 | 0.925× | 37.13 |
| gear | 11 | rebuild | [172032, 172032, 172032] | ['full-profile', 'full-profile', 'full-profile'] | 27.26/32.89 | 1.000× | 36.93 |
| gear | 11 | budget-v3 | [172032, 172032, 172032] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 26.76/29.81 | 1.008× | 36.97 |
| gear | 11 | projection-v4 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 28.75/32.50 | 0.942× | 37.20 |
| gear | 12 | rebuild | [180224, 180224, 180224] | ['full-profile', 'full-profile', 'full-profile'] | 26.60/29.41 | 1.000× | 37.15 |
| gear | 12 | budget-v3 | [180224, 180224, 180224] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 26.64/30.29 | 0.995× | 37.31 |
| gear | 12 | projection-v4 | [188416, 188416, 188416] | ['budget-record-bytes', 'budget-record-bytes', 'budget-record-bytes'] | 28.97/33.91 | 0.916× | 37.57 |

4212正式、936历史完整身份查询的排序、BM25绝对差<=1e-10、title/sentences/当前
精确locator均匹配完整重建。234人为不存在标记阴性控制，不称科学反例。234历史
快照实例全源SHA/大小重读，当前源逐字节一致；同分块CAS树一致，查询不改持久树。
234新进程，各一预热排除。新6篇/12正文转换，18诊断词项非gold QA；0模型调用。

原始XML完整保存、整文件offset0定位。FTS只投影标题、普通摘要与正文段落，过滤
图表/评审等；原始数式/表格仍保留，文本投影不等于完整科学语义。新kind需v0.23，
旧v0.22不解码JATS；归档v1–v6/CAS1/应用清单v1–v4不变。默认仍预算v3，v4显式。
writer没有为获得收益放宽预算；下一实验应独立定义更细证据记录及完整身份。

query计整个search与释放，启动另列；commit含全源读取/解析/预算/校验/HEAD发布，
源准备不计。worker RSS含整个进程与选题输入，不能和v0.22小输入历史峰值直接比。
全部RKV Python/HTML计一次，Gear加整个精确旧DLL/元数据；公共Python/SQLite/OS、
pyc、安装/文件系统元数据未全额分配，非完整部署净压缩。不得把Gear CAS节省称为
v4增量索引收益，也不把同一论文两个转换当两个独立论文。
仅本机温缓存；无新QA质量、E3、多跳、长期对话、形式证明、冷缓存/跨机器、掉电/
并发或GC结论。原始科学输入/正文/私有研究不发布，固定来源和SHA可复建。
