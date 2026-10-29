# RKV-1 v0.83 实验报告：固定跨度准入的有界缓存

## 目的、先验和边界

v082已见诊断发现主4096每query初始142相关缓存key在使用前被全部淘汰。本版只测试一个已事先提出的span>=64准入候选；不扫阈值、不改64KiB或8请求、不重跑失败，保持旧负结果。D复制整个旧NodeLRU，put在原SID/range/value验证后只新增span<64不存入；复制源码全额收费，不把继承隐藏字段或源码复制称免费。A全树/B逐请求重遍历/C旧所有node LRU/D固定准入，四法同一任务。已见owned机制实验，不是未知数据泛化、自然语言、科学NLI、真实长会话或回答收益。

## 冻结方法和正式工作量

源码/协议/input freeze `e4d0c56a5b63bc7c44d2e564931031f979ee4b33`，exactCI 40825183767成功后唯一48freshworkers，9/64/512/4096×3轮×4角色，ABCD/BADC/CDAB。每worker8次迟到双path，父READY后fresh实际Store认证根才生成请求，600s上限0retry。384packet/768成员/192控制，追加48fresh根、56172叶、56220文件原bytes和768成员独立验证。517检查516pass1权限skip；必要预检仅真实9/17source，63/64/65边界用合成cachekey，不做4096规模预检或性能挑参。初次fixture错误和资源warning日志保留，后者仅统一driver资源释放修复，不修改旧基线源码或旧结果。

## 主要结果

H1原packet/原bytes/生命周期/计量与cache操作后上界通过；H2 D/A初末额外状态<=一半 **True**；H3 D/A完整phasewall/CPU与parentwall三轮都<=1 **False**；joint **False**。0CPU分母null不能通过。headline固定D/A；D/B、D/C及旧B/A、C/A全诊断见JSON，不换容易基线。

|轮次|D/A phase wall|D/A CPU|D/A parent|D/A初始状态|D/A最终状态|D/A RSS|
|---|---|---|---|---|---|---|
|1|1.9168004644761105|1.3333333333333333|1.0001937612325529|0.019003097362453036|0.01902641711203224|0.9515537541015248|
|2|1.99574669297436|2.5|1.0275361456345702|0.019003097362453036|0.01902641711203224|0.9407371948300622|
|3|1.742455060005606|1.6666666666666667|0.93862167423493|0.019003097362453036|0.01902641711203224|0.9557309209893177|


全部48case和72配对（12几何×6对照）的原始指标见derived-metrics.json。算法phase包含constructor+8issue/read/verify/canonical/写packet；共同ingest/Scope初始化/等待父请求/额外RAM对象图计量在phase外单列但进入完整worker与parent，不能用共同成本掩盖慢。父自身freshroot验证成本单列。所有查询同SID/同requestSHA/同packet精确相等；原CAS原文件bytes验证保留。

## 缓存、RAM与完整成本

固定65536B是每个合法cache操作后的完整cache-owned graph保守上界，包含slotted对象、OrderedDict、keys、ints、digest与stamp；插入后淘汰前provisional可更高，单列，不是全流程峰值硬cap。初始完整Snapshot O(N)和临时排序keys保留，Scope/完整RSS/对象图观察器、stamp/LRU/淘汰与维护CPU均另计。原source损坏仍由原read_range拒绝，节点checksum只防事故，非任意内存攻击认证。初始/final trace/hits/misses/hash_nodes/evictions/rewrites详见每case raw，计数不是物理IO。

整库实际67Python+HTML 429612B；全部scripts保守1753927B；源码/测试/协议/input SHA、专用复制代码、整运行库分别记账。worker完整source/CAS/snapshot/request/packet残留18338808B，outer raw/parent/stdio 7140230B，私有准备297134B，后置实际应用读取5496456B单列。旧science/human/train/model/源数据/帧/restored/历史快照/派生/下载缓存/失败全部保留，不当0；未知OS/SSD物理与全系统IO、冷缓存/跨机仍null。

## 重现、图表和交付

运行必要tests后，以冻结inputs和scripts.run_span_membership.execute_case执行父子协议；不可重建旧时钟或只重跑获胜轮。原始rawparent/worker-finally、input/sourceSHA、标准图及独立审计器随本版保存。图必须实际视觉检查，分析自身完整finally/parent计时另附。

![四法完整比较](span-membership.png)

本机CPU离线，0新模型调用/下载/训练；E3净空间整体、E4整体、开放NL科学NLI、真实长期会话/回答与无限上下文未完成。原science/model/frames/restored/私研/课程模板个人报告密钥不发布。Release必须local初始build0→仓库外actualwheel-currentnative/new+全部legacyactualsdist→finalbuild/sourceaudit0→ReleaseCI→实际7资产SHA/递归source/外publishedinstall/proof8齐才完整交付；未齐保持未完成。
