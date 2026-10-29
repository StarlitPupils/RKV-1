# RKV-1 — Reversible Knowledge Vault

面向科学知识与推理的可逆记忆研究项目。原始证据逐字节保存；摘要、图谱、语义索引和
神经记忆作为未来辅助表示，最终结论能回到精确来源。

[![tests](https://github.com/StarlitPupils/RKV-1/actions/workflows/ci.yml/badge.svg)](https://github.com/StarlitPupils/RKV-1/actions/workflows/ci.yml)
[版本发布](https://github.com/StarlitPupils/RKV-1/releases) · [路线](docs/ROADMAP.md) · [格式](docs/FORMAT.md)

## 最新实验：v0.89.0 · 同批证据对照未完成（发行待核验）

计划24题×两条件48次API，第7次请求出现URLError，按协议停止：7次尝试、6份响应、41次未尝试。没有重试或补齐，H1/H2未通过，不能据此比较两组有效性。原48分母、失败记录和独立审计保留；后续仅报告与发行工程。

![未完成轮的完整分母](results/v0.89.0/oracle-intervention.png)

562检查561pass/1权限skip；[详实报告](results/v0.89.0/SUMMARY.md) · [冻结协议](docs/API-ORACLE-INTERVENTION.md)。科学实验未完成与软件发布是否通过分别记录；下方v0.88为最新完整交付版本。

## 当前版本：v0.88.0 · 两批回答的失败定位

原32问题、96回答审计完成，0新API。两批各12有标注检索题：第一批缺标注论文5题、已有论文仍判定错2题；第二批分别3题和2题。缺来源占完整依据失败的5/7及3/5，两批多数假设成立，但不能据此推断加预算或补论文一定改善回答。

![原回答失败定位](results/v0.88.0/failure-diagnostic.png)

556检查555pass/1权限skip，worker与独立审计各89来源绑定通过；[详实报告](results/v0.88.0/SUMMARY.md) · [协议](docs/API-FAILURE-DIAGNOSTIC.md)。仅已见事后诊断；[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.88.0)实际7份资产SHA、67Python+HTML/全部源码、仓库外发行wheel/current native及新旧sdist复测均通过，第8份proof已重下载核验。

## 当前版本：v0.87.0 · 第二批问题API复测

另一批16题、三条件共48次真实API及独立审计完成：检索证据12/16正确，空证据和其他题证据各4/16；12有标注题的判定加完整依据为7/12对两组0/12。固定门槛通过，仍是项目已见公开数据，不代表未知科学泛化或无限上下文。

![第二批API复测](results/v0.87.0/api-intervention.png)

549检查548pass/1权限skip；[详实报告](results/v0.87.0/SUMMARY.md) · [协议](docs/API-EVIDENCE-REPLICATION.md)。本批48次额度全部使用，两图实际检查；实际7份资产SHA、67Python+HTML与所有源码、仓库外实际发行wheel/current native和新旧sdist均通过，第8份proof重下载核验通过。[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.87.0)。

## 当前版本：v0.86.0 · 固定预算的来源选择三法对照

270个已见问题、三方法各三轮共2430本机查询完成。168有标注问题中，旧词法宏来源recall为76.24%、完整覆盖126题；按分数/原字节排序降至57.86%、95题，长度控制为1.19%、2题。新候选算法wall约4.54–4.74倍，质量与时间联合门槛失败，保留旧默认方法。

![固定预算质量与成本](results/v0.86.0/cost-aware-sources.png)

544检查543pass/1权限skip，独立11244原记录绑定和完整语料恢复通过。0新API/训练；[详实报告](results/v0.86.0/SUMMARY.md) · [冻结协议](docs/COST-AWARE-SOURCES.md)。图已实际检查，[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.86.0)的7份实际资产SHA、67Python+HTML与所有源码、仓库外实际发行wheel/current native和新旧sdist核验均通过，第8份[最终核验文件](https://github.com/StarlitPupils/RKV-1/releases/download/v0.86.0/published-verification.json)重下载通过。不称模型回答提升或未知科学泛化。

## v0.85.0 · 排名与原记录准入诊断

原16问题的词法排序、43旧选中文献、12标注论文与原字节完全匹配。5个漏选来源中，没有一条自身超过4096B，原先“多数因为单篇太大”的假设失败（0/5）；其余预算不足与排序相互影响，原rank包含2、2、4、7和225。不能据此声称加预算必有收益。

![排名和原记录准入](results/v0.85.0/api-admission-audit.png)

536检查535pass/1权限skip，0新模型调用；[详实报告](results/v0.85.0/SUMMARY.md) · [协议](docs/API-ADMISSION-AUDIT.md)。这是已见事后解释，H1True/H2False，[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.85.0)原7资产SHA/源码/外安装/第8proof重下载通过，另有仅人工scope文案的第9份追加更正，原数据/结果/原proofSHA不变。

## v0.84.0 · 模型API证据干预

16个已见科学主张×三条件共48次真实API完成。空证据与其他题证据均4/16正确，检索证据9/16；12有标注问题中“判定+完整标注依据”分别0/12、0/12和5/12。独立原文/引用核验通过，冻结质量门槛通过；但16题较小、p=.125，不称普遍或显著提升。SUPPORT仅1/6，5题未取回标注论文，完整错误分解保留。

![API三条件对照](results/v0.84.0/api-intervention.png)

530检查529pass/1权限skip；[详实报告](results/v0.84.0/SUMMARY.md) · [协议](docs/API-EVIDENCE-INTERVENTION.md)。原source/prompt/response/密钥私存，48次新预算已用完，不额外调用；[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.84.0)实际7资产SHA/全部源码/仓库外安装/最终第8份proof重下载已通过。引用身份不是科学蕴含，尚未实现无限上下文。

## v0.83.0 · 固定跨度准入四法对照

48worker/384证明/768成员/192控制，以及独立48根/56172叶/56220文件恢复通过。固定span>=64候选主4096每轮80命中、零淘汰，额外状态约为全树1.90%；但算法wall仍为全树1.74–2.00倍、CPU1.33–2.50倍，H1/H2=True、H3/joint=False。完整RSS比0.941–0.956，不能把额外状态降幅当总RAM或压缩收益。

![跨度准入完整比较](results/v0.83.0/span-membership.png)

517检查516pass/1权限skip；[详实报告](results/v0.83.0/SUMMARY.md) · [冻结协议](docs/SPAN-ADMISSION.md)。图已实际视觉检查；[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.83.0)的实际7资产SHA、67Python+HTML/全部源码、仓库外实际发行安装和第8份proof重下载均通过。不改阈值/预算/请求数追正，不称科学NLI、回答或无限上下文收益。

## v0.82.0 · 缓存使用前淘汰诊断

原12case/96请求的保真重放通过，原初末trace、96证明和192成员原字节一致。主4096的24个请求每次开始有142个相关缓存节点，但实际查找前全部被淘汰，解释零命中；H1/H2通过。已见任务事后诊断，没有新策略、提速或问答收益，旧负结果不变。

![使用前淘汰诊断](results/v0.82.0/cache-replay.png)

507检查506pass/1权限skip；[详实报告](results/v0.82.0/SUMMARY.md) · [协议](docs/CACHE-REPLAY.md)。[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.82.0)实际7资产SHA、67Python+HTML及所有源码、仓库外实际发行wheel/current native与新旧sdist复测、最终第8份[核验文件](https://github.com/StarlitPupils/RKV-1/releases/download/v0.82.0/published-verification.json)重下载均通过。已发布tag、原实验与图表保持冻结；本段在核验完成后更新。

## v0.81.0 · 有界 metadata 子树缓存

36worker/288packet576成员/144控制和fresh36根、42129叶、42165文件恢复通过。完整cache-owned graph操作后上界65536B满足，主4096额外prover状态约为全树2.52%，但cache实际0命中、反复淘汰，算法phase慢15.9–18.5倍，CPU13.3–22倍，parent回退。H1/H2=True、H3/joint=False，负结果保留。

![有界缓存完整费用](results/v0.81.0/bounded-membership.png)

504检查503pass/1权限skip；[详实报告](results/v0.81.0/SUMMARY.md) · [协议](docs/BOUNDED-MEMBERSHIP.md)。插入瞬时graph可70552B、完整RSS另列，不把64KiB当全流程峰值上限，不称压缩/NLI/回答收益。[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.81.0)实际7资产SHA/全源码/仓库外安装与最终proof均已核验。

## v0.80.0 · 迟到成员请求的 RAM/CPU 取舍

固定24worker/192packet/384成员与额外24fresh根、28086叶、28110原文件恢复通过。重算法额外常驻状态约为完整树的0.0623%，但完整进程peakRSS只小约5–6%；算法phase慢约5.4–5.6倍、CPU约6–7倍，parent也回退。H1/H2=True、H3/joint=False，负结果保留。

![迟到请求的内存与阶段时间](results/v0.80.0/late-membership.png)

496检查495pass/1权限skip；[详实报告](results/v0.80.0/SUMMARY.md) · [协议](docs/LATE-MEMBERSHIP.md)。保持初始完整metadata和外部可信anchor，不称总RAM同幅降低、生产加速/压缩/NLI或回答收益。[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.80.0)实际7资产SHA/全源码/仓库外安装与最终proof均已核验。

## v0.79.0 · 选中来源的短成员证明

24成员/96篡改与预算拒绝、历史SID和14043叶metadata/14055原文件复核通过。主4096短消息显著变小，但完整index+全部新增源码和固定8条消息后成本增加约34万B，H1=True/H2=True/H3=False/joint=False；负结果保留，不增加摊销次数追正。

![短成员与完整费用](results/v0.79.0/catalog-membership.png)

需要独立可信anchor SHA/SID/path和初次完整manifest校验，不是仅凭SID自认证、逻辑DAG/NLI/压缩或回答收益。485检查484pass/1权限skip；[详实报告](results/v0.79.0/SUMMARY.md) · [协议](docs/CATALOG-MEMBERSHIP.md)。[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.79.0)实际7资产SHA/67Python+HTML/所有源码/物理仓库外安装与最终proof重下载均已通过。

## v0.78.0 · 显式同快照读取 SDK

新增 opt-in `Store.read_scope(explicit_sid)`；默认 snapshot 和磁盘格式保持不变。固定12 worker的96对SDK/原实验接口证明、14055完整文件与范围读取、48拒绝控制，以及追加192 fresh原DAG/14055文件恢复通过。实际旧v0.77 wheel仓库外读取新wheel普通快照通过，H1/H2/H3/joint=True。

![SDK一致性和metadata大小](results/v0.78.0/sdk-read-scope.png)

478测试477 pass/1权限skip；[详实报告](results/v0.78.0/SUMMARY.md) · [协议](docs/SDK-READ-SCOPE.md)。无新速度、压缩、科学NLI或回答收益声明；Release CI、实际7资产SHA/全部67Python+HTML/物理仓库外新旧wheel与actualsdist、最终proof重下载均已通过。[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.78.0)。

## v0.77.0 · 有限批次元数据复用

固定48worker/384query与额外384fresh原DAG、56220原file恢复通过，H1/H2/H3/joint=True。主4096/meterOFF查证批wall约0.0416–0.0419倍，整进程约0.331–0.336倍，peakRSS约0.761–0.770倍；原source读取B与证明不变。收益限于单SID有限批次规则负载，缓存保留初始metadata的故障语义已说明，无科学NLI/回答/压缩收益声明。

![元数据复用完整计量](results/v0.77.0/pinned-metadata.png)

472检查471pass/1权限skip；[详实报告](results/v0.77.0/SUMMARY.md) · [协议](docs/PINNED-METADATA.md)。[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.77.0)实际7资产/全源码/物理仓库外安装/最终proof重下载已通过。

## v0.76.0 · 训练集结构模板

一次训练1681理论得到1099模板；新测试308human句子命中0，baseline/learned/control各532题全拒答，H1=False/H2=False/H3=True/joint=False。8个训练实体名字覆盖测试实体，不能把失败归因于缺人名；不补已见测试模板。

![模板全部问题分母](results/v0.76.0/typed-templates.png)

461检查460pass/1权限skip，0模型API。不是神经模型/开放NL/科学NLI，E3净收益/E4整体/长期对话/回答/无限上下文未完成。[详实报告](results/v0.76.0/SUMMARY.md) · [协议](docs/TYPED-TEMPLATES.md)。[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.76.0)实际7资产/全源码/物理仓库外安装/最终proof重下载均已通过。

## v0.75.0 · 原Store依赖紧凑证明

1152精确恢复/原证据通过H0=True；主Zstd计入全部新增源码后节省42136–42177B，H1=True，但耗时约1.44–1.51倍，H2=False/joint=False。节省依赖既有Store，非contextless压缩/E3净收益/科学NLI；后置分析收尾时间缺项保留null。

![紧凑证明完整账本](results/v0.75.0/compact-witness.png)

452检查451pass/1权限skip；[详实报告](results/v0.75.0/SUMMARY.md) · [冻结协议](docs/COMPACT-WITNESS.md)。[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.75.0)实际7资产/全源码/物理仓库外安装与最终核验重下载均已通过。

## v0.74.0 · 固定证据下的目录放大

12worker/96query与追加96原DAG、14055原file恢复通过，H1=True；但4096/9耗时214–243倍、证明25.84倍，H2=False/H3=False/joint=False。只取少量证据不等于整体成本固定；没有宣称科学NLI或加速。

![目录增长成本](results/v0.74.0/catalog-scaling.png)

436检查435pass/1权限skip；[详实报告](results/v0.74.0/SUMMARY.md) · [协议](docs/CATALOG-SCALING.md)。[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.74.0)实际7资产SHA/全源码/仓库外安装/最终核验文件重下载已通过；下载失败和额外缓存费用保留。

## v0.73.0 · 部分记忆中的证据

3个进程共78证据case、36预算拒绝、9旧严格控制、30篡改拒绝、24历史相等通过。可从少量原文件找出可核验证据，所有全库结论保持null；不是语言理解或科学真理判断。427检查426pass/1权限skip，0新训练/API。

[详实实验报告](results/v0.73.0/SUMMARY.md) · [冻结协议](docs/SELECTED-WITNESS.md)。[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.73.0) 的实际7资产、全源码、仓库外安装及最终核验文件均已通过。

## v0.72.0 · 人工改写来源的适用边界

同32个官方NatLang理论每方法532题，规范text控制正确532，实际human句子正确0、接受0；H1=False/H2=False。没有用规范旁注冒充人的改写，所有解析拒绝留在分母。

![人工改写适用性](results/v0.72.0/human-source-coverage.png)

412检查411pass/1权限skip；旧parser不调，0新训练/API，默认SDK/UI不改。受限合成句型成绩不能外推开放NL，E3净收益/E4整体/科学问答/无限上下文未完成。
[协议](docs/HUMAN-SOURCE-COVERAGE.md) · [详实报告](results/v0.72.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.72.0)。

## v0.71.0 · 证明共享布局与普通压缩对照

768组证明包逐字节恢复及原querySHA通过，主Zstd完整保守空间H1=False、整进程时间H2=False、联合=False。源码/metadata/全部残留和时间都计费；这是已见证明的格式实验，未新增科学NLI或回答收益。

![证明格式完整账本](results/v0.71.0/proof-frame.png)

406检查405pass/1权限skip，0新训练/API，默认SDK/UI不改。E3净收益/E4整体/可靠长会话/无限上下文未完成。
[协议](docs/PROOF-FRAME.md) · [详实报告](results/v0.71.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.71.0)。

## v0.70.0 · 受限英语输入到证据规则

官方人工OWA test64理论共1394题，正确且接受1394，H1=True/H2=True。预测只读声明范围内的English句子，给定formalreference仅在预测后独立核验；未实现通用语言理解或科学真理判断。

![受限English全部分母](results/v0.70.0/proofwriter-english.png)

395检查394pass/1权限skip；0新训练/API，默认SDK/UI不改。E3净收益/E4整体/可靠长对话/无限上下文未完成。
[协议](docs/PROOFWRITER-ENGLISH.md) · [详实报告](results/v0.70.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.70.0)。

## v0.69.0 · 外部人工规则形式表示

官方OWA前64理论共1360问题，正确且独立接受1360，H1=True、全题接受/恢复H2=True。只用数据给定形式表示，原JSON到派生source逐条独立审计，自动English解析和科学真理判断仍未实现。

![外部规则全部分母](results/v0.69.0/proofwriter-representation.png)

389检查388pass/1权限skip；0新训练/API，默认SDK/UI不改。E3净收益/E4整体/可靠长对话/无限上下文未完成。
[协议](docs/PROOFWRITER-REPRESENTATION.md) · [详实报告](results/v0.69.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.69.0)。

## v0.68.0 · 多来源显式规则与原文件证据链

能把不同文件里的显式事实/规则接起来，逐条核验原file来源；216检查中36完整、144证据不全、36工作不足，72旧快照proof一致、12篡改拒绝。来源与推导范围受限于人工公理，自动语言理解和科学真理判断仍未实现。

![多来源原证](results/v0.68.0/source-set-logic.png)

380检查379pass/1权限skip；0新训练/API，默认SDK/UI不改。E3净收益/E4整体/可靠长对话/无限上下文未完成。
[协议](docs/SOURCE-SET-LOGIC.md) · [详实报告](results/v0.68.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.68.0)。

## v0.67.0 · 证据来源未读全时明确拒绝

36来源集合检查：12完整、24预算或遗漏时明确incomplete，12旧快照证明不变，10无效完整proof拒绝。只验证机器来源字节集合，语法/逻辑/科学验证均未声称通过；自动自然语言理解仍未实现。

![来源集合边界](results/v0.67.0/source-universe.png)

369检查368pass/1权限skip，0新训练/API，默认SDK/UI不改。E3净收益、E4整体、可靠长对话和无限上下文未完成。
[协议](docs/SOURCE-UNIVERSE.md) · [详实报告](results/v0.67.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.67.0)。

## v0.66.0 · 有限规则程序变形检查

12人工程序、4种变形，1296推导证书/972一致性/36跨源拒绝/48历史恢复通过。检查规则改名、行序、正负符号变化后结果是否一致；结构化公理仍是显式输入，不代表自然语言科学理解。

![有限规则变形检查](results/v0.66.0/logic-metamorphic.png)

361检查360pass/1权限skip；0新训练/API，旧引擎和默认SDK/UI不改。E3净收益/E4整体/可靠回答/无限上下文未完成。
[协议](docs/LOGIC-METAMORPHIC.md) · [详实报告](results/v0.66.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.66.0)。

## v0.65.0 · 显式规则来源证明与词序碰撞反例

72份受限规则证书、3个未完成预算控制、6个篡改控制通过；更新后读旧快照结果相同。自造主客体反转问题上，旧四模型各8/16，说明词袋丢失顺序，不能据此声称科学NLI/回答提升。

![受限机制与词序反例](results/v0.65.0/signed-logic.png)

357检查356通过/1权限skip；0新训练/模型API，默认SDK/UI不变。结构化公理是人工输入，自动语言到可靠证据关系仍未实现。E3净收益、E4整体、真实长会话与无限上下文未完成。
[冻结协议](docs/SIGNED-LOGIC.md) · [详实报告](results/v0.65.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.65.0)。

## v0.64.0 · 实际检索证据上的CPU词面关系probe

同一原BM25真实source，四方法12worker，先预测实际返回paper再读gold；1训练campaign含3fit与多数类，4model SHA先冻结。明确gold/unknown/missing分母分别记录。
**H1关系分类质量False / H2局部CPU与model可行性True / 本probe联合False**。弱词面分类不等于可靠NLI/科学验证或回答，所有verified始终False。

![关系分类对照与分母](results/v0.64.0/relation-probe.png)

349检查348pass/1权限skip，66runtime仅版本，默认SDK/UI/归档不改；0新模型API。
[协议](docs/RELATION-PROBE.md) · [详实报告](results/v0.64.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.64.0)。E3净收益/E4整体/回答/无限上下文未完成。

v0.64实际发行核验已完成：7base资产SHA、66Python+HTML与全部新旧源码、物理仓库外实际wheel/currentnative及actualsdist新旧功能、最终proof重下载通过。[最终证明](https://github.com/StarlitPupils/RKV-1/releases/download/v0.64.0/published-verification.json)，SHA78a6d1274da990f277e8c7e0d8fdb94644facfbd442343c64e95334757dfa8aa。原tag前报告的待办状态不回写。

## v0.63.0 · 冻结词语关联无重训跨语料迁移

旧SciFact关联与source/target模型3SHA不变，9fresh worker，ID/literal质量与时间分别验收；全部sourcebase/sidecar/target加载与历史训练成本计账。
**来源ID质量False / literal质量False / 时间False / 全联合False**。已见EntB目标，不称语义蕴含、回答或E4整体通过。

![跨语料来源覆盖与成本](results/v0.63.0/expansion-transfer.png)

340检查339pass/1权限skip；默认SDK/UI/归档不改，0新训练/模型API。
[协议](docs/EXPANSION-TRANSFER.md) · [详实报告](results/v0.63.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.63.0)。E3/E4整体/回答/无限上下文未完成。

## v0.62.0 · 训练问题字面相似度诊断

固定4/5 Jaccard，1诊断worker/298已有问题、188annotated/110null，独立整数交叉乘与2682既有proof核对；0新检索/训练/source范围绑定/模型API。
**H1至少一半正增益在近似训练问题组：False；H2非近似组仍有来源质量提升：True**。字面nonnear不是语义独立/无泄漏证明，v061质量/时间/联合结论不改。

![相似组与来源覆盖](results/v0.62.0/query-similarity.png)

335检查334pass/1权限skip；默认SDK/UI/归档不变，完整source/模型历史账本保留。
[协议](docs/QUERY-SIMILARITY.md) · [详实报告](results/v0.62.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.62.0)。E3净收益/E4整体/回答/无限上下文未完成。

## v0.61.0 · 训练集词语关联来源检索

来源质量通过、时间和联合未通过：完整证据139→142/188，macro recall .750443→.767730；查询约慢21.14%，新增完整sidecar609487B。331检查330pass/1权限跳过。
7实际资产SHA、递归66Python+HTML及新旧源码、物理仓库外actual wheel/currentnative/actualsdist新旧smoke和最终proof重下载均通过。

[详实报告](results/v0.61.0/SUMMARY.md) · [协议](docs/SUPERVISED-EXPANSION.md) · [实际发行核验证明](https://github.com/StarlitPupils/RKV-1/releases/download/v0.61.0/published-verification.json)。报告内“待发行”是tag前状态，实际完成证明为准；原实验结果不回写。E3净收益/E4整体/NLI/回答/无限上下文未完成。

## v0.60.0 · 同frame的Rust批量规范varint读取

27新鲜无profiler配对原byte/model一致，追加27Python/9actualnative decode审计通过；旧Python格式/变换不改，整个DLL/metadata/专用源码收费。
**H1相对typed Python加载时间：True；H2相对plain完整空间/加载联合：False**。C/B是实现时间，C/A才是完整活动路径；不把内核或已见索引结果当回答提升。

![同frame的原生实现时间与完整费用](results/v0.60.0/native-postings.png)

320检查319pass/1权限skip，CI Win/Linux native测试通过；66runtime仅版本、默认SDK/UI/归档不集成，0新模型API。被测DLL与current发行binary身份分开。
[协议](docs/NATIVE-POSTINGS.md) · [详实报告](results/v0.60.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.60.0)。E3净收益/E4整体/回答/无限上下文未完成。

## v0.59.0 · 索引加载观察器成本诊断

固定旧typed/LZMA frame，18新鲜OFF/ON配对全部原字节与model一致；9ON调用/时间守恒、9OFF计数null及追加18实际解码审计通过。
**H1观察器开销≤10%：False；H2 instrumented inverse+varint self-time占比每轮≥50%：False**。仅已见索引的工程诊断，instrumented占比不是未剖析CPU份额，尚无Rust提速结论。

![观察器开销与函数份额](results/v0.59.0/index-profile.png)

314检查313pass/1权限跳过；66runtime仅版本，原格式/变换/默认SDK/UI不变，0新模型API。v058主联合失败保留。
[协议](docs/INDEX-PROFILE.md) · [详实报告](results/v0.59.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.59.0)。E3净收益/E4整体/回答/无限上下文未完成。

## v0.58.0 · 可逆索引postings存储格式

RKVPOST1实验格式/CLI，原两个canonical词法/图索引及一个人工结构控制，72worker全部逐字节恢复、追加72实际frame审计通过。
预定typed/zstd空间/加载/联合均False；同codec和LZMA空间点完整保留，但加载明显更慢，不称综合推理收益。

![含恢复JSON与源码的完整活动路径](results/v0.58.0/index-frames.png)

typed/LZMA相对best plain/LZMA完整空间净少60122B和527350B；原模型不改，默认SDK/归档/UI不集成新frame。310检查309pass/1权限跳过，66runtime仅版本，0新模型API。
[格式/协议](docs/INDEX-FRAME.md) · [详实报告](results/v0.58.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.58.0)。E3旧净收益/E4整体/回答/无限上下文未完成。

## v0.57.0 · 最佳原句匹配重排整篇论文

原返回单位、12篇/4096原B不改，唯一新候选按abstract最佳句BM25分数排parent；旧paper词法/图基线不改，独立一次source索引SHA冻结后9worker。
**来源质量False / 时间False / 联合False**。sentence_max完整109/188、macro 0.588209，逐题损失/额外索引35012961B及全部CPU/RAM成本保留。

![最佳原句父论文排序](results/v0.57.0/sentence-parent.png)

已见dev探索性试验，不是未知数据/回答/压缩收益；298检查297通过/1权限跳过，66runtime仅版本，默认SDK/Memory/CLI/UI不集成新方法，0新模型API。
[协议](docs/SENTENCE-PARENT.md) · [详实报告](results/v0.57.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.57.0)。E3净收益/E4整体/真实长会话/回答/无限上下文未完成。

## v0.56.0 · 原整论文证据的容量上界诊断

原预算12篇/4096原B不改，1诊断worker/188唯一gold主张、209组，贪心/独立DP及总B可行性核对通过；0新科学试次/训练/源范围绑定。
H1失败主张至少半数gold本身放不下：**False**（9/49）；H2漏gold至少半数单篇>4096B：**False**（4/62）。

![原整论文容量诊断](results/v0.56.0/paper-capacity.png)

全知gold上界可完整179/188，实际graph仍139/188；oracle不是可部署检索或干预收益。289检查288通过/1权限跳过，66runtime仅版本，完整模型/历史训练/全部文件费用保留。
[协议](docs/PAPER-CAPACITY.md) · [详实报告](results/v0.56.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.56.0)。E3净收益/E4整体/真实长会话/回答/无限上下文未完成。

## v0.55.0 · 可调用的实验性论文证据API

新增wheel内PaperRetriever：显式SID/modelSHA、固定BM25/图/控制、最多12篇/4096原B，返回可核原文位置。默认Memory/CLI/UI不改，不生成答案。
3机制worker/894调用全部匹配原proof，2559原文绑定及独立追加2559/整源恢复通过；285检查284通过/1权限跳过。

![实验API一致性检查](results/v0.55.0/paper-api.png)

这是工程兼容性，不是新增科学质量或速度收益；v053时间/联合失败不变。66递归Python+HTML 426112B、完整模型10152832B及全部CPU/RAM/历史文件费用保留，0新模型API。
[协议](docs/PAPER-RETRIEVER-API.md) · [详实报告](results/v0.55.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.55.0)。E3净收益/E4整体/真实长会话/回答/无限上下文未完成。

## v0.54.0 · SciFact既有结果的漏证诊断

原v053结果/模型/4096原B预算不改，3诊断worker、894记录/627来源组；新科学试次/训练/源range绑定均0。
剩余byte预算拒绝占graph漏证至少一半：**True**（实际100.00%）；至少半数有gold主张的top6 seed能触图：**False**。

![漏证位置与图暴露](results/v0.54.0/paper-gap.png)

诊断不代表增加预算/补图后的实际收益；v053仅多1篇gold、时间及联合失败不变。277检查276通过/1权限跳过，65runtime仅版本，0新模型API。
[协议](docs/PAPER-GAP.md) · [详实报告](results/v0.54.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.54.0)。E3净收益/E4整体/真实长期会话/回答/无限上下文未完成。

## v0.53.0 · 已见SciFact整篇论文来源迁移

固定BM25/graph/control与12篇/4096原整行B，训练一次另冻模型SHA、9fresh worker；300原行/298实际检索/188有gold评分/110无gold/2训练重叠排除。
**论文来源质量True / 时间False / 联合False**：graph仅多找回1篇gold，完整找全仍139/188，query wall中位比1.007687。不是稳健、显著或回答收益。

![SciFact论文来源迁移](results/v0.53.0/scifact-graph.png)

7677原paper绑定/9整源恢复与proof/全树通过；273检查272通过/1权限跳过，65runtime仅版本，0新模型API。
已见benchmark来源定位不当未知数据验证/NLI/verdict/生成回答，E3净收益/E4整体/真实长会话/无限上下文未完成。

[冻结协议](docs/SCIFACT-GRAPH.md) · [详实报告](results/v0.53.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.53.0)。

## v0.52.0 · 已见漏证分解与gold-aware诊断上界

6诊断worker、1578旧题方法记录/6204源ID组排他分类和独立DP核验通过。前12字节排除占漏证多数假设False，graph dev/test比例0.000/0.000。

![已见漏证分解](results/v0.52.0/retrieval-gap.png)

oracle知道gold，仅为上界，不是可部署检索成绩。0新科学试次/训练/原source range绑定；旧v050/51成绩与literal负方向保持。
270检查269通过/1权限跳过，65runtime仅版本，0新模型API；E3净收益/E4整体/回答质量/真实长会话/无限上下文未完成。

[冻结协议](docs/RETRIEVAL-GAP.md) · [详实报告](results/v0.52.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.52.0)。

## v0.51.0 · 原模型封存官方test迁移

同一模型和固定算法/12facts/4096B不改、新训练0，9fresh worker原test340行/评分339/重叠排除1。
源ID质量True / 时间True / 联合True，36612原成员绑定/9整源恢复、proof/全树确定。

![同模型官方test复现](results/v0.51.0/question-test.png)

严格literal完整覆盖graph4题反而少于lexical6题；未解/改写/逐题负方向/全部费用保留，来源ID窄门槛通过不当NLI/整体证据或回答质量收益。
268检查267通过/1权限跳过，65runtime仅版本、默认不改，0新模型API，E3净收益/E4整体/真实长会话/无限上下文未完成。

[冻结协议](docs/QUESTION-TEST.md) · [详实报告](results/v0.51.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.51.0)。

## v0.50.0 · question-only封存开发集来源定位

训练一次→独立model SHA冻结→首次揭dev，固定BM25/训练共现graph/置换图3方法9worker。质量门槛True，时间门槛False，质量与时间联合False。
原187行/评分187行/重叠排除0，20196原成员绑定/9全源恢复与proof/全树通过。

![仅问题文本的证据定位](results/v0.50.0/question-retrieval.png)

固定12facts/4096原memberB，未解/UUID改写留ID+literal两口径；不是生成答案准确率或NLI/长期会话收益。
267检查266通过/1权限跳过，65runtime仅版本，0新模型API，私有原问题/科学源/模型图不发布，E3净收益/E4整体未验收。

[冻结协议](docs/QUESTION-RETRIEVAL.md) · [详实报告](results/v0.50.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.50.0)。

## v0.49.0 · 训练标注原始来源就绪审计

3fresh worker、17292重复叶检查/16533原成员绑定/3整源恢复通过；严格全可解/全literal两门槛均False。
单轮5764叶：3982 UUID+1529精确文本+253未解；2142 literal相等、3369 UUID绑定但改写，不能当语义证明。

![训练来源身份审计](results/v0.49.0/source-alignment.png)

已见训练输入的独立物理诊断，开发集仍封存，图/模型训练0、检索分数0。263检查262通过/1权限跳过；65runtime仅版本，0新模型API。
默认能力不改，E3净收益/E4整体/真实长会话/回答质量/无限上下文未完成。

[冻结协议](docs/SOURCE-ALIGNMENT.md) · [详实报告](results/v0.49.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.49.0)。

## v0.48.0 · 公共API固定1/3/32条科学记录成本

36fresh worker、1152bundle/13824原record绑定/36完整源恢复和9组proof/全部树一致。各size时间联合：1key: False / 3key: True / 32key: True。
base-only所有CAS计数相等，没有读取字节节省；低批量/CPU/parent/RSS反向和全部费用保留。

![公共批查询不同批量成本](results/v0.48.0/api-bundles.png)

公共lookup_many与原memory.py逐字等v047，默认不切换；原语料已见、3key组等旧v046，不称未知科学验证或回答提升。
260检查259通过/1权限跳过，65递归Python+HTML收费，0新模型API；E3净收益/E4整体/真实长会话/无限上下文未完成。

[冻结协议](docs/API-BUNDLES.md) · [详实报告](results/v0.48.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.48.0)。

## v0.47.0 · 可选公共批查询API

新增Memory.lookup_many：固定历史SID、1..32个已知来源key，原record逐次验证；入证字节预算默认1MiB，不是读取或RAM上限。
6fresh worker、126机械case=66返回/60预期预算拒绝，666原record绑定/36历史源恢复通过；259检查258通过/1权限跳过。

![公共批查询机械验收成本](results/v0.47.0/batch-api.png)

默认lookup/CLI/UI未改，无method patch或decoded块cache。预算拒绝前view仍可能读CAS，完整文件/65递归Python+HTML和CPU费用在报告。
本版没有提速对照，performance_gain_gate=null；不把v045/46旧assessment科学耗时外推新API。0新模型请求，E3净收益/E4整体/真实长会话/无限上下文未完成。

[接口和冻结协议](docs/BATCH-LOOKUP.md) · [详实报告](results/v0.47.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.47.0)。

## v0.46.0 · SciFact指定来源三键批查询迁移

24fresh worker、768bundle/2304绑定/24完整源恢复及6组proof/全树一致。base-only全部CAS计数相等控制：True/True；没有读取字节节省。
spread/repeated时间联合门槛：True/True，query wall中位比0.440/0.426；CPU/parent/RSS/源码和全部费用见报告。

![科学记录批查询成本](results/v0.46.0/science-bundles.png)

既有5183doc科学语料、SHA规则选128doc，非未知数据/开放检索/自然多跳/回答收益。原文和完整hit只留本地，public仅SHA/locator/计数。
255检查254通过/1跳过，默认不集成、旧QueryView逐字不改，0新模型API；E3净收益/E4整体/真实长会话/无限上下文未完成。

[冻结协议](docs/SCIENCE-BUNDLES.md) · [详实报告](results/v0.46.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.46.0)。

## v0.45.0 · 固定SID单trace视图复用候选

24fresh worker、2400proof/6840绑定/624历史源及6组完整树一致。分散工作量严格下降/同块相等控制联合True；
clustered/separated时间联合门槛True/True。
分散decoded少61.49%，meterOFF trace wall中位比0.608/0.402、parent完整wall0.922/0.659；RAM/源码/全部费用另列。

![视图复用工作量和时间](results/v0.45.0/view-paths.png)

请求开始完整验证一次视图，每selected record仍原SHA；**不承诺每hop重查未选中源/索引的中途篡改**，新请求重验。
仅assessment/v3/固定显式SID，不默认集成，无decoded块cache。253检查252通过/1跳过，64 runtime仅版本，0模型API。
既有合成机制非真实推理/长会话/回答收益，E3净收益/E4整体未验收，SSD物理/冷缓存/跨机未测。

[冻结协议](docs/QUERY-VIEW.md) · [详实报告](results/v0.45.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.45.0)。

## v0.44.0 · CAS角色归因：80%假设门槛True

两布局cacheOFF各3轮、6fresh worker，600proof/1710绑定/156历史文件及12795原block事件守恒，proof/完整树/计量等v0.43。
按manifest_validation/index_view/source_hit/other_trace排他归因，不跳校验；重仪表时间只报成本，不是优化速度验证。
分散布局3978次解码中3691次发生在index_view，直接目标读取仍287次；没有实施视图复用。

![CAS调用角色归因](results/v0.44.0/path-roles.png)

250检查249通过/1权限跳过，64 runtime只变版本，0模型API。v0.43两个时间联合失败仍保留；无默认集成。
已知合成显式链，非自然多跳/真实长会话/回答质量；E3净收益/E4整体未验收，SSD物理/全系统IO/冷缓存/跨机未测。

[协议](docs/PATH-ROLES.md) · [详实报告](results/v0.44.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.44.0)。

## v0.43.0 · 跨块布局控制：迁移工作量门槛True

同一原始行保留，两布局×cache×meter、24新worker，2400proof/6840绑定/624历史文件恢复及6组完整树一致性通过。
clustered工作量/时间联合：True/False；separated：True/False。
分散后解码量只少1.54%，查询wall中位反而+3.85%；两个布局时间联合失败，保留负结果。
固定65536B cap/4096B入证/3hop，不调参数、不默认集成；逐轮原值/RAM/全部文件与CPU/源码费用见报告。

![两布局成本比较](results/v0.43.0/layout-paths.png)

248检查247通过/1权限跳过；64 runtime只改版本。已知合成显式链，非真实多跳/推理或生产收益。
0模型API；物理SSD/全系统IO/冷缓存/跨机/真实长会话未测，E3净收益/E4整体未验收。

[冻结协议](docs/PATH-LAYOUT-CONTROL.md) · [详实报告](results/v0.43.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.43.0)。

## v0.42.0 · 单trace有界缓存：工作量门槛True，时间联合门槛True

完整2×2缓存/仪表、12新worker，1200 proof同v0.40；1152主问题/48控制/24负审计、3420绑定符合预期。
只在一次trace内复用已验证块，固定65536B payload，hit仍验raw SHA，每record绑定不变，退出清空。
meter OFF时间比率中位：wall 0.9619275063736824、CPU 1.0、parent 0.989782083766798。
meter ON只评应用CAS工作量，RAM/源码/observer与所有memory文件另收费；无默认集成。

![缓存工作量、无仪表时间和RSS](results/v0.42.0/cached-paths.png)

已见链集中同块的有利合成机制，不能推广为真实科学/推理收益。64 runtime只改版本，246测试245通过/1权限跳过。
0模型API，物理SSD/冷缓存/跨机/真实长会话未测，E3净收益/E4整体未验收。

[协议](docs/QUERY-BLOCK-CACHE.md) · [详实报告](results/v0.42.0/SUMMARY.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.42.0)。

## v0.41.0 · 补齐新批次进程计时，测到CAS读取/解码放大

同一已见E4合成fixture的OFF/ON六worker复测，600 proof与v0.40一致；576主问题/24控制/12负审计、1710绑定通过。
新增6份父测完整process wall，原v0.40漏项保持null，不回填。64 runtime除版本不变。
ON300 trace入证156426B，CAS应用read返回2444100B（15.62×）、解码56426496B（360.72×）；
4096B入证预算不约束CAS工作量，SSD物理/全系统IO仍未测。

![CAS应用流量和完整process计时](results/v0.41.0/path-traffic.png)

observer trace wall成对中位比率1.117、parent 1.033，开销/噪声照实保留。
所有memory文件SHA配对相等，每目录1171964B；评测sidecar/源码单列。243检查242通过/1权限跳过。
这次是成本仪表，不是新科学/推理收益；0模型API，冷缓存/跨机/真实QA未测。下一项先冻单trace有界块复用假设。

[协议](docs/PATH-TRAFFIC.md) · [详实报告](results/v0.41.0/SUMMARY.md) ·
[原始计量](results/v0.41.0/round-1-on-meter.json) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.41.0)。

## v0.40.0 · 三跳原证据路径机械通过，完整进程计时缺项

新增显式known-root/指定SID的合成引用路径，不改Archive/Memory默认。
288主问题状态/值/全路径符合预期：279完成、6缺证、3循环；另12控制、6篡改负审计符合预期。
855原record绑定、39完整历史源及HEAD/旧文件保持核验通过。不是开放检索/自然语言多跳或模型答案收益。

![指定快照证据路径与完整文件成本](results/v0.40.0/evidence-paths.png)

每轮最终memory1171964B，派生路径166682B；所有64模块+HTML及旧快照/索引费用单列。
协议要求的父测完整process wall漏记为null，**资源记录完整性false，整份协议未全满足**；原结果不覆盖。
4096B是入证record预算，物理IO/解压未仪表化，不能叫4096B读盘上限。下一版优先补仪表。
240本地检查239通过/1权限跳过，0模型API；E3净收益、E4整体/真实长会话/回答质量仍未验收。

[冻结协议](docs/EVIDENCE-PATHS.md) · [详实报告](results/v0.40.0/SUMMARY.md) ·
[资源缺项](results/v0.40.0/resource-completeness-audit.json) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.40.0)。

## v0.39.0 · 有界在线统计能恢复，科学净收益0/9

新增无需训练权重的显式order0/order1实验帧，旧61模块除版本号不改。
固定新[32768:40960]科学区段+噪声/循环控制，75对/150新codec阶段/150文件fsync全精确，25帧条件三轮SHA一致。
科学净B空间：order0 0/9、order1 0/9；联合分别0/9、0/9。
无权重文件不等于免费模型：状态逻辑516B/132612B，持久容器、RSS、CPU和完整源码都单列。

![在线统计完整成本](results/v0.39.0/online-counts-cost.png)

237测试236通过/1权限跳过；递归63模块+HTML，0新模型API。新段来自已见文件，不能称未知项目泛化。
默认不改；冷缓存/跨机/长期会话/多跳/模型回答收益未测或未证明。

[冻结协议](docs/ONLINE-COUNTS.md) · [详实报告](results/v0.39.0/SUMMARY.md) ·
[原始JSON](results/v0.39.0/round-1.json) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.39.0)。

## v0.38.0 · 编码器只多不到2位，压缩瓶颈在别处

冻结原模型/CDF/已见前缀，独立计算概率信息量并核对24个原帧：8条件L-I为0.25–1.72位，
全部通过预定[-1,4]工程门槛；3合成控制恢复、2 uniform解析golden通过。0新增科学编码/恢复。
相对普通codec的科学payload差距至少10892位，去掉不足2位冗余仍不改输赢；不追加同CDF空间优化。
这次是账本诊断，没有新增压缩或推理收益；神经/静态完整成本仍未胜普通压缩器。

![原帧码长审计](results/v0.38.0/cdf-information-audit.png)

233测试232通过/1权限跳过，递归61模块+HTML成本完整，发行仅版本号不同。
审计wall13.916s/CPU13.531s单列诊断成本，0模型调用，冷缓存/跨机/长期会话未测。
下一项先冻无外置训练权重的有界在线统计候选和新留出数据，不调这些已见前缀追收益。

[冻结协议](docs/CDF-INFORMATION-AUDIT.md) · [详实报告](results/v0.38.0/SUMMARY.md) ·
[原始aggregate](results/v0.38.0/aggregate.json) · [验证](results/v0.38.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.38.0)。

## v0.37.0 · 神经模型学到了规律，但完整费用未胜廉价统计

新增同训练资料的静态unigram+同算术码诊断。旧60模块除版本号字节不变，原神经模型
不重训、不改参数；先冻结静态520B模型（压缩203B）再评估已见前缀，不称新独立验证。

| 科学8192B前缀 | 神经payload B | 静态payload B | 神经净B总计 | 静态净B总计 |
|---|---:|---:|---:|---:|
| SciPy | 4734 | 4898 | 18358 | 14915 |
| SymPy | 4487 | 4721 | 18111 | 14738 |
| LaTeX | 5313 | 5504 | 18937 | 15521 |

神经payload **3/3更小**，但科学完整B成本 **0/3更小**，模型费用4878B对203B吃掉优势。
静态和神经对普通codec的科学净空间/联合都0/9，不把只胜神经当作实用压缩改善。
噪声中NN仅在专用源码B分配下小169B，完整帧反而大899B；整库C结论不同，反向案例照实保留。

![同资料诊断的payload、完整费用和CPU](results/v0.37.0/neural-unigram-diagnostic.png)

60恢复对/120新阶段进程/120文件fsync全精确，48个原v0.36条件帧SHA逐项复现。
230测试229通过/1权限跳过；新独立RKVUNI01只供显式诊断，旧NeuralFrame/主Archive拒绝，默认不变。
所有61模块+HTML递归账本；新静态模型只构建一次，原NN训练与NumPy费用单列历史，不重复训练/收费。
0模型API，冷缓存/跨机器未测；净收益、长期对话/多跳/无限上下文仍未验收。

[冻结协议](docs/NEURAL-UNIGRAM.md) · [详实报告](results/v0.37.0/SUMMARY.md) ·
[原始JSON](results/v0.37.0/round-1.json) · [验证](results/v0.37.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.37.0)。

## v0.36.0 · E3整数神经预测原型：精确恢复，净成本失败

新增小MLP、纯整数CDF/32bit算术编码和独立`RKVNN001`自包含实验帧；
运行时不需要NumPy或模型API。主Archive v1–v6/Memory/CAS和默认保持不变。
先冻代码/协议，再以95292B训练一次并提交量化模型SHA，最后才测3科学8192B前缀和噪声。

| 每对象8192B，完整帧 | Neural | Zlib6 | Zstd3 | LZMA6 |
|---|---:|---:|---:|---:|
| SciPy前缀 | 9746 | 3379 | 3506 | 3422 |
| SymPy前缀 | 9499 | 2911 | 3083 | 2962 |
| LaTeX前缀 | 10325 | 2526 | 2669 | 2562 |
| 固定噪声 | 14152 | 8337 | 8340 | 8386 |

科学净空间/联合**0/9**，噪声均0/3；科学神经位流本身在9/9比较已比普通payload更大。
每神经帧还实收4878B权重（原模型6944B），专用源码另计，不能靠免费模型或扩大N解释收益。
不集成当前候选，也不追加同表示的Rust/共享模型格式。这个小候选失败不代表所有神经方法失败。

![神经模型/位流/源码/CPU完整成本](results/v0.36.0/neural-small-cost.png)

48恢复对/96新进程/96文件fsync全部逐字节一致；227测试226通过/1权限跳过。
运行库60模块+HTML 402581B，专用分配与整份分配分开；训练NumPy安装52666902B、
训练/导入/依赖盘点CPU与RSS单列，编解码96进程均未导入NumPy或执行输入项目代码。
这是固定档案前缀/CPU可行性，非完整源文件、未知领域、生产压缩或模型回答收益。
E3有机械原型，净收益门槛未完成；长期对话/多跳/无限上下文仍未实现，0新增模型调用。

```python
# 未训练零权重的机械恢复示例；科学结果使用另行冻结的真实训练模型。
from rkv1.neural_small import model_bytes, PARAMETERS
from rkv1.neural_frame import encode, decode
raw = b'byte exact\r\n'
frame, info = encode(raw, model=model_bytes([0] * PARAMETERS))
assert decode(frame) == raw
```

训练只测试Python3.13/NumPy2.4.4；输入完整文件URL/SHA见docs/text-lanes-inputs.json。
按NEURAL-SMALL.md先训练并锁模型，再评估；跨机器训练复现、冷缓存/跨机性能未测。
下一项固定同训练资料的廉价unigram+同算术码诊断，分离条件预测与权重成本；
已有测试前缀不当新验证、不调参追正结果。

[冻结协议](docs/NEURAL-SMALL.md) · [详实报告](results/v0.36.0/SUMMARY.md) ·
[训练/模型冻结](results/v0.36.0/model-freeze.json) · [原始JSON](results/v0.36.0/round-1.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.36.0)。

## v0.35.0 · 固定边界硬退出后，一次恢复写入通过

运行库除版本号与v0.34逐字节相同。新增单writer固定Python hook进程实验：
7个硬退出点+1成功控制，3轮共24个新目录；21次os._exit(77)、3次正常返回。
**24/24原计划通过**，退出后HEAD符合原阶段、旧SID可读，一次epoch1恢复与一次epoch2更新成功。

192次完整源/locator审计、768条原文绑定、72次历史SID复查通过；
初始及退出时已存在的全部非HEAD文件SHA不变，不重试直到成功、不清理负结果。

![进程边界恢复及完整文件账本](results/v0.35.0/interruption-recovery.png)

实际残留也计费：HEAD临时文件fsync后、名称发布前退出，每轮留下94B，合计282B，
恢复不会自动回收。Memory.stats原分组不包含根目录其他临时文件，本实验用递归完整
文件账本对账，最终383915B对stats383821B；其他案例最终383821B。
这不是断电、任意指令时刻终止、多writer或生产恢复证明，没有推理质量收益结论。

223测试222通过/1权限跳过。0模型调用，冷缓存/跨机器未测。
下一项回到E3本地小型预测器+熵编码：先冻结确定性、训练/验证分离和完整权重/运行库/
训练及编解码成本，再研究是否有净收益；长期对话/多跳/无限上下文仍未完成。

[冻结协议](docs/MEMORY-INTERRUPTIONS.md) · [详实报告](results/v0.35.0/SUMMARY.md) ·
[原始JSON](results/v0.35.0/round-1.json) · [验证](results/v0.35.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.35.0)。

## v0.34.0 · Windows边写边读修正，本机原负载通过

读取HEAD时允许Windows共享删除/重命名；最终发布名称使用FileRenameInfoEx的
替换/POSIX语义。旧句柄继续读旧内容，新句柄读新内容；原字节/格式/预算/校验不变。
不支持该API的Windows文件系统回到原单次os.replace，不保证该降级路径的并发。
没有权限重试、缓存SID或放宽原文验证，所有其他Memory方法保持不变。

| 同一个冻结计划、各3新目录 | v0.33基线 | v0.34修正 |
|---|---:|---:|
|门槛通过|0/3|3/3|
|成功更新|141|240|
|完整审计查询|2689|5462|
|历史快照复查|144|243|
|观察到的worker/audit错误|6|0|

两版原driver/合成源/预算/超时逐字节相同，调度交错和实际操作数量不同，
不能据此声称吞吐或模型质量提升。新结果21848条原句/位置绑定、4341次add区间
重叠，全部历史保留；每轮80更新后Memory863971B。新增源码2856B，整体393969B。

![原计划下的失败与修正](results/v0.34.0/head-sharing-baseline-comparison.png)

完整套件222通过/1权限跳过，旧句柄/新句柄、关闭/不可继承和缺失/损坏边界实测。
v0.33源码账本漏计4子模块12842B，已按原标签/实际wheel追加更正，旧实验不改。
这是本机有界机械验证；生产并发、多writer、进程中断/断电、长期对话和推理收益尚未证明。
下一项固定提交边界的进程中断恢复；0新增模型调用，冷缓存/跨机器未测。

[修正协议](docs/MEMORY-HEAD-SHARING.md) · [详实报告](results/v0.34.0/SUMMARY.md) ·
[原始JSON](results/v0.34.0/round-1.json) · [验证](results/v0.34.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.34.0)。

## v0.33.0 · 边写边读发现 Windows HEAD 共享冲突

新增冻结的单writer/四reader合成机械实验，运行库除版本号外与v0.32相同。
3轮各计划80次更新、2048条记录；原预算、原默认，不重试失败操作。
**三轮均失败：成功提交80/48/13次，4次reader读HEAD异常，2次writer替换HEAD异常。**

2689次查询完成10756条原句/位置绑定，144个已提交历史快照复查通过，
1930次当前查询区间与实际add重叠。成功返回部分未见串版，但文件访问失败意味着
并发可用性未达标，不能把它称为支持生产并发。实际保留树含失败写入留下的对象。

![操作数量/重叠/写入时间/保留空间](results/v0.33.0/snapshot-concurrency.png)

完整套件219通过、1权限跳过；新增审计器主动拒绝损坏的来源/投影/SID/位置。
下一版优先修正Windows HEAD读取共享方式，定向句柄测试后同负载复测。
没有模型新调用，冷缓存/跨机器/断电未测；E3、多跳推理、长期对话收益仍未完成。

[冻结协议](docs/MEMORY-CONCURRENCY.md) · [详实报告](results/v0.33.0/SUMMARY.md) ·
[逐次原始JSON](results/v0.33.0/round-1.json) · [验证](results/v0.33.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.33.0)。

## v0.32.0 · 代码/数学词法字节通道的完整负结果

新增独立`RKVTEXT1`实验帧与四类ASCII词法字节通道：原始拼写、空白/注释/字符串/
换行/Unicode都保存，control记每token原顺序/长度，不执行代码或做语义规范化。
这不是主RKV归档v7；旧归档v1–v6、Memory/CAS及所有默认保持不变。

```python
from rkv1.text_frame import encode, decode
frame, info = encode(b'alpha = 1.00e-3\r\n', codec='zstd', mode='auto')
assert decode(frame) == b'alpha = 1.00e-3\r\n'
```

固定SciPy/SymPy/LaTeX2e各两份公开历史源文件(581292B)，另固定噪声负对照；
Zlib6/Zstd3/LZMA6，同完整帧比较plain/lanes/auto，不搜规则/级别或扩大对象数。

| 六科学文件共享专用源码一次 | plain总B | 强制lanes总B | auto总B |
|---|---:|---:|---:|
| Zlib | 157405 | 232204 | 159919 |
| Zstd | 167086 | 263084 | 169600 |
| LZMA | 141149 | 198907 | 143663 |

科学候选净空间0/36、联合0/36通过，噪声联合0/6。强制lane连不计源的帧也更大；
auto21/21条件都回退plain，帧与原样完全相同，仍付变换/两次codec和2514B候选源。
不能靠免费回退或扩大N声称收益，不做当前表示的Rust原生化/默认集成。

![同codec净成本](results/v0.32.0/text-lanes-net-cost.png)

189编码/恢复对、378全新阶段进程、378实际文件fsync，全部逐字节恢复及SHA相等，
三轮帧/选择/control账本一致，源/协议不变。217测试通过、1权限跳过、0模型调用。
对首次导入/预载、I/O/纯计算、字典/模型、专用源与全部57模块分配分别记账；
公共运行时未全额分配，不是完整部署成本或推理收益。冷缓存/跨机器未测。

下一项优先验证动态证据记忆的单writer/多reader快照一致性，作为机械正确性实验；
不把它当生产并发/长期对话/模型质量证明。E3神经预测仍需独立设计和完整模型成本。

[冻结格式/协议](docs/TEXT-LANES.md) · [详细实验报告](results/v0.32.0/SUMMARY.md) ·
[原始逐阶段JSON](results/v0.32.0/trials.json) · [验证](results/v0.32.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.32.0)。

## v0.31.0 · PubMedQA精确来源支持与冻结迁移边界

新增显式`*.pubmedqa.json`原始成员reader：原JSON不改写，精确保留成员范围/SHA，
仅`CONTEXTS`投影为证据。无独立文章标题时使用PMID元数据，问题/长答案/决策/
预测等字段不进FTS或模型上下文。支持历史及v4来源重绑定；新来源需v0.31 reader，
实际旧v0.30 lookup/search拒绝，原来源/Memory/CAS/归档格式及默认保持不变。

[官方PubMedQA](https://github.com/pubmedqa/pubmedqa) PQA-L原文件1000 PMID/1000
唯一问题，候选模块与v0.30逐字节相同、whole-paper搜索AST/STOP不变。这里将原本
给定context的任务改为1000篇池的自定义来源定位，**不是官方QA/答案准确率**。

| 精确目标PMID定位 | whole-paper | best-unit候选 |
|---|---:|---:|
| @1 | 957/1000 | 950/1000 |
| @5 | 984/1000 | 986/1000 |
| @10 | 990/1000 | 988/1000 |
| @20 | 994/1000 | 992/1000 |
| MRR@20 | 0.970238 | 0.965823 |

@5仅5赢/3输，净+2题，描述区间跨零；无稳健正迁移。候选额外1249639B，查询wall
中位10.855→14.712ms；计入总2152450→3402089B，原JSON2584787B。候选更大更慢，
保持显式、默认不换，不在这些gold上继续调权重/融合。公共运行时未全额分配。

![新来源检索与计入空间](results/v0.31.0/pubmedqa-transfer.png)
![配对差及描述区间](results/v0.31.0/pubmedqa-paired-delta.png)

三轮新进程、3000题对/6000读取、6预热排除，全部身份/分数稳定；1000成员范围与
投影独立核对、整文件恢复/持久树不变。209测试通过、1权限跳过、0模型调用；
QA正确率/证据覆盖、近重复/论文真正独立、冷缓存/跨机器仍未测。

此前“仓库外安装”表述已更正：v0.24–v0.30原烟测在仓库内隔离目标、外部cwd，
现已全部补做物理上的仓库外wheel/对应native安装，并在Release追加核验附件。
旧tag/观测保留。新发布继续使用真正外部目标，同Windows依赖，不称跨机器。

下一优先项回到E2代码/数学字节表示：先冻结可逆类型规则，计控制/字典/解码器
成本与同codec对照，不把语义等价重建当字节恢复。E3及真实推理仍需独立设计。

[冻结协议](docs/PUBMEDQA-TRANSFER.md) · [详细实验报告](results/v0.31.0/SUMMARY.md) ·
[原始轮次](results/v0.31.0/round0.json) · [验证](results/v0.31.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.31.0)。

## v0.30.0 · 段落先行检索的收益与迁移失败

新增显式`ParagraphIndex`：标题单独一行、每个原段落一行的contentless FTS5，按
每篇最佳单元BM25归并前20篇。不接收gold来源、不调权重/融合。辅助索引精确绑定
一个snapshot，逐查询验证整DB/Memory/原记录SHA和投影；源更新须显式重建或读旧
snapshot。原Memory格式及search/answer/CLI/HTTP默认保持不变。

```python
from rkv1.memory import Memory
from rkv1.memory_paragraph import ParagraphIndex
m = Memory('MEMORY')
index = ParagraphIndex.create(m, 'EXPLICIT-SIDECAR')['index']
result = index.search(m, 'scientific question', top_k=20)
```

| 全任务文档召回@5 | 整篇基线 | 最佳单元候选 | 结论 |
|---|---:|---:|---|
| QASPER dev · 1005题 | 44.279% | 45.871% | +1.592pp，论文区间跨零 |
| QASPER train · 2593题 | 39.028% | 41.998% | +2.970pp |
| SciFact dev · 188条有证据claim | 88.342% | 81.117% | −7.225pp |
| SciFact train · 505条有证据claim | 89.175% | 82.937% | −6.238pp，迁移失败 |

24KB lexical的QASPER完整参考dev260→284、train471→487，后者论文区间跨零。
这些是文档定位/参考暴露，非模型准确率；SciFact只评文档召回，不评证据句/答案。

![检索粒度与覆盖](results/v0.30.0/paragraph-retrieval.png)

QASPER dev/train额外aux 5742950/16855400B，查询wall中位24.90→50.44ms、
34.73→116.62ms；计源及aux总12191525/35931532B已大于原JSON，未达净压缩。
SciFact aux另9044318B。公共运行时未全额分配，不能称完整部署成本或同任务普遍
加速。**候选保持显式，默认不换，不因负结果调参重试。**

12轮新进程、12873问题对、25746读取、129528选句绑定；原基线逐题复现，原文/
持久树不变。204测试通过、1权限跳过，0远程模型调用。SciFact train是新增任务
评测，摘要语料此前已使用；非新独立语料或盲测。冷缓存/跨机器仍未测。

下一项将冻结规则迁移到新来源任务，先保证精确原始成员/标注隔离，并明确只测
自定义检索而非官方QA；不把现有任务收益外推，不自动混合分数或提供oracle来源。

[冻结协议](docs/PARAGRAPH-RETRIEVAL.md) · [详细实验报告](results/v0.30.0/SUMMARY.md) ·
[原始轮次示例](results/v0.30.0/qasper-dev-round0.json) · [验证](results/v0.30.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.30.0)。

## v0.29.0 · 来源已知与开放检索分开评测

新增显式Python `Memory.lookup(key, snapshot=...)`，只读取调用者已知的原证据key，
与search共用CAS/记录SHA及解析身份核验。支持v1–v4/历史/迁移/重绑定；未找到为空，
无检索回退，rank为null。现有memory-answer/CLI/HTTP与检索/选择默认保持不变。

```python
from rkv1.memory import Memory
result = Memory('MEMORY').lookup('qasper:already-known-paper-id')
```

沿用dev/train全量任务，三条件、两选择器、三预算、三轮新进程：10794问题对、
21588读取、194292原句绑定；open逐题keys/BM25/原文身份/全部覆盖分数复现v0.27。

| 24KB / lexical | open top5 | 调用者提供来源 | 仅保留已召回目标论文（oracle诊断） |
|---|---:|---:|---:|
| dev · 927非空参考题 | 260 | 764 | 352 |
| train · 2240非空参考题 | 471 | 1728 | 674 |

提供未召回来源解释dev/train额外412/1054成功，来源定位是当前主要瓶颈。
oracle用到目标身份，且移除其他论文同时改变预算竞争和词法IDF，不能算开放检索
算法收益。已知来源24KB仍有127/392题无全文映射参考、36/120题被预算遗漏。

![来源条件覆盖](results/v0.29.0/known-open-coverage.png)

已知来源8KB lexical相对原顺序净增26.11/25.40pp，但输60/154题；24KB dev论文组
区间仍跨零。不切换默认，不把覆盖当模型正确率。199测试通过、1权限跳过，原文/
持久树不变，0模型请求；冷缓存/跨机器未测。来源相同，属于任务分解而非新盲测。

下一项优先冻结一个不接收目标身份的开放检索候选，计入辅助索引、构建和查询
全部实际成本；不在现有gold上搜参数。Python/SQLite等共享运行时未全额分配。

[冻结协议](docs/KNOWN-SOURCE.md) · [详细实验报告](results/v0.29.0/SUMMARY.md) ·
[原始轮次示例](results/v0.29.0/dev-round0.json) · [验证](results/v0.29.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.29.0)。

## v0.28.0 · 显式上下文控制与完整请求体核验

Python/CLI/本机HTTP新增显式context selector与8000/24000/48000正文UTF8预算；
默认仍source-order/24000。因v0.27不同预算收益混合，不自动切换为lexical。
派生记录新增实际body/context JSON/完整POST字节与实际发送SHA，引用仍绑定原句。

```powershell
python -m rkv1 memory-answer MEMORY "claim" --context-selector lexical --context-body-budget 8000
```

HTTP先读/api/status，显式控制用`X-RKV-Client: memory-v2`；新服务拒绝v1携带
控制，旧服务拒绝v2 header，避免静默忽略新选择。原v1仅question/原页面默认兼容。
无效选择/预算不调用上游、不写答案；错误引用只写失败派生，不重试/降级/升格证据。

| 合成合同条件 | 实际body B | context JSON B | 实际完整POST B | 可见原句ID |
|---|---:|---:|---:|---|
| source-order / 8000 | 7990 | 8086 | 8793 | [0] |
| source-order / 24000 | 23980 | 24105 | 24818 | [0,1] |
| lexical / 8000 | 57 | 155 | 866 | [2] |
| lexical / 24000 | 8047 | 8174 | 8891 | [0,2] |

这是确定性合成fixture，不是科学QA/模型质量或语料压缩实验。13个正式本地HTTP
请求、0远程模型调用；旧24次预算未扩大。省略/显式原默认、实际旧发行默认POST
逐字节一致；CLI/HTTP/拒绝路径、原句ID/locator、body上限和raw POST len/SHA均核验。

![本地合同实际请求字节](results/v0.28.0/context-wire-bytes.png)

196测试运行、195通过、1权限跳过。原证据持久树与源逐字节不变，仅新增非primary
派生答案；Memory/CAS/归档格式无变化，HTTP能力版本新增2。原页面仍用默认控制。
全部53模块/HTML源一次计入，公共运行时未全额分配，不是完整部署成本。下一步
区分来源已知/开放检索工作负载，不以本地fixture回显当真实推理提升。

[协议及接口](docs/CONTEXT-API.md) · [详细实验报告](results/v0.28.0/SUMMARY.md) ·
[原始合同数据](results/v0.28.0/contract.json) · [验证](results/v0.28.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.28.0)。

## v0.27.0 · 同检索/同预算的词法证据选择

新增显式`context_selection.lexical_order/choose`：只对已检索top5论文的原段落
按问题做临时词法排序，保留原句ID/locator，预算仍只扣正文UTF8；不看gold来选句。
现有默认source-order不变。独立评分器逐字段核对所选上下文，拒绝伪造句子/定位。

| 数据/正文预算 | 原顺序完整参考 | lexical完整参考 | 赢/输 | 结论 |
|---|---:|---:|---:|---|
| dev 8KB | 107/927 | 179/927 | 108/36 | 覆盖提高7.77pp |
| train 8KB | 176/2240 | 305/2240 | 217/88 | 覆盖提高5.76pp |
| dev 24KB | 232/927 | 260/927 | 78/50 | 提高3.02pp，论文组区间跨零 |
| train 24KB | 445/2240 | 471/2240 | 162/136 | 提高1.16pp，论文组区间跨零 |
| dev 48KB | 295/927 | 307/927 | 54/42 | 仍有输题 |
| train 48KB | 570/2240 | 559/2240 | 104/115 | 净少11条成功 |

8KB两split论文组bootstrap描述区间为正；24KB区间均跨零，48KB train更差，且
lexical在train两对预算各出现1次真→假回归。排序中位约4.0/4.7ms，不能称全预算
支配或推理提升。**不替换默认**；下一版只做显式CLI/API选项与本地协议/引用核验。

![同检索同预算选择对照](results/v0.27.0/paired-context-selection.png)

固定dev281论文/1005题、train888论文/2593题，各三轮，共10794正式查询、64764
选择器/预算绑定核验、6预热排除。train用于新增任务迁移评测，原文曾做CAS存储，
不称新科学来源/官方test或盲测；两split论文ID无重叠，问句文本重叠58条。
dev基线逐题与v0.26的keys/BM25/来源身份及三预算分数全同；全部轮次/预算/原句
绑定一致，起止原文恢复与持久树不变。190测试通过、1权限跳过、0模型调用。

全部53模块/HTML源一次371171B，新selector模块2641B另列；临时FTS只在query中
存在，CPU/RSS收费，公共运行时未全额分配。紧凑context JSON不等于完整wire/token
成本，完整参考暴露不等于科学回答正确率。默认Memory/所有来源与存储格式不变。

[冻结协议](docs/CONTEXT-SELECTION.md) · [详细实验报告](results/v0.27.0/SUMMARY.md) ·
[配对差及区间](results/v0.27.0/derived-metrics.json) · [验证](results/v0.27.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.27.0)。

## v0.26.0 · 全dev科学检索与上下文证据覆盖

新增独立`qasper_audit`离线评分器，扩到固定QASPER v0.3 dev全量281篇/1005问题
实例（948种问题文本，比此前64题新增884种字符串）。原语料论文已使用，不算新
独立论文；qas/答案/标注不进FTS，不给检索目标论文或gold证据，0模型请求。

| 指标 | 结果 |
|---|---:|
| 目标论文召回@1 / @5 / @20 | 29.65% / 44.28% / 56.02% |
| 8KB正文预算完整参考可见 | 107/927 · 11.54% |
| 24KB正文预算完整参考可见 | 232/927 · 25.03% |
| 48KB正文预算完整参考可见 | 295/927 · 31.82% |
| 24KB已召回且文本可映射、但预算遗漏 | 134题 |

927题有非空可答参考，其中800题至少一整组可映射文本；图表/无法映射项仍在
分母。原QASPER任务给定论文，此处是281候选池定位和上下文诊断，不是官方
Answer/Evidence F1，也不是模型回答正确率。正文UTF8预算不含标题/ID/JSON；
24KB条件实际context JSON中位25689B。更大预算覆盖在本数据没有真→假回归，
不由合成反例推断实际发生。下一版同检索/同预算对照问题相关证据选择。

![全dev召回与上下文覆盖](results/v0.26.0/qasper-retrieval-coverage.png)

3015正式top20查询/3轮，keys、BM25、原记录身份SHA和覆盖分数全一致，3预热排除；
完整原文起止逐字节恢复、持久树不变。187测试通过、1权限跳过。top20检索wall
中位23.175ms，不与历史top5/top10算加速。实际Memory6065400B，全部52模块/HTML源
一次367366B，共计6432766B；公共运行时未全额计入，不是完整部署净压缩。

[冻结协议](docs/QASPER-COVERAGE.md) · [详细实验报告](results/v0.26.0/SUMMARY.md) ·
[全量原始指标](results/v0.26.0/trials.json) · [验证](results/v0.26.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.26.0)。

## v0.25.0 · 内容锚定段落预检与停止集成决策

独立JATS审计API新增显式`mode='content'`：父论文ID/角色/text SHA/重复序号构键，
分别保留完整父SHA与原range SHA，避免把派生文本当原文。已有position/xml-id及
默认输出与实际v0.24发行包的36个描述逐字段一致；旧v0.24明确拒绝新content模式。
Memory默认/来源kind/清单格式不改，仍不自动用片段。

| 记录规则 | 固定/v4 range乐观可过/12 | Gear/v4 range乐观可过/12 | 当前完整父校验可过/12 |
|---|---:|---:|---:|
| 整篇 | 0 | 0 | 0 |
| 位置段落 | 1 | 1 | 0 |
| 内容锚定段落 | 3 | 2 | 0 |

同批六篇18版本/12真实修订，内容键减少部分插入级联，但改写变成删除+插入操作，
完整父验证仍超预算，未压缩13状态定位候选达1631278B。
只有相邻状态必要条件，没有实际索引节省或查询加速。**暂缓片段Memory集成**，
不调高预算追求正结果；下一轮转向扩大离线科学检索任务与上下文覆盖评测。

![内容锚定必要条件对照](results/v0.25.0/content-anchor-preflight.png)

1854范围审计含两规则重复；9新进程162解析、144规划、26历史CAS快照核验；
183测试通过、1权限跳过。0新独立论文/科学QA/模型请求，现有API密钥不参与本轮。
全部51模块/HTML源一次、Gear整个精确库/元数据另计；定位候选仅部分账本，
未计FTS/Memory清单/公共运行时，不与旧完整系统体积算净压缩。仅本机温缓存。

[冻结协议](docs/JATS-ANCHORS.md) · [详细实验报告](results/v0.25.0/SUMMARY.md) ·
[逐转换计划](results/v0.25.0/plans.json) · [验证](results/v0.25.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.25.0)。

## v0.24.0 · 精确论文片段身份与预算预检

新增独立的`rkv1.jats_fragments`审计API：定位原始XML标题/摘要/正文p的连续字节，
绑定父论文ID/完整父SHA与range SHA；不重写XML，不把派生text冒充原文。修复外部
DTD未加载时跳过未解析实体的遗漏，改为拒绝。现有Memory默认/来源kind/格式不变。

复用v0.23六篇/18版本、12真实修订，1854次范围校验含两种键规则重复，927个版本内
投影单元均无元素id，xml-id全部回退位置。保留32变化/256KiB记录/2MiB CAS预算。

| 记录规则 | v3乐观下界可过/12 | v4乐观下界可过/12 | 当前完整父校验可过/12 |
|---|---:|---:|---:|
| 整篇 | 0 | 0 | 0 |
| 段落位置 | 0 | 1 | 0 |
| 优先元素id | 0 | 1 | 0 |

固定/Gear同计数；v4片段下界9次变化数、2次CAS字节超限。两种键规则解析18文件约
0.273/0.276s，whole为0.057s；13状态未压缩定位候选1114496B，对整篇20904B。
这只是相邻状态必要条件与部分候选账本，没有集成片段Memory、实际索引空间或查询
加速。完整父校验费用不能省略。下一轮先测内容锚定键与重复段落规则，避免位置级联。

![片段预算预检](results/v0.24.0/fragment-budget-preflight.png)

9新进程、162次文件解析，26历史CAS快照全源核验；181测试通过、1权限跳过，0模型/
新增独立论文/科学QA。全部51模块/HTML源一次、Gear整份旧实测库/元数据另计；公共
运行时/实际FTS未全额计入，不与v0.23系统体积算净压缩率。仅本机温缓存。

[冻结协议](docs/JATS-FRAGMENTS.md) · [详细实验报告](results/v0.24.0/SUMMARY.md) ·
[逐转换规划](results/v0.24.0/plans.json) · [验证](results/v0.24.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.24.0)。

## v0.23.0 · 独立真实论文正文修订基线

新增eLife JATS原始XML整文件证据定位，标题/普通摘要/正文段落只作检索投影；
完整原文、评审/图表等所有字节仍在CAS。内部实体声明与外部实体引用拒绝，外部
DTD不加载。新来源kind需v0.23，旧v0.22不能解码，归档/CAS/清单格式不变。

实现/协议于a58d640冻结。固定官方提交、内容查看前选定的前六篇三版本论文，
18文件、12次实际正文投影变化；不是正文相同的QASPER标注发布。逐篇v2再逐篇v3，
初始加12更新，共13快照。固定/Gear、三策略各三轮，全部历史保留。

| 条件 | 全部历史计入B | 总提交wall中位s | 基础索引数 |
|---|---:|---:|---:|
| 固定 重建 | 3556231 | 0.943 | 13 |
| 固定 预算v3 | 3556330 | 0.900 | 13 |
| 固定 投影v4 | 3663389 | 0.999 | 13 |
| Gear 重建 | 3645981 | 0.860 | 13 |
| Gear 预算v3 | 3646080 | 0.863 | 13 |
| Gear 投影v4 | 3753139 | 0.923 | 13 |

**整篇记录粒度没有获得增量索引收益。** 每次旧+新记录都超过256KiB，预算v3/v4
均因记录字节建立检查点；没有为获得收益调高门槛，v4指纹表还增加空间。
Gear CAS和原生依赖另计，不能把CAS复用当成v4索引收益。下轮研究更细证据粒度。

![真实正文修订整篇基线](results/v0.23.0/revision-costs.png)

4212正式/936历史身份查询全部匹配重建排序、BM25和精确当前来源；234历史实例
全源核验、234阴性控制通过。同表示CAS树一致，查询不改持久树。177测试通过、
1权限跳过，0模型调用/新增科学QA。18自动诊断词项非人工gold题，六篇非大样本。
全部50模块/HTML计一次、Gear另计整份旧实测库/元数据；公共运行时未全额分配。
默认继续预算v3，v4显式。仅本机温缓存；E3、多跳、长期对话等仍未验证。

[协议及输入](docs/PAPER-REVISIONS.md) · [全矩阵](results/v0.23.0/SUMMARY.md) ·
[核验](results/v0.23.0/validation.json) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.23.0)。

## v0.22.0 · 降低v4查询定位准备成本

v4查询批量核对全部重绑定，仅在命中时替换当前locator；纯定位/位移overlay直接
查询只读基础，不再复制SQLite。有FTS删除/upsert仍复制并完整重放；完整基础/
overlay/源树、CAS原字节、原记录与投影SHA校验保留，非命中重绑定也全部核对。
不加跨查询缓存，writer/格式/默认策略不改，v4继续显式选择。

实现/协议于659c354冻结。复用v0.21六个完整保留库、15状态，实际已发布v0.21
读取器、批量但强制复制消融、当前直接读取、当前v3参考各三轮。同轮查询结果：

| 官方发布组/阶段 | 旧v4中位/p95 | 当前v4中位/p95 | 配对加速 | 同轮v3中位 |
|---|---:|---:|---:|---:|
| 固定64KiB，v0.2 | 23.37/25.45ms | 19.41/21.37ms | 1.200× | 12.40ms |
| 固定64KiB，v0.3 | 23.24/25.57ms | 19.54/21.83ms | 1.200× | 12.42ms |
| Gear64KiB，v0.2 | 24.64/27.08ms | 20.68/23.06ms | 1.189× | 14.18ms |
| Gear64KiB，v0.3 | 24.64/27.29ms | 20.60/23.13ms | 1.177× | 13.94ms |

末版新进程峰值固定41.10→35.55MiB、Gear41.06→35.80MiB；只是同轮完整进程
峰值，不是查询增量RAM。批量消融约1.02倍，免复制在此基础上再配对快1.15–1.17倍。
初始/单条标注无稳定收益，小合成基础的免复制也无额外稳定收益；**v4仍慢于v3，
默认继续预算v3。** 混合FTS变化仍复制，不能由纯定位收益推导所有更新更快。

![保留库上的查询准备消融](results/v0.22.0/projection-query-costs.png)

6336正式查询、720历史完整身份查询均匹配实际v0.21及原发布记录的排序、BM25和
精确当前来源。108未来探针阴性，30历史快照实例全源核验，180新进程前后整库
逐文件大小/SHA不变；6个原库完全不改。174测试通过、1项权限跳过，0模型调用/
新科学问题。官方正文相同，合成控制非真实正文修订；仅本机温缓存。

无新增持久索引/压缩收益或提交性能结论。全部49个Python模块/HTML分配
352222→353491B，增加1269B一次；Gear保留原生成库/元数据124419B，查询不加载
原生模块。公共运行时/pyc/安装/文件系统元数据未全额分配，不称完整部署净压缩。
worker使用相同小问题输入，不与v0.21历史RSS直接相除。旧v0.21仍可读写同格式v4，
旧v0.20拒绝v4，旧记忆v1–v3及归档v1–v6/CAS1兼容，无迁移。

下一步转向独立真实论文正文修订，继续记录精确来源、索引空间与读取代价。E3、
长期对话、多跳、冷缓存/跨机器、并发/掉电及GC仍待验证，新问答需另定API预算。

[冻结协议/复现](docs/PROJECTION-QUERIES.md) · [全矩阵](results/v0.22.0/SUMMARY.md) ·
[核验](results/v0.22.0/validation.json) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.22.0)。

## v0.21.0 · 分离论文文本与精确字节定位

新增显式候选 compact-projection-v4：论文title/abstract/full_text段落指纹与当前
原始成员定位分开。仅路径、标注、JSON排版改变时保留FTS，更新当前SID/原路径/
偏移/长度/原SHA；正文变化仍完整重放。每个命中验证当前原文与完整论文投影SHA。
所有原始字段/全部历史保留；归档v1–v6/CAS1不变，新应用清单v4需v0.21读取器。

实现/协议于419b6b8冻结；三策略、三组、各三轮。QASPER官方dev原始三次发布
每版281论文、正文投影相同，复用既有64问题；固定/Gear单列，非真实论文正文修订。

| 官方发布组，全部历史 | v0.20预算v3 | 投影v4候选 |
|---|---:|---:|
| Gear：最终计入空间 | 15.718 MB | **9.441 MB，省39.94%** |
| 固定64KiB：最终计入空间 | 18.129 MB | **11.851 MB，省34.63%** |
| Gear：末版查询中位/p95 | **13.79 / 16.14ms** | 24.17 / 26.92ms |
| 固定：末版查询中位/p95 | **12.29 / 13.87ms** | 22.90 / 27.32ms |
| Gear：三次提交wall总中位 | 1.716s | 1.635s |
| 固定：三次提交wall总中位 | 2.168s | 2.114s |

每版新写索引由3182592B变成约27000B定位overlay，但首份基础多32768B指纹表；
真实组三份完整基础减至一份。空间收益明确，查询准备变慢；小幅提交差异不证明
普遍提速。**默认继续compact-budget-v3；v4显式选择，不迁移现有库。**

![空间收益与查询代价](results/v0.21.0/projection-costs.png)

160篇合成论文9状态另测标注/改名/重排、正文增删、33篇标题改写、恢复和label别名。
v4在0/5/6建基础，预算v3建5份；最终计入685095B/709315B。正文变化不被当作标注
跳过，三预算/25%/256位移规则保留，重绑定另限4096条；并非所有控制阶段更快。

4752正式、540历史完整身份查询均匹配重建的排序/BM25/精确来源；135历史快照
实例全源核验，81未来探针阴性。同表示CAS树一致，查询不改持久树。170项测试
通过，1项Windows权限跳过；0新增科学问题或模型调用，仅本机温缓存。

成本含全部49个RKV Python模块/HTML共352222B一次，Gear另计整个实测库/元数据
124419B；公共运行时未全额分配，非完整部署净压缩。不与旧版不同成本口径混比。
旧v0.20读取器拒绝v4，v1/v2/v3继续兼容。新库显式启用候选：

```powershell
python -m rkv1 memory-init path/to/new-memory path/to/evidence --index-profile compact-projection-v4
```

下一步优先减少v4查询定位准备，再补独立真实论文正文修订。E3、长期对话、多跳、
冷缓存/跨机器、并发/掉电、GC仍未验证，新问答实验需另定API预算。

[冻结协议/复现](docs/MEMORY-PROJECTION.md) · [全矩阵](results/v0.21.0/SUMMARY.md) ·
[核验](results/v0.21.0/validation.json) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.21.0)。

## v0.20.0 · 为增量索引增加回放预算

新建记忆库默认 compact-budget-v3：相对基础的累计变化最多32条、重放原记录
最多256KiB、逐次CAS解码工作最多2MiB，超过任一项则建立完整索引检查点。
保留既有25%变化/256位移区间门槛；原文、全部历史和全部校验继续保留。
预算约束重放工作量，不能保证总查询时延或RSS上限。

实现与协议于7df94f7冻结。四组合成控制×四策略×三轮，包含上一版100更新原样
回归、默认固定分块复测，以及大记录/大分块定向控制。同轮同源码对照：

| 场景 | 旧策略查询中位/p95 | 新三预算查询中位/p95 |
|---|---:|---:|
| 固定64KiB，第42次更新 | 534.47 / 684.67ms | **2.36 / 8.18ms** |
| Gear64KiB，第42次更新 | 589.44 / 780.32ms | **2.19 / 9.03ms** |
| 大记录，第2次更新 | 11.14 / 21.66ms | 2.61 / 13.49ms |
| 固定1MiB，第2次更新 | 29.77 / 66.21ms | 7.91 / 45.90ms |

第42次更新提前检查点，保留全部101个状态的Gear总计成本由旧策略9.162MB变为
9.140MB（完整重建83.739MB），检查点从0/43/80变为0/42/80，数量仍为3。
大记录/大分块组则各从1个基础增至3个：总计成本1.159→2.461MB、5.620→10.977MB。
这是读写与空间取舍；第43/79次更新新策略约5ms、旧策略约2–3ms，不能称处处更快。

![回放预算与检查点附近的查询](results/v0.20.0/replay-costs.png)

4032正式查询、10176历史身份查询均匹配完整重建的排序、BM25和精确来源；2544
历史快照实例全源核验通过，2544未来探针阴性。同表示CAS树一致，查询不改持久树。
164项测试通过、1项Windows权限跳过。0次新模型调用，0条新增科学问题；这些是
合成定向控制与已见回归，本机温缓存，不能推出新科学推理质量或真实修订泛化收益。

成本统一计入全部48个RKV Python模块及HTML一次，Gear另计完整实测DLL/元数据
124419B；公共运行时未全额分配，不是完整部署占用。口径与v0.19不同，不跨版算
压缩提升。物理归档v1–v6、CAS1、记忆清单v1–v3不变；v0.19能读新v3视图，但其
writer拒绝新策略。旧库不自动切换，显式启用只影响未来新建视图：

```powershell
python -m rkv1 memory-budget path/to/existing-v3-memory
```

该命令不改HEAD、不修复旧慢快照；复用同一输入/标签仍返回原视图。新库可显式
`--index-profile compact-base-v3` 保留旧策略。QASPER路径/标注耦合仍待修正；冷缓存、
跨机器、并发/掉电、E3、长期对话和多跳验证仍未完成。

[冻结协议/复现](docs/REPLAY-BUDGET.md) · [全矩阵](results/v0.20.0/SUMMARY.md) ·
[核验](results/v0.20.0/validation.json) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.20.0)。

## v0.19.0 · 原始QASPER与100更新边界

新增QASPER原始JSON成员字节定位，只索引论文title/abstract/full_text，不索引问答
标注。原文件名、空白/转义/全部原字段仍在CAS原样保存。单个成员可独立恢复ID与
原文SHA；未知模式、重复key、截断拒绝。新来源kind需v0.19；旧文本/SciFact兼容，
归档v1–v6、CAS1与记忆v1-v3物理格式不变。

**本轮发现明确限制：真实发布未获增量空间收益；25%门槛前可出现严重查询退化。**
实现/协议于26a8e89冻结。三轮对照都用同Gear/Rust提交，隔离完整重建与v3增量；
默认仍固定/v3，本轮不代表默认固定提交性能。全部原文/历史保留，无GC。

| 实验组 | 完整重建计入成本 | v3增量计入成本 | 全部提交wall中位，重建/增量 |
|---|---:|---:|---:|
| QASPER官方dev三次发布 | 15.40 MB | **15.40 MB** | 1.689 / 1.704s |
| 2048合成记录，初始＋100更新 | 83.43 MB | **8.86 MB，省89.38%** | 6.239 / 5.372s |

真实组每版281篇，正文投影相同，原成员改变281/9条；保留版本化文件名后，每次
均完整建索引。它验证真实数据集发布，不代表论文正文修订。三版各保留一个索引，
v3未有空间优势。控制组仅在初始/更新43/80写完整基础，其余保留累计差异。

| 合成控制位置 | 完整重建查询中位/p95 | v3增量查询中位/p95 |
|---|---:|---:|
| 更新42：512变化，恰为25% | 2.10 / 7.88ms | **462.80 / 478.63ms** |
| 更新43：513变化，检查点 | 2.03 / 7.32ms | 2.11 / 7.87ms |
| 更新80：260区间超256，检查点 | 2.17 / 8.28ms | 2.11 / 7.85ms |
| 更新100：小幅差异 | 2.16 / 7.72ms | 5.62 / 10.50ms |

![长历史空间和检查点邻近查询](results/v0.19.0/history-costs.png)

固定记录占比门槛不能约束实际重放耗时。空间/提交收益不等于读多负载收益，下一步
优先修正检查点代价策略，并分离论文投影变化与原始路径/标注变化，再扩论文真修订。

1800正式查询、2496完整身份历史查询均匹配完整重建；606未来词项探针阴性，624
历史快照全源大小/SHA重读一致，同表示CAS树逐字节相同，查询不改持久文件。
新增64个QASPER问题，其来源论文@5为22/64，仅为全局检索诊断；原任务给定论文，
不与SciFact召回或答案质量混比。控制问题非科学样本；**0次模型调用**。

统一计四份完整源36,033B＋整个实测DLL/元数据124,419B一次；公共运行时未全额分配，
不是完整部署净压缩。本机温缓存；158测试通过、1项Windows权限跳过。无E3、长期
对话、多跳、冷缓存/跨机器、并发/掉电或GC结论。Release保留精确实测库，与CI新库区分。

[冻结协议/复现](docs/MEMORY-HISTORY.md) · [全矩阵](results/v0.19.0/SUMMARY.md) ·
[核验](results/v0.19.0/validation.json) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.19.0)。

