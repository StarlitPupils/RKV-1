# v0.49.0 实验报告：训练标注到原始科学来源的身份就绪审计

## 结论：来源机械验证通过，两个严格数据就绪门槛失败

冻结3 fresh worker完成17292重复叶检查、16533实际原始成员范围绑定和3整corpus逐字节恢复，原Store全部文件树前后/跨轮相同。严格“所有训练叶可定位原source”门槛 **False**，严格“所有annotation逐字等原source”门槛 **False**。这些负结果保留，不换匹配规则追全通过。

| 单轮5764叶出现 | 数量 | 含义 |
|---|---:|---|
| 原provided UUID可定位 | 3982 | 按原来源ID，仍单独核literal是否相同 |
| 无有效UUID但精确decoded句子相等 | 1529 | 仅逐字fallback，无大小写/标点/模糊匹配 |
| 无精确来源可解 | 253 | locator为null，原样保留分母 |
| 总可原文范围绑定 | 5511 | stored/raw/member SHA与原JSON成员核验通过 |
| annotation与原source逐字相等 | 2142 | 含UUID和精确fallback |
| UUID绑定但annotation文字改写 | 3369 | 不据ID存在宣称语义等价或正确推理 |

未解不等于已证明标注错误，文字改写也不等于错误；本版不做语义等价/NLI判断。不能把5511次机械来源绑定叫5511次推理成功，也不能把三轮重复当三个独立科学样本。开发集仍未解析、模型/图训练0、检索分数0、retrieval_quality_gate=null。这是已见训练输入的独立物理诊断，准备阶段计数已看过，不声称未知科学验证。

## 数据来源和隔离

