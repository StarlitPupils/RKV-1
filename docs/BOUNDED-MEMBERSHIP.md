# v0.81 冻结候选：同快照的有界子树 metadata 缓存

v0.80已完全发布核验；原RAM/CPU取舍 H3/joint False和v079固定8metadata净增340600B保持。本版只做已见owned目录成员机制，不是未知科学/自然语言检索、逻辑DAG、回答或生产压缩。

## 三方法同任务

A retained使用既有v079 Catalogue全树；B ephemeral为v080每迟到请求全重算；C bounded采用固定65536B metadata子树hash LRU。三者同held Store.read_scope/SID、完整初始metadata、独立可信anchor和8迟到双path请求；初始anchor全扫描成本不可省略，关闭后都拒绝，finally清空持有tree/anchor或cache entries。A/B实现沿用既有代码，C不改源payload read_range/校验，不缓存原bytes。

C只对不包含本次requested leaf的子树尝试复用，包含请求叶的分支仍展开生成siblings。缓存只在同owner/SID/count内使用，key为(lo,n)，32B node SHA及独立校验stamp绑定SID/key/hash；stamp是无密钥事故校验，不宣称抵御有权改任意进程内存的攻击。最终完整anchor和每个原bytes成员仍由外部独立可信SHA认证；仅SID或缓存自报root不能自认证。所选源CAS损坏仍在原read_range失败。

每请求先对全部原metadata求eligible总B和排序keys，再展开/复用hash，不因为跳过子树丢失总B。初始Scope O(N)、每次排序/完整字节数扫描仍存在，不称全流程常量或O(logN)RAM。

## 缓存完整费用和上限

预算65536B指每次cache API操作完成后的整个cache-owned graph保守上界：slotted NodeLRU实例、所有slot值、OrderedDict实际backing/node内存、tuple keys及其两个int、(digest,stamp) tuple和全部bytes，非hash payload-only。int重复引用保守多算，实际对象图另独立去重核；所有计数器饱和在2^30-1，使primitive大小不变。固定slot基础费用一次计算，后续基于真实dict sizeof和累计entry费用O(1)维护；维护/校验/淘汰CPU全部进入算法phase。

先插入再LRU淘汰意味着瞬时provisional cache graph可超过65536B；max_provisional_bound_B单列，max_retained_bound_B记录操作后上界。不是插入峰值、全prover、共同Scope或总RSS硬cap。实际prover状态还含anchor/包装字段，必须另计。关闭清entries；private被任意修改不属于合法API容量保证，必要测试显式污染值/不匹配stamp时拒绝。

没有用4096 source规模预检调cap。私有7必要测试覆盖<=17叶/真实9source的hit/miss/严格尺寸/错误key/SID/同key冲突/eviction/污染/关闭/CAS拒绝/与旧A精确proof；4KiB小预算只用于必要淘汰正确性，不是正式cap。source结构选slots降低普通记账开销，未基于大规模性能挑参数。新增实际IPC unit后完整504检查需通过，先冻结源/协议/input和exactCI再正式。

## 固定工作量

count9/64/512/4096，3轮countorders沿v080；roleorders ABC/BCA/CAB，A retained/B ephemeral/C bounded，共36fresh workers，每个600秒/0正式重试。每worker8迟到请求、每请求2unique路径，合计288packet/576成员和144负控制（wrong anchor/raw/missing path/closed owner）。父先观察constructor完毕READY，从fresh真实Store独立认证root后才生成请求/SHA/时间线；规则j%N和(N-1-j)%N，重合第二+1modN。公开可预测controlled task，不叫未知问题，不预生成paths给C缓存。

后置36fresh根/42129全部eligible leafmetadata/42165原file逐byte恢复、288实际packet和576原bytes成员复核；同round/count三法canonicalpacket/querySHA/返回B相同。旧v080结果不替代新审核。

## 预定 gate

H1以上全量正确性/关闭/时序/文件/完整timer及C max_retained_bound_B<=65536、cache upperbound定义完整通过。

H2 primary4096每轮C/A初始及最终额外常驻prover对象图<=0.5。共同Scope文件metadata/SID同对象引用去重扣除，cache.slots值和OrderedDict所有条目实际递归计入；原metadata/临时sorted keys/完整child peakRSS另列。不是把常驻状态比当同幅总RAM节省。观察state graph耗时放phase外单记，仍进入完整worker/parent/RSS。

H3 primary4096每轮C/A完整算法phase wall/CPU及parent wall都<=1。phase=全部constructor(anchor/caching/维护) +8次issue/read原bytes/独立verify/canonical/写packet；初始化Scope、等待父、source创建/ingest、observer均另计并进入完整worker/parent。父自己的fresh root/请求成本亦完整计入parent。0CPU分母null不pass。B/A和C/B也完整报告，只C/A为headline；不得改primary/增加请求/按最好轮追正。

joint=H1&H2&H3。若64KiB维护开销抵消收益或仍慢，保存负结果；该负结果也属于进展。部分late请求靠近叶两端、对复用有利，必须披露已见机械负载，不能称新科学或生产收益。

## 交付和资源

全部raw/parent/finally/stdio/请求SHA/缓存trace、完整源/CAS/snapshot/metadata/packet残留、所有新旧source和67Python+HTML/全部scripts、历史science/human/train/models/frames/restored/下载cache/失败成本分开计费；当前model0/API0不抹除旧成本。cap不省略Python容器，维护CPU不藏observer。

正式后独立审核、标准图实际视觉看、详报告/README/release，localinitialbuild0→物理仓库外actualwheel/currentnative/actualsdist新旧smoke→finalbuild/sourceaudit0→tagReleaseCI→实际7资产SHA/递归allsource/外actualpublished安装/proof8齐才交付，收尾再下一公共版。原science/model/帧/恢复/私研/模板课程个人报告密钥不外发。旧24API已耗尽无新增/模型下载授权，CPU离线。E3净收益/E4整体/真实长会话/科学NLI/回答/无限上下文未完成，冷缓存跨机/物理SSD/全系统IO未知null。

当前授权额度参考1793258458，实际100%/ordinary不允许/到ref或确认新窗口保存准确partial并删除续跑，不跨窗。
