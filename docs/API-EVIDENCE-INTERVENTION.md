# 下一轮：有证据、空证据与置换证据的真实API对照

状态：公开候选，真实模型调用0；v083已完整发行核验，密钥已在用户环境配置。当前代码/协议/输入待全回归与冻结/CI后才能正式调用，不当交付。用户已明确选择调用API；旧24次调用不复用，新方案硬上限48次、每次512输出token、0自动重试。没有新模型下载授权，不使用发现的本地MiniLM分支。

## 可证伪问题

在相同模型、提示和证据预算下，原文检索是否同时优于空证据和其他问题的证据？引用身份机械正确与标注判定/rationale正确分别评分，绝不把可读取原文当科学蕴含证明。现有数据已在项目中多次使用，也可能在远程模型训练中，不能称封存未知科学验证。

## 数据、隔离和对照

旧SciFact corpus5183/8307875B SHA b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62、dev300/65007B SHA86f0435d08fdb65d1aa41d1472684f57e6e71930626497bdf4d7a9ec1a632217、train809/175616B SHAf4c8fa82d8bd0653a9cc8d61a6ea48c25eacea64e90af5dbf390ebb1b74372f0。选择阶段只按标签分层和SHA顺序固定6SUPPORT/6CONTRADICT/4无标注，共16条；排除旧v015实际12个API题及相同normalized query，排除trainID和normalized query。已用v015实际tag核对旧plan，不凭记忆排除。固定16题/48job的questions-private、gold-private、plan和SHA在源冻结前准备；没有按检索表现筛题。

三个条件每题一次：empty不给证据；retrieved给本问题的旧冻结BM25检索；rotated给固定SHA环中下一问题的检索证据。donor只按固定身份SHA，不读相反标签挑坏控制。其他题来源可能仍相关或与本题共用论文，保留overlap并在预测后审计，不能重置donor制造负对照。相同12篇/4096原记录B上限，不保证各条件实际wireB相等；实际输入B/token/费用逐一记录。empty为受同一only-evidence提示约束的对照，非无约束闭卷模型。

旧PaperRetriever/模型f062c7a784421b71bbfaf3c299be78ff323a391847afbf5420e4c06a4d422be0（10152832B）/词法排序/12与4096/旧sourceSID完全不改、无新训练。推理只读questions、corpus、旧model，禁止读取gold-private或claims_dev/train标签。16次检索完整原Store范围读取及SHA先完成并持久化，API条件都从相同原始retrieval取证。每个API原文prompt、原响应和实际source record只留本机，不发布原文/研究/模型或密钥。

## 调用和失败

服务https://api.deepseek.com，用户指定deepseek-flash；官方文档当前说明alias由DeepSeek-V4.1-Flash-1017服务，记录实返model名、时间/usage，远程weights/runtimeSHA未知null，不能自行冻结或把它当本地CPU推理。temperature0、thinking disabled、JSON object、512输出token、单request<=20000UTF8B、响应<=1MiB、timeout90s。所有48job按固定SHA混合次序，单次调用无重试，格式不合格也占slot、错误保留；超时/HTTP/连接失败停止后续浪费，missing保留在16/48分母。

每次传输前slot exclusive写盘fsync预留，已预留即使中断也不得自动重发；原bodySHA/byte预算写盘，认证key仅Authorization头不入日志/报告。只从进程或Windows用户RKV_LLM_API_KEY读入子进程，不扫描私有旧文件/聊天找旧key。官方host固定、拒绝redirect，禁止将key发给别的host。每个slot预留前读取Codex官方实际quota及reference window，耗尽/拒绝/窗口变化停止。本窗口参考1793272390，不跨窗。

## 门槛与独立审计

H1所有已完成调用的计划、输入SHA、原Store/source/title/sentence定位、实际暴露证据、requestSHA、slot保留、模型输出schema/citation与usage记录独立审计通过。完整性单列，未满48不称完成。

H2只在48完整时计算：retrieved的16题全分母判定正确数和12有标注题“判定+至少一个完整gold rationale”数均严格高于empty和rotated。0missing不补正确；失败为错误。H2负结果保留，不换指标/样本/预算追正。citation precision基于已标注集合、并非全部真相关精确率；4无标注expected INSUFFICIENT只是数据集代理，不证明全库无证据，不把不存在gold rationale记为成功。正确类分母6/6/4，混淆、paired win/loss/tie、描述性exact McNemar及小样本区间完整给出，不从16题推普遍收益。无“机械NLI已过”或生产总目标宣称。

独立audit不调用candidate score/strict parser，自行核原JSON/title/abstract、exposed每句、label/rationale/citations、raw输入SHA/slot/输出schema/句SHA、同题三条件和全48分母。所有API预测持久化后才读gold。还要统计rotated与本题/本题gold来源重合，解释control污染，不能因此改运行。必要owned tests含48fake API全流程、真实toy Store原bytes、禁止推理读gold、超限/无source/截断/重复JSON/越界citation/布尔index、timeout只留一次且停后续、篡改拒绝/独立score一致。预检不调用真实服务，不消耗48正式预算。

## 完整费用和交付

检索constructor/16queries本机CPU与RAM，API每slotwall、实际usage(input/cachehit/cachemiss/output)/输出截断、wireB、价格快照或未知cost null分别记录；不能把token数当货币，未知远程RAM/weights/能耗不记0。旧retrieval训练/model/index/source/CAS/snapshots/原模型调用费用、全新专用代码/全部runtime/库依赖/新旧原prompt-output和日志残留均计入。完整worker/parent/finally和后置审计CPU/RAM单列。公开raw aggregateJSON/图实际视觉检查/详报告/README/release，source/protocol/input先冻结并CI成功再唯一正式48；本地和实际发行资产SHA/源码/外部安装/proof8齐才交付。

API资料（实际核对）：https://api-docs.deepseek.com/quick_start/pricing 和 https://api-docs.deepseek.com/api/create-chat-completion/ 。不要将网页示例或模型卡当本项目实验结果。

补充原响应审计：真实HTTP响应以原始bytes留私有.response-private.bin，再解析JSON；记录bytes/SHA/id/created/model/system_fingerprint/usage/finish_reason；独立审计原响应与记录逐项对应。异常HTTP状态仅记录错误类别/状态，不持久化认证header或服务端可能回显的错误body。