## v0.18.0 · 减少查询重复准备与定位重放

每次查询只打开/验证一次各个不同CAS快照与overlay，结束全部释放。v3仍完整重放
FTS改写并使用全库BM25，先检查所有位移范围计数、非负与不重复，再只换算命中的
未改写记录位置。完整基础索引/overlay SHA、每次CAS stored/raw及原记录SHA保留；
没有跨查询缓存或校验跳过。仍复制基础SQLite视图，不称消除全部准备工作。

实现/协议于4926af6冻结。固定/Gear两种现有v3存储、五阶段、三计划各三轮，
90个新进程完成**17,190次正式查询**。每阶段全部188条标注主张＋3探针的排序、
BM25和完整来源身份匹配实际v0.17发布模块。22个历史快照全源重读核验，两组持久
树每个文件大小/SHA完全不变。0次新模型调用，不是新推理质量结果。

| 同轮阶段 | v0.17中位 / p95 | v0.18中位 / p95 | 逐问题配对加速中位 |
|---|---:|---:|---:|
| 固定，原始 | 15.36 / 19.03ms | 13.78 / 17.50ms | 1.122× |
| 固定，追加 | 22.28 / 26.14ms | 18.80 / 22.29ms | 1.195× |
| 固定，13B插入 | 33.72 / 44.32ms | **22.04 / 30.03ms** | **1.543×** |
| 固定，最终 | 33.31 / 37.44ms | 21.08 / 24.84ms | 1.586× |
| Gear，13B插入 | 33.55 / 38.23ms | **22.26 / 26.38ms** | **1.515×** |
| Gear，最终 | 33.95 / 38.43ms | 22.48 / 27.87ms | 1.516× |

