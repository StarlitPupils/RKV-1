> 当前v0.19原始QASPER及长历史见[MEMORY-HISTORY.md](MEMORY-HISTORY.md)，v0.18查询见[MEMORY-QUERIES.md](MEMORY-QUERIES.md)。新建库默认
> 固定分块＋基础相对v3，旧v1/v2库继续原策略。v0.16协议见[MEMORY-INDEX.md](MEMORY-INDEX.md)。
> 下文为v0.15冻结协议，复现旧实验使用对应标签，不覆盖旧结果。

# v0.15 首个证据记忆与模型回答基线

本版提前搭建E4的最小工程闭环，E2继续保留，E3仍未实施。不是完整长期对话智能体。
资料入库→词法检索→从CAS读原始记录→模型据证判断→校验引用→派生回答写回。
原始资料与模型回答隔离，新增来源以显式memory-add更新，不让模型输出自行变成证据。

## 本地存储与引用

memory-init创建CAS1，原文件路径和字节保留；使用既有固定64KiB/Zlib，不改旧格式。
SQLite FTS5 BM25（porter unicode61）只索引原始title/abstract或UTF-8文本，属于英文
词法基线，没有embedding或图检索。查询最多64个去常见停用词的词项，用OR匹配，
排序按bm25及document key；参数和问题集在正式结果之前固定，不按dev结果调优。

JSONL只接受SciFact doc_id/title/abstract格式，不能把claims/gold labels混入索引。
来源定位为snapshot/path/offset/length/SHA256，指向原始JSON行字节，包括原JSON
转义与换行。每次搜索计入整个索引SHA检查，重新从CAS读取每个命中的原始记录，
校验记录SHA及索引文本与解析原文的一致性后才能进入模型上下文。索引可以重建。
哈希证明完整性，不证明来源身份或科学结论。父目录可信，单写者；无签名或恶意
重写全套清单的防护承诺。最多64MiB来源文件、1MiB记录/文本文件、20检索结果。

每个快照有完整独立SQLite索引及清单；HEAD仅在索引完成后更新，旧快照可读。
存储账本计所有保留对象、快照、索引、清单、HEAD和派生回答。索引不是免费资源，
模型/远程运行时体积未知，公共本地运行时未完整分配；不宣称总部署净空间收益。
文件同步、原子替换/链接沿用研究原型边界，未测目录/卷同步、真实掉电或自动GC。

## 模型边界

模型来自用户指定Chat Completions服务，环境变量为RKV_LLM_BASE_URL、RKV_LLM_MODEL、
RKV_LLM_API_KEY；密钥只用于请求鉴权头，不写源码/实验记录。拒绝URL凭证、查询
参数或跨站重定向。DeepSeek官方服务采用deepseek-flash，关闭thinking，JSON输出，
temperature=0，max_tokens=256，不调用其他模型，不对失败请求自动重试。
资料与检索在本机CPU，模型推理在远程API，不能称为全本地CPU模型评测。

每条主张提供最多5个命中文档、24,000 UTF-8字节的完整原句；超出预算的原句不
发送，且禁止引用未发送句子。模型给SUPPORT/CONTRADICT/INSUFFICIENT、句子ID和
短解释；解析或引用越界失败保留原响应，拒绝当成有效答案。无证据时允许弃答。
证据内容始终是数据，不是工具指令，模型没有写源文件或执行代码的权限。

引用绑定有效只表示模型引用了实际提供的原句；它不证明该句支持模型结论。
scientific_entailment_verified始终false，科学正确性另用人工标注评分，不混淆两者。
派生回答以独立answers记录写回，绝不自动进入原始证据检索。memory-add显式替换
当前来源集合、保留旧快照；它不是已实现自主记忆整理或跨轮对话推理。

## 冻结评测

