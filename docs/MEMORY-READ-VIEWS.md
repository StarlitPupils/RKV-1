# v0.98 固定来源读取视图与真实读写交错

状态：公开候选，正式结果尚无；全回归、source/protocol/input/SHA及exact CI必须先于正式运行。

新增 opt-in `Memory.pin(snapshot=None)` 返回固定SID只读视图，支持search/lookup/lookup_many/info/close/context manager。None只在构造时解析一次HEAD；显式SID不读HEAD。构造验证manifest，每次操作调用原Memory API重新验证manifest/索引/选中CAS/原记录，无跨请求decoded/results/DB缓存。info返回新dict、snapshot_id只读；close幂等，后续读取/enter拒绝；不关闭原Memory。lookup_many沿用v3限制和重复key逐次计费，不扩展格式/预算。固定身份不意味着底层被损坏后仍可读，不保证外部恶意改写时整个多调用事务原子性。

## 固定实验（不得按结果调参）

自建JSONL三修订epoch0/1/2，规模17/129/513，3轮；9控制进程，每个3真实持久reader（pinned/原显式SID/current）+1真实writer =36子进程，18修订更新；每reader11操作，全部297操作，无重试/补跑。规模9仅tiny owned准备/测试，不预跑正式矩阵。所有9个(size,epoch)完整原始source bytes/size/SHA在冻结inputmanifest中外部固定，0训练标签/原科学输入。

原Memory默认compact-budget-v3/zlib/fixed4096不改。每controller建立epoch0，先baseline的search/lookup/batch3次，然后各epoch1/2：writer构造真实对象、快照、索引，在原_head前暂停；3reader实际search先选SID进入_manifest屏障；父确认三者进入后放行原HEAD发布；HEAD新SID已实际可读后才放行查询继续验证原source。随后3种操作各一次。pinned及explicit所有11次epoch0；current重叠search取发布前版本（第二次为epoch1），后续操作使用当前revision。batch重复doc0/doc1/doc0每次occurrence计费；current batch显式解析当时HEAD供已有lookup_many，不声称该接口有隐式HEAD。

全部297操作每次primary完整source恢复，独立后置每次再恢复297；每controller另4隔离坏副本/返回literal控制，共36控制。返回literal控制及HEAD损坏下已存在pin成功lookup各另完整source恢复1，共18次；总612次完整source应用返回。错误CAS/manifest拒绝的底层解码/OS流量未知null，不视为0。9controller每个4种closed拒绝=36，不合并冒充额外独立样本。

H1：9/36/297完整；每条original JSONL物理offset/length/SHA/全文/标题/重复/unicode/CRLF与完整Store source一致，所有固定历史SID文件不变，pinned与原explicit接口结果（除wall）逐次相同，父真实producer PID/handle实际exit0且footer一致。
H2：54个重叠区间均满足原HEAD前marker <= 实际query已选SID <= 实际HEAD后marker <= query完成；3roles的固定SID/动态SID按完整预定轨迹匹配，不混新旧返回证据。此合同仅该受控singlewriter交错，不是所有并发调度或多写者证明。
H3：36坏副本控制拒绝/隔离正确：选中CAS损坏、manifest损坏必须让已打开view拒绝；后来HEAD损坏不影响已固定SID，但新implicit pin拒绝；保存returned literal篡改被独立校验拒绝。36关闭调用拒绝，info修改不改变SID，关闭原Memory仍可读。联合仅H1&H2&H3；缺失/0基线不发性能结论，不用子阶段挽救。

正式controller最多180秒/全plan900秒/0retry/exclusive输出；失败停止剩余计划，始终保留36子进程/297操作/36控制全分母，缺失执行/额外成本unknownnull，禁止自动重放/回填。root预约/started/真实PID父退出/各entry-finally和outerfinally、坏字节及全部旧文件账本保留。官方quota在controller前，父每阶段缓存最多30秒，子每操作读取外部父提供的当前ordinary证据并检查deadline；未知/denied停止，参考窗口1793881841（<=60秒服务抖动），不跨窗口。

Whole process entry在imports前至footer，含source生成/Store创建/全部真实索引/屏障/查询验证/persistence/关闭；父wall含启动/退出，4重叠parent区间不得相加冒充串行耗时。selfCPU不含quota子进程，whole process-tree CPU/RSS未知null；文件/源payload/应用返回B不是RAM/物理SSD/全系统IO。控制、复制、源代码、以前所有science/train/models/Store/CAS/snapshots/frames/failed/API成本保留。无缓存提速/空间压缩/RSS收益门槛或headlines。

0新模型/提供方HEAD/下载，0原科学corpus/question/gold/model/旧回答读取。不是物理掉电/目录同步/冷缓存/跨机/多写者/语义NLI/科学回答/长期人类对话/无限上下文证明。v095原中断轮与v089旧API轮永久封存，不补跑。公开仅SHA/数量/indices/metadata，owned原始文件与source/query文本留private。每轮全部代码测试、冻结协议、父raw、独立审计、实际看图、完整费用报告、local/outside实际wheel+全部legacy、ReleaseCI/实际7SHA/allsource/outsidepublished/proof8后才交付。
