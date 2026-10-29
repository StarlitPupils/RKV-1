# 下一个完整离线候选草案：固定预算的分数/原记录字节排序

状态：v085完整实际资产与安装核验已完成，候选已公开采用。8项必要owned检查通过；真实270查询结果未知，未冻结/正式/交付。0新API/训练/模型下载；API48授权已花完。

根据v085排除单条原record>4096的多数假设（0/5）后，提出一个新单候选B：同一旧BM25正分候选全集，把既有binary-float BM25分数以精确Fraction除以原JSONL recordB，值降序/ID升序，再用旧12/4096原record准入。A旧词法顺序，C只按原长度升序（同正分候选，仍有查询过滤信号，不是假装完全无关）；0新可调参数、没有改预算/记录表示/源验证，不扫alpha/候选数或只挑旧16题追正。score密度是已知工程启发式，不称学术原创或语义推理。

主评测拟固定全部原SciFact dev去trainID/normalized-query及旧v01512和v08416的ID/query重合后的剩余集合，所有剩余问题都检索；annotated宏paper recall/完整来源组作质量分母，无标注只读检索成本、质量null，不能猜NEI。主集合依然是项目已多次使用的公开dev，不称未知泛化；原16模型题只作已见诊断secondary，不换headline。先只做身份/数量/SHA准备，预测结果禁止读gold；保持原model f062 SHA/StoreSID/12/4096，旧查询SOURCE/WIRE预算不扩大。

建议三角色×3轮=9freshworker固定ABC/BCA/CAB，不用重复轮次作独立科学样本。H1同source/原locator/SHA/每次实际selected原record恢复、预算/原baseline与旧标签分母审核；H2 B在primary annotated宏recall严格大于A和C，完整gold组数量均不低于两者；H3 B/A完整constructor+全部query wall/CPU与parent三轮均<=1，0CPU分母null不pass。B/C诊断不换headline，联合H2/H3都满足才说本机该表示综合门槛通过，仍不称API回答收益/科学NLI/长会话/无限上下文。Fraction维护/排序/额外RAM/源码与整库/旧10MBmodel/Store/历史source/全部残留全计，length-only控制若不弱仍保留不改。

源/协议/精确primary数目和分母/原inputSHA、每角色CPU读写范围、全部timers与预算先冻结/exactCI，后唯一正式9worker0retry；独立old词法score/Fraction交叉乘积排名/实际Store/query-source proof/候选宇宙与所有预算再审计。必要owned检查包含tie/原始长度/NaN/布尔/陌生ID/预算不绕过/源损坏/实际toy Store及full worker。当前没有新科学结果，仅3项pure必要测试，无实际worker；不要拿准备或采样元信息当性能验证。


身份/分母准备已完成（仅元信息，无方法评分）：primary270问题、168有标注/102无标注质量null、270唯一normalized query；排除旧API28题及train重合，数据仍为已见dev不称独立新科学。questions-private/gold-private及SHA已单独保存；三角色×3轮=9workers，primary正式2430本地查询(270×9)，不把三轮当独立问题。原16题不再列单独新评分worker，若需secondary只比较既有数据不额外模型调用。

实现准备补充：cost_aware_worker.py已具备3角色原Store读取/逐rowSHA/标题摘要SHA sourceproof、独占query文件与fsync、完整constructor+query-读取-核验-proof写出phasewall/CPU和workerfinally/RSS；5项owned检查通过，含数据损坏拒绝、问题字段禁止gold、raw单位12/4096、旧SDK baseline相同。Baseline A直接调用旧PaperRetriever.query，不加新cost-order guard开销；B/C包含自身新验证/Fraction或排序开销。不得用给baseline加observer慢循环掩盖新算法CPU成本。原数据未评分，所有科学结果未知。

正式精确定稿：primary270问题/168annotated/102无标注质量null；3methods×3round=9freshworkers，round顺序lexical-score_per_byte-length_only、score_per_byte-length_only-lexical、length_only-lexical-score_per_byte，全部2430本机query。每worker600秒0retry；模型只load/validate一次，A直接旧PaperRetriever.query，B/C新验证/排序全部计phase。phase=constructor+270query(score/rank/admit/原Store读取SHA/JSON identity/标题摘要SHA/proof canonical与fsync写出)，完整parentwall含Pythonstartup/input与processfooter，子进程从module time import至finally before footer的wall/CPU另报；run-body计时不是进程全程，两个字段不能混称。所有9预测目录完整后才读gold，独立跨乘积排序、来源SHA/元数据/原字节审核和所有宏recall exactFraction/complete/缺失分母核对；三轮纯机械复测不当独立科学。数据/方法/预算/顺序/primary不可看结果后改。worker不得读取gold-private文件或先预测后当作sourceStore。源码fullRuntime和API48旧支出/全部残留保留，不加API调用。
