# v0.99 协作式写入作用域、进程退出与历史来源

公开候选，无正式结果；full regression/source/protocol/input/SHA freeze/exactCI 必须先于唯一正式矩阵。

## API 与 OS 合同

新增 opt-in `Memory.writer()`，构造时对原Memory根目录的固定`.writer.lock`取得非阻塞OS句柄，作用域 `add`仅委托原Memory.add；info返回新dict，context/close幂等，关闭或跨进程/跨线程/重入操作拒绝，active add期间不允许close。弱引用finalizer是遗忘close的资源兜底，业务应明确with/close。Windows使用CreateFileW OPEN_ALWAYS/读写访问/share0/非继承句柄，POSIX使用O_NOFOLLOW/非继承fd+flock LOCK_EX|LOCK_NB。失败仅报告BlockingIOError，不轮询重试、不删除或替换锁pathname。锁文件不存活跃owner或操作完成状态、不解析内容、不截断，关闭后保留原pathname；旧内容不阻止下次OS取得句柄。拒绝目录/symlink/reparse锁路径（POSIX另拒绝多hardlink），拒绝无权限错误，不把权限错误冒充锁竞争。

API是创建进程/线程内的序列作用域。所有参与写入者必须协作使用Memory.writer；原Memory.add、enable_replay_budget、外部工具可绕过，默认Memory/CLI/UI不改，**不声称整个库已具备强制多写者保护**。不支持持锁后fork继承或恶意unlink/reparse路径替换、远端文件系统/网络锁一致性。scope非可序列化lease，不提供超时抢占、强制清除、自动回滚或重试。OS句柄非继承状态实际记录，进程结束释放锁与原写入调用是否完成是不同事实。

主机制依据[Microsoft CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)与[Python fcntl.flock](https://docs.python.org/3/library/fcntl.html#fcntl.flock)。文档说明不替代本轮实际来源/进程验证；文件/目录fsync、物理掉电、跨机器、所有并发调度未验证。

## 固定方案，不按结果调参

自建三修订JSONL epoch0/1/2，规模17/129/513，各3轮 =9controller。每controller3独立case：A更新在原HEAD前终止、原HEAD后终止、正常close，共27case；每case两个fresh写入进程A/B，共54进程、18真实A进程终止、9正常A完成。tiny规模9仅准备/测试，不提前运行正式规模。外部9个(size,epoch)完整source bytes/size/SHA先冻结。无旧科学输入/训练标签。

每case父进程用原Memory默认compact-budget-v3/zlib/fixed4096建立epoch0，保留oldSID+pin。A取得OSscope并尝试独立intent A/epoch1；只包装原_head用于固定边界屏障。A的原Store/CAS/快照/索引均真实执行。A进入屏障后父记录原库所有字节，才启动B。B第一次取得scope必须非阻塞拒绝，尚未调用add，原Memory全文件与HEAD保持屏障前SHA；Windows活跃`.writer.lock`内容按API无法打开，此时仅文件size可观测、SHA明确null，其余所有文件仍严格完整SHA，close后lock正常计入全账本。

A-held时父各一次current/pin/explicit-old search共3次。A在beforeHEAD case保持epoch0、afterHEAD/clean-close保持epoch1；pin/explicit固定epoch0。父绑定真实producer PID/句柄及owned launcher父子关系，实际终止A或放行cleanclose，记录producer/launcher退出。只有观察A实际结束后父才给B发准许信号。B第二次取得OSscope后执行**已冻结的不同新意图epoch2**，绝不是重放A/补跑中断操作；B写入返回后仍持scope，父再次尝试scope必须拒绝。再做current/pin/explicit-old三查询(current2，pin/old0)；B正常close并实际exit0，父最后再取得并close空scope证明无需删锁文件。B关闭后的add/enter各拒绝。A未正常返回的18例完成状态unknown，不从B取得锁推断A未执行/已完成/数据已回滚。

完整27baseline+27A尝试+27B独立新意图=81 source/index构造；A returned9+Breturned27=36已确认add返回，A剩18未知。27×6=162保存查询，54实际contention；primary每query完整source恢复162次，后置独立另162次，每case返回literal篡改独立恢复1次(27)，共351完整source返回。每case隔离bad-CAS/bad-manifest/returned-literal3控制=81；B每case2closed拒绝=54，均全分母保留。损坏控制的CAS/manifest内部错误读/OSIO未仪表化unknownnull，不当0。

H1：完整9controller/27case/54真实producer/162源查询及全部计划marker/parent/entry/finally；每row完整Store source与独立原JSONL物理offset/length/SHA/原title/重复句/unicode/CRLF匹配，当前/old/pin SID按固定轨迹一致，所有旧对象/索引/manifest除允许HEAD不变；同规模三轮SID一致。
H2：全部54 contention非阻塞拒绝且A held前后库未修改；外部实际PID/handle与launcher退出区分；ready<=B拒绝<父确认A退出<B取得scope<=B返回<=父拒绝<B退出，ownerA/B info均非继承。A无footer/无返回不判完成，cleanclose有footer/return/close；B全27有footer/返回/正常关闭，最终不用删锁重获scope。
H3：81隔离坏副本/返回证据拒绝、54closed方法拒绝通过；18A退出后释放只说明scope可用，不成为A重试/rollback许可。联合仅H1&H2&H3，未提出性能/压缩/RSS改善门槛，任何未知不作免费/0，不用子阶段结果替换。

## 完整资源、拒绝与交付

正式每controller最多180秒/全plan900秒、0retry/exclusive输出。任何子失败停止剩余固定计划，保留54/162/81全分母与原始字节，未知槽执行/额外CPU/RAM/IO记null，不补跑。官方quota在controller前及父阶段20秒cache，子每操作与HEAD屏障放行前读父AUTH证据(max30秒)，reference1793894538/<=60服务抖动；未知/100/denied/reference/laterwindow停止，不跨授权窗口。各spawn预约/started/真实PID/OS退出/cleanup/完整root、controller、childentry从imports前、finally与outerparent时钟均保存；kill无childfooter则CPU/RSS未知，不能拿parent冒充。

父进程wall含spawn/等待/退出，两个writer parent区间重叠不相加冒充串行时延；selfCPU不含quota子进程/fulltreeCPU-RSS unknownnull/CPU0粒度不免费。所有source/Store/CAS/快照/索引/孤立对象/坏副本/lock文件/metadata/fsync/原source校验/脚本与库源码/历史science/train/models/failed/API资源账本保留。应用返回B非CASdecode/物理SSD/fullsystemIO，payload/文件byte非RSS，remoteweightsRAM未知null。默认API未改，scope不是数据库事务或持久性证明。

原v095缺失18/1728执行和额外成本未知、不填；v089旧41slots永久封存。0新模型/提供方HEAD/下载，0原科学corpus/question/gold/model/旧回答读取。不是科学NLI/回答/真实长期人类对话/无限上下文或物理掉电/一般多写者安全证明。公开owned计数/SHA/indices/metadata，原始source/查询留private。每轮全code/tests/frozenprotocol-input/exactCI-beforeformal/rawparents/独立审计/实际看图/完整report/README/localoutside实际wheel-currentnative新+ALLlegacyactualsdist/ReleaseCI/实际7SHA/allsource/outsidepublished/proof8/完成docs后交付。
