# v0.80 冻结候选：迟到成员路径的 RAM/CPU 取舍

v0.79已完整发行；原H3固定8metadata费用净增340600B不回填。当前仅已见owned目录成员机制，非开放检索/逻辑DAG/自然语言或科学NLI/回答收益。默认Store格式/SDK/UI不变。

## 同任务同信任

A retained保留v079完整Catalogue records/nodes/positions；B ephemeral初始无selectedpath进行全扫描anchor_only，之后每次收到迟到path重算必要siblings。两者同一真实held Store.read_scope/显式SID，先完整metadata验证；每次issue均检查Scope和prover未关闭，关闭后两者都拒绝，finally都显式close并清tree/anchor。初始anchor和后续成员必须符合父任务从fresh真实Store独立构建的可信anchor SHA，不信证书自行声明root。仅原SID不能认证派生root；不实现签名或可信网络分发。

B初始全扫描/后续重复排序及hash都计入算法阶段，不偷省初始O(N)认证；共同Snapshot O(N)metadata及每次排序keylist仍存在，不称全流程O(logN)内存。A/B exact canonical anchor/proof及原payload一致才验收。缓存原metadata期间后来manifest损坏仍沿用原始合法metadata，下一个scope重验；原CAS损坏必须在原read_range拒绝，metadata成员关系本身不是当前CAS健康证明。

## 工作量和严格时间线

已见count9/64/512/4096，3轮countorders：[9,64,512,4096]、[64,9,4096,512]、[512,4096,9,64]。每count2角色，roleorders AB/BA/AB（A retained/B ephemeral），共24fresh worker；每worker600s/0正式重试。每worker8迟到请求/每请求2unique路径，合计192packet/384正成员，4负控制/worker合计96：错误anchor、错误原bytes、缺失path、owner关闭拒绝；结束prover清字段另核。

父任务启动child→child造owned source/Store、Scope完整初始化、A/B constructor和状态计量→stdout READY含SID/anchor/constructed_at_ns→父任务fresh真实Store独立root验证，然后才构造8请求并exclusive保存/SHA和generated_at_ns→stdin发完整请求→child请求验证/原bytes读取/证明写入→DONE/reportSHA→finally/parent计时。请求规则第j对索引j%N和(N-1-j)%N，重合时第二+1 mod N，排序canonical path。虽然协议可预测，仍落实生成在constructor之后且父已观察READY，不能预生成列表帮B做批量缓存。不是未知科学或自然语言问题。

正式前10owned core/lifecycle/故障测试及1真实IPC unittest，全部只<=17叶/真实9source；另私有9source IPC预检2case，只验通信正确，不取时间/内存数字来调gate。无4096规模预检。完整496回归需通过，代码/协议/input冻结、精确CI成功后唯一正式campaign。旧quota/换行失败历史仅保留，不当本版正式数据。

## Gate与观测边界

H1全部192packet/384成员独立原bytes核、同count/round A/B canonical完全相同、原SID/query工作量/返回B守恒、96负控制、prover清理和父子生成时间线/完整计时/文件SHA守恒通过。后置以fresh真实Store重算24整目录root及28086 eligible leafmetadata，逐byte恢复28110全部原文件，复核192落盘packet/384成员；不依赖worker共享缓存视图或旧v079成功替代。

H2 primary4096每轮B/A额外常驻对象图初始和最终都<=0.5。额外图用实际prover实例/__dict__/tree实例及tree vars递归sys.getsizeof；对共同scope.files对象图和SID先收集seen以扣除相同对象引用，不把共享str重复当新增。固定scope/所有原metadata/全process RSS另列，不把该图当峰值/RSS上限。输出packet与文件账本分别记录，非prover长期状态。状态计量本身需扫描共同metadata及A额外图，在算法phase以外单独wall/CPU记账；仍进入完整worker/parent与RSS，不用observer差异推断生产收益。

H3 primary4096每轮B/A算法phase wall、CPU及完整parent wall都<=1。算法phase=完整initial tree/anchor constructor +8次issue/原bytes独立verify/canonical/证明文件写入；exclude等待父请求、source生成/Store ingest/共同Scope初始化及状态计量，这些均另记且进入整个worker/parent。父自己的独立root/请求生成wall/CPU另计，同工作量两方法都做。0CPU分母保留null不能pass；所有count/round全部报告，不取最佳轮。共同ingest/父验证大成本不能掩盖phase回退。

joint=H1&H2&H3。若省状态却更慢，保留负结果，不调8请求次数/取样/缓存策略追正。worker完整finallywall/CPU/RSS和parentwall/自身CPU/原root验证时间/timeout/exit/error齐备。

## 完整费用与发行

两方法都保存source/CAS/snapshot/请求时间线/packet/raw/stdout/stderr/完整ledger，不以删v079 diagnostic index.json声称新算法或磁盘净收益。本版评价运行状态与CPU；没有持久tree索引的cold-start load实现，磁盘成本若讨论必须注明表示及实验输出保留，不假定必要依赖。

保留并分别计费：整67Python+HTML、所有新public源/测试/协议/input/全部scripts、排序瞬时状态/初始Scope、源/CAS/历史metadata/派生请求、原模型训练/科学数据/恢复/帧/下载与失败日志；当前0模型/0新训练/0远程API不抹除旧成本。物理SSD/全系统IO/coldcache/crossmachine未知null。

raw/parent/finally/请求SHA标准图实际看、详报告/README/release/push，本地initialbuild0→物理外actualwheel/currentnative/actualsdist所有新旧机制→finalbuild/sourceaudit0→tag ReleaseCI→actual7资产SHA/递归全Python+HTML/scripts/外published实际安装/proof第8资产重下载全齐才交付。原science/human/train/model/frame/restored/私研/模板课程个人报告密钥不外发。仅CPU离线；E3净收益/E4整体/长会话/科学NLI/回答/无限上下文未完成。

授权窗口参考1793258458。实际100%/ordinary不允许/窗口终止或确认新窗口即保存准确状态并删除续跑，不跨窗口或消费reset credits。
