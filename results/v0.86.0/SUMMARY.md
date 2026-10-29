# RKV-1 v0.86 实验报告：固定原记录预算的分数密度排序

## 结果与门槛

H1排序/原source/预算/预测先于gold/独立审计与完整计时True；H2密度排序宏来源recall严格优于旧词法及长度控制、complete不低 **False**；H3密度/旧词法完整phasewall、CPU和parent三轮均<=1 **False**；联合 **False**。该结果只为已见公开dev的本机source retrieval；没有新API、语义模型、科学NLI、回答或无限上下文收益。不能把168来源标注评分当模型答案正确率。

|方法|annotated宏paper recall|全部gold论文完整题/168|原source bindings（轮1）|
|---|---|---|---|
|lexical|0.7624007936507936|126|777|
|score_per_byte|0.5785714285714286|95|1115|
|length_only|0.011904761904761904|2|1856|

## 固定方法与数据

旧lexical、单候选score_per_byte、length_only控制，同BM25正分候选全集/旧model SHA/原SID/12wholepaper4096B。B用binaryfloat原BM25分值的精确Fraction除原JSONL recordB，降序/ID升序；无alpha、温度、候选数、预算或训练搜索。C仍有query正分过滤，不假装是完全无关噪声。A直接旧PaperRetriever.query，未人为给其加新guard或慢observer；B/C新验证与排序CPU全部在phase。

固定主集合270原dev题，剔除旧v01512和v08416的ID/query与trainID/query重合；168annotated、102无标注质量null、270独特问题。数据被项目使用过，不能称封存未知科学泛化。无根据新候选得分筛题；原API16题不混入headline，也没再调用模型。源码/协议/input SHA freeze `2abb53c543b6fedb3ee69774441064096ee80779`，exactCI 40840682897成功后唯一9freshworker，ABC/BCA/CAB三轮；2430本机query是机械复测，不是2430独立科学问题。544全回归543pass1权限skip、8owned检查覆盖Fractiontie/非法float/原bytecap、真实9Store原bytes/损坏拒绝/gold字段与fresh subprocess时钟。

## 独立核验与资源

全部9worker270份预测/proof持久化和子进程退出后才解析gold，时间线另存。后置独立old词法、整数交叉乘积比较（不调用新order）和旧admit重建所有方法排序/预算；共11244原record绑定及完整corpus1次恢复，实际应用返回17721659B，原locator/docID/title/abstract SHA完整核。每method三轮proof一致；annotated宏recall用精确Fraction，complete和缺失分母独立复算。原注释不穷尽所有相关证据，无法把无标注当错误或NEI。

algorithm phase含constructor+270query（score/rank/admit/原Store读取SHA/JSON身份/标题摘要SHA/proof canonical/fsync写出）。run-body、module entry→finally前过程、parent完整process（含Pythonstartup和footer写出）三类计时分开，不能混称或用共同成本掩盖新算法慢；全部CPU/RSS和父计时在rawJSON。冷缓存/跨机/SSD全系统IO未测。原record预算不是SSD物理读取上限；未创建新索引/模型不代表旧10MBmodel、源码、PythonFraction/RAM或Store免费。

整库实际67Python+HTML、全部scripts、新代码/测试/协议/旧模型/Store与270questions/gold及全部worker2430query files/outer日志/私有准备sizeSHA均分列。旧science/human/train/model/旧24+48API费用/快照/CAS/帧/restored/derived/失败全保留，无通过删除diagnostic文件声明压缩。analysis自身完整finally/parent另外附，0CPU分母null不pass；所有负结果保留。

![质量与完整阶段时间](cost-aware-sources.png)

图已实际视觉检查：三方法质量柱、完整覆盖题数和三轮时间比均清晰，原图无裁切。本报告不等于完成发行。完整localinitialbuild→物理外actualwheel/currentnative/newowned+alllegacyactualsdist→finalbuild/sourceaudit0→ReleaseCI→实际7SHA/全递归source/外publishedinstall/proof8齐才交付。原science/model/原APIprompt-response/私研/课程模板个人报告/密钥不发布。v084/v085的scope人工措辞仅追加更正，原数值/数据/tag/proofSHA保持，记录见docs/PUBLICATION-SCOPE-CORRECTIONS.md。

## 三轮完整成本与结论

|轮|B/A算法wall|B/A算法CPU|B/A完整parentwall|
|---|---|---|---|
|1|4.741315|4.647541|4.492718|
|2|4.553122|4.785714|4.358595|
|3|4.537880|4.689655|4.311926|

密度排序比旧词法多放入原记录，但标注宏来源recall从76.24%降到57.86%，完整覆盖题数126降到95；长度控制仅1.19%与2题。这反驳了本轮“以分数除原字节即可同时改善质量与成本”的候选，保留旧词法默认行为。结果不能证明所有成本感知检索都无效，也不能从更多记录数推断更好证据。停止在此已见集合调分母、系数或预算追正；下一研究需新的预先声明假设与独立评估。0新模型调用，原API回答质量不回填或改变。

## 原始三轮资源摘要

|轮/方法|constructor+query wall s|CPU s|完整parentwall s|process finally wall s|peakRSS B|应用返回B|
|---|---|---|---|---|---|---|
|1/lexical|1.905982|1.906250|2.044746|1.994799|78553088|1060585|
|1/score_per_byte|9.036861|8.859375|9.186467|9.135272|78090240|1055107|
|1/length_only|2.753570|2.593750|2.891051|2.846564|78426112|1022236|
|2/lexical|1.904070|1.750000|2.038334|1.992704|78209024|1060585|
|2/score_per_byte|8.669461|8.375000|8.884273|8.763742|78430208|1055107|
|2/length_only|2.737024|2.703125|2.873981|2.830061|78540800|1022236|
|3/lexical|1.898554|1.812500|2.032652|1.985715|78385152|1060585|
|3/score_per_byte|8.615408|8.500000|8.764647|8.710697|78458880|1055107|
|3/length_only|2.744764|2.625000|2.882746|2.837784|78434304|1022236|

peakRSS为各fresh worker的进程峰值，不是新排序器专属占用；原record返回B仅应用读取工作量，未测底层SSD。没有给此候选计入新模型训练或远程推理零费用替代旧成本：原模型10152832B、Store、全部历史原数据和API成本始终另列，远端内部weights/runtime/RAM未知保持null。独立分析parent完整wall为30.0980254s，子过程CPU/wall和环境见analysis-finally与parent文件；分析重复访问不是新样本。
