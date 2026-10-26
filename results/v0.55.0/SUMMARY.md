# v0.55.0 实验报告：显式快照与模型身份的论文证据API

## 交付目标与结果

新增可从wheel调用的实验模块`rkv1.experiments.paper_retriever.PaperRetriever`。此前BM25/图候选主要在assessment脚本；现在调用方可以显式指定Store、SID、私有模型路径及expected SHA，以纯claim文本检索并返回本地原论文证据和精确locator。默认Memory/CLI/UI不改，不自动读取HEAD，不调用远程模型，不生成回答。

**唯一3 fresh机制worker、894次接口调用全部逐项等既有v053 proof**，每方法298/298。正式2559 selected原文绑定，独立审计另2559绑定；worker各自完整原corpus恢复3次，审计另3次。所有selected IDs/原record入证B/原title及abstract SHA/指定SID/offset/length/rawSHA均一致。只是已见结果的工程兼容性，不是新增科学质量试次、未知数据验证、检索收益或回答提升。

| 方法 | 匹配原proof调用 | selected绑定 | 构造wall s | 构造CPU s | query总wall s | query总CPU s | worker wall s | worker CPU s | parent完整wall s | 观察peakRSS B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lexical | 298 /298 | 853 | 0.303378 | 0.296875 | 1.338822 | 1.343750 | 2.177580 | 2.140625 | 2.285435 | 88645632 |
| graph | 298 /298 | 853 | 0.303401 | 0.281250 | 1.330706 | 1.359375 | 2.168741 | 2.093750 | 2.279043 | 89063424 |
| permuted_graph | 298 /298 | 853 | 0.297515 | 0.296875 | 1.339415 | 1.343750 | 2.170247 | 2.078125 | 2.280433 | 88829952 |

三方法各一次，不能从小时间差推稳定加速/优劣；query包含源校验、构造包括模型JSON加载/结构检查，父wall包含解释器启动/ingest/序列化/恢复。没有与旧进程作同负载配对性能实验，不能从旧版本不同计时边界扣减得出算法加速。285检查284通过/1Windows权限跳过；exact候选CI 40377301295成功后才正式运行。

## 固定原数据与分母

SciFact原corpus5183paper/8307875B，SHA b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62；模型10152832B，SHA f062c7a784421b71bbfaf3c299be78ff323a391847afbf5420e4c06a4d422be0。原v053训练只一次，此版不训练或改权重。新方法代码/协议/input freeze `7cfe023d834222fe8b01456f1fc11e99ada4c812`，输入原byte SHA和前版实际proof身份在[清单](../../docs/paper-api-inputs.json)。

沿既有v053 round1三方法原report和对应私有query-check，原dev300行/训练重叠排除2/实际检索298，其中188有gold、110无gold。新API只拿claim字符串，机制比较不重新计算gold分数，0新科学质量试次；188/110与原quality门槛不变。894=同298条×三方法，不是894独立科学样本。使用已见数据，不能声称封存未知题目或领域泛化。

原v053质量True/时间False/联合False、仅多1个gold来源组且完整仍139/188；v054诊断正图漏证62组原byte拒绝、188条有gold仅26条seed触图，均不由本版覆盖。原v051 literal负方向和E3净收益失败继续保留。接口可调用是工程进展，不是总科学目标完成。

## API契约与使用

```python
from rkv1.experiments.paper_retriever import PaperRetriever

reader = PaperRetriever(
    store_root, snapshot_id, model_path,
    model_sha256=expected_model_sha256,
)
evidence = reader.query(local_claim_text, method="lexical",
                        max_papers=12, source_byte_budget=4096)
```

Store、SID及同SHA模型须由调用方在本机合法准备；本项目不发布原科学source、原claims或私有postings/图模型。可通过已公开scripts.run_scifact_graph的train入口对冻结原corpus/claims_train重建确定性模型，再匹配清单；API不是自动模型下载器或训练服务。此版不提供自动选择当前HEAD、远程生成或默认UI集成。

query只允许非空字符串≤4096字符、无NUL；方法lexical/graph/permuted_graph固定。预算最多12篇/4096原整行B，只能收紧，拒绝bool和越界。原token/BM25 k1=1.2,b=.75、top6词法seed+6邻居及tie/超剩余预算skip继续，从冻结assessment复制为wheel内自包含函数，AST逐项相等并有实际三方法合成/原proof验证。没有要求wheel导入scripts。

返回本地原title/abstract、paperID及指定SID/path/offset/length/rawSHA，附title/abstract SHA。`selected_source_identity_verified=True`仅说明所选原文身份；`scientific_entailment_verified=False`、`generated_answer=None`明确不验语义和不答题。空预算返回空hits，并非空证据“正确回答”。不对未选的所有CAS重新读取核验，不把snapshot元数据中有整源hash称当次整源全部实读。

## 身份、损坏与生命周期

constructor显式expected model SHA、最多32MiB原payload后加载，拒绝重复JSON key/非有限常量、不支持source kind/参数、坏locator/重叠范围、posting与token长度不符、非对称图或控制degree不符。仅支持scifact-whole-original-record-v1，不把EntailmentBank短句模型直接用于论文。32MiB限制是原payload，不是RAM上限；JSON对象和瞬态buffer照实占内存。

