# v0.78.0 实验报告：显式 SDK 同快照读取作用域

## 结果与交付边界

H1逐字节/范围/完整验证及原实验接口证据一致 **True**；H2同SID/深只读/关闭后拒绝/零容量控制 **True**。H3旧实际v0.77 wheel读取新版普通快照 **True**：实际新旧wheel均已物理仓库外安装，4个完整文件、固定范围及完整验证报告通过；联合 **True**。原正式worker结果未重跑或覆盖。12freshworker、96SDK+96reference证明、14055完整文件及14055固定范围比较、48负控制均通过，另192落盘证明以全新真实Store元数据/DAG复核、14055源文件再次完整恢复。正式0重试，失败不覆盖，不用最优轮代表全体。

本版把v077实验接口的机制纳入显式可调用SDK，不是新速度实验。默认Store.snapshot和磁盘格式不变，不跟随HEAD，不缓存解压后的sourcepayload；v077的约24倍查证批和约3倍整个进程速度属于原固定实验，不能当作本版新测收益。公开API可运行，不等于生产成熟、开放自然语言、科学NLI、长期会话或无限上下文完成。

## 冻结与固定实验

本机478测试477通过/1权限跳过，源码/协议/输入冻结 `f47c00918bc165b8fffb5ed8341191fede1c9119`；精确CI `40647454213` 成功后唯一执行。已见owned geometry9/64/512/4096、各3轮、每轮8固定问题（4ground query各重复2次）、两固定selected source、work100000，不调旧问题/预算/顺序。每worker600秒、0retry；父进程另计完整启动到退出wall，worker finally记录完整wall/CPU/RSS，所有raw和parent逐worker保留。

逐文件完整读取与offset=1、length=min(10,len-1)范围和旧真实Snapshot比较；每worker SDK.verify()与Snapshot.process(None)完整验证报告相等。SDK/原v077独立实验脚本接口对8问题canonical证书逐字节相等，旧独立DAGchecker仍回原file/SID/SHA/range，不把摘要/派生索引当原证据。global_verdict始终null。

## 所有轮次与费用

| round |eligible |完整文件比较 |范围比较 |SDK/reference证明对 |tracked metadata B |peakRSS B |worker全wall s |worker全CPU s |parent全wall s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 9 | 10 | 10 | 8 | 15844 | 28753920 | 0.07969560008496046 | 0.078125 | 0.17155730002559721 |
| 1 | 64 | 65 | 65 | 8 | 95227 | 28545024 | 0.15445760008879006 | 0.140625 | 0.2438842998817563 |
| 1 | 512 | 513 | 513 | 8 | 743371 | 31416320 | 0.7416693000122905 | 0.734375 | 0.8291821000166237 |
| 1 | 4096 | 4097 | 4097 | 8 | 5923451 | 48939008 | 5.542664899956435 | 5.484375 | 5.632615000009537 |
| 2 | 9 | 10 | 10 | 8 | 15844 | 28377088 | 0.08240419998764992 | 0.078125 | 0.17059440002776682 |
| 2 | 64 | 65 | 65 | 8 | 95227 | 28520448 | 0.15287200012244284 | 0.15625 | 0.23997560003772378 |
| 2 | 512 | 513 | 513 | 8 | 743371 | 31215616 | 0.7378595999907702 | 0.734375 | 0.8239349001087248 |
| 2 | 4096 | 4097 | 4097 | 8 | 5923451 | 49475584 | 5.505290100118145 | 5.421875 | 5.5925042000599205 |
| 3 | 9 | 10 | 10 | 8 | 15844 | 28151808 | 0.0781487999483943 | 0.078125 | 0.16639959998428822 |
| 3 | 64 | 65 | 65 | 8 | 95227 | 28405760 | 0.1532748001627624 | 0.140625 | 0.240460499888286 |
| 3 | 512 | 513 | 513 | 8 | 743371 | 31129600 | 0.7466516001150012 | 0.703125 | 0.8346756999380887 |
| 3 | 4096 | 4097 | 4097 | 8 | 5923451 | 49102848 | 5.493691300041974 | 5.375 | 5.582402100088075 |

