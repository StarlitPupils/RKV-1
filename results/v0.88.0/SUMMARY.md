# v0.88 两批原回答的来源可得性与失败定位

H1独立原96输出/来源/判定/分类核验通过；H2各批缺标注论文占grounded失败严格多数：{'v084': True, 'v087': True}。0新模型调用、训练或检索试次；32个已见问题、96原输出及24个主有标注retrieved，非新科学样本。

|批/条件|各类别计数|原题数|
|---|---|---|
|v084:empty|{'unannotated_proxy': 4, 'no_annotated_paper_available': 12, 'annotated_paper_available_verdict_wrong': 0, 'verdict_correct_rationale_incomplete': 0, 'grounded_correct': 0}|16|
|v084:retrieved|{'unannotated_proxy': 4, 'no_annotated_paper_available': 5, 'annotated_paper_available_verdict_wrong': 2, 'verdict_correct_rationale_incomplete': 0, 'grounded_correct': 5}|16|
|v084:rotated|{'unannotated_proxy': 4, 'no_annotated_paper_available': 12, 'annotated_paper_available_verdict_wrong': 0, 'verdict_correct_rationale_incomplete': 0, 'grounded_correct': 0}|16|
|v087:empty|{'unannotated_proxy': 4, 'no_annotated_paper_available': 12, 'annotated_paper_available_verdict_wrong': 0, 'verdict_correct_rationale_incomplete': 0, 'grounded_correct': 0}|16|
|v087:retrieved|{'unannotated_proxy': 4, 'no_annotated_paper_available': 3, 'annotated_paper_available_verdict_wrong': 2, 'verdict_correct_rationale_incomplete': 0, 'grounded_correct': 7}|16|
|v087:rotated|{'unannotated_proxy': 4, 'no_annotated_paper_available': 12, 'annotated_paper_available_verdict_wrong': 0, 'verdict_correct_rationale_incomplete': 0, 'grounded_correct': 0}|16|

分类依据原提供的任一annotated paper是否存在，不要求所有gold论文，同时不证明语义充足。判定正确但无标注来源不算grounded；无标注质量保持null，零失败分母null，半数不算多数。缺来源不是增加预算必然有效的因果证明；有来源仍错也不能只归因模型，标注不穷尽、提示和有限上下文均可能影响。原两批答案/时钟/模型预算不改，不以合并样本替代原门槛。

worker和独立审计各重核89来源绑定，独立应用返回125625B，非物理SSD或全系统IO。所有原prompt/原响应/科学原文/模型及密钥私存；public仅ID/SHA/计数/分类。完整parent/body/main-finally及分析时钟/RSS另列；旧模型、Store、全部历史科学/训练/API/派生/失败/源码费用不归零。冷缓存/跨机/真实长会话/科学NLI/无限上下文未测或未完成。

![原回答失败定位](failure-diagnostic.png)

图已实际视觉检查，图例在数据区域外、分段计数清晰；全部本地打包/外安装/CI/实际发布资产与proof核验齐才交付，当前报告不是完成发行。

## 主有标注问题的完整失败表

|原批|有标注retrieved|缺标注论文|有论文但判定错|判定对但依据不全|grounded正确|失败分母|缺论文占失败|
|---|---|---|---|---|---|---|---|
|v084|12|5|2|0|5|7|5/7=71.43%|
|v087|12|3|2|0|7|5|3/5=60.00%|

两批H2均通过，但不能把5/7与3/5当独立新科学实验。24有标注retrieved合计8缺论文、4已有来源仍判定错、0仅依据不全、12grounded正确，8无标注仅proxy另列。条件对照96份原输出全保留，原API正确率及依据率不改。该分类提示后续需同时研究证据召回和已提供来源的理解错误；不能推断单加预算、单换模型或补齐某篇必然修复答案。

正式worker完整parentwall0.2285166s、parentCPU0s为系统计时粒度记录；独立分析parentwall0.853467s、parentCPU0.015625s。正文、main-finally、parent分别作用域，原JSON保留；不把零parentCPU当无CPU成本。图例移至图外并标注计数仅改展示，展示重绘耗时独立记录，不回填原科学或审计时钟。

## 冻结身份与必要验证

源码/协议/input冻结0b8798d37af3a0a0833f1aeb2aa28ab96e279635，exactCI40857860441成功。556项检查555通过、1权限skip；新增7项覆盖全部互斥类别、grounding矛盾拒绝、严格多数半数反例、零分母null、任一gold不等全gold、私有输入SHA篡改拒绝与真实9文献Store的2×48fake响应端到端审计。合成检查不当科学结果。唯一正式worker及独立审计已完成，不重跑覆盖。

源码上传初次沿用旧额度参考值，在任何blob/ref和正式评分前被guard拒绝；原日志保留。读取官方当前额度并仅修正私有运输helper的窗口参考后恢复未执行的上传，源码/协议/input和正式结果未改，没有重复科学实验。