只复用资源消融在13B插入阶段为25.94/26.70ms（固定/Gear）；延后定位在此基础上
再配对快1.197/1.199×。无位移阶段无额外定位收益，部分中位略慢于消融。进程峰值
RSS约39–50MiB，无全面下降结论。wall含整个search及清理，启动另列；本机温缓存。

![查询成本对照](results/v0.18.0/query-costs.png)

无新持久索引/压缩收益或提交时序结论。两份完整专用源25,552→29,353B，增加
3,801B一次；公共Store/core/Python/SQLite/OS未全额分配。查询不加载Rust库。
记忆v1/v2/v3、归档v1–v6/CAS1兼容；默认固定/v3、Gear/Rust提交仍显式选择。
154项测试通过，1项Windows权限跳过。无格式迁移、GC、长期对话、多跳、E3或新
问答质量结论。主张仍188条，重复计时不增加科学样本量，不跨历史批次直接算加速。

[冻结协议/复现](docs/MEMORY-QUERIES.md) · [全矩阵与原始记录](results/v0.18.0/SUMMARY.md) ·
[核验](results/v0.18.0/validation.json) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.18.0)。
本机检索演示：http://127.0.0.1:8768 ，25条既有派生记录逐字节保留，未配置模型。
下一步扩真实版本/更长历史与基础索引成本；新问答评测需另定API预算。

