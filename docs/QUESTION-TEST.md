# v0.51 冻结协议：同一训练模型迁移到封存官方test

## 目的和不变候选

v050 actual资产/外部安装/finalproof全通过后实施。同一EntailmentBank领域的官方test检验，而非新领域或真实长对话。v050 dev图IDmacro30.68% vs lexical26.17%，完整22/12，但CPU比1.048387、联合False均保留，不在dev调参数/seed/预算；此版检验其来源定位增益能否在未打开的test复现。

scripts/evidence_retrieval.py、source_alignment.py和65runtime（除版本）逐字等v050。模型原SHA2f82ee4b28c943038e7a37ddcbd8871443f7a441ddd45a1af599decc8bade183、4629668B原byte完全复用，不重训、不用dev加边/调词表。原训练codeca9fddc、model freeze与v050发布proof为身份根；新的code/input/test协议另冻结后才揭test。旧训练一次的CPU/parent/组件B作为历史共享成本保留，新训练0/新模型bytes0而非部署模型免费。

三方法原BM25(k1=1.2,b=.75,token/stop完全不变)、训练共现graph、固定rkv050control置换；top6seed+6邻居、12facts/4096原JSON memberB、原tie/skip规则和原UUID/精确alias/未解/literal双口径都不变。候选不是wheel语义图API，仍assessment脚本，默认Memory/CLI/UI不改；0生成回答/NLI或新模型API。

## 新test原始身份与排除边界

官方repo固定daac2fdb7ab52ec3ef8f2953f59288c1edd7c2f0，Task1 test.jsonl原1827479B、Git blob a0c64843ae49f789d74758bf143dcccf8dcf8ba5，SHA256 ae02515bf620f2cc865a4c6ed60adba595aba575e3ab471ecd27d65e6ff9c52f、340换行。准备阶段只下载/byte SHA/行数，未JSON解析/阅读问题gold/评分；源/句子/原题/fullmodel留私有，原文件不重分发。corpus/source/旧train/license沿原固定输入。

新docs/entailment-test-inputs.json包含rawtestSHA、原corpusSHA与准备成本，以及从v050已公布187dev行提取的qid/normalized question SHA封存排除表。test首次解析后，任何训练或已见dev的qid或规范化question SHA重叠行均排除、保留原row index/原因，不根据成绩丢题。相较v050只排train，此版明确增加seen-dev排除以确保尚未评分问题的迁移；总体样本不同，不能把跨split绝对召回差当算法变化。其余340物理行全部评分，独立uniqueqid和排除数另列，重复testqid不事后合并。

仍只传官方question字符串给ranking/admit，绝不拼接answer/hypothesis/context或gold。先产生selected/原文hits，再用权威Task1 proof叶计算ID组和literal双指标。未解和UUID改写继续留不可命中分母，不把ID覆盖当语义证明。

## 精确次数和先验门槛

268完整检查267pass/1Windows权限skip（新增1个真worker合成端到端：固定模型SHA/只提供corpus+test/恶意answer等不作query/seen-dev排除/原source验证），代码/本协议/input/model身份/exactCI成功后唯一9fresh worker。ABC/BCA/CAB三方法三轮，seed20261027+round仅打乱340原行；每worker每合格物理题一次选择/验证。一个worker600s，失败保留返回码/异常/childSHA/父完整subprocesswall，不覆盖重跑、无再训练。三轮相同质量只证明确定性，不将样本数×3×方法。

原quality gate不变：graph macro ID recall严格胜lexical和置换控制，且完整ID组覆盖题数≥两者，三轮都满足。时间联合graph/lexical query wall/CPU/parent完整wall比三对中位数都≤1，零CPU分母null失败，不加epsilon/追加轮。quality与time/联合单列，完整模型/源码/内存费用另报，不称总体TCO净收益。逐题胜/负/平、literal辅助低覆盖和全部负方向保留。没有根据dev成绩放宽test门槛。

每selected原Store固定zlib/fixed65536/bounded校验read_range/stored/raw/原memberSHA/JSON身份，9全corpus逐字节恢复/Store全树前后跨worker同身份。新worker只改变固定test输入、排除表和字段名，原核心模型/检索不改。独立analyzer直接raw slice/Store重读/gold重建/同model纯排名重放，诊断费用单列；原v050坏analyzer保留，本版从三tuple修正后的独立audit复制，不恢复旧错误。

## 成本和发行

全部原model4.6MB每worker实际载入（lexical也载图），旧训练成本历史复用情景和shared/index/graph/control SHA/B明确；不称没有新训练就无模型成本。共享corpus/已见train/dev/新test及准备副本/Store/CAS/config/snapshot/源copy/plan/private-question/ledger/原始JSON/全部日志/侧车/图/程序按实际B/SHA收费。复制test到已用私有输入目录只为loader目录一致，两个物理副本均计B，不改原byte，原source仍唯一真值。

query wall/CPU含检索/入证/原源校验，ingest/gold/recovery/workerCPU及父从启动到末尾退出完整wall、观察RSS另列。实际模型、source/catalog/record对象内存不免费，RSS不是完整生命周期增量采样；4096入证不是CAS读取或RAMcap，SSD物理/全系统IO/冷缓存/跨机继续null。模型/平台依赖不称完整TCO；原input准备计时元数据保留，训练新增0。

源码/冻结协议/无原文原始JSON/标准图实际视觉检查/详实报告/README/release/GitHub，CI后actual5资产SHA/65递归Python+HTML/tag/新testdriver和analyzer、物理外部actual wheel+current native/actual sdist模型检索与新test排除worker合成smoke/旧格式CLI/最终proof重下载全通过才完成，收尾再下一版。

旧24模型API耗尽0新增调用，本机CPU离线。私有原science源/questions/fullhits/model图/帧恢复副本/研究模板个人报告密钥不发布。E3净收益仍失败，E4语义蕴含/多跳生成回答/真实长期会话/形式化证明/无限上下文未完成。后续不能在此test反复调图/预算追分，应另冻独立诊断或新数据假设。
