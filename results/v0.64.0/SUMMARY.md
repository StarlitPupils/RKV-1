# v0.64.0 实验报告：实际检索论文上的CPU词面支持/反对关系probe

## 结论与判别对象

**H1关系分类质量False / H2局部CPU与model可行性True / 本probe联合False**。这是known SciFact上小型词面二分类可行性候选，不是可靠NLI、形式证明、医学/科学结论或生成回答。`scientific_entailment_verified`对全部模型/预测始终False，`generated_answer`始终None。若局部门槛通过，也不能当E4整体或真实长期会话完成。

本轮pair balanced accuracy0.511001，低于claim-only0.522112和label-shuffle0.522222；conditional判对97/146，低于多数类101/146，allgold正确覆盖97/209（0.464115）。pair模型8545B，分类wall约0.235s/1000输出pair，局部资源上限通过但质量失败，不能以模型小/运行快冒充科学判别收益。

12 fresh worker以同一冻结BM25真实检索来源为输入，先对实际返回整paper预测，再读取gold relation标签。未给gold文档/人工rationale选择当oracle输入，12份全部source retrieval proof逐题等于v053原lexical。旧source缺失不会被分类器魔法补齐，结果分母如下。

| 方法 | retrieved明确gold balanced accuracy | retrieved明确gold conditional accuracy | correct / 全部明确gold | 全gold正确覆盖 |
|---|---:|---:|---:|---:|
| majority | 0.5 | 0.6917808219178082 | 101/209 | 0.48325358851674644 |
| pair | 0.511001100110011 | 0.6643835616438356 | 97/209 | 0.46411483253588515 |
| claim_only | 0.5221122112211222 | 0.6712328767123288 | 98/209 | 0.4688995215311005 |
| permuted_pair | 0.5222222222222223 | 0.7054794520547946 | 103/209 | 0.49282296650717705 |

H1严格要求pair balanced accuracy胜多数类、claim-only与label-permuted三个控制，且全gold正确数不低于三个控制；若某class分母缺失或shuffle无效，gate False/null。3轮均须满足，不挑最好一轮。此为预定工程门槛，单known-dev点结果/三机械重复不证明独立科学泛化或统计显著。

## 分母、unknown与缺失保持

每worker原300dev排2 train ID/normalized overlap，298检索/188有source标注/110无source标注。每worker所有实际输出claim-paper pairs **853**，其中retrieved且明确relationgold **146**，全明确gold **209**，没检回明确gold **63**；ambiguous gold **0**、实际selected ambiguous **0**，selected但没有该claim关系标注 **707**。

110无gold和selected未标注paper都保持unknown，不能作为NEI、反对或真负例。分类器仍对全部返回paper给出实验预测，但其未标注部分错误支持率/precision没有groundtruth可核，不能从条件准确率推出全pipeline验证成功。`all_labeled_gold_correct_coverage`把未检到明确gold也留在分母，不能用conditional accuracy掩盖检索失败。

| 方法 | 全明确gold各class | retrieved明确gold各class | 正确各class | retrieved明确gold混淆矩阵（row为gold） |
|---|---|---|---|---|
| majority | {'CONTRADICT': 71, 'SUPPORT': 138} | {'CONTRADICT': 45, 'SUPPORT': 101} | {'CONTRADICT': 0, 'SUPPORT': 101} | {'CONTRADICT': {'CONTRADICT': 0, 'SUPPORT': 45}, 'SUPPORT': {'CONTRADICT': 0, 'SUPPORT': 101}} |
| pair | {'CONTRADICT': 71, 'SUPPORT': 138} | {'CONTRADICT': 45, 'SUPPORT': 101} | {'CONTRADICT': 5, 'SUPPORT': 92} | {'CONTRADICT': {'CONTRADICT': 5, 'SUPPORT': 40}, 'SUPPORT': {'CONTRADICT': 9, 'SUPPORT': 92}} |
| claim_only | {'CONTRADICT': 71, 'SUPPORT': 138} | {'CONTRADICT': 45, 'SUPPORT': 101} | {'CONTRADICT': 6, 'SUPPORT': 92} | {'CONTRADICT': {'CONTRADICT': 6, 'SUPPORT': 39}, 'SUPPORT': {'CONTRADICT': 9, 'SUPPORT': 92}} |
| permuted_pair | {'CONTRADICT': 71, 'SUPPORT': 138} | {'CONTRADICT': 45, 'SUPPORT': 101} | {'CONTRADICT': 2, 'SUPPORT': 101} | {'CONTRADICT': {'CONTRADICT': 2, 'SUPPORT': 43}, 'SUPPORT': {'CONTRADICT': 0, 'SUPPORT': 101}} |