公开官方[allenai/entailment_bank](https://github.com/allenai/entailment_bank)固定commit daac2fdb7ab52ec3ef8f2953f59288c1edd7c2f0，原文件路径/Git blob SHA1、本项目SHA256/字节数见[输入身份](../../docs/entailment-inputs.json)。根LICENSE是Apache-2.0，不据此臆断全部上游事实独立许可；原数据不重分发。正式只读取corpus.json和Task1 labels-train.jsonl，不读两个dev或题目/答案/hypothesis/context/relevance内容作特征。

准备下载的Task3训练1313条proof全空，不能误当gold。另取Task1权威proof原1313行/1308唯一qid，5764叶出现；不使用Task3已检索25句及relevance分数当本项目结果。两个开发文件仅下载固定原字节/行数/SHA，未解析问题答案或评分。本正式程序两文件入口可静态审查，没有全系统文件访问监视，不能将标记冒充OS层I/O证明。

原corpus 11941 source IDs，11521精确decoded句子组、420完全相同文本alias。代表固定lexmin原ID；原JSON完整保留，不删除原alias字节，不把派生代表选择冒充压缩节省，也不做语义合并。UUID映射到其精确alias代表仍是原文件里确实存在的成员。

每leaf按proof的sent数字引用取原meta triples/provenance，若UUID存在先按原ID定位；另核annotation literal。无有效UUID只能精确decoded文本相等fallback，不能把gold补到原科学corpus或丢掉253未解。UUID改写虽有原ID，未提供语义证明，未来若评估ID召回也必须明确此口径。

## 冻结、必要检查和唯一计划

263检查262通过/1Windows权限跳过；代码/协议/输入manifest于`efe8c44299acafe8e5db45ac912513eb61fc4b4f`冻结，exact candidateCI `40357693859`成功后唯一正式3进程，重试0。65 runtime除发行版本字面量逐字等v048，未改默认存储/lookup/API。新增3必要检查用合成语料覆盖Unicode/转义/CRLF原member offset/SHA、精确alias、重复key/非string/坏JSON拒绝、UUID优先但改写独立记录、大小写不同不模糊fallback、未解保留、真Store跨块原range及损坏拒绝。

每worker使用原Store zlib/fixed65536/bounded，固定label、只存原corpus。原memory_qasper.members只作为精确JSON根成员解析器复用，不把本数据当QASPER schema；locator包含key+colon+value。每可解叶真正Snapshot.read_range，原stored/raw SHA/codec/EOF/size不绕过，再核raw成员SHA与JSON {原key:原source句子}。新Store树前后和三轮完全一致，无remember/派生答案。

独立analyzer直接json.loads原corpus和Task1 train，重建alias与每叶映射，用物理raw slice核成员SHA/JSON/Store真实范围，而不是仅比较两段候选相等。三轮records逐个相同，source/label原SHA对冻结输入，原整corpus再恢复相等。解析schema失败必须记录/中止，不隐去失败分母。

## 标准图和原始成本

![训练来源身份与诊断成本](source-alignment.png)

标准图已实际打开检查，左为映射计数、中为literal/UUID改写/未解、右为三轮CPU/parent完整wall成本；单位/图例和余白无裁切。计数是单轮5764叶，三次重复不扩大科学样本量；没有提速对照或模型收益图。

| 轮 | 原成员绑定 | 范围审计wall s | 审计CPU s | worker wall s | worker CPU s | parent完整wall s | 观察peakRSS B | 完整Store B | 原source副本B | ledger B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5511 | 3.332108 | 3.281250 | 3.467106 | 3.375000 | 3.610789 | 71401472 | 315672 | 909930 | 5280 |
| 2 | 5511 | 3.301753 | 3.203125 | 3.422320 | 3.328125 | 3.541788 | 71462912 | 315672 | 909930 | 5280 |
| 3 | 5511 | 3.302714 | 3.265625 | 3.424263 | 3.390625 | 3.543137 | 71905280 | 315672 | 909930 | 5280 |

父wall紧包subprocess.run启动到退出，含初始读入、JSON/alias准备、建Store、范围校验、序列化与末尾释放。worker/源审计/ingest CPU/wall另列；本版只是诊断成本，不将少量原读或缓存当性能收益。shared_input_application_read_returned_bytes只计两次Python input read返回B，非SSD/全系统IO；CAS/SQLite/OS缓存等未做全系统仪表，继续null。

全部Store对象/config/snapshot/残留都计入Store B，原source副本和完整ledger另列；共享原输入保留17403646B，包含准备阶段额外下载但本版未使用的Task3/dev/license及metadata，逐文件B/SHA见measurement-context，不假装它们必须部署或免费。3评测目录不是部署常驻3份。input副本/ledger/child/parent exclusive+fsync，内部Store fsync次数未知null；不称断电验证。

原始child+parent公共JSON7870753B，全部行只含qid/leaf/sourceID/映射/annotation SHA/locator/计数成本，科学原句、问题、答案、完整proof不发布。完整65递归Python+HTML源码416514B，专用/复用脚本逐个B/SHA在source-resource，协议/输入metadata/测试另计；不漏递归模块或HTML。无训练模型/图/字典产物，未来graph草稿没有执行或交付，不当本版能力。

观察RSS只是worker区间的系统peak，不是完整生命周期增量RAM或source字节上限。源/annotation解码对象、alias/全部records都占内存，计入观察峰；平台/依赖未分配，不称完整TCO。独立复核/全恢复/全树/画图额外wall 8.141728s、CPU 6.609375s、观察RSS 128950272B，不含初始解释器启动及写分析计时文件，不混为在线查询。

## 发行和下一步

新work/out运行scripts.run_source_alignment --inputs原私有输入目录，再scripts.analyze_source_alignment带work/out/inputs/freeze/test-log。原数据保持本机；公开程序/冻结协议/无原文原始JSON/图/详实报告/README/release说明。CI后Release，actual资产SHA/65递归源码/tag/脚本、物理仓库外actual wheel+current native与actual sdist新alias/UUID改写/未解和原Store来源绑定合成smoke、旧格式/CLI、最终proof上传后重下载全通过才完成。

下一项再冻结问题文本单独输入的词法/训练共现图与置换控制、固定预算、train-only模型SHA后才揭dev；未解目标留负分母，UUID改写不当语义证明。当前E3净收益仍失败、E4整体/真实长会话/回答质量/形式证明/无限上下文未验收。旧24模型API耗尽无新增授权，本机CPU离线0新调用；SSD物理/全系统IO/冷缓存/跨机未测。科学原文/段/帧/恢复副本、私有模型研究/模板/个人报告/密钥不发布。

发行前最终sdist核验首次因私有路径列表新增项误用str触发AttributeError，原失败日志B/SHA在measurement-context，修正为Path后继续同资产核验。只修发行harness，未改冻结程序/协议或重跑3worker实验。
