# v0.70.0 实验报告：受限英语输入与预测后的形式语义对齐

## 本轮结果和实现范围

H1全部问题正确且接受至少95%/三class齐 **True**；H2全题受限English对齐/完整closure/64恢复 **True**。固定官方OWA test前64理论共 **1394** 问题，正确 **1394**，allquestion accuracy **1.0**，独立接受 **1394**。所有unsupported、语义对齐失败、work不足和冲突都留分母，不只展示可解析子集。

本版预测器输入从给定formal representation推进到**受限合成English**。只读triples/rules.text与query.question进行预测，providedrepresentation/gold/proofs不用于预测。全部预测先持久化，之后providedrepresentation仅作独立对齐oracle，可拒绝错误解析，不能纠正/重跑预测。实现范围是声明过的人工控制语法，`unrestricted_English_NLI_verified=False`、`scientific_entailment_verified=False`，无生成回答；不能称开放科学NLI或真实长对话已完成。

v0.69在dev64、1360题使用给定形式表示，v0.70在test64用English，两者输入与样本不同，不能由两个百分数宣称同题提升。E3净收益/E4整体/可靠科学问答/无限上下文仍未完成，原科学词面关系分类负结果保留。

## 数据、冻结与精确次数

官方[ProofWriter入口](https://allenai.org/data/proofwriter)指向原V2020.12.3 archive，214185889B/SHA `bbc5694901e8306d0bd659aa1ad53ccfd02c201864f4b320ffa3777827d1fc26`。原archive/README/32train行/完整test行与私有proof都留本地，不发布原文。只用OWA显式负前提，不支持CWA NAF。原[论文](https://aclanthology.org/2021.findings-acl.317/)提供数据背景，论文模型成绩不当本项目收益。

人工grammar只看32train source.text：初版25/32解析，复数they动词和literal'bald eagle'模板补齐后32/32派生语义与给定source一致。初版25/32和private It被误认人名的测试失败日志保留；修复后reserved/unbound pronoun拒绝。没有dev/test English用于grammar设计；v0.69开发集已用于formalrepresentation实验，此事实保持，不称所有benchmark都未见。当前test成员内容在本版freeze/exactCI之前未打开。

完整395检查394pass/1既有Windows权限skip（389old+4parser/2worker必要测试）。代码/协议/input冻结 `7621aebba20aa26df272e4b922a3817d1aff43ab`，exactCI `40465723718`成功后才读取OWA/depth-5/meta-test.jsonl前64物理行，不挑class/depth；prefixrawSHA/size在任何test预测/scoring之前落盘另冻，见first-access-input-SHA。1freshworker/600s/0retry。all64theory全部问题入分母，实际问题数首次读取后报告，未根据答案调整数量、grammar、work或source预算。0训练fit、0模型加载、0模型API。

## 受限English方法

支持proper人名、The/the小写animal（含训练中出现的bald eagle）；is/are属性与not；6固定动词eats/likes/needs/sees/visits/chases及do/doesnot基本形；bound they后复数基本形；If...and...then...最多3前提、it/they回指规则变量、属性ellipsis；All/optionalAll逗号属性people/things规则。句末period、无换行/双空格、长度8192内；未声明句法不做模糊语义fallback。大写It/They/He/She等reserved不误认propername，未绑定pronoun拒绝。原JSON整体先解码，因此providedreference/gold字段存在于对象里，但预测phase禁止access这些值，guard测试实测；EnglishCompiler只访问text，query只访问question。

OWA not前提转换为显式hardnegative，仅有正证据缺失不能满足负前提；CWA明确拒绝。复用v0.69稳定symboliccompiler把grammar输出映射到分离u/r/c namespaces，旧signed/sourceSetEngine不改，原100000逻辑work/1MiBloaderpayload/1024record64rule上限不调。unsupportedsource让整理论全部题abstain，unsupportedquery仅该题abstain，所有仍在分母。

## 后置独立oracle对齐与原来源

每个English生成的derivedrecord绑定original.json整行SHA、JSONpointer到.text、实际sentenceSHA和derivedlineoffset/length/SHA。query原questionSHA也保留。DAG指向派生file，不能称其offset是原英语字符串offset。

每理论所有预测与certificate先exclusive存盘，然后独立audit从实际Store原JSON读取**给定formalreference**，用独立parser重建期望derivedrecord并比English生成的完整files/mapping；query同样在预测后比较formalreference。只有reference对齐、原recordDAG和独立完整closure都通过才计accepted/correct。这个oracle仅能拒绝错parse，不能给预测器提供formal答案或修改预测。它证明当前受限parser输出与数据给定语义一致，不是新的独立人类科学语义标注或开放NL理解。

新增worker测试在所有预测文件落盘前对representation/answer/QDep访问抛错；完整True/False/Unknown例通过。另一测试让English与给定representation故意不符：即使raw预测可能匹配gold，也必须拒绝acceptance，不用oracle修正重跑。unsupported全理论的全部题照计失败。`controlled_English_alignment_with_supplied_reference_verified`只属于被接受样本，不扩展为科学verified。

实际English source bindings **1221**、derivedrecordDAG bindings **27114**。每理论pinnedStore源集合完整，查询和恢复时CAS账本不变，原JSON+全部derivedfiles恢复；未完整推导/冲突保持null label，不把unknown当科学false。

## 所有问题、负结果和深度分布

| goldclass |全部题 |正确且接受 |预测为该label数 |
|---|---:|---:|---:|
| True | 384 | 384 | 384 |
| False | 384 | 384 | 384 |
| Unknown | 626 | 626 | 626 |

混淆gold→acceptedlabel/abstain：`{'False': {'False': 384, 'True': 0, 'Unknown': 0, 'abstain': 0}, 'True': {'False': 0, 'True': 384, 'Unknown': 0, 'abstain': 0}, 'Unknown': {'False': 0, 'True': 0, 'Unknown': 626, 'abstain': 0}}`。引擎verdict `{'refuted': 384, 'supported': 384, 'unknown': 626}`，prediction failures `{}`，audit failures `{}`，sourcealignment错误逐theory留表。H1预先固定allcorrect/allquestions>=.95且三class均非空，H2allaccepted==allquestions且全部64原/derived恢复；未过门槛保留负结果，无最好seed/预算择优。

| goldQDep（仅预测后访问） |全部题 |正确 |
|---|---:|---:|
| 0 | 450 | 450 |
| 1 | 334 | 334 |
| 2 | 191 | 191 |
| 3 | 152 | 152 |
| 4 | 135 | 135 |
| 5 | 130 | 130 |
| 6 | 1 | 1 |
| 7 | 1 | 1 |

| theory序号 |datasetID |全部题 |正确 |独立接受 |English编译失败 |reference对齐失败 |
|---|---|---:|---:|---:|---|---|
| 0 | RelNeg-OWA-D5-332 | 24 | 24 | 24 | None | None |
| 1 | AttNoneg-OWA-D5-865 | 24 | 24 | 24 | None | None |
| 2 | AttNoneg-OWA-D5-357 | 16 | 16 | 16 | None | None |
| 3 | AttNoneg-OWA-D5-872 | 14 | 14 | 14 | None | None |
| 4 | RelNeg-OWA-D5-685 | 24 | 24 | 24 | None | None |
| 5 | RelNoneg-OWA-D5-1003 | 24 | 24 | 24 | None | None |
| 6 | AttNeg-OWA-D5-232 | 22 | 22 | 22 | None | None |
| 7 | RelNeg-OWA-D5-428 | 24 | 24 | 24 | None | None |
| 8 | RelNoneg-OWA-D5-645 | 24 | 24 | 24 | None | None |
| 9 | AttNeg-OWA-D5-524 | 20 | 20 | 20 | None | None |
| 10 | AttNoneg-OWA-D5-446 | 18 | 18 | 18 | None | None |
| 11 | RelNoneg-OWA-D5-713 | 24 | 24 | 24 | None | None |
| 12 | AttNeg-OWA-D5-1126 | 24 | 24 | 24 | None | None |
| 13 | RelNoneg-OWA-D5-929 | 24 | 24 | 24 | None | None |
| 14 | RelNoneg-OWA-D5-715 | 24 | 24 | 24 | None | None |
| 15 | RelNoneg-OWA-D5-390 | 24 | 24 | 24 | None | None |
| 16 | RelNoneg-OWA-D5-587 | 24 | 24 | 24 | None | None |
| 17 | RelNeg-OWA-D5-537 | 24 | 24 | 24 | None | None |
| 18 | RelNeg-OWA-D5-125 | 24 | 24 | 24 | None | None |
| 19 | AttNoneg-OWA-D5-1268 | 20 | 20 | 20 | None | None |
| 20 | AttNoneg-OWA-D5-98 | 22 | 22 | 22 | None | None |
| 21 | RelNeg-OWA-D5-571 | 24 | 24 | 24 | None | None |
| 22 | RelNoneg-OWA-D5-157 | 24 | 24 | 24 | None | None |
| 23 | AttNoneg-OWA-D5-822 | 16 | 16 | 16 | None | None |
| 24 | AttNoneg-OWA-D5-547 | 12 | 12 | 12 | None | None |
| 25 | AttNeg-OWA-D5-1184 | 16 | 16 | 16 | None | None |
| 26 | RelNeg-OWA-D5-694 | 24 | 24 | 24 | None | None |
| 27 | AttNeg-OWA-D5-174 | 20 | 20 | 20 | None | None |
| 28 | RelNoneg-OWA-D5-161 | 24 | 24 | 24 | None | None |
| 29 | RelNeg-OWA-D5-373 | 24 | 24 | 24 | None | None |
| 30 | RelNeg-OWA-D5-326 | 24 | 24 | 24 | None | None |
| 31 | AttNoneg-OWA-D5-304 | 20 | 20 | 20 | None | None |
| 32 | AttNoneg-OWA-D5-709 | 14 | 14 | 14 | None | None |
| 33 | RelNeg-OWA-D5-274 | 24 | 24 | 24 | None | None |
| 34 | RelNoneg-OWA-D5-228 | 24 | 24 | 24 | None | None |
| 35 | RelNoneg-OWA-D5-335 | 24 | 24 | 24 | None | None |
| 36 | RelNoneg-OWA-D5-839 | 24 | 24 | 24 | None | None |
| 37 | RelNeg-OWA-D5-28 | 24 | 24 | 24 | None | None |
| 38 | RelNoneg-OWA-D5-206 | 24 | 24 | 24 | None | None |
| 39 | AttNoneg-OWA-D5-883 | 18 | 18 | 18 | None | None |
| 40 | RelNoneg-OWA-D5-226 | 24 | 24 | 24 | None | None |
| 41 | RelNeg-OWA-D5-210 | 24 | 24 | 24 | None | None |
| 42 | RelNeg-OWA-D5-837 | 24 | 24 | 24 | None | None |
| 43 | RelNoneg-OWA-D5-497 | 24 | 24 | 24 | None | None |
| 44 | AttNeg-OWA-D5-198 | 18 | 18 | 18 | None | None |
| 45 | RelNeg-OWA-D5-104 | 24 | 24 | 24 | None | None |
| 46 | RelNeg-OWA-D5-374 | 24 | 24 | 24 | None | None |
| 47 | AttNoneg-OWA-D5-984 | 20 | 20 | 20 | None | None |
| 48 | RelNoneg-OWA-D5-881 | 24 | 24 | 24 | None | None |
| 49 | AttNeg-OWA-D5-15 | 20 | 20 | 20 | None | None |
| 50 | RelNoneg-OWA-D5-400 | 24 | 24 | 24 | None | None |
| 51 | RelNoneg-OWA-D5-887 | 24 | 24 | 24 | None | None |
| 52 | RelNeg-OWA-D5-999 | 24 | 24 | 24 | None | None |
| 53 | AttNoneg-OWA-D5-334 | 18 | 18 | 18 | None | None |
| 54 | AttNoneg-OWA-D5-1107 | 16 | 16 | 16 | None | None |
| 55 | AttNeg-OWA-D5-1061 | 20 | 20 | 20 | None | None |
| 56 | RelNeg-OWA-D5-507 | 24 | 24 | 24 | None | None |
| 57 | RelNeg-OWA-D5-368 | 24 | 24 | 24 | None | None |
| 58 | RelNoneg-OWA-D5-192 | 24 | 24 | 24 | None | None |
| 59 | AttNoneg-OWA-D5-1295 | 12 | 12 | 12 | None | None |
| 60 | AttNoneg-OWA-D5-751 | 18 | 18 | 18 | None | None |
| 61 | AttNoneg-OWA-D5-556 | 20 | 20 | 20 | None | None |
| 62 | AttNeg-OWA-D5-878 | 24 | 24 | 24 | None | None |
| 63 | RelNeg-OWA-D5-877 | 24 | 24 | 24 | None | None |

## 资源、原始文件与未测项

完整worker wall **16.028128s** / CPU **10.703125s** / peakRSS **46944256B**，父完整subprocess wall **16.171164s**。每query prediction/audit、theorycompile/ingest/recovery/全段CPU与wall在raw-worker。Observer费用含在CPU/wall，单轮机制验收未测OFF开销，不称提速或生产推理收益；局部CPU0是平台粒度而非无成本。

Constructor eligiblepayload返回 **259531B**，closureaudit eligible返回 **17008534B**，后置referencealignment原JSON+derived复核 **2167382B**，原JSON完整恢复 **1907851B**，派生恢复各fileB另列。Loaderpayload cap不含audit/recovery/metadata/SQLite/OS/SSD，failed读取B未计量为null；冷缓存/跨机/物理IO未测。

完整递归66Python+1HTML源码 **426112B**；当前全部189experimental scripts保守 **1570776B**，含共享/未执行旧脚本，不声称动态import集合；protocol/tests/input另外列。全部64source/CAS/snapshot/mapping/prediction/certificate/prefix/theoryaggregate等私有残留 **22315549B**，原archive/schema官方文档准备目录再 **215291314B**；train32 grammar准备/负日志也保留本地，本report/context补记其cost。所有历史science/model/train/source/snapshot费用保持，当前model0/新training0不代表历史免费。依赖/系统二进制、OS/allocator/metadataRAM未分配项显式保留，payloadcap不是总RAMcap。

## 可运行交付与下一步

```powershell
python -m unittest discover -s tests
```

proofwriter_english.py为显式OWA受限English编译，audit_proofwriter_english.py为预测后reference对齐，run_proofwriter_english.py为冻结officialtest64驱动；ownedtests/sdist示例无需原benchmark。正式CLI需官方privatearchiveSHA、frozencommit和不存在的work/out，拒绝覆盖。默认SDK/UI/存储格式不改，66runtime只version、HTML不改。

![受限English全部分母与独立对齐](proofwriter-english.png)

图已实际视觉检查，三class分母/接受数和source费用范围清楚。本报告tag前状态，localactualoutsidewheel/currentnative+actualsdist新旧smoke/finalbuildsourceaudit、ReleaseCI/实际7baseSHA/全source/outsideactualreleaseinstall/proof8重下载全部完成后，以published-verification.json判发行完成，不回写formal结果。

后续若扩大到人为改写/真实科学文本，须另冻独立数据与parser边界，不能把受限合成English结果外推成通用NLI。若优化同题审计效率，也须另冻证明一致性与完整source/CPU/RAM费用，不能只减记录成本虚称收益。E3净收益/E4整体/可靠科学问答/长会话/无限上下文仍未完成，0新远程API，原English/科学/benchmark原文/model/私研/模板个人报告密钥不公开。

补记本轮私有English grammar准备源码、train-only aggregate和全部negative/fixed单元日志 45486B，逐文件size/SHA在measurement-context.json，非正式重跑，不公开原English。

图表标签更正：原绘图模板中间子图曾沿用devaccess字样，实际冻结输入始终是test-member；正式数据/预测/分数未重跑，发行前改为testaccess并重新视觉核对，旧图私留及SHA/bytes见context，最终build/sourceaudit以更正图为准。

打包验收恢复记录：初次localactualsdist combined smoke因Windows CreateProcess单条命令长度超限WinError206未能启动，原日志保留；把同一实际sdist smoke代码改为仓库外临时脚本，复用同一actualwheel/native安装后全部新旧功能通过。正式科学/模型实验未重跑，未重复wheel安装；失败时完整安装残留size/SHA与恢复scope见package-harness-recovery.json，后续actual-release smoke也用该文件执行方式。
