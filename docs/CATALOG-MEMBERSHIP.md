# v0.79 冻结候选协议：选中来源的短成员证明

本版只研究metadata成员证明，不做完整逻辑证书压缩/恢复、自然语言、科学NLI或回答实验。默认SDK/UI/Store格式不改，v0.78已完整发布核验后才采用本候选。

## 信任与格式

先由真实Store验证整个SID的manifest，再将全部eligible .logic.jsonl按path排序，叶为canonicalJSON {path,bytes,sha256}。使用RFC9162 §2.1.1/2.1.3的域分隔树形哈希思想：SHA256(0x00||leaf)，内部SHA256(0x01||left||right)，按小于n的最大2次幂分割，不填充；这不是CT wire protocol、签名/一致性服务或新密码算法。[第一手说明](https://www.rfc-editor.org/rfc/rfc9162.html#section-2.1)。

应用anchor固定format/snapshot_id/eligible_count/eligible_payload_B/root_sha256；接收者必须独立持有**可信anchor SHA、SID和期望path**。anchor不能由待验证消息自行指定为可信。单独原SID不提供派生root的无信任验证；初始发布者恶意生成同SID另一root是保留反例。建立/认证root需初次完整manifest校验；每个SID单独anchor，即使仅notes变化而eligible root不变，anchor SHA仍不同。不存在签名或远程认证渠道实现。

proof固定format/snapshot_id/anchor_sha256/leaf_index/entry/siblings。index必须真int非bool，count1..4096，path规范且<=240字符，size真int0..2^63-1，64lowerhex SHA，恰好所需的树形路径，最多12siblings。独立checker不导入builder、不访问Store；先验外部anchor身份/期望SID/path，检查原bytes长度和SHA，再独立推导唯一树形方向并折叠root。成员True不代表全eligible覆盖、完整closure、科学真理或原自然语言蕴含。每单文件payload budget0..1MiB不是整包/物理IO预算；正式两文件总B另计且固定小于1MiB。当前消息并不单独验证逻辑DAG，不能称独立逻辑证明成功。

## 正式工作量与顺序

沿用已见owned source geometry count9/64/512/4096，3轮count orders：[9,64,512,4096]、[64,9,4096,512]、[512,4096,9,64]。12fresh worker，每个600秒、0重试。两selected paths固定one.logic.jsonl/two.logic.jsonl，无科学数据/模型/训练/API。原型只检查17叶以内与实际小Store，不先测4096体积/时间调整参数。

每worker：创建原source/Store→全manifest元数据构建树（不读取source CAS）→两个原payload成员验证→8种固定负控制：wrong index、entry SHA、truncated/trailing path、bool index、wrong SID、wrong bytes、zero payload budget→改notes新HEAD→旧SID proof仍通过，新anchor拒绝重绑定→生成固定8 metadata messages/baseline与完整index文件。总24正成员、96负控制、12历史保留+12新HEAD拒绝。全部失败留分母，不重跑覆盖；12完整parent壁钟/worker finally壁钟CPU/RSS均要保留。

正式前7必要owned测试及完整回归通过，源/协议/input冻结+精确CI成功后才启动唯一controller。后置从fresh实际Store复核全部14043 eligible leafmetadata、独立完整树root、24实际成员，以及全部14055文件逐byte恢复；后置计时/CPU/RSS分开，不冒充worker开销。

## 预定可证伪门槛与费用

H1：所有24成员、96负控制、12旧SID/12新anchor控制、后置完整metadata/文件核对通过。

H2：primary4096每轮一次实际packet canonical B / 旧selected_witness.catalog canonical B <=0.25。两个wire envelope不同，只有“选中原bytes属于已受信目录”这个有限目标；不是逐字节恢复旧完整证书、不保留全eligible list外发或全覆盖声明。小规模也全报，不改primary。

H3：primary4096每轮 `完整index文件B + 全部新增public code/tests/protocol/input B + 固定8条candidate metadata消息B - 固定8条旧catalogue消息B <0`。整库runtime/既有Store/source/payload在两边同额列账，不省略，不重复计入增量。8继承既有8query workload，不能见结果再增加摊销次数。正式保存candidate-batch和baseline-batch实际canonical字节计算：candidate共享anchor一次、每消息query_index+anchorSHA+两proof；baseline每消息query_index+旧catalogue。逻辑DAG/原payload双方不在metadata消息中且相同、单列原source B。不得把H2当H3或生产净收益。

joint=H1&H2&H3，负结果保留。fullnewpublic fee冻结列表为2新核心scripts+正式worker+本版tests+本协议+input manifest，全部全额一次，不剔除测试或只计最佳核心。索引包含完整leafrecords和所有tree range/hash并落盘，整份index收费；额外Python对象图含record/node/position/anchor按去重sys.getsizeof量，非RSS/峰值上限。完整process RSS、初始化/验证CPU/wall、所有source/CAS/旧新snapshot/notes/index/packet/control/log残留、全部scripts/67Python+HTML与旧science/train/models历史费用单列。协议/实现不设性能提升gate，不把验证少数leaf的CPU当整流程速度收益。

## 交付

raw/parent/finally JSON、source/protocol/input SHA、标准图且实际视觉检查、详实报告/README/release。local initialbuild0→物理外actualwheel/currentnative/actualsdist新成员验证及所有旧机制→finalbuild/sourceaudit0→tag/ReleaseCI→actual7资产SHA/递归源码/外实际publishedinstall/proof8。模型/原科学/帧/恢复/私研/模板个人报告密钥不公开。冷缓存、跨机、物理SSD/全系统IO未测，E3净收益/E4整体/科学NLI/真实长期对话/回答/无限上下文未完成。

额度参考1793187699，每轮实读；ordinary denied/实际100%/到参考reset或确认新窗口保存断点删除续跑，不跨窗。