实例固定原已加载模型；磁盘同路径后续变更不改变该实例，fresh loader按expectedSHA拒绝。每次query重新打开并验证指定snapshot/sourceSHA和locator范围，所选read_range保留stored/raw/codec/EOF/size检查，再验原recordSHA、docID、title/abstract schema及hash。无跨请求decoded缓存，上一请求后损坏selected CAS，下一请求拒绝。旧SID在新snapshot提交后仍固定，新SID/source与旧model不符拒绝。

model_info参数深拷贝、返回hit.abstract及locator不暴露可变内部模型；调用方修改返回对象不污染下次调用。模型对象留在实例RAM是有意状态和费用，不称“没有缓存所以没有内存成本”。

## 唯一机制运行与独立验证

正式3worker按lexical/graph/control顺序各1，600s/worker，0补轮/重试；每worker新Store zlib/fixed65536/bounded、同原label，实际SID等v053。每条selected与B先由新API得到，再与已有proof比较，公开记录只留ID/locator/hash和时间，原title/abstract与claim不写公共JSON。

独立analyzer直接原JSONL raw slice核paperID/title/abstract SHA、offset/length和实际新Store read_range，再匹配原report proof和新proof SHA；另整源逐字节恢复。它的2559追加绑定不是新增科学试次，不能把重复审计数当独立样本。所有worker Store整树前后相同。

冻结前8合成检查覆盖方法等价/精确原记录预算、旧SID与newSID不配、跨请求CAS损坏、输入限额及拷贝隔离、model SHA/schema/重复key/NaN/32MiB+1拒绝、坏locator/graph/posting、内存模型pin与fresh loader、返回值修改隔离。私有3个298次重复假query的harness smoke另保留，是人工数据预检，不能混到本正式894次真实源机制调用里。

## 完整成本与边界

每方法实际载完整10152832B模型（包含shared索引及正/控制两图），不能把lexical实际部署说成未载图。历史一次训练wall 1.071652s/CPU 1.046875s、父完整wall 1.167893s继续计共享成本，新增模型B0不是模型或原训练免费。

每worker原source副本8307875B、Store全部CAS/config/snapshot/残留2963638B，所有报告/parent/log另占B。历史原训练/v053全部worker及新3worker保留文件共146299374B，逐文件实际B/SHA在measurement-context；不是生产必须常驻这些评测副本，也不把不随包发布等同不存在。旧其他任务模型/快照/原语料历史文件不删，不以删除历史算压缩。

完整66递归Python+HTML实际426112B，相对前版416514B新增9598B；旧模块除版本逐字不变。新增实验模块、全部实际assessment脚本、协议/input/test源码实际B/SHA分别列。平台/解释器/依赖未分配，不称全机TCO；private model/source/frames/restored bytes不发布。

独立原源/实际Store二次审计和标准图额外wall 1.748815s、CPU 1.750000s、观察RSS 86249472B，不计API query。worker观察RSS不是完整生命周期增量RAM；4096入证上限不是全CAS读取、OS/SSD物理IO、模型或总RSS上限，SSD物理/全系统IO/冷缓存/跨机继续null。

![已见proof API兼容机制检查](paper-api.png)

图已实际打开检查：左为298次原proof全一致，右为各一次worker的总query wall，从0起、标签/余白无裁切。不是答案准确率或稳定性能对照，不以三个近似柱子推显著性。

## 跨额度窗口收尾与发行核验

本次原机制试验在前一授权窗口唯一运行完成，达到实读100%后保存原JSON/图及checkpoint、删除自动续跑；用户再次明确授权后只收尾报告和发行，不重跑测量、不回填或修改原时间。原冻结CI、原输出SHA和原失败分母不变。

准备中的私有发行smoke发现新encoded名字缺导入，已在实际两个helper和生成器补导入；发生于真实包smoke前，未改冻结API/协议或正式机制数据。后续发行真实失败如有应原样保留，不覆盖原实验。285全检查与冻结CI通过之后仍须真实包验证，不能将开发版检查代替发行验证。

代码/冻结协议/rawJSON/图/本详实报告/README/release推送；CI成功Release后实际5资产SHA、66递归Python+HTML集合与tag/冻结成本一致，实际物理仓库外wheel+current native/新PaperRetriever三方法及原source预算/旧sdist功能，最终proof上传重下载全部完成，才完整交付。无新增远程模型API（旧24次已耗尽），本机CPU离线。

后续应另冻预算/证据单位或来源约束的新假设，或测试新API在更复杂生命周期中的行为，不能在已见dev调k/图/预算追正。**E3净收益失败，E4整体、真实长期会话、科学verdict/NLI/形式证明、生成回答质量和无限上下文仍未验收。**

发行前真实本地安装smoke首次失败于内嵌子进程缺hashlib导入（不是API或原证失败）；原失败日志保留B/SHA在package-harness-recovery.json。只修私有smoke helper/生成器后在新临时目录恢复合成包检查，冻结runtime/协议和正式机制数据不改，不重跑科学或机制试次。
