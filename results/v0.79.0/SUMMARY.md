# v0.79.0 实验报告：选中原文件的短成员证明

## 预定门槛与结果

H1所有原bytes成员、负控制、历史SID和后置原metadata/文件复核 **True**；H2主4096短packet<=旧全路径catalogue四分之一 **True**；H3固定8消息、完整index及全部新增public代码/测试/协议/输入费用后净省 **False**；联合 **False**。12独立worker，24正成员、96负控制、12旧SID保留及12新HEAD拒绝，追加14043真实eligible leafmetadata/全部tree nodes独立重算及14055文件恢复、24原bytes成员通过。0正式重试，不以最好轮代替全部。

本版只检验已见owned来源的metadata成员组件。成员packet与旧完整catalogue是不同wire envelope，不能当作旧canonical证书逐字节压缩；逻辑DAG和全局closure未在本版新消息中验证，全部全覆盖/科学NLI标志保持False。H2即便True也不能代替H3。固定8消息来自旧8query workload，不调摊销次数追正。

## 可信anchor的关键边界

初始真实Store完整manifest验证后，按SID建立eligible(path,size,file SHA)目录树。接收端独立持有可信anchor SHA、SID、期望path；只看proof自报root或只给原SID都不够。恶意发布者可以对同SID构造另一anchor，必要测试明确保留这一反例。没有签名/可信网络分发渠道实现，也不免除首次O(N)读取/建树。成员证明只表明给定原bytes属于已受信目录，不能推出原文科学真理、自然语言蕴含、目录完整覆盖或回答正确。

