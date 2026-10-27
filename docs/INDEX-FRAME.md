# v0.58冻结候选协议：现有可用索引的逐字节可逆postings格式

v057实际发行proof已完成后采用候选。12项必要人工合成检查已通过，完整310检查以实际log为准；随后代码/协议/input/exactCI先冻结，唯一72worker。当前未测量两个原模型的压缩大小，不得称交付。v057最佳句排序质量/时间均失败，停止该表示/35MB索引的优化，不用本实验压缩它追正。

目标：只压缩现有两个原可用模型的canonical JSON字节，不改任何TF、docID、locator、graph、参数或查询行为。EntailmentBank v050原model4629668B SHA2f82ee4b28c943038e7a37ddcbd8871443f7a441ddd45a1af599decc8bade183；SciFact v053原model10152832B SHAf062c7a784421b71bbfaf3c299be78ff323a391847afbf5420e4c06a4d422be0。模型全部私有，原科学原料/query/索引词表/frames/恢复副本不发布。

唯一typed候选保留除shared.postings以外全部metadata原canonical JSON；doc字典取metadata.doc_lengths按原ID字典序，无另造semantic alias。postings按原token/ID序，UTF8 token+严格规范uvarint数量/正doc-index delta/原正TF；解码重建原object再canonical序列化，必须逐字节等原SHA。只支持明确canonical/shared-postings格式，非canonical/重复key/nonfinite/非法TF/身份拒绝，不称所有JSON或所有模型通用最优。

同一RKVPOST1实验frame包plain原JSON或typed payload，130B header：magic8、method1、codec1、原/变换/存储长度各u64、source/payload/stored SHA各32B；与RKV archive/text/neural frame不同magic。raw0、Zlib6、Zstd3(content size/checksum)、LZMA6固定4profile，双方同header与codec参数，不自动挑模式fallback或改level追结果。source≤64MiB/payload≤65MiB/strict EOF、三SHA、单codec frame、原JSON输出size预算先于重复长ID展开，varint溢出/非规范/重复/越界明确拒绝。尺寸cap不是RSScap，LZMA固定memlimit256MiB、Zstd窗口按既有bounded codec校验。

原2模型是两个已见scientific-index工作负载，不是新科学问答评测。另固定seed20261027人工控制：256随机docID、1024随机token、每token8doc、TF1..65535，原长度为真实聚合TF，代码可重建SHA。它是随机结构化postings，不是白噪声/理论不可压缩对照；结果照报不混入2原模型科学主分母。

确切3数据×2方法×4codec×3轮=72 freshworker，8cell A=plain/raw B=typed/raw C=plain/zlib D=typed/zlib E=plain/zstd F=typed/zstd G=plain/lzma H=typed/lzma；三轮ABCDEFGH/HGFEDCBA/EFGHABCD，每轮三数据固定顺序，每worker600s/0重试。原source/model/control SHA、代码/协议/必要合成与全库检查/exactCI先冻结，后唯一72worker；不得预看原模型的压缩大小后调整布局/参数。

每worker原SHA输入一次，encode计全部验证/变换/codec；写实际private frame并fsync、重读frame再decode、json.loads到consumer-ready对象。encode/decode/JSON-load/decode-to-model-ready wall和CPU、父完整wall、observed RSS、写frame/恢复file/fsync、实际所有残留文件B与SHA分列。恢复原JSON实际文件再重读SHA；原frame/mode/原模型object完全一致。parent完整时间含文件I/O及额外核验，不称冷缓存；SSD物理/全系统IO/跨机仍null。

预先primary：typed+zstd在两个原模型上都比4个plain profile中完整空间最小者更小才space gate通过。complete B=frame+整个66递归Python/HTML+共同index_frame wrapper；typed额外收费整个postings_transform.py源码，不能只数payload。另报同codec空间比较、全实际实验脚本/生成器/旧模型/所有72帧与恢复副本总B，完整RKV/原source CAS没有自动变小，不称全机TCO。

为避免把当前SDK需raw JSON文件的消费路径省略，primary complete B还包含实际写出的restored raw JSON（双方同B），即frame+restored+RKV全部源码/HTML+common wrapper，typed再加整个transform源码。原输入文件是全campaign共享的单份，另全量计B；实际72worker frame/恢复file和全部测量JSON等总B完整列，不能把压缩frame单独存储的未来透明加载方案当已实现。另可列frame-only，但不据此宣称现有SDK部署已压缩。平台/依赖二进制和pycache未分配，源码账本不是全机TCO。

time gate固定typed/zstd对plain/zstd，3配对decode-to-model-ready wall/CPU和parent完整wall中位比全部≤1，零CPU分母null失败，不加epsilon/追加迭代。index-space/load joint需两个原模型空间/时间均通过；只是索引存储/加载指标，不是LLM推理、实际检索时间或回答收益。全部矩阵与control负结果保留。另列所有typed profile相对best plain的空间Pareto点，仅是预定矩阵描述，不能改primary或隐藏多次编码成本。若以后选codec/Rust优化须另冻实验且完整二进制/metadata费用计入，不能用旧DLL功能测试推新性能。

独立analyzer实际重新读取72帧/恢复文件/原输入，解码复核原SHA与JSON一致，追加72次decode审计CPU/wall单列、不算额外正式轮。原input不变、frame/proof/sidecar SHA/父wall/返回码、三轮各cell frame确定性、所有源码/参数freeze核对。新压缩试次72、原模型逐字节恢复72、额外审计72；科学问题/原科学source范围查询/新监督训练/远程模型API均0。

必要合成检查：标准uvarint golden/边界/溢出/非规范，固定literal typed payload golden，Unicode/opaque float/bool/null/empty postings，TF/schema/noncanonical/duplicate/nonfinite拒绝，header长度与三SHA/截断/trailing、内层codec串帧拒绝、长ID恢复输出预算在展开前拒绝、文档delta0/EOF/count拒绝、旧text frame及公共PaperRetriever拒绝新frame。补真实worker小fixture验证实际frame/恢复文件、consumer ready与source object及manifest SHA篡改拒绝；不是镜像实现或只测happy path。

每版代码/格式协议/rawJSON/标准图真实视觉检查/详实报告/README/release/GitHub，CI后actual5资产SHA/66+HTML/物理外actualwheel+currentnative/新sdist所有codec/plain+typed byte恢复并加载原SDK合成模型、旧功能与finalproof重下载后完整收尾。默认SDK/Memory/CLI/UI/归档格式不改。0新模型API旧24耗尽，仅CPU离线；E3净收益旧失败/E4整体/真实长期会话/NLI/回答/无限上下文未验收。

这里的model是既有词法/来源共现图索引JSON，不是LLM参数权重。新格式不量化、不删字段、不总结原文；原科学source归档与其既有费用保持。