## v0.17.0 · 降低短插入与连续版本的重写放大

新v3应用索引用单份基础相对差异与偏移区间表示每个快照，未改写记录仅更新位置，
不再因为整批偏移变化重建索引。复用已有Gear-v1和可选Rust扫描，分别对照CAS复用
与索引更新。新建库默认固定分块＋v3；Gear/Rust显式选择，既有库不自动迁移。

5条件×3轮、每组11个连续快照，包含追加、等长改写、短插入/撤销、删除。全部
原文/历史/索引保留，**8,070次正式查询＋1,815次旧快照查询**的排序及来源身份
匹配固定/v2；165个历史快照最终重开核对整源SHA/大小。初始188条主张排名保持
v0.16水平，无新模型调用，不作新科学推理质量结论。

| 条件 | 11快照＋源码/原生分配 | 对固定/v2净省 | 11次提交总wall中位 |
|---|---:|---:|---:|
| 固定/v2 | 39.29 MB | — | 6.923s |
| Gear Python/v2 | 30.47 MB | 22.45% | 24.563s |
| 固定/v3 | 17.47 MB | 55.53% | 5.569s |
| Gear Python/v3 | 8.65 MB | 77.98% | 23.142s |
| Gear Rust/v3 | **8.78 MB** | **77.66%** | **4.097s** |