以上时间包含创建/导入/全部扫描/重复独立校验，不是SDK生产查询延迟，也没有速度门槛。额外后置分析应用返回2319447B；不是SSD物理IO或全系统读取。全部保留worker文件10747791B、outer raw/parent/log1777824B、私有准备22191B分别列SHA/size。当前加载模型0、新训练0、新远程调用0；旧训练/模型/science/human/CAS/快照/帧/恢复与下载缓存历史成本不清零。

实际递归运行库67Python+HTML计429606B，新增snapshot_scope.py以及store.py API增量不省略；所有专用源/测试/协议/输入和全scripts保守1686687B单列。新旧外部安装、旧wheel、publication缓存和proof另记发行核验账本；不把额外SDK源码当免费压缩或存储收益。OS/目录分配/全部allocator等未测不当0。完整分析finally/父timer另附，不能只报成功写报告的一段成本。

## API、生命周期与故障含义

```python
with store.read_scope(explicit_snapshot_id) as scope:
    data = scope.read_range('owned/path.bin', 0, 128)
    verification = scope.verify()
```

必须显式固定SID、同步单作用域，不跨线程/进程共享。files为深只读metadata视图；关闭后read/verify/新view拒绝，已取得的只读metadata值不是可撤销权限。16MiB cap量保留对象图（包括proxy背后的dict表），初次完整加载/验证/构造后才检查，排除callerStore/OS/allocator，不是构造峰值或RSS保证。SDK/producer/checker可共享一次初始metadata信任，不能称完全独立；本版追加fresh真实Store审计分开做。

scope持有最初合法metadata；磁盘manifest随后被外部改坏时，已活跃scope继续使用初始metadata，下一scope重验并拒绝。新HEAD不改变旧SID；原CAS损坏即使scope活跃也由原payloadvalidator拒绝。测试验证这条已声明语义，不把它外推为每次fresh读取的同等故障探测。先前原型错误假设Snapshot有verify方法已在正式前纠正为实际process，原失败日志留本地。

## 安装兼容性与复现

旧reader兼容H3须实际已发布v0.77 wheel安装在仓库外，确认无read_scope API仍能读新wheel生成的普通快照、完整/范围/verify均与原bytes一致；源代码相似或prefixSHA不能代替。先本地真实新wheel/旧wheel安装，再actual发布新wheel重复核验。此项未齐不能把整版叫交付。

```powershell
python -m unittest discover -s tests
python -m scripts.run_sdk_read_scope --work exclusive-work --count 9 --round 1 --report exclusive-report.json
```

![SDK一致性与metadata实际大小](sdk-read-scope.png)

图需实际视觉检查。后续local initialbuild退出0→物理外actual新wheel/currentnative/newlegacyactualsdist/旧v077兼容→finalbuild源码审核→commit/tag/ReleaseCI→实际7资产SHA/全部递归Python+HTML/所有脚本/tag/隐私/外部实际安装/proof第8资产重下载才算交付。原科学/自然语言数据、模型、frames/restored、私研、课程模板、个人报告和密钥不发布。

E3净收益/E4整体/科学NLI/真实长期会话/回答和无限上下文仍未完成。冷缓存、跨机器、物理SSD/全系统IO未测。下一项应针对真实瓶颈单独提出可证伪问题，不能把包装或机制验收反复称新科学结果。


## 后续实际安装兼容补充

本地initialbuild已退出0，actual新wheel/currentnative与actualsdist全部旧机制和本版SDK smoke通过。随后actual已发布v0.77 wheel SHA核对后新装仓库外，确认版本0.77.0且无read_scope，读取actual新wheel生成的空文件/ASCII/二进制/Unicode嵌套路径4文件逐byte、范围和全验证通过；H3由未测null追加为True，不回填正式campaign。新/旧reader完整父wall、外安装全部残留文件和SHA另附pre-tag-SDK-compatibility.json。此安装检查不是新性能或科学实验。最终published实际新wheel安装及proof尚需发行后重复核验。
