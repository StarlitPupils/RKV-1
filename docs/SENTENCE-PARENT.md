# v0.57冻结候选协议：按最佳原句匹配重排整篇论文

v056实际发行proof完整核验后采用候选。9项必要人工合成检查已通过（原string span3、索引/排序/预算/原SDK拒绝4、独立结构offset/重复句和标题冒充/TF篡改审计1、真三方法worker/排重/hint1）；完整298检查以实际log为准，随后代码/协议/input/exactCI先冻结，唯一构建新source sidecar/另冻SHA后正式9worker，未完成不得称交付。

依据v056诊断：graph49个未完整主张仅9个gold全体原记录本身装不下，另40个有容量但原检索未找全；漏62gold仅4单篇>4096。先测试改变检索表示/排序，不扩大预算或改返回单位。上界179/188不是部署成绩，不据此追参数。

唯一新候选sentence_max：原abstract的每个原句各为独立BM25检索单元，只用该句decoded文本（不拼标题/标签/问题/答案），k1=1.2,b=.75、原ASCII tokens/STOP不变。unit BM25得分按parent取最大，unit tie用固定unitID、parent tie用原paperID；每paper只出现一次，再按原全序admit。实际返回仍完整原JSONL论文记录，最多12篇/4096原B，超剩余skip继续，整个parent source字节/元数据计费不缩成句子。默认Memory/CLI/UI/PaperRetriever现有方法不集成新候选。

两个新鲜基线paper_lexical、paper_graph沿v053/55原模型和原排名数学逐字不变；与sentence_max共3方法各3freshworker=9，ABC/BCA/CAB，Random(20261027+round)同题序，600s/worker/0补轮。仍原300行/训练ID或规范化claimSHA重叠排除/实际298/188有gold/110无goldnull，不能因结果更改排除。新候选在项目已见dev上作探索性方法试验，不能称未知数据/独立新科学样本/真实会话验证。

quality gate：sentence_max macro gold-paper recall严格>两个基线，完整gold-paper找全数≥两个，三轮均满足。time gate相对paper_lexical，query wall/CPU/parent完整wall三配对中位数≤1，无epsilon/加轮。另列全部方法逐题胜/负/平，附选中gold论文的best-sentence hint落在任一原标注rationale句集合中的比率（仅定位提示，不评label/NLI）。质量、时间、联合分别报告，不以任一正方向掩盖负结果。完整空间/RAM/新索引构造成本另列，不凭质量门槛称压缩或总收益。

只建一次新无监督source索引：先完整代码/协议/input/合成及全库/CI冻结，再读原corpus+原model构建unit索引，不读dev gold或查询；独占fsync新sidecar并另冻SHA/构造CPUwallparent/RSS/全部component B，再正式评分。不是神经训练/不新增train标签，原监督graph模型仍保留且各worker实际load，sentence候选再load全部新sidecar；新增B/瞬态/索引/运行库/历史训练/原source和所有残留文件都计费。原model不改，不将多载新索引说成免费。

原句定位必须结构解析JSON原string span，保留引号/转义/UTF8原byte offset/length/SHA；原paperID、sentence index及parent rawSHA完整绑定。重复同文本不同paper或同paper不同句不得合并；标题/嵌套decoy字符串不能混作abstract，非法/重复root key、坏schema/UTF8/range明确拒绝。先在人工escaped quote/backslash/Unicode/CRLF/重复句/嵌套额外字段上验证，不在真实source上猜string.find。

每selected parent query实际Store读完整原记录、原SHA/docID/title/abstract哈希校验；sentence候选的best unit再从已验证完整parent原bytes切出核原unitSHA/decoded句值/句号位置，不省parent校验、不另声称物理IO减少。hint只加locator/hash，不把原句隐式增加为预算外原文；返回主context仍整parent，metadata与serialized proof B另计，4096原B不是总prompt/RSS或IO上限。

独立analyzer直接重建原JSONL记录与goldpaper集合/原rationale索引、核实际Store parent范围/whole parent proof与best unit位置、三轮proof确定/整Store树不变/每worker整source恢复。独立排名重放只是诊断，不作新增正式试次或重新训练。保留新方法退步的主张和hint错误/缺失分母，无gold行检索成本也不丢。

独立完整unit catalog审计另用已冻结QASPER原root-member decoder定位abstract成员，再以JSONDecoder.raw_decode逐原数组元素定位，重新计算全部unit offset/length/原SHA/decodedSHA、TF/postings/doc-length/N/avgdl，并与新索引逐项相等；不是调用相同source span构造器自证。重复句/标题同文本即使value和SHA相同也不能冒充其他结构路径位置。全catalog raw内存切片绑定数与selected实际Store范围绑定数分别列，不当新独立科学样本。

输入source/model同v053固定SHA；新sidecar/原科学文本/claim/fullhits/postings/帧恢复副本/私有研究模板个人报告/密钥不发布。0新增模型API旧24耗尽，CPU离线；SSD物理/全系统IO/冷缓存/跨机/真实长期会话/回答收益未测。E3净收益失败、E4整体和无限上下文未验收。

每版必要测试/冻结协议/rawJSON/标准图实际视觉检查/详实报告/README/release/GitHub，CI成功后actual资产SHA/66递归Python+HTML/物理外actualwheel+currentnative/新sdist unit parser/父定位/排序与旧API功能/finalproof重下载后完整收尾。正式索引/九worker/结果目前均未开始，不把工具草稿或上界当新候选已通过。