统一计整份memory.py/memory_index.py/chunking.py源28,756B一次，Rust另计完整实测
DLL＋元数据124,419B；公共Python/SQLite/Store/core/OS、文件系统元数据未全额分配。
不是完整部署净压缩，也不与v0.16不同阶段/回答账本直接算版本提升。

![多版本更新成本](results/v0.17.0/update-costs.png)

13B插入时，固定分块新增127个CAS对象，Gear仅1个；v2新写5,455,872B索引，v3
只需387B（固定）/385B（Gear）差异。11快照中v2完整建基础索引5次，v3仅初始1次。
Python/Rust Gear的整个持久树逐阶段逐字节一致；Rust只加速扫描，不加速查询。

查询有代价：13B插入后固定/v2中位/p95为16.37/20.83ms，Gear Rust/v3为
36.70/44.73ms；新查询进程峰值36.21→40.21MiB。位置重放使v3查询更慢，不称
全流程支配；Python Gear提交也明显更慢。仅本机温缓存，启动时间另列。

本机149测试：148通过、1项Windows权限跳过。新v3清单需v0.17；旧v1/v2继续原
策略，归档v1–v6/CAS1不变。累计非位置改动超过25%或偏移区间超过256仍建检查点，
无自动迁移或GC，不声称任意更新恒定成本。E3、长期对话、多跳/形式验证仍未实现。