借用[RFC9162 §2.1](https://www.rfc-editor.org/rfc/rfc9162.html#section-2.1)域分隔SHA树和unbalanced inclusion path思想，应用canonicalJSON和anchor envelope是项目自定义，并非CT wire/签名服务或新密码算法。builder与checker分开，checker不导入builder/Store，独立计算方向和折叠；后置又从fresh实际Store重算每个leaf和全部内部node。

## 冻结与固定实验

485检查484pass/1权限skip；最终freeze `0a8b71ff3f74c18774312b3c8048c159e30af45a`，精确CI `40655001347` 成功后唯一12worker。最初额度读取传输故障中止controller；恢复后发现test原始CRLF与Git LF不同，manifest预检拒绝，正式worker仍0。只规范换行/输入SHA后另freeze/CI；原失败log保留，不重跑已评分case，缺完整预检CPU/wall为null。原型只测<=17叶，不用4096预检调预算。

owned9/64/512/4096、3固定轮次、两个固定selected paths，600秒/0retry。每worker完整保存tree建造、独立选中原bytes验证wall/CPU、整个finallywall/CPU/RSS和外层parent时间。8负控制含index/entrySHA/缺或多sibling/boolindex/SID/原bytes/零payload预算；notes新HEAD保持eligible root相同但anchor SHA随SID变化，拒绝旧proof改绑。

## 所有轮次与完整费用

| round |eligible |packet B |old catalogue B |packet ratio |完整index B |candidate8 B |baseline8 B |全新增metadata delta B |额外树对象图 B |peakRSS B |完整parent wall s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 9 | 1287 | 482 | 2.6701244813278007 | 2583 | 9381 | 4118 | 33630 | 7640 | 29065216 | 0.23595119989477098 |
| 1 | 64 | 1759 | 1857 | 0.9472267097469036 | 17380 | 13150 | 15118 | 41196 | 47602 | 28729344 | 0.2253479000646621 |
| 1 | 512 | 2165 | 13058 | 0.16579874406494102 | 138773 | 16384 | 104726 | 76215 | 380754 | 30560256 | 0.9034251000266522 |
| 1 | 4096 | 2571 | 102659 | 0.025044077966861162 | 1116732 | 19618 | 821534 | 340600 | 3088418 | 50532352 | 6.220621700165793 |
| 2 | 9 | 1287 | 482 | 2.6701244813278007 | 2583 | 9381 | 4118 | 33630 | 7640 | 28241920 | 0.13743019988760352 |
| 2 | 64 | 1759 | 1857 | 0.9472267097469036 | 17380 | 13150 | 15118 | 41196 | 47602 | 28667904 | 0.22538209985941648 |
| 2 | 512 | 2165 | 13058 | 0.16579874406494102 | 138773 | 16384 | 104726 | 76215 | 380754 | 30523392 | 0.8577785000670701 |
| 2 | 4096 | 2571 | 102659 | 0.025044077966861162 | 1116732 | 19618 | 821534 | 340600 | 3088418 | 49074176 | 6.139987499918789 |
| 3 | 9 | 1287 | 482 | 2.6701244813278007 | 2583 | 9381 | 4118 | 33630 | 7640 | 28581888 | 0.1427756999619305 |
| 3 | 64 | 1759 | 1857 | 0.9472267097469036 | 17380 | 13150 | 15118 | 41196 | 47602 | 28823552 | 0.22965540015138686 |
| 3 | 512 | 2165 | 13058 | 0.16579874406494102 | 138773 | 16384 | 104726 | 76215 | 380754 | 30486528 | 0.8968992999289185 |
| 3 | 4096 | 2571 | 102659 | 0.025044077966861162 | 1116732 | 19618 | 821534 | 340600 | 3088418 | 50388992 | 6.402776499977335 |

每轮全新增public fee固定25784B，包含两核心scripts/worker/tests/协议/input。H3把完整落盘index（所有leaf和所有tree range/hash）加上该费及固定8消息，减去旧8catalogue；既有整库67Python+HTML 429612B/Store/原source/payload在两边等额、并非免费省略。原完整文件仍精确恢复，selected原bytes应用返回量单列，不是物理IO。包内metadata每单file的1MiB上限不宣称整包或SSD读取上限。

额外Python图按去重sys.getsizeof包含records/nodes/positions/anchor，不是完整RSS或峰值cap。完整worker源码/CAS/原新snapshots/source/notes/index/packets/batches/控制残留14644122B，outer raw/parent/log1749357B，私有准备20612B；各文件SHA/size见账本。所有scripts保守1699055B，所有旧science/human/train/models/帧/恢复/cache历史保留。当前model0、训练0/API0，不抹除旧成本。诊断同时保存candidate/baseline等额外残留不等于部署仅需其中一种，全部残留和H3特定对照增量分开说明，不把它叫全系统磁盘净收益。

后置额外应用读取1357557B，与formal分开；完整分析finally/parent计时另附。builder初始O(N)、索引空间、全部专用源码和构造/验证CPU都报告，没有速度收益gate。零clock不可算比值时保留null，不使用预检/较少校验推断生产收益。

## 运行与交付

```powershell
python -m unittest discover -s tests
python -m scripts.run_catalog_membership --work exclusive-work --count 9 --round 1 --report exclusive-report.json
```

![成员消息与完整费用](catalog-membership.png)

图需实际查看。raw/parent/标准图/详报告和README/release同步；local initialbuild0、物理外actualwheel/currentnative/actualsdist新旧机制、finalbuild源码审计0之后才能tag/ReleaseCI，再实际7资产SHA/递归源码/外published实际安装/proof8重下载齐全才交付。原科学、模型、帧/恢复、私研、课程模板个人报告和密钥不公开。

默认SDK/UI/Store格式不变。逻辑证书集成尚未完成；E3净收益/E4整体/开放NL科学NLI/长期会话/回答/无限上下文仍未完成，冷缓存/跨机/物理SSD/全系统IO未测。下一步必须服从完整成本结果，不能把短wire packet称总体净收益。


中断后续跑记录：2026-10-29用户重新授权当前实际额度窗口1793258458，原实验输入/代码/工作量/门槛不变。启动前Git stat缓存曾将相同byte/SHA的test记为修改；对照原blob和manifest后仅刷新index，无内容变化。此前所有controller拒绝均发生在0正式worker；本次仅执行一次完整12case。图已实际视觉检查，未裁切关键信息。


## 打包字节来源纠正

首次local源码审核拒绝：仅版本/导入信息文件rkv1/__init__.py实测255B含Windows换行，原Git freeze为249B，规范换行后完全相同。实测文件未修改、原source-checksums/资源和实验结果未改写；为该模块明确-text保存实测字节，使最终tag/wheel/sdist与实测255B逐byte一致。原精确CI测的是逻辑相同的LF元信息；最终Release CI将验证与实测相同的原字节。差异、原失败与新Git绑定均单列runtime-line-ending-provenance.json，不宣称初始Git模块字节完全相同。无正式实验或安装重跑。
