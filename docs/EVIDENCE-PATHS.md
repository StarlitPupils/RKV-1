# v0.40 冻结协议：显式三跳原证据路径与历史SID

目的只是在离线条件下验证精确记忆基础设施：给出已知根文档与指定快照，顺着原文显式引用读出三跳证据，原始数据后续更新/删除后仍区分历史来源。不是开放检索、自然语言多跳、真实长对话或回答质量。E3当前候选净收益失败，不改其参数，不称E3完成。原63模块除发行版本标识保持不变；新增独立evidence_path显式API，Memory/Archive/default不变。无模型调用或训练。

## 显式接口与预算

trace(memory,key,snapshot=required,max_hops=3,max_evidence_bytes=4096)。snapshot必须合法hash且不可省略/为空，key限定doc:数字。通过Memory.lookup(key,snapshot=同一个SID)读取，不调用search、不猜源、不回退HEAD。每条原记录必须恰有一个完整指令句：RKVNEXT doc:数字，或RKVVALUE 后接非换行1–512字符。循环、缺证、无/多指令、跳数不足、预算不足给出独立状态，非complete时value必须None。源完整性异常直接抛错，不返回猜测值。

byte budget只限制加入证明的原JSONL记录字节（4096），不是物理CAS I/O上限：lookup必须先读取/验证才知道大小，预算不够的记录仍计入verified_record_bytes而不进入admitted_record_bytes或证明。physical_read_or_decompressed_bytes固定null，尚未仪表化；不得把locator长度当实际读盘/解压B。独立审计再读的逻辑记录B与运行时逻辑记录B分列，不能叫真实IO。max_hops为admitted证据记录上限，默认3，不能为了通过调大。

每跳证明含key、locator父SID/path/offset/length/原record SHA、sentence_index、decoded quote和quote UTF8 SHA；原JSON可能有Unicode转义，因此quote UTF8字节不承诺是原文件连续子串。正确合同是原record范围字节SHA+JSON成员索引+解码后原句一致。结果明确primary_evidence=false，是派生路径，不能替换原始证据。

## 冻结合成输入

32条互不共享链，每链3原文档（0..95），另768个干扰记录（10000..10767），初始864记录。无真实科学事实，标题和正文标明synthetic fixture。JSON sort_keys、紧凑separators、ensure_ascii=True、CRLF，固定Unicode/引号/1.00e-3字面量，均由scripts/evidence_path_fixture.py生成，不执行科学源码。

epoch0+12次单writer提交。第e步更新六个chain=((e-1)*6+k)%30的terminal记录，修订号/长度padding变化造成后续record偏移移动；epoch6额外删除chain31中间节点doc94，此后保持缺失；epoch12额外把chain30中间doc91引用改为doc90形成循环。除这两个明列的结构变动，每步六条普通更新；不声称严格仅六条总变动。每轮新memory根目录，默认compact-budget-v3/zlib，原存储预算不改，无并发/崩溃。

## 问题时间线和精确分母

3轮，各一个新worker进程，轮timeout600s。每轮完成全部13提交后才构造96个问题：每chain对epoch0/6/12的根key+指定SID，Random(20261026+轮号)打乱。问题文件以exclusive创建、flush+fsync，锁SHA，再开始任何trace；记录ingestion_finished≤questions_fsynced≤first_query_started。所有seed与结构事先公开，所谓“迟到”仅指操作顺序，不能声称真正未知未来问题/盲测。

每轮独立gold由fixture修订公式、删除/循环条件生成，不从候选路径反推。96中93应complete、2应missing（chain31@6/12）、1应cycle（chain30@12）。三轮288主问题=279应完成+9应明确失败；gate要求全部状态/值/完整key路径符合gold，不把正确失败从分母删除或报成全部都回答。

每轮另4固定控制（均指定epoch0）：doc0预算1→budget、doc0跳上限2→hop-limit、doc10000→invalid-reference、doc999999→missing；总12控制，均不得给值。每轮取第一条complete派生证明制作两种独立篡改：首hop错SID、末quote改写且重新计算quote SHA；独立auditor必须拒绝，总6次负审计。只篡改owned派生副本，不破坏存储后重跑。

预定接受绑定：主问题每轮93*3+2*1+1*2=283跳；控制每轮2跳，共三轮855接受的原record绑定。负审计拒绝尝试/额外读B另列，不混进855。形式上路径能到终点是合成构造的性质，不是检索器或模型提升；不设置天然会输的one-hop baseline来宣传收益。

## 独立审计和存储费用

auditor不调用trace/lookup，不导入trace regex；打开指定SID的CAS snapshot直接read_range，验证原record SHA、JSON doc_id、abstract成员、解码quote与UTF8 SHA、前后显式引用链、终值和入证B。运行时与auditor都必须使用问题指定SID。gold额外核完整key列表和终值，避免候选删掉中间证据也算对。

每个主问题/控制的派生结果通过Memory.remember分区保存（每轮100个），相关文件字节、写入wall计费，不进入主证据索引。所有query前已存在memory文件SHA在query后必须不变，HEAD不得移动，新增文件只准answers/。统计全memory根递归文件（含CAS snapshots、索引、manifests、HEAD、derived和任何残留），与Memory.stats另对账，不忽略根目录临时文件。

源码账本是全部递归runtime Python+HTML；新增trace专用源码单列但已包含整库，不重复相加。fixture/driver/auditor/analyzer程序与protocol metadata作为评测费用另列。对每轮报告13 ingest CPU/wall、trace CPU/wall、独立audit CPU/wall、派生写wall、全worker CPU/wall/peakRSS和完整process wall；peakRSS覆盖整个worker而非每题孤立内存。fixture写fsync13+问题冻结fsync1另列，Memory内部fsync次数未仪表化为null。外部源文件与评测日志/原ledger不冒充部署memory费用。无权重/字典/训练/远程请求费用，平台/依赖未分配部分不能声称完整TCO。

## 事先验收与交付

288主问题/12控制/6负审计全部按预期、855接受绑定回原记录、13提交×3轮全成功、历史/当前来源区分、问题时间线和旧文件/HEAD保持，任一不符保留失败，不重跑覆盖或改预算。源每epoch SHA及问题SHA公布，三轮是同fixture重复执行，不是三个独立科学样本。

候选/独立审计器必要合成测试和完整测试通过后提交冻结本协议及runtime/驱动，再等待CI通过，随后仅执行计划三轮。冻结前不跑正式32链/768干扰/12更新评分。

交付原始aggregate JSON/标准图并实际打开视觉核验/详实报告、README/release说明、代码和必要测试；推送后CI成功发布Release，并实际资产SHA/递归source+HTML/物理仓库外实际wheel/current native安装/新证据路径smoke/旧兼容/最终proof重下载。原真实科学源/帧/私有研究模型/模板/个人报告/密钥不发布。冷缓存/跨机/断电/真实长期会话和回答质量未测，E4整体与无限上下文目标未验收。