```powershell
python -m pip install -e .
python -m rkv1 memory-init data/new-memory data/memory-source
# 可选Gear；每次Rust提交都显式指定已核验库和相邻native.json。
python -m rkv1 memory-init data/gear-memory data/memory-source --chunker gear-v1 --chunker-backend rust --native-library measured/rkv1_core.dll
python -m rkv1 memory-add data/gear-memory data/updated-source --chunker-backend rust --native-library measured/rkv1_core.dll
```

[冻结协议/复现](docs/MEMORY-UPDATES.md) · [全部成本与原始记录](results/v0.17.0/SUMMARY.md) ·
[核验](results/v0.17.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.17.0)。
Release另附**实际参与测量的旧Gear库及原始元数据**，区别于本次CI新编译的原生库。
下一步剖析查询定位重放，扩真实更新家族与更长历史；新问答评测需另定API预算。

## 记忆索引成本对照（v0.16.0）

新建库使用紧凑FTS5基础索引与增量重放：去掉索引中的正文副本，小幅更新复用基础
索引；每次查询核验完整基础/增量SHA，在内存中重放当前完整视图，再用SQLite全库
BM25排序。命中仍回CAS读精确原记录，保留所有旧快照和旧索引，不删除历史。

三策略×三轮，**4,275次正式查询＋1,764次旧快照检查**的排序与来源身份全部匹配
旧完整索引，BM25误差<=1e-10。初始188条主张排名与v0.15一致，gold文档召回@5仍
**88.34%**。本轮**0次模型生成**；已有模型请求SHA/响应引用的离线重放不算新推理结果。

| 同轮同来源成本 | 旧完整索引 | 紧凑完整索引，计专用源 | 紧凑增量，计专用源 | 增量相对旧策略净省 |
|---|---:|---:|---:|---:|
| 初始一快照 | 19.32 MB | 8.43 MB | 8.43 MB | 56.36% |
| 追加88B，保留两快照 | 35.69 MB | 13.90 MB | **8.44 MB** | **76.34%** |
| 定位大幅变化，保留三快照 | 55.01 MB | 22.32 MB | 16.86 MB | 69.34% |
| 删除控制，保留四快照 | 74.32 MB | 30.73 MB | 25.28 MB | 65.99% |

一份索引从16,355,328B降至5,455,872B；88B追加只新写**234B**索引增量。仍全量
读取/哈希提交来源。超过25%记录定位改变或已有8层增量时完整建紧凑检查点，旧文件
全部保留。改写/删除是合成机制控制，不代表新科学数据或推理提升。

![索引成本对照](results/v0.16.0/index-costs.png)

追加场景查询中位/p95：旧索引37.09/54.46ms，紧凑完整16.82/24.55ms，紧凑增量
25.61/36.37ms。增量相对旧策略配对加速中位1.393倍，但比紧凑完整更慢；查询进程
峰值RSS分别48.35/38.01/46.76MiB（含解释器/加载）。增量完整提交中位298.37ms，
旧策略666.44ms。空间、速度、内存分别衡量，不称全流程支配；本机温缓存。

计入整个memory_index.py源10,731B一次后，初始库仍为原文8.31MB的**1.015倍**。
公共Python/SQLite/core、文件系统元数据未全额分配，尚无整个记忆系统净压缩结论。
本轮没有回答写回，不能直接用v0.15含回答的35.73MB计算配对节省。

本机141项测试：140通过、1项Windows权限跳过。归档v1–v6/CAS1不变；旧v1记忆库
继续原策略，新v2应用清单需v0.16读取器，v0.15拒绝新清单。无自动迁移或GC。

```powershell
python -m pip install -e .
python -m rkv1 memory-init data/new-memory data/memory-source
python -m rkv1 memory-search data/new-memory "rare genetic variants"
python -m rkv1 memory-add data/new-memory data/updated-source --label revision-2
python -m rkv1 memory-serve data/new-memory
```

模型仍按本机RKV_LLM_BASE_URL/MODEL/API_KEY配置，未配置时仅检索，密钥不写仓库。
[冻结协议](docs/MEMORY-INDEX.md) · [全部时序/资源与结果](results/v0.16.0/SUMMARY.md) ·
[核验](results/v0.16.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.16.0)。
下一步压低单份索引/定位元数据，扩大更新负载和独立问题评测，再测长会话；
E3神经压缩、多跳及形式化验证仍未实施。新增模型评测需另定调用预算。

## 首个证据记忆与模型回答（v0.15.0）

已打通原始资料CAS保存 → SQLite FTS5/BM25检索 → 原记录SHA校验 → 模型判断 →
句子引用绑定 → 派生回答写回。新增CLI与本机中文演示页，支持资料更新及读取旧快照。
这是E4最小基线；E2尚未完成，E3神经压缩尚未实施，不宣称无限上下文。

SciFact 5,183篇摘要（8,307,875B）逐字节保存，索引不含主张/gold标签。188条有标注
主张三轮共564次查询，重复轮次不是独立样本。gold文档宏平均召回@1/@5/@10分别
**70.70% / 88.34% / 94.21%**；含索引和CAS校验的本机温缓存检索中位43.58ms、p95
57.47ms。冷缓存、跨机器未测，词法基线不代表跨语言语义检索。

| 同一个证据约束模型，两种输入 | 格式/引用绑定有效 | 标注判定正确 | 8条有证据主张判定与完整依据同时正确 |
|---|---:|---:|---:|
| 空证据 | 12/12 | 4/12 | 0/8 |
| top5检索证据 | 12/12 | **10/12** | **6/8** |

真实DeepSeek `deepseek-flash` 官方API共24次生成，12条预定平衡dev主张每条件一次，
关闭thinking、JSON模式、最多256输出token，无重试。资料/检索本机CPU，模型远程。
空证据仍被要求仅据所给证据回答，不是无约束闭卷或成熟RAG对照；公开dev小样本、
模型可能见过数据，不据此宣称通用推理提升。引用绑定不证明科学蕴含。两条错误的
完整gold依据都已提供，失败在模型判断/引用选择，原始记录全部保留。

![首个证据记忆基线](results/v0.15.0/memory-baseline.png)

资源成本尚未达标：初始库加一个完整索引为**19,319,447B，原文2.325倍**；保留两个
索引快照和派生记录后**35,728,598B，原文4.301倍**，索引占32,710,656B。不能称整个
记忆系统净压缩；公共运行时、文件系统元数据和远程模型成本未完整分配。服务报告
输入30,634、输出1,029token，实际账单未知。派生回答不会自升格为原始证据。

本机132项测试：131通过、1项Windows权限跳过。旧归档v1–v6/CAS1保持兼容。

```powershell
python -m pip install -e .
python -m rkv1 fetch data/scifact --dataset scifact
New-Item -ItemType Directory -Force data/memory-source
Copy-Item data/scifact/corpus.jsonl data/memory-source/corpus.jsonl
python -m rkv1 memory-init data/my-memory data/memory-source
python -m rkv1 memory-search data/my-memory "rare genetic variants"
$env:RKV_LLM_BASE_URL="https://api.deepseek.com"
$env:RKV_LLM_MODEL="deepseek-flash"
# RKV_LLM_API_KEY只在本机环境配置；未配置模型时页面仅检索。
python -m rkv1 memory-serve data/my-memory
```

浏览器打开 http://127.0.0.1:8765 。手动回答每次会调用API，正式评测不会自动重跑。
`memory-add`的source为完整新版资料树，旧快照仍保留；当前每快照一份完整索引。

[协议/执行说明](docs/MEMORY.md) · [原始结果与失败分析](results/v0.15.0/SUMMARY.md) ·
[独立核验](results/v0.15.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.15.0)。
下一步优先扩大独立问题、诊断弃答/引用选择和检索误差，并降低索引重复成本；
之后再测长会话、多跳与语义检索，不把存储无损等同于推理无损。

## 跨领域字节重排与代码/数学对照（v0.14.0）

E2复测既有简单字节重排：新增地球物理SAC样例和分子动力学DCD样例，加入完整
Python源码、LaTeX数学文档作为非数值对照，另保留已见ECG与固定噪声。输入、规则、
算法在新压缩结果前冻结；本轮没有新增归档格式或编码算法。六组各8条件，统一
v4：Zlib6/Zstd3 ×64KiB/1MiB ×普通/重排；恢复全部显式files，含文件fsync。

**240次正式完整恢复、43,520次正式范围读取**，另48次恢复预热、5,440次查询预热
全部逐字节一致。正式完成文件fsync请求320次；20次Windows目录发布重试等待
计入时序，全部阶段和范围返回有追加日志，不重跑整次任务。本机120项测试：
119通过、1符号链接权限跳过；冻结候选Windows/Linux CI通过。

下表为本矩阵中每方法事后最小完整归档，重排另计整个numeric.py源1,431B一次；
不是预先固定的部署策略或速度最优，公共运行时未全额分配：

| 输入 | 最小普通归档 B | 最小重排归档 B | 加源后净省 |
|---|---:|---:|---:|
| 新SAC地震样例 | 66,749 | 47,854 | **26.16%** |
| 新DCD分子轨迹 | 3,634,034 | 3,067,142 | **15.56%** |
| Python源码对照 | 6,148 | 6,161 | −23.49% |
| LaTeX数学文档对照 | 22,478 | 22,491 | −6.42% |
| 已见ECG | 865,389 | 627,711 | 27.30% |
| 合成噪声 | 262,677 | 262,690 | −0.55% |

两份新科学输入共用专用源一次：普通3,700,783B；重排3,114,996+1,431B，净省
**15.79%**，由较大DCD主导。不能与不同语料的v0.11/v0.12百分比当作升级幅度。

![跨域样例与文本对照的完整归档和专用源成本](results/v0.14.0/crossdomain-costs.png)

两个新科学输入的主联合验收 **2/8通过**，均为DCD的Zlib工作点。相对同codec/块
普通编码，64KiB/1MiB重排计源净省14.69%/15.36%，完整恢复配对加速1.371×/1.308×，
常驻p95 1.713×/1.407×，重开p95 1.196×/1.445×；但编码配对仅0.600×/0.595×，
编码更慢。两个工作点的无发布重试配对子集恢复仍快1.220×（3对）/1.330×（4对），
仅作事后诊断，全部原轮次保留。通过不代表胜过所有普通codec或全流程支配。
本轮比较重排与普通编码；v0.12比较分段与普通/整文件重排，不能把0/8→2/8当版本胜负。

SAC有空间收益但同步恢复/读取未满足全部速度门槛。文本和噪声均无实际重排块，
完整归档仍多13B顶层标签，并有失败压缩尝试成本；时序波动不当作重排收益。
没有新增AST/数学语义压缩，也不把已有ECG当新验证样本。八个ECG归档完整SHA与
v0.10相同，证明这次没有改变其编码字节；不跨历史同步批次计算速度提升。

SAC只有一个公开样例；DCD只有一个分发测试文件，3,341原子、实际98帧，原头声明
500帧差异完整保留。不是完整数据库/模拟运行、严格盲测或大样本跨域泛化。
默认编码不切换，原始输入/用户研究文档不进入发行包。冷缓存、跨机器性能、数值Rust、
CAS+数值及E3/E4推理未测；文件同步不等于目录或真实掉电持久性证明。

```powershell
python -m pip install -e ".[zstd]"
python -m scripts.run_crossdomain --out results/local-crossdomain
```

[冻结协议](docs/CROSSDOMAIN.md) · [全部原始结果与逐阶段日志](results/v0.14.0/SUMMARY.md) ·
[独立核对](results/v0.14.0/validation.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.14.0)。
下一步优先在明确负载下筛选工作点，并实现代码/数学的可逆语义候选；根据计算热点
决定数值Rust，不把同步等待误判为Python循环成本。

## 恢复文件同步、故障边界与账本更正（v0.13.0）

归档 `unpack` 默认在每个完整文件 SHA 验证后执行 **flush → fsync → close**，
空文件同样处理，全部文件完成后再发布目录。同步错误直接失败；显式
`--sync-policy close` 保留历史关闭边界作为对照。编码与 v1–v6 格式不变，
不宣称压缩率改善；CAS 恢复不在本次同步策略变更范围内。

同归档、同 SHA、十轮配对，本机 Windows/E: NTFS 温缓存，80 次正式恢复和 8 次
预热全部逐字节一致；正式完成 1,350 次文件 fsync 请求。以下耗时包含校验、关闭、
发布和实际 Windows 重命名重试等待，不含进程启动与外部真值比较：

| 案例 | 文件数 | close 中位 ms | files 中位 ms | 配对额外 ms | files/close 配对中位 |
|---|---:|---:|---:|---:|---:|
| ECG / v4 | 3 | 7.038 | 22.231 | 15.298 | 3.135× |
| M13 / v4 | 1 | 29.660 | 87.844 | 58.733 | 3.003× |
| M13 / v6 | 1 | 27.365 | 88.260 | 61.207 | 3.257× |
| 合成文件数对照 / v2 | 130 | 40.273 | 553.017 | 512.846 | 13.716× |

差值和倍率先逐轮计算再取中位。130 文件案例不是科学语料；同步成本依文件数、
设备和缓存变化，不能将这些倍率推广到其他机器或解释为纯 fsync 内核延迟。

![同归档的恢复同步成本](results/v0.13.0/restore-sync-costs.png)

v1–v6 ×11 情形×3轮的 **198 条故障审计**均符合预期：写/flush/fsync/关闭/发布前
失败不发布；发布前强杀留下私有暂存，目标不存在；发布后强杀目标完整存在，但
客户端可能未收到成功。没有自动孤儿恢复，也没有目录/卷同步或真实掉电证明。
本机115项测试：114通过、1 Windows符号链接权限跳过。

首轮实验因 Windows rename 拒绝及诊断编码问题中止，记录单独保留。修订版仅对
Windows rename 的5/32/33错误最多尝试4次，等待10/50/100ms，所有等待计时；
最终正式样本有1次发布重试、0失败，不重试同步或整次恢复。

**历史更正：** v0.12 分段读取的分析性工作量误用固定块偏移。本版按真实前缀定位，
重编码100个归档确认完整SHA不变，再以独立线性扫描核对96,000次原请求；24个
分段配置、720组账本需更正。旧标签/结果不覆盖，原延迟和0/8联合验收计算不变。

```powershell
python -m pip install -e ".[scientific]"
python -m rkv1 unpack evidence.rkv restored
python -m rkv1 unpack evidence.rkv close-control --sync-policy close
python -m scripts.run_sync --out results/local-sync
```

[协议与边界](docs/PERSISTENCE.md) · [原始结果与分析](results/v0.13.0/SUMMARY.md) ·
[中止记录](results/v0.13.0/attempt-history.json) ·
[账本更正](results/v0.13.0/v012-work-ledger-correction.json) ·
[Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.13.0)。
后续继续 E2 类型候选、代码/数学与热点筛选；E3/E4、冷缓存、跨机器性能及推理未测。

## FITS 类型分流与区域分块（v0.12.0，历史实验）

E2新增显式FITS白名单和区域分块：识别一个完整2D float32/64主图像，头、图像、
填充按原始边界分块，只对图像字节重排；不转换数值/端序，不重写文件。未知格式
保守回退普通编码。新v6保存实际块配方，解码不依赖外部FITS解析器，支持精确范围读。
默认none/v2、数值/v4、Blosc/v5、单元/v3、CAS1保持不变，旧读取器拒绝v6。

规则与验收先固定，再测新验证记录：11,586,240 B的M13叠加float64图像及478,080 B
的ROSAT float32图像。另保留已见Spitzer开发记录、ECG和噪声回退对照。
全部20条件/组、五轮、统一v6：Zlib6/Zstd3 ×64KiB/1MiB ×普通固定、整文件重排、
固定块类型分流、仅分段、分段类型分流。**500次正式完整恢复、96,000次正式范围
读取**，另100次恢复预热、12,000次查询预热全部逐字节一致。本机104项测试：
103通过、1符号链接权限跳过；Windows/Linux CI通过。

**新增布局未超过已有整文件重排的联合收益。** 两份新验证输入各自按最小归档
选参，专用源共用一次（不是预先固定的部署策略或速度最优）：

| 方法 | 合计完整归档 B | 专用源一次 B | 对最小普通归档加总净省 |
|---|---:|---:|---:|
| 普通固定块 | 2,921,262 | 0 | 基线 |
| 整文件字节重排 | 1,961,771 | 1,431 | **32.80%** |
| 固定块仅图像重排 | 2,068,709 | 4,824 | 29.02% |
| 仅区域分块 | 2,921,393 | 3,393 | −0.12% |
| 分段且仅图像重排 | 1,960,598 | 4,824 | **32.72%** |

分段类型归档合计比整文件重排少1,173 B，但新增整个layouts.py计3,393 B后，
反而多2,220 B。M13/ROSAT整文件重排单组计源后分别净省35.70%/8.92%，分段类型
为35.56%/8.31%；这些是新数据上的观察，不能把32.80%与v0.11的13.60%当成升级收益。
两个新记录的四种codec/块工作点共 **0/8通过预定联合验收**：须同时相对普通固定
和整文件重排，在计源后不增大，恢复/常驻p95/重开p95配对中位均>=1且各至少4/5轮更快。
编码成本另列，空间单项收益不冒充联合通过。规则没有按结果回调，默认不切换。

![新增验证记录的完整归档与专用源成本](results/v0.12.0/layout-costs.png)