只把固定SHA的SciFact corpus.jsonl 5,183篇摘要入库，claims_dev.jsonl不进入CAS或索引。
数据沿用既有下载SHA。标注主张/证据CC-BY-4.0，摘要ODC-By-1.0，来源署名和许可见
[上游许可](https://github.com/allenai/scifact/blob/master/LICENSE.md)。原始语料不再分发。

检索：全部188条有证据的dev主张，三轮，每轮种子20261018+round打乱；一次预热后
共564次top10搜索，逐条原记录校验。报告@1/5/10宏平均gold文档召回、至少命中一份
gold的主张数与wall分布。空标注112条不作为全库无证据证明。dev不是严格盲测，
公开模型也可能见过该数据，gold不是完整相关文献全集。重复轮次不是独立样本。

模型：按主张ID升序每类先取4条，SUPPORT=[3,5,49,50]、CONTRADICT=[42,48,51,54]、
INSUFFICIENT=[1,13,36,72]。12条×有检索/空证据两条件，共最多24次真实生成，
用种子20261018打乱。相同模型、提示约束、温度和输出预算，单样本，无重试。
空证据条件仍要求只能据证回答，是受约束无证据基线，不是无约束闭卷模型或成熟
RAG系统对照。报告格式/引用绑定有效率、标注判定准确率、完整任一gold rationale
引用率、判定与rationale同时正确率；INSUFFICIENT按标注判定，不证明全库确无证据。
模型正确性失败计入分母，传输/鉴权故障立即停下并保留已用请求，报告未完成。

API记录保留问题、来源定位/文档ID、请求SHA、原响应、usage和耗时；不保存完整
摘要提示词副本或鉴权头。总token按服务返回字段统计，缺失记未知；费用未获账单
则为null，远程权重成本未知，不声称总体压缩/推理资源最优或通用推理提升。

机制检查：新增带固定独特词项的UTF-8/CRLF合成记录，重新打开记忆库，验证新版
可召回、旧快照不可看到未来记录；另存合成派生记录，验证不进入原始证据检索。
这部分与真实模型调用分开，不以合成测试冒充模型长会话能力。温缓存、本机；
无冷缓存/跨机器/长期连续对话/多跳图谱/形式化证明或E3神经压缩结论。

## 使用

```powershell
python -m rkv1 memory-init data/my-memory data/evidence
python -m rkv1 memory-search data/my-memory "a scientific claim"
$env:RKV_LLM_BASE_URL="https://api.deepseek.com"
$env:RKV_LLM_MODEL="deepseek-flash"
# RKV_LLM_API_KEY只在本机环境变量配置，不粘贴到仓库文件。
python -m rkv1 memory-answer data/my-memory "a scientific claim"
python -m rkv1 memory-add data/my-memory data/updated-evidence --label revision-2
python -m rkv1 memory-serve data/my-memory --port 8765
python -m scripts.run_memory --out results/local-memory --work .tools/local-memory --api
```

浏览器仅绑定127.0.0.1，不对外部署；页面原文用textContent展示，不执行证据HTML。
模型服务配置缺失时仅能检索，不以模板回答冒充LLM。HTTP合同测试使用本机明确
标记的测试服务，不计入真实模型评测。发行包应包含memory_demo.html。

## v0.20回放预算

新建库默认compact-budget-v3，旧v3库可memory-budget显式启用未来写入；历史视图
不重建。默认32变化/256KiB原记录/2MiB逐次CAS工作，超限完整检查点，并保留原
25%/256区间规则。预算不保证总wall/RSS上限，详见[REPLAY-BUDGET.md](REPLAY-BUDGET.md)。

## v0.21显式论文投影候选

memory-init可显式--index-profile compact-projection-v4，默认继续预算v3。v4将
QASPER投影指纹与当前原始成员locator分开，标注/路径变化不重写FTS，但仍保存
所有原始字段和历史、验证当前命中原文/投影；新应用清单v4需新读取器，旧v0.20
拒绝。空间省、官方发布查询更慢，完整说明见[MEMORY-PROJECTION.md](MEMORY-PROJECTION.md)。

## v0.22 v4查询准备

v4批量检查全部重绑定、仅投影命中定位，纯定位/位移直接读基础，FTS变化仍复制
完整重放。旧库直接读，无格式/持久字节变更；默认v3不变。官方组有改善但v4仍慢
于v3，小基础/单条更新收益不稳定；见[PROJECTION-QUERIES.md](PROJECTION-QUERIES.md)。

## v0.23真实正文修订与JATS来源

eLife固定六篇三版本，12次正文投影变化，13状态、固定/Gear三策略各三轮。
JATS原始XML整文件为精确记录，新kind需v0.23，旧v0.22来源解码器拒绝；旧来源
兼容，应用清单/归档/CAS不改。4212正式/936历史身份查询对齐重建，177测试
通过/1权限跳过。所有预算策略逐次因旧+新整篇记录>256KiB完整检查点，v4无增量
索引收益；默认仍v3。0模型调用，新6篇非大样本；详见[PAPER-REVISIONS.md](PAPER-REVISIONS.md)。