只比较SUPPORT/CONTRADICT人工显式标注；label冲突单列ambiguous，不任选标签或删去未记录反例。原[官方schema](https://github.com/allenai/scifact/blob/master/doc/data.md)定义证据rationale的这两种标签，官方[项目说明](https://github.com/allenai/scifact)区分oracle/open retrieval及label prediction。本项目数据已被旧来源实验使用，不能称未知科学测试或与官方大模型性能直接同口径对比。

## 固定方法、训练与四模型身份

每claim和实际返回paper title+整abstract作为字符串输入，tokenizer为casefold ASCII alnum全词（包括stop/否定）。claim/document/minTF共有词各128个SHA256固定bucket，logTF后bucket求和、各channel L2归一；再加claim/doc是否有no/not/never/without/neither/nor、二者异或、claim词集合被doc覆盖分数四标量及bias，共389维。没有语法、因果、数量推理或语义嵌入，hash碰撞/词序丢失是方法局限；原科学证据仍逐字节留在CAS。

A多数类，仅训练计数；B pair-linear；C claim-only-linear（文档和共享词channel/doc标量恒0，防止把主张措辞线索当证据使用）；D相同pair features但训练labels用seed20261027一次打乱并保持class marginal。3fit在同一campaign按B/C/D训练，固定200epoch fullbatch logistic、lr.5、L2=.01不罚bias，初始bias log((support+.5)/(contradict+.5))其他0。未根据dev调超参或选择最佳epoch，终端loss不是科学收益。

原train809行只取显式标注claim-paper；normalized-questionSHA+paperID归组去重，同group多label记录ambiguous并排除该训练group，无gold行不训练负类。实际训练统计 `{'all_unique_pair_groups': 562, 'ambiguous_unique_pairs': 0, 'input_rows': 809, 'physical_annotated_claim_paper_rows': 564, 'unannotated_rows': 304, 'unique_CONTRADICT': 194, 'unique_SUPPORT': 368, 'unique_unambiguous_pairs': 562}`；3fit和多数类完整费用分别如下。

| 方法 | 完整model JSON B（含metadata） | fit wall s | fit CPU s | fit期观察peak RSS B | model SHA256 |
|---|---:|---:|---:|---:|---|
| majority | 488 | 0.000068 | 0.000000 | 69369856 | e4f8d05a688935f476b846751185c58fbc4a5ac9d73ce2c2abe94ed01cb02996 |
| pair | 8545 | 3.953629 | 3.890625 | 73728000 | aad660b51b3361177311212e920a52b08115afa047c3af6aa911b8781bdc9961 |
| claim_only | 4211 | 4.146465 | 4.093750 | 73728000 | 25ffc7eb96bd69ef8360fae01a7f77c70281b10464e4cc13fed0425c6a856fd7 |
| permuted_pair | 8563 | 3.736788 | 3.734375 | 73756672 | fe6ed6235947995c1c56fbeba0b4682e3b3e827f20c0e0b90b29abf73a9e3870 |

训练campaign wall 11.911443s、CPU 11.781250s、观察peak RSS 73756672B；完整训练parent `{'error': None, 'parent_full_process_wall_s': 12.007936300011352, 'return_code': 0}`另列。原source检索索引10152832B及旧训练CPU/字典/graph继续保留；各worker只加载当前method model，不让多数类承担不需要的其他weights/feature工作。所有4模型原文件/训练identity记录/摘要/model-freeze完整目录实际114942B留本地，weights/原训练样本不发布。

code/protocol/input freeze `125924b3e485794d2f1ec0d93a8dc27130c35e1d`、exact CI `40452438712`成功后才真实训练campaign一次（明确3个fit，不是假装只有一个model成本），exclusive四model SHA固定先于首次新关系dev预测。模型/CPU/log/loss全部保留，不重训追正结果。

## CPU可行性与完整pipeline代价

| 方法 | 分类wall /1000实际输出pairs s | 分类CPU /1000pairs s | 全query+sourcewall中位s | 对应CPU中位s | parent完整wall中位s | 三轮观察peak RSS最大B |
|---|---:|---:|---:|---:|---:|---:|
| majority | 0.002476 | 0.000000 | 1.213307 | 1.218750 | 2.018598 | 122544128 |
| pair | 0.233929 | 0.201495 | 1.426984 | 1.421875 | 2.241174 | 122368000 |
| claim_only | 0.072981 | 0.109906 | 1.279309 | 1.234375 | 2.107746 | 123379712 |
| permuted_pair | 0.228655 | 0.274766 | 1.411682 | 1.359375 | 2.224740 | 123011072 |

H2是预定局部资源可行性：pair当前完整model≤1MiB、分类phase wall/CPU各≤2s/1000输出pair，3轮全过。这个预算在真实train/dev前已固定，未加宽。分类phase含feature extraction与dot/sigmoid；原source read/JSON parse/全部验证、检索、模型加载在同query/worker/parent另计。H2不是对多数类或全pipeline提速，也不是压缩净收益；更慢的source读/构造/训练不能藏在分类phase外。CPU短区间零值可能受本机计时分辨率影响，0不代表免费CPU；分母0则null/False，无epsilon或补轮。

sigmoid `support_score_uncalibrated`未做概率校准，不等于“科学结论为真概率”，高分也不设置verified或生成答案。RSS是观察峰值，不是纯增量/精确常驻RAM，byte cap不是RSS cap。平台/解释器/依赖/pycache未全部归因，源码和weights不是全机TCO；物理SSD/全系统IO/冷缓存/跨机未测。

## 独立审计与实际证据

349检查348pass/1Windows权限skip，新增9项覆盖hashchannel/L2/否定/稳定、claim-only完全不依赖doc、有限差分核梯度、toy训练确定、label shuffle marginal/多数类无weights、modelSHA/nonfinite/参数/单class拒绝、明确label/duplicate group/冲突/unknown不作NEI、独立dense features/logit/全部gold与missing分母、以及实际toy Store四角色完整训练写盘/每个实际返回paper预测先于gold读取。

正式4方法×3轮=12，ABCD/BADC/CDAB，原12wholepaper/4096原recordB不变，每轮shuffle20261027+round，600s/worker、0retry/重训/threshold调整。所有原source范围/ID/title/abstract/模型输入projection SHA核验后才预测；gold relation和source指标在全部该claim预测完成后才读取。12source readonly ledger和完整恢复通过。

独立analyzer不用candidate RelationProbe/features，自己重算dense token/hash/channel/logit与score（1e-12容差、label完全相同），核训练group/明确label counts/3个terminal objective（不重做optimizer、不算新训练），claim-only doc维weights恒0、shuffle一次marginal和source SHA。实际原source位置/字节/metadata/proof绑定 **10236**、独立预测核对 **10236**，四角色prediction proof跨轮确定，全部298source retrieval proof每method每轮都与原v053 lexical相同。独立重新核全部explicit/unknown/ambiguous/missing class分母及混淆/conditional/allgold、各模型/全部真实文件B和parent-child SHA。

追加auditwall 18.315481s、CPU 16.312500s、观察peak RSS 165867520B单列；独立terminal training objective3次只是已有weights审计，额外source rebindings和prediction重算不是新正式trial/训练。原始JSON和失败也保留，不以loss下降/机械byte校验冒充NLI收益。

## 全部源码、model与历史文件账本

66递归Python+HTML 426112B，专用relation runtime源码8667B、全部assessment/test/protocol/input逐文件B/SHA见source-resource；各role整个model bytes/metadata，不只算浮点payload。base/sourceCAS/旧E2/E3模型/旧snapshot/负迁移/原v061词语关联/数据副本仍在，沿历史账本保留，不能因private不发布当0B。raw child/parent JSON 10845772B、formal worker log 0B，图/环境/分析/训练summary/sidecar另计。各worker实际源副本、CAS和plan/private查询/ledger如下。

| 轮 | 方法 | 实际文件分组B |
|---|---|---|
| 1 | majority | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |
| 1 | pair | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |
| 1 | claim_only | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |
| 1 | permuted_pair | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |
| 2 | majority | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |
| 2 | pair | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |
| 2 | claim_only | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |
| 2 | permuted_pair | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |
| 3 | majority | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |
| 3 | pair | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |
| 3 | claim_only | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |
| 3 | permuted_pair | {'other_worker_files_bytes': 98337, 'source_copy_bytes': 8307875, 'store_bytes': 2963638} |

![实际检索证据的弱词面关系对照](relation-probe.png)

图已实际打开核验，conditional balanced和allgold正确覆盖分图、0–1完整轴，分类budget单独表，不把未标注unknown画成负类，也没有“回答准确率”。真实science/claim原文/fullhits/model weights留本地，public rawJSON只有ID/SHA/指标/实验预测/显式标签与计数。

## 复现与交付范围

```text
python -m scripts.run_relation_probe --train --inputs data/scifact --work NEW_PRIVATE_TRAINING
python -m scripts.run_relation_probe --inputs data/scifact --model FROZEN_RETRIEVAL_JSON --model-freeze FOUR_MODEL_SHA_RECORD --work NEW_PRIVATE_WORKERS --out NEW_RESULTS
```

须按协议先source/protocol/input+CI冻结，训练campaign一次、另冻4model SHA再正式推理。路径exclusive，不覆盖原失败。RelationProbe仅研究scripts/sdist，不默认写入SDK/UI/Memory/归档或生成科学答案，旧格式兼容/字节恢复不变。

代码/必要测试/冻结协议/rawJSON/标准图/本详实报告/README/release，CI后actual7base资产SHA/递归66+HTML/Rust+scripts/物理外actualwheel/currentGear/currentpostings/actualsdist新关系3fit+多数类/独立score/unknown分母与所有旧smoke/finalproof8重下载才完整交付。0远程模型（旧24已耗尽），E3净收益/E4整体/可靠NLI/回答/真实长期会话/无限上下文未验收。