分段读取器额外建立unsigned-64前缀偏移数组，其逻辑字节和进程RSS均报告。
识别与分段也有成本；ECG不在本次FITS白名单内，回退会错过人工声明int16重排的收益。
M13大文件主导合计，ROSAT约22.66%正零；两个新样本仍是同一项目的天文数据，
不是跨科学领域验证。专用源4,824 B不是完整部署大小，公共Python/core/Zstd/pyc未全额分配。

```powershell
python -m pip install -e ".[zstd]"
python -m scripts.run_layout --out results/local-layout
python -m rkv1 pack data/layout/m13_64 m13.rkv --codec zstd --chunk-size 65536 --layout fits-segments-v1 --transform fits-byte-shuffle-v1
python -m rkv1 verify m13.rkv
```

[冻结协议与执行说明](docs/LAYOUT.md) · [全部原始结果与对照](results/v0.12.0/SUMMARY.md) ·
[独立核对](results/v0.12.0/validation.json) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.12.0)。
持久性描述同步校正：归档写入flush/fsync；既有归档解包关闭文件、校验后发布目录，
没有逐文件fsync。此前部分说明对此描述过强，不把未执行操作计入成本，不声称掉电持久性。
冷缓存/跨机器、数值Rust、代码/数学、CAS+布局和推理收益仍未测。下一步先补持久性
语义的明确对照，再按热点与新领域数据筛选类型方案；E2未完成，E3/E4待开展。

## 完整浮点 FITS 与 Blosc 对照（v0.11.0）

E2 增加三个完整公开 FITS 示例（两个 float32、一个 float64），复测同一 ECG int16，
并保留随机字节负对照。完整文件、头、填充和 NaN payload 均逐字节恢复，不转换
数值/端序。新增固定 python-blosc **1.11.4** / C-Blosc 的 Zstd 无过滤、字节重排和
位重排，单线程、内部块 64KiB；不是 Blosc2 或 NDArray 子块随机读。

每组 18 条件、五轮、全部同 **v5 平块容器**；普通 Zlib6/Zstd3 与 Python 字节重排/
XOR 为对照。**450 次正式完整恢复、86,400 次正式范围读取**，另 90 次恢复预热、
10,800 次查询预热全部逐字节一致。源/源码/整份专用依赖冻结，各轮归档确定性一致。
本机 97 项测试：96 通过、1 Windows 符号链接权限跳过；Windows/Linux CI 通过。

下表在本次有限矩阵内分别按最小完整归档选参，不按速度选。Python 重排列为
Zlib/1MiB，净节省另计整个 numeric.py **1,431 bytes**；Blosc 列仅为依赖已安装
情景的归档增量。跨后端 Zstd 版本、级别映射与分块不同，不把差异归因于单个过滤器。

| 科学输入 | 最小普通归档 B | Python 字节重排归档 B | 加源后净省 | 最小 Blosc 过滤器 / 归档 B | 已安装情景节省 |
|---|---:|---:|---:|---|---:|
| Spitzer float32 | 1,838,171 | 1,631,953 | 11.14% | shuffle / 1,649,920 | 10.24% |
| Bolocam float32 | 1,455,509 | 1,333,725 | 8.27% | shuffle / 1,358,357 | 6.67% |
| MSX float64 | 109,110 | 92,840 | 13.60% | bitshuffle / 94,400 | 13.48% |
| ECG int16 | 865,389 | 627,711 | 27.30% | shuffle / 650,199 | 24.87% |

**归档收益没有覆盖本次小语料的整份专业库成本。** 实测 Blosc 发行包 4,876,827 B，
适配源 2,690 B；合计专用资源 **4,879,517 B**，独立环境没有 NumPy。
四组科学输入均选 Blosc shuffle、共用资源一次时：归档共 3,756,343 B，较各组最小
普通归档合计少 11.99%；加资源后共 8,635,860 B，反而多 **102.33%**。
同样四组 Python 字节重排加源一次共 3,687,660 B，净省 **13.60%**。
这些仍未完整分配公共 Python/core/Zstd/OS 成本，不称完整部署占用。

**速度取舍也分场景。** 完整恢复计入首次 Blosc 导入/设置，三个 FITS 的最小
Blosc 过滤归档恢复均慢于各自最小普通归档；正式范围读在查询预热后测量。
同 Blosc/64KiB 的 ECG 位重排相对无过滤：归档少 22.59%，编码/完整恢复/常驻 p95/
重开 p95 逐轮配对加速中位为 1.27×/1.10×/1.43×/1.27×，均 5/5 轮更快；
这只支持该工作点的同后端消融，不代表比所有普通 codec 更优或跨机器稳定。
Python XOR 在两个 float32 上恢复明显较慢，位重排也并非普遍比字节重排更省空间。

![完整归档、专用依赖成本与首次恢复时间](results/v0.11.0/scientific-costs.png)

默认 none 仍写 v2，数值策略仍自动写 v4，专业 codec 自动写新 v5；旧读取器拒绝 v5。
既有 v3 单元/CAS 格式不变，未组合数值与共享 CAS 的收益。噪声全部回退 raw，
仍有策略标签与编码尝试成本，默认不启用新策略。

```powershell
python -m pip install -e ".[scientific]"
python -m scripts.run_scientific --out results/local-scientific
python -m rkv1 pack data/scientific/spitzer32 spitzer.rkv --codec blosc-zstd-bitshuffle-4 --chunk-size 65536
python -m rkv1 verify spitzer.rkv
```

正式复现请使用不含 NumPy 的独立环境，完整步骤见 [SCIENTIFIC.md](docs/SCIENTIFIC.md)。
[原始结果与完整比较](results/v0.11.0/SUMMARY.md) · [独立核对](results/v0.11.0/validation.json) ·
[数据来源](docs/DATASETS.md) · [Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.11.0)。
三个 FITS 同属天文领域且同一托管项目，float64 很小，Bolocam 约 5% NaN；不外推
全部科学数组。冷缓存/跨机器/跨日、数值 Rust、代码/数学、CAS+数值、推理质量
尚未实测，E2 未完成，E3/E4 待开展。下一步优先按成本和读取工作点筛选类型/布局策略。

## 精确数值字节原型（v0.10.0）

E2新增显式`byte-shuffle-{2,4,8}-v1`和`xor-shuffle-{2,4,8}-v1`策略。
它们重排原始字节，或先对相邻字做XOR，再重排；不解析/舍入数值、不改端序，
残尾原样保留。数值策略写新 **v4** 平块归档，旧读取器拒绝v4；默认none仍写v2，
CSV/v3单元/CAS格式不变。块/文件/manifest SHA、有界解压和发布fsync均保留。

实测两个公开数据库各一条原始int16记录：EEGMMIDB S001R01的完整EDF+，以及
PTBDB s0010_re的dat/xyz/hea；另有固定种子随机字节负对照。无采样或文件转换，
原始头和注释也计入；每组12条件、五轮、全部同v4容器。
**180次正式完整恢复、34,560次正式范围读取**，另36次完整预热、4,320次查询预热
全部逐字节一致。本机90项测试：89通过、1符号链接权限跳过；Windows/Linux CI通过。

下表在本次Zlib6/Zstd3、64KiB/1MiB集合内，分别按体积选最小归档，包含全部
容器成本；另给每个候选全额加专用numeric.py源文件 **1,431 bytes**。这不是完整
部署成本；无额外DLL、模型或字典，公共Python/core/codec未全额分配。

| 原始记录 | 策略 | 归档+专用源 bytes | 对最小普通净节省 | 编码 ms | 恢复 ms |
|---|---|---:|---:|---:|---:|
| EEG | 普通 Zstd/1MiB | 682,548 | 基线 | 14.268 | 7.874 |
| EEG | 重排 Zlib/1MiB | 640,179 | **6.21%** | 114.230 | 8.417 |
| EEG | XOR重排 Zlib/1MiB | 585,333 | **14.24%** | 174.255 | 35.985 |
| ECG | 普通 Zlib/1MiB | 865,389 | 基线 | 44.029 | 9.307 |
| ECG | 重排 Zlib/1MiB | 629,142 | **27.30%** | 62.011 | 8.007 |
| ECG | XOR重排 Zlib/1MiB | 637,699 | **26.31%** | 120.620 | 32.224 |

**字节重排有值得继续验证的空间收益；XOR不自动更优。** EEG的XOR进一步缩小存储，
但恢复中位需普通最小归档约4.57倍时间；ECG中XOR既比单纯重排大，也恢复更慢。
所有真实记录的候选编码均比相同codec/块的普通编码慢，五轮均如此。

也存在有利的局部工作点：ECG/Zlib/64KiB重排归档减少26.90%，同轮恢复、常驻p95、
重开p95配对加速分别1.30×/1.97×/1.31×，均5/5轮更快；编码加速倍率为0.657×（更慢）。
大块虽能减少元数据，仍需整块反变换/校验，不能从压缩率直接推断随机读取改善。
所有配对倍率逐轮相除再取中位，不用两个耗时中位之比替代。

![数值字节策略的完整归档与专用源成本](results/v0.10.0/numeric-costs.png)

噪声12条件全部回退普通块，但策略标签仍增加12/13bytes，专用源另计，编码尝试
还需时间；因此默认保持none。v4数值本轮只测独立归档，未与共享CAS组合测量，
不能将本轮收益与v0.9的共享节省比例叠加。

```powershell
python -m scripts.run_numeric --out results/local-numeric
python -m scripts.summarize_numeric results/local-numeric
python -m rkv1 pack data/numeric/eeg eeg.rkv --codec zstd --chunk-size 65536 --transform byte-shuffle-2-v1
python -m rkv1 verify eeg.rkv
python -m rkv1 unpack eeg.rkv restored
python -m rkv1 compare data/numeric/eeg restored
```

运行器先下载并校验原始数据；[协议/格式/执行说明](docs/NUMERIC.md)、
[完整记录](results/v0.10.0/SUMMARY.md)、[数据来源与引用](docs/DATASETS.md)、
[独立核对](results/v0.10.0/validation.json)。首批仅两个int16单记录，4/8字节与浮点
特殊位模式仅为正确性测试；真实浮点数组、专业压缩器广泛对照、冷缓存/跨机器/
跨日和推理质量未测。本版没有数值Rust加速，E2仍待扩大，E3/E4尚未实测。

## 既有同格式对象 IO 消融与第二个真实版本家族（v0.9.0）

新增显式 `--io-backend bounded` 与 Windows `--publisher rename` 候选：减少重复的
目录/对象长度查询，用有界读取检查精确 EOF；发布使用不覆盖已有目标的重命名。
每个新文件仍 flush/fsync，复用仍验证旧对象，全部原文/存储摘要保留；CAS 格式不变。
**默认仍为 reference/link**，Gear 默认仍为 Python，Rust 扫描须显式选择。

QASPER v0.1→v0.2→v0.3，加 Evidence Inference v1.2→v1.3→v1.4 的两张原始主 CSV 表；
每家族八条件、五轮本机温缓存。冻结 v0.8 Store 与当前 reference 作对照，全部 Gear
条件使用同一个实测 Rust 库。**240 次正式完整恢复、92,160 次正式范围读取**，另
48 次恢复预热、5,760 次查询预热全部逐字节一致。同表示完整存储树、快照与账本
完全相同；QASPER 结果也与 v0.8 同表示的字节相同。

| 三版指标 | QASPER | Evidence Inference 两表 |
|---|---:|---:|
| 独立 1 MiB 归档 bytes | 31,519,475 | 3,760,981 |
| 共享 Gear CAS bytes | 23,946,864 | 2,608,262 |
| 共享 Gear + 整份原生库 bytes | 24,071,283 | 2,732,681 |
| 含库后相对独立归档节省 | 23.63% | 27.34% |
| reference 提交中位 s | 2.397 | 0.223 |
| 组合候选提交中位 s | 2.124 | 0.214 |
| 组合提交配对加速中位 | **0.974×，2/5 轮更快** | **1.026×，4/5 轮更快** |

**IO 候选未证明稳定、全面提速，因此不升级默认。** 配对倍率先按同轮 reference/
candidate 计算，再取中位；它与两个耗时中位之比不同。单独 bounded 的提交配对
为 0.889×/0.766×，单独 rename 为 0.760×/0.929×；负结果和全部波动均保留。
bounded 常驻范围 p95 配对为 1.103×/1.081×，重开为 0.991×/1.036×；收益依赖指标。

![同字节 IO 消融的中位与五轮观测](results/v0.9.0/io-ablation.png)

原生库继续复用 v0.8 实测 DLL 123,904 bytes + 原始元数据 515 bytes，各家族上表全额
加一次。Evidence Inference 的 prompts 三版完全相同，约占每版原文 17.9%；较高共享
收益不能直接推广到全文或独立科学数据。逻辑字节包含所有对象/头/双摘要/快照/
配置/未引用对象；文件数据分配另记，目录/MFT/日志与公共运行时未全额分配。

本机 82 项测试：81 通过、1 Windows 符号链接权限跳过；Windows/Linux CI 通过。
覆盖损坏与尾部多字节、复用验证、并发发布、同步/快照失败、不覆盖已有文件和旧版
读取兼容。冷缓存、跨机器、跨日、断电耐久性和推理质量未测，E3/E4 尚未实测。

```powershell
python -m rkv1 store-init vault --chunker gear-v1 --codec zstd
python -m rkv1 store-add vault data/qasper-versions/v0.1 --io-backend bounded --publisher rename --chunker-backend rust --native-library native/rkv1_core.dll
python -m scripts.run_io --native-library native/rkv1_core.dll --out results/local-io
python -m scripts.summarize_io results/local-io
```

