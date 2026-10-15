# v0.17 多版本更新放大对照（结果前冻结）

本轮处理v0.16控制实验中13B插入触发全量CAS重写/索引重建的问题，不调用模型API。
CAS1和归档v1–v6不变；复用现有Gear-v1及可选Rust扫描，保持逐字节来源与全库BM25。

## v3基础相对差异

新建库默认compact-base-v3，固定64KiB分块仍为默认；已有v1/v2库继续原策略，不迁移。
新v3应用清单需v0.17读取器，旧v0.16明确拒绝。Memory.create和memory-init新增
chunker/chunk_size选项；提交可显式选择Python/Rust Gear，Rust不参与检索或解码。

每个快照只保存相对不可变基础索引的累计差异，最多一份overlay；不追加无界重放链。
原记录SHA/路径/长度等不变而位置改变时，按原始位置合并为偏移区间，单独更新定位，
不触碰FTS词项。区间先统一选取旧rowid再移动，避免相邻范围交叉导致重复移动。
记录删除/改变/新增仍用CAS原字节删除/插入FTS，最终仍以SQLite完整当前统计排序。

记录的非位置变化累计超过基础记录数25%（最少容许1条），或位置区间超过256段时
建完整紧凑检查点；仅位置变化不触发25%门槛。v2仍保留其8层/25%旧策略。
每次查询仍核验基础索引/overlay完整SHA，读取必要基础/当前CAS记录并逐条校验。
所有原文、旧快照、基础和overlay保留并计费，不删历史。提交仍全量扫描/哈希来源。
修复仅增加空白字节、索引记录未改变时的发布处理；新旧v2读取兼容。

## 冻结矩阵

固定SciFact原始corpus.jsonl 5,183摘要、8,307,875B，使用既有SHA。只修改独立工作
副本，不把合成变动当新科学语料。Zlib6、64KiB尺度；5个条件×3轮，轮内种子
20261020+round打乱条件顺序，各自新进程/新库：

| 条件 | CAS | 索引 | 提交扫描 |
|---|---|---|---|
| fixed-v2 | fixed | compact-delta-v2 | Python固定 |
| gear-python-v2 | gear-v1 | compact-delta-v2 | Python Gear |
| fixed-v3 | fixed | compact-base-v3 | Python固定 |
| gear-python-v3 | gear-v1 | compact-base-v3 | Python Gear |
| gear-rust-v3 | gear-v1 | compact-base-v3 | 冻结既有Rust Gear |

固定/Gear分开考察CAS复用；v2/v3分开考察索引变化。Gear Python/Rust须逐阶段整个
存储树逐字节相同；只比较扫描实现的耗时，整份实测DLL＋native.json单独计入Rust。
原生库由--native-library指定，开始前记录并验证其SHA；不将CI新二进制冒充实测库。

11个连续阶段（全保留）：初始；追加88B note1；末条title等长单字节修改；首条
abstract插入13B固定标记；删除该标记；追加88B note2；末条title再次等长修改；
首条插入不同长度第二标记；删除note1；删除首条JSON记录；追加88B note3。
每次修改记录源字节数变化、对象新写/复用、索引新增、检查点和全部保留成本。

初始188条标注主张查询top10，后10阶段各固定前32条＋3个独特词项探针，共
8070次正式查询；初始阶段每条件/轮仍相同188条，不是新增独立问题。另每阶段
重查初始前8条＋3探针，共1815次旧快照查询。查询每阶段新起子进程，一次预热
排除正式统计；wall含索引/原文SHA与完整重放，不含进程启动，启动总时长另列。
峰值RSS含整个查询进程/解释器/输入加载，不是单请求内存增量。温缓存、本机。

每阶段的排序、BM25（绝对差<=1e-10）、title/sentences及路径/offset/length/原SHA
与同轮fixed-v2一致。CAS表示不同的snapshot_id不要求相同，但各自定位必须从其
实际快照读取并校验；初始排名另对照v0.16。每阶段全源逐字节比较，最后重新读取
全部历史快照，核对当时文件SHA/大小，不只核对当前HEAD。查询不得修改持久树。

成本：全部保留CAS对象/快照、索引/overlay/config、清单、HEAD；本轮无回答写回。
所有条件统一另计整个memory.py、memory_index.py、chunking.py源各一次；Rust再计
整个实测DLL/元数据。公共Python/SQLite/Store/core/OS未全额分配，不称完整部署净压缩。
不与v0.16不同阶段数/回答账本直接算版本压缩提升。空间、查询、提交、RSS分别报告，
不设事后速度门槛，不称全流程支配；等长/插入/删除是控制负载，不代表真实版本家族。

本轮不测长会话、科学推理质量、E3、冷缓存、跨机器、真实掉电或自动GC。

```powershell
python -m scripts.run_memory_updates --out results/local-memory-updates --work .tools/local-memory-updates --native-library .tools/native-v0.8-measured/rkv1_core.dll
python -m scripts.analyze_memory_updates results/local-memory-updates --test-log path/to/test.log --plot
```

离线复核可用analyze_memory_updates的--native-library指定已解压的精确实测库位置，
库及原native.json的SHA仍须匹配，不允许替换CI新二进制后沿用原计时。
