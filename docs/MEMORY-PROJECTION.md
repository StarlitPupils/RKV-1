# v0.21 论文投影与原始字节定位（结果前冻结）

目标：避免QASPER版本文件名、标注、JSON排版变化造成FTS正文无变化却全量重建。
显式候选compact-projection-v4；默认仍compact-budget-v3，不迁移现有库/历史视图。
归档v1–v6/CAS1不变；新应用清单/overlay版本4及基础projections表需要v0.21读取器，
旧v0.20拒绝。v1/v2/v3读写与v0.20预算策略保持。

每个基础记录保存32B SHA256，输入为项目确定性JSON编码的
{version:1,title:原title,sentences:[abstract,full_text各paragraph]}。沿用现有论文
投影，不含section_name/qas/图表等；保留句子边界、顺序、Unicode及全部投影字符，
不是token归一化或有损摘要。所有来源记录均保存指纹，但只有相同key/kind的QASPER
记录允许字节SHA/路径改变而不改FTS。指纹表与基础SQLite一起由完整文件SHA绑定。

每次提交仍全量读取/校验原始源，重新解析投影、计算指纹和精确字节位置。相对单份
基础，投影相同但成员原字节/路径改变时生成rebound=[新locator,投影SHA]，保留原FTS
postings。查询验证整个基础/overlay SHA、快照/源树绑定，并逐条核对rebound与基础
指纹相等、key/kind存在、操作不重复/不交叉。当前命中仍解码当前CAS字节、验证原
成员SHA、重新解析key/kind及完整投影SHA。返回当前SID/路径/偏移/长度/原SHA；不
从摘要恢复原文，不返回基础版本原始成员冒充当前来源。

正文改变/新增/删除仍完整重放FTS，以全库BM25查询；相对基础最多32变化、256KiB
原记录读取、2MiB逐次CAS解码工作，另保留原25%/256位移规则。元数据rebinding
最多4096条，超限也完整检查点；不将它混计为FTS重放字节。该上限不保证wall/RSS。
label-only状态可复用基础。无跨查询缓存/索引物化文件/GC，所有历史原文和索引保留。

三条件：compact-full-v2完整重建；v0.20默认compact-budget-v3；显式v4候选。每组
各三轮，新库/工作进程，条件顺序用20261024+round打乱。比较当前同源码的策略，
不把整个历史版本时序相除。两表示分别隔离：

* official-gear：沿用固定SHA的QASPER dev v0.1/v0.2/v0.3，原文件名/所有字节原样。
  同Gear64KiB/Zlib6/精确旧Rust扫描库。重建每阶段的SID及持久树须匹配v0.19。
* official-fixed：相同发布、固定64KiB/Python，单列默认分块环境。
* synthetic-fixed：160个确定性生成的QASPER模式论文，固定64KiB，9状态：初始；
  所有标注增长并改路径；逆序/JSON排版及Unicode转义变化；1篇真正文编辑；删1添1；
  相对基础33篇标题编辑触发预算检查点；恢复原始论文及新路径，再次检查点；相同
  字节/不同label；1篇标注增长。v4预期只0/5/6完整基础，状态1/2仅160重绑定、FTS
  重放0字节。控制验证正文变化不会被误当标注，不是真实论文修订或新科学样本。

官方三次发布每版281论文，正文投影相同，原成员变化281/9。已见数据集发布负载，
非新独立论文修订。官方问题复用v0.19的64条（v0.1按ID排序每篇首个未重复问题），
不新增科学问题。原任务给定论文，来源论文@5仅为全局检索诊断，不作答案质量。
合成组16词项/阴性探针，三轮同计划同顺序。每阶段新查询进程，1次预热排除，共
135进程/预热，4752正式查询（3456官方既有问题重复、1296合成）。每次提交再对
初始快照查询4题，共540历史身份查询；合成81次原始快照未来词项探针必须阴性。
所有135历史快照实例结束重开全源SHA/大小，当前源逐字节一致；实例含轮次/策略重复。

同轮/同组各策略CAS树必须逐字节一致。所有正式/历史查询比较key顺序、BM25绝对
差<=1e-10、title/sentences/完整locator摘要；查询前后每个持久文件大小/SHA不变。
query wall/CPU包含整个search/资源释放，进程启动另列；commit包含投影SHA、预算
估计、全源解析/验证、建索引/HEAD发布，源准备不计。进程峰值RSS含输入/完整进程。
逐问题/轮配对速度比后取中位，完整列出各阶段新写索引/检查点/空间/提交/查询/RSS。

完整计所有RKV Python模块和HTML一次，含未用v4模块，Gear另计完整实测DLL及原
native.json；固定组无原生依赖。Python/SQLite/OS、pyc、安装及文件系统元数据未
全额分配，不称完整部署净压缩。v4指纹表/每版重绑定本身全部计费，不能只报FTS省。
旧精确实测库另附Release，与CI新二进制功能验证区分。原始科学语料/问答内容和
私有研究报告不发布；只保存固定来源、SHA与聚合/不含原文的查询摘要。

仅本机温缓存；无新模型调用/预算、推理质量、E3、多跳、长期对话、真实论文正文
修订、冷缓存/跨机器、并发写入、掉电或GC结论。指纹/内容SHA提供现有完整性校验，
不声称对任意重写清单/索引的恶意者进行认证或替代科学蕴含证明。

```powershell
python -m rkv1 memory-init path/to/new-memory path/to/evidence --index-profile compact-projection-v4
python -m scripts.run_memory_projection --out results/local-projection --work .tools/local-projection --native-library measured/rkv1_core.dll
```