先从 [v0.9 Release](https://github.com/StarlitPupils/RKV-1/releases/tag/v0.9.0) 解压
`rkv1-native-measured-v0.9.0-windows-x86_64.zip` 到 `native/`，保留原始 `native.json`。
该冻结实测库与通用平台新构建资产分开标识，不能假定其二进制相同。
[完整记录](results/v0.9.0/SUMMARY.md) · [IO 协议与复现](docs/IO.md) ·
[数据来源](docs/DATASETS.md) · [独立核对](results/v0.9.0/validation.json)。下一优先项
转向 E2 数组/数值类型，先做完整成本基线和负对照，再决定编码方案。

## 既有热点剖析与精确 Rust Gear 扫描（v0.8.0）

冻结v0.7源码的cProfile诊断定位到逐字节Gear循环；v0.8新增显式Rust扫描后端。
同一表、u64递推、最小/最大边界和流状态保持不变。Python仍组装原文字节，执行
全部哈希、压缩、旧对象验证、fsync和发布。CAS格式与默认Python后端不变。

原始QASPER三个发布，六条件、五轮本机温缓存；Python/Rust所有轮次的完整存储树、
对象账本及快照ID相同，并与v0.7已发布的同表示存储树字节完全一致。
**90次正式完整恢复、34,560次正式范围读取**，另18次恢复预热、2,160次查询预热
全部逐字节一致。本机75项测试：74通过、1 Windows符号链接权限跳过；跨平台CI通过。

| 三版存储/扫描方式 | 完整逻辑存储 bytes | 三版提交中位 s | 完整恢复中位 s | v0.3重开p95 ms |
|---|---:|---:|---:|---:|
| 独立RKV / 固定1MiB | 31,519,475 | 0.623 | 0.260 | 2.233 |
| 共享CAS / 固定64KiB | 35,981,908 | 3.970 | 0.572 | 4.704 |
| 共享CAS / Gear Python | 23,946,864 | 28.989 | 0.519 | 3.893 |
| 共享CAS / Gear Rust | **23,946,864** | **2.971** | 0.517 | 3.793 |

同轮提交配对加速中位：共享Gear **9.88倍**、独立Gear **10.54倍**，两者均5/5轮
更快。配对比值中位与表内耗时中位之比不是同一统计量；结论使用本轮内部对照，
不将历史版本耗时变化直接当作迁移收益。恢复/读取仍用同一Python实现，未获Rust解码收益。
共享配对逐轮加速范围8.15–16.66倍，仅为观测范围；Rust三版提交wall为1.70–3.56秒，
波动仍存在，不声称统计显著或固定倍率。

实测冻结DLL 123,904 bytes + 原始native.json 515 bytes，整份共享资源 **124,419 bytes**。
三版共享Gear加一次全额库成本为 **24,071,283 bytes**，相对旧独立1MiB归档节省
**23.63%**；公共Python/codec/OS和目录/MFT/日志未全额分配，不是完整部署或物理卷成本。
提交仍为旧1MiB归档 **4.77倍耗时**，完整恢复约 **1.99倍**，重开p95约 **1.70倍**。
原生扫描解决了主要诊断热点，综合性能仍有明确取舍。

![Gear同存储字节的提交与资源成本](results/v0.8.0/gear-tradeoffs.png)

```powershell
python -m rkv1 store-init vault --chunker gear-v1 --codec zstd
python -m rkv1 store-add vault data/qasper-versions/v0.1 --label v0.1 --chunker-backend rust --native-library .tools/native-v0.8-measured/rkv1_core.dll
python -m scripts.run_gear --native-library .tools/native-v0.8-measured/rkv1_core.dll --out results/local-gear
```

[完整记录](results/v0.8.0/SUMMARY.md) · [原生协议/复现](docs/NATIVE.md) ·
[逐轮原始结果](results/v0.8.0/qasper-gear.json)。Release另附
`rkv1-native-measured-v0.8.0-windows-x86_64.zip`，保留通过源CI的实测库和元数据原字节。
通用新构建库须按自己的身份使用，不能假定与实测库相同。源/输入/库/元数据前后
指纹一致；诊断树与主实验均保留。一个家族三版、温缓存五轮；冷缓存、跨机器、
跨日和科学推理质量未测。对象 IO 消融和第二个版本家族由 v0.9 补充；E2 其他类型待开展。

## 既有真实版本序列与共享 CAS（v0.7.0）

新增可选目录 CAS：不可变内容对象、独立快照、全量/局部恢复与逐层校验。支持固定
分块和简单 Gear CDC；对象按原文字节 SHA-256 寻址，跨版本引用已有对象，实际只
存一份。旧归档 v1/v2/v3 和 pack/read/unpack 默认行为保持不变。

使用 QASPER 官方原始 train/dev **v0.1→v0.2→v0.3**，保留原始文件名和全部字节，
不重序列化 JSON。一个语料家族、三次真实发布，128,076,252 bytes 原文；八条件：
独立 RKV、同格式独立 CAS、共享 CAS，固定64KiB/1MiB及 Gear scale64KiB。
**120 次正式完整恢复 + 24 次预热恢复、46,080 次正式范围读取 + 2,880 次查询
预热全部逐字节一致**。本地70项测试：69通过、1符号链接权限跳过；跨平台CI通过。

所有方法 Zstd3，无CSV/模型/字典/原生后端。同边界的独立/共享 CAS 快照ID相同，
对象文件字节并集相同，避免将不同编码表示的收益当成共享效果。

| 三个版本的存储方式 | 完整逻辑文件 bytes | 分配文件数据 bytes | 文件数 | 三版提交 s |
|---|---:|---:|---:|---:|
| 独立 RKV / 固定1MiB | 31,519,475 | 31,522,816 | 3 | 0.650 |
| 独立 CAS / Gear64 | 35,408,908 | 38,224,616 | 1,436 | 23.040 |
| 共享 CAS / 固定64KiB | 35,981,908 | 39,780,480 | 1,928 | 3.100 |
| 共享 CAS / Gear64 | **23,946,864** | **25,759,992** | 914 | 22.529 |

共享 Gear 相对同格式独立 Gear 节省 **32.37%**；相对独立1MiB RKV逻辑字节减少
**24.03%**，但提交约 **34.69倍耗时**，三版完整恢复约 **2.00倍耗时**。v0.3 的
跨版本独特对象复用 **94.21%**（独特原文91.23%）；固定64KiB对应仅4.83%/4.84%。
v0.3 新增对象+快照约1.05MB，固定1MiB约10.42MB。固定分块会受字节偏移影响，
CDC改善了这组真实修订的复用，Python扫描/大量对象也增加了时间成本。

![三版存储与累计增长](results/v0.7.0/version-storage.png)

逻辑字节包含所有对象头/双摘要/payload、快照/config与未引用对象；额外报告文件
数据分配空间和文件数。目录/MFT/日志/公共运行时未全额计入，不称为完整物理卷
占用。Gear64是mask scale，实际平均块约89,500 bytes（约87.4KiB），
不是与固定64KiB实际平均严格匹配，也不是FastCDC复现。

[本轮完整记录](results/v0.7.0/SUMMARY.md) · [格式/协议/执行说明](docs/STORE.md) ·
[固定数据来源](results/v0.7.0/dataset-provenance.json)。使用 store-init/store-add/
store-verify/store-unpack/store-read/store-stat。局部验证只证明触及对象；每次复用
验证旧对象，完整恢复验证文件。失败提交可留下计费对象，无GC和断电耐久性证明。
仅本机温缓存、一个语料家族；冷缓存/跨机器/跨日、E3/E4科学推理质量未测。
Gear热点剖析与原生扫描已由v0.8补充；其他真实版本家族和E2类型仍待扩大。

## 既有 Rust 反变换与本机配对（v0.6.0）

新增读取器实例级 `--decoder-backend rust --native-library ...`，只替换 CSV v1 的
字面量检查和精确反变换。保留原有受限解压、单元/父块/文件 SHA-256；两个后端
读取同一个归档。默认仍为 Python、Zlib/1 MiB、v2，CSV 和独立单元须显式启用。

Wine、超导材料、HTRU2；26 份确定性归档、52 个条件，**260 次正式完整恢复 +
52 次预热恢复、99,840 次正式范围读取 + 6,240 次查询预热全部逐字节一致**。
本机使用 v0.5 Release 的冻结 Windows DLL，库/元数据/源码/输入哈希前后一致。
本地 63 项测试：62 通过、1 符号链接权限跳过；Windows/Linux CI 验证新后端。

超导材料、Zstd、CSV：同归档 Python → Rust，恢复含库校验/加载、FFI 和复制；
范围已预热。五轮配对，不做显著性结论。

| 布局 | 总 bytes | 完整恢复 ms | 恢复配对加速 | 重开 p95 ms |
|---|---:|---:|---:|---:|
| 1 MiB 整块 | 7,442,705 | 427.17 → 91.94 | 4.63× | 30.997 → 4.496 |
| 1 MiB + 64 KiB 单元 | 7,817,638 | 395.15 → 99.45 | 3.97× | 2.457 → 1.009 |
| 1 MiB + 16 KiB 单元 | 8,423,479 | 626.74 → 120.09 | 5.22× | 1.491 → 0.924 |

上述 CSV 恢复/重开均五轮更快，但普通 Zstd/1 MiB 本轮恢复 **61.08 ms**、重开
**2.346 ms**；不能把 CSV 后端加速当作普通编码已被全面超过。额外 DLL+元数据
**121,747 bytes** 单列部署成本：本轮体积最小的超导材料 CSV/Zlib 归档 7,284,903
bytes，比最小普通 Zstd 的 7,548,059 bytes 减小 263,156 bytes；计入一次原生资源后
净省 **141,409 bytes**，恢复却为 **136.34 ms**（普通约61.08 ms）。Wine 单份归档
的节省不足抵消原生资源；HTRU2 CR-only 回退并无变换收益。默认策略保持不变。

![原生后端空间与读取代价](results/v0.6.0/native-tradeoffs.png)

[完整配对结果](results/v0.6.0/SUMMARY.md) · [原生协议与执行说明](docs/NATIVE.md) ·
[库来源](results/v0.6.0/native-provenance.json)。归档格式不变，兼容 v1/v2/v3；
Release 附 Windows/Linux 原生库 ZIP，复现实验须选协议指定的冻结二进制。
冷缓存/跨机器/跨日、推理质量未测。真实版本序列、CDC与共享CAS已由v0.7补充；
数组/代码/数学类型、E3/E4仍待开展。

## 既有独立单元与索引实验（v0.5.0）

显式 `--unit-size` 生成 RKV v3：1 MiB 父块内含独立 16/64 KiB 单元，每个单元有
大小、codec、变换标志和原始 SHA-256。二进制索引按需校验并缓存，范围请求只
解码触及单元；完整恢复继续验证父块和文件。默认仍写 v2，CSV 仍关闭。

四组科学输入、53 个条件；**265 次正式完整恢复 + 53 次预热恢复、101,760 次正式
范围读取 + 6,360 次查询预热全部逐字节一致**。本地 56 项测试：55 通过、1 权限跳过。
所有大小包括索引；对照包含整块、直接小块、普通编码及关闭索引缓存。

Zstd、同源码/同请求、温缓存，各轮 p95 中位数：

| 数据 / 变换 | 布局 | 总 bytes | 重开 p95 ms |
|---|---|---:|---:|
| 超导材料 / CSV | 1 MiB 整块 | 7,442,705 | 30.921 |
| 超导材料 / CSV | 直接 16 KiB 块 | 8,761,101 | 13.645 |
| 超导材料 / CSV | 1 MiB + 16 KiB 单元 | 8,423,479 | 1.378 |
| QASPER / none | 1 MiB 整块 | 10,660,769 | 2.221 |
| QASPER / none | 直接 64 KiB 块 | 12,415,158 | 5.208 |
| QASPER / none | 1 MiB + 64 KiB 单元 | 12,299,774 | 0.870 |

两层单元相对同大小直接小块改善了较大语料的打开成本并减少元数据；常驻读取并非
全胜。超导材料/CSV/16 KiB 对直接小块节省 3.85%，配对重开 p95 加速中位约9.75倍；
但对原1MiB CSV归档仍增大约13.18%，完整恢复也未必更快。不能只拿整块 CSV 作参照：
普通 Zstd 的两层64KiB方案本组重开约0.703ms，优于相同CSV约2.463ms。

![独立单元空间与重开延迟](results/v0.5.0/unit-tradeoffs.png)

[本轮记录](results/v0.5.0/SUMMARY.md) · [协议](docs/UNITS.md) · [v3 格式](docs/FORMAT.md)。
v0.5 读取器兼容 v1/v2/v3；旧读取器不支持 v3。局部读取只证明触及单元，完整 verify
检测所有损坏；索引摘要的校验链不代表来源身份。单元哈希尚未实现跨父块 CAS/增量共享。

Rust 新增精确 CSV 反变换 C ABI 候选，Windows/Linux CI 做函数及 Python 差分验证，
Release 附带平台库/来源哈希；本轮时序实验全部使用 Python，尚无 Rust 加速结论。
下一里程碑量化原生内核，再推进真实版本序列/共享块存储。冷缓存/跨机器继续未测。

## 既有 CSV 反变换试验（v0.4.0）

在首版无损核心之上加入 Zstd、可关闭的跨文件去重、可选数值 CSV 列重排，以及
manifest version=2；新读取器仍能恢复首版归档。默认 Zlib/1 MiB、CSV 变换关闭；
codec、块大小和变换策略由参数选择。

本版新增 HTRU2 脉冲星候选与 Superconductivity 超导材料数据，固定 ZIP/原始成员
哈希。CSV 反变换保留全部校验，把按单元 Python 索引改为列切片 + zip；与冻结旧
反变换读取同一归档、匹配同一查询。默认仍为 Zlib/1 MiB，CSV 关闭，格式仍为 v2。

**18 个条件、90 次正式完整恢复 + 18 次预热恢复、15,360 次正式范围读取 + 1,920
次预热读取全部逐字节一致。** 本地 44 项测试：43 通过、1 权限跳过。

| 数据 / codec | CSV 对同 codec 归档节省 | 旧/新 CSV 完整恢复耗时 | 新 CSV/普通恢复耗时 |
|---|---:|---:|---:|
| Wine / Zlib | 4.62% | 1.21× | 6.68× |
| Wine / Zstd | 0.40% | 1.09× | 2.17× |
| Superconductivity / Zlib | 11.79% | 1.15× | 7.17× |
| Superconductivity / Zstd | 1.40% | 1.16× | 6.94× |

优化使有实际变换的条件恢复速度提高约 9–21%（耗时减少约 8.6–17.1%），但仍明显慢于普通编码，超导材料条件
峰值内存增加约 1.5–1.9 MiB。与本轮最小普通归档 Zstd 比，超导材料的最小 CSV
归档 Zlib 只再省约 3.49%，恢复慢约 11.1 倍，不能把同 codec 的 11.79% 当作全面优势。
HTRU2 为 CR-only，当前 CSV v1 不适用，回退保留全部原文，启用策略仅多 10 bytes
头部成本；不为获得正结果改换行。正则验证与整块重建仍是后续优化候选，尚无 Rust 加速。

![CSV 空间收益与恢复代价](results/v0.4.0/csv-tradeoffs.png)

[本轮完整结果](results/v0.4.0/SUMMARY.md) · [E2 配对协议](docs/CSV-TRIALS.md) ·
[成本账本](results/v0.4.0/runtime-footprint.json)。发布前 CI 再运行跨平台 Python/Zstd 和 Rust 骨架测试。

## 已完成的多轮读取评测（v0.3.0）

上一版沿用 RKV v2 格式和压缩核心，补强 E0 读取协议。SciFact/QASPER × 三种 codec
× 三种块大小，18 个配置；每配置两个连续批次、每批五轮不同查询种子。常驻读取器
与每次重开分别使用独立 worker，配置/轮次/模式交错打乱，记录打开、读取和关闭
阶段。非跨块请求完全配对；原始请求、样本、执行顺序和输入/源码指纹随版本保存。

全部归档先完整校验，每个请求逐字节验证，实验末尾检查输入、实现和归档未变。
正式范围读取 **161,280 次**，另有 **10,080 次预热读取**，全部逐字节一致；
共 360 个独立 worker，18 个完整校验的归档与 v0.2 对应条件字节完全相同。
计时前预读完整归档，只报告本机温缓存结果；冷缓存、跨机器与跨日结果明确未测。
该版本地 **38 项测试：37 通过、1 权限跳过**；
发布流水线再运行 Windows/Linux、Python 3.10/3.13 和 Rust 骨架测试。

读取统计报告十轮各自 p95 的中位数、最小/最大值和配对方向；范围不是置信区间。
[本轮结果](results/v0.3.0/SUMMARY.md) · [读取协议](docs/READING.md)。

Zstd、温缓存、按文件字节加权的短范围请求：

| 数据 | 块 KiB | 常驻：十轮 p95 中位 ms | 每次重开：十轮 p95 中位 ms |
|---|---:|---:|---:|
| SciFact | 64 / 256 / 1024 | 0.177 / 0.442 / 1.749 | 1.465 / 1.027 / 2.140 |
| QASPER | 64 / 256 / 1024 | 0.152 / 0.413 / 1.623 | 5.298 / 2.014 / 2.321 |

常驻时 64 KiB 在两组全部十轮都快于 1 MiB，但归档增加 14.41%/16.46%。重开时
256 KiB 对 SciFact 十轮全胜，对 QASPER 九轮胜过 1 MiB，后者收益更小且有波动。
QASPER 64 KiB 清单打开中位约 4.658 ms，说明只优化块解码不能解决重开成本。
这些结果支持按读取器生命周期选候选配置，尚不改变默认策略。

## 压缩观察（v0.2.0）

以下为同容器、1 MiB、去重开启、无变换的归档大小，包含所有容器元数据。

| 语料 | 原始 bytes | Zlib 6 bytes | Zstd 3 bytes | Zstd 归档节省 |
|---|---:|---:|---:|---:|
| SciFact | 8,582,267 | 2,863,283 | 2,745,550 | 4.11% |
| QASPER train/dev | 43,368,073 | 10,902,467 | 10,660,769 | 2.22% |
| UCI Iris/red wine | 88,750 | 25,150 | 26,681 | -6.09% |
| Wine red/white | 348,625 | 93,493 | 98,417 | -5.27% |

Zstd 在这两组科学文本上编码、恢复更快，CSV 的最小体积则由 Zlib 获得。
小块改善范围读取延迟，但增加压缩损失和索引开销；选择应结合查询工作负载。
在相同流式容器下，两 codec 恢复内存相近，首版与整流 TAR 的内存差距受实现方式影响。

E2 的列重排保留数值原文、表头、换行及跨块边界。Zlib 条件下归档节省约 **4.6–4.7%**，
但 Python 解析、恢复和范围读取明显变慢，所以保留为可选试验。真实输入在本次三种
固定分块下没有重复块收益；合成对照验证去重机制，但不代表自然科学语料。

[多轮读取与打开方式图](results/v0.3.0/reading.png)

[完整结果与原始样本](results/v0.2.0/SUMMARY.md) · [复现协议](docs/EXPERIMENTS.md) ·
[数据署名/许可](docs/DATASETS.md) · [运行时成本记录](results/v0.2.0/runtime-footprint.json)

归档字节不等于部署总占用。本机可选 Zstd distribution 另占约 1.13 MB；共享 RKV
源码、transform 模块以及安装占用都记录在成本账本，Python/全部共享原生依赖尚未
分摊到单归档。本版没有外部字典、模型权重或语义索引。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[bench]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m rkv1 fetch data/scifact --dataset scifact
.\.venv\Scripts\python.exe -m rkv1 pack data/scifact data/scifact.rkv --codec zstd
.\.venv\Scripts\python.exe -m rkv1 verify data/scifact.rkv
.\.venv\Scripts\python.exe -m rkv1 unpack data/scifact.rkv data/restored
.\.venv\Scripts\python.exe -m rkv1 compare data/scifact data/restored
.\.venv\Scripts\python.exe scripts/run_controlled.py --out results/local-controlled
.\.venv\Scripts\python.exe scripts/summarize_controlled.py results/local-controlled
.\.venv\Scripts\python.exe scripts/run_reading.py --out results/local-reading
.\.venv\Scripts\python.exe scripts/summarize_reading.py results/local-reading
.\.venv\Scripts\python.exe scripts/run_csv_trials.py --out results/local-csv
.\.venv\Scripts\python.exe scripts/summarize_csv.py results/local-csv
.\.venv\Scripts\python.exe scripts/run_units.py --out results/local-units
.\.venv\Scripts\python.exe scripts/summarize_units.py results/local-units
```

Python 3.10+；Linux/macOS 使用 `.venv/bin/python`。核心 Zlib 模式可安装 `pip install -e .`，
Zstd 可仅安装 `.[zstd]`。绘图可另装 `.[plots]`。归档默认不覆盖，恢复目标须不存在。

```powershell
python -m rkv1 pack data/scifact data/small-blocks.rkv --codec zstd --chunk-size 65536
python -m rkv1 pack data/scifact data/no-dedup.rkv --codec zstd --no-dedup
python -m rkv1 fetch data/wine --dataset wine
python -m rkv1 pack data/wine data/columns.rkv --codec zlib --transform csv-columns-v1
```

## 路线与版本

| 阶段 | 状态 |
|---|---|
| E0 基准 | 完成首版、受控对照和多种子读取评测；仍是单机温缓存 |
| E1 无损核心 | v1–v6兼容；共享CAS、真实版本复用与Gear分块；默认v2、CAS1保持不变；归档默认逐文件fsync已测，目录/掉电持久性未验证 |
| E2 类型感知可逆编码 | CSV/小单元/Rust配对、int16/float字节变换、Blosc、FITS布局已测；新布局0/8联合通过，代码/数学待开展 |
| E3 神经预测 + 熵编码 + 精确残差 | 后续，计入模型和解码成本 |
| E4 科学记忆、检索、证据回溯与可验证推理 | v0.15首个检索/API/引用与写回基线；v0.16索引成本、v0.17多版本更新对照；长会话/多跳/形式证明未测 |

Rust 已用于可选CSV反变换与Gear扫描。传统归档的`--base`复用编码结果，仍写独立
完整快照；目录CAS可跨版本只存一份对象。两者仍全量读源、计算哈希并验证旧对象。

[FORMAT Draft 0.6](docs/FORMAT.md) 只恢复普通文件路径和内容，不保留权限、时间戳、
空子目录或链接；恢复合计上限 2 GiB。v3需v0.5+，v4需v0.10+，v5需v0.11+，v6需v0.12+；默认v2仍可由v0.2+读取。
SHA-256 用于完整性检查，不能证明来源身份或科学结论正确。当前没有神经压缩、
无限精确上下文或科学推理收益的验证。

[首版 v0.1.0 记录](results/v0.1.0/SUMMARY.md) 与 [v0.2.0 记录](results/v0.2.0/SUMMARY.md) 保留；各版协议不同，不能直接把耗时
变化全归为单个优化。每版本在 [Release](https://github.com/StarlitPupils/RKV-1/releases)
更新改动、结果和限制；tag 不改写。代码 [MIT](LICENSE)。
