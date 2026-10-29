# RKV-1 v0.85 实验报告：原API漏检的排名与准入审计

H1排序/原选集/原source与完整计量 **True**；H2“5个missing来源中单条记录自身>4096B者严格过半” **False**，实际 **0/5**。这是原v08416已见问题的事后诊断，0新API/训练/科学验证，不是新的回答收益或泛化试验。原v08448输出/9对4对4、p=.125、全部计时/失败保持不改。

## 先验、冻结与分母

source/protocol/input freeze `f014dd70277b9d9f1b21f35e6fd39655bf24f961`，exactCI 40836348267成功后唯一1fresh worker16case、0retry/600s上限。原模型10152832B/f062 SHA、corpus8307875B/b8d6 SHA、原SID/16question+gold/全部48API请求响应slot和旧tag结果SHA先冻结。已知43selected/12gold/5missing仅用于fidelity分母，没有预看真实rank/record length分类。6项owned检查+536回归535pass/1权限skip，preflight仅17paper/合成budget，不扫4096阈值。初次准备manifest脚本漏json import在冻结/正式前修正，原trace保留，不是实验重试。

## 诊断方法

独立ASCII旧STOP词法/BM25 k1=1.2 b=.75复算，与旧词法函数在1e-12数值和完全同序比较；固定12wholepaper/4096原recordB顺序准入，原gold分类如下：{'recovered': 7, 'no_candidate': 0, 'byte_rejected': 5, 'count_stop': 0}。每个gold的原rank、原记录B、到达前已用/剩余B/已选数、是否单条超完整cap见raw和derived JSON。byte_rejected同时可能由低排名先耗费预算造成，不能把其分类直接当纯预算因果，更不能推导加预算/切句子必然提高模型答案。

## 独立原字节复核

worker恢复完整corpus1次并核SHA、原selected+gold48record bindings；后置独立fresh Snapshot再次恢复完整corpus1次和48bindings，与全部43旧selectedIDs/原locator/title/sentences/SHA匹配。缺gold和已选复合时同一问题按并集实际读取，不用prefixSHA代替恢复。后置实际应用返回8380618B，worker独立记录其应用返回B；ledger文件SHA读取/元数据/缓存另有成本，非SSD物理或全系统IO。536检查535pass1skip。worker/finally和parent完整计时、分析自己的finally与parent另附；CPU零分母不造时间收益。

## 资源和限制

整库实际67Python+HTML、全部scripts/专用代码/测试/协议/input与私有旧模型/Store/CAS/所有原APIprompt-response/所有残留sizeSHA逐项记账，复用不免费，旧science/human/train/models/帧/restored/derived/失败不删除抹费用。当前0新模型调用、旧24与v08448支出保持，远程权重/物理IO等未知保留null。H2是结构性必要限制检查，不是生产压缩/性能优化或科学蕴含证明，fullE3净收益/E4整体/开放NL/真实长会话/回答/无限上下文未完。

![原记录与预算及排名](api-admission-audit.png)

图需实际视觉检查后记true。完整代码/原JSON/报告/README/release及localinitialbuild0→物理仓库外actualwheel-currentnative/newowned审计+alllegacyactualsdist→finalbuild/sourceaudit0→ReleaseCI→实际7SHA/全递归source/外published安装/proof8齐才算交付。原science/model/prompt/response/私研/课程模板个人报告密钥不发布。

## 缺标注来源的具体位置

下列原record各自均可装入4096B，结构性超长假设0/5不成立。图中蓝色=已入证，橙色=未入证。

|claim ID|原词法rank|原record B|到达时剩余B|差额B|
|---|---|---|---|---|
|1019|2|1835|1759|76|
|540|7|1369|847|522|
|185|4|2199|130|2069|
|921|2|2664|2642|22|
|1241|225|2029|418|1611|

两个遗漏原rank为2，差额分别76B/22B；一个rank225。它们共同显示排序和累计准入相互作用，不能统一称文献太大，也不能仅从此诊断证明加预算、截短或任何新排序必然改善模型回答。原4096/12与旧48输出均保持，0额外调用。
