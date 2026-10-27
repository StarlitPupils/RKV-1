# v0.69.0 实验报告：官方人工OWA规则的给定形式表示与原来源回溯

## 结论与项目阶段

H1全部问题formal正确率至少95%且三goldclass均存在 **True**；H2所有问题通过原表示翻译/完整closure且64理论恢复 **True**。固定前64理论共 **1360** 问题，正式判对 **1360**，allquestion accuracy **1.0**，独立接受 **1360**。unsupported/预算不足/冲突/audit失败都留在全部问题分母，未根据gold/depth挑选成功子集。

这是新的外部人工规则数据上的**给定形式表示**测试，不从自然语言提取公理，不证明科学NLI、开放检索、生成回答、真实长对话或无限上下文。原始benchmark同时带English、gold与proof，reasoner只使用事实/规则/query的representation。`scientific_entailment_verified`与`English_translation_verified`始终False，generatedanswer0。v0.64科学关系分类负结果、E3净收益/E4整体未完成的结论保持。

## 官方来源、先后顺序与负准备记录

[官方数据入口](https://allenai.org/data/proofwriter)重定向至AI2官方V2020.12.3 ZIP，214185889B，SHA `bbc5694901e8306d0bd659aa1ad53ccfd02c201864f4b320ffa3777827d1fc26`；原archive/README只保留本地，不按镜像推断许可或公开原文。第一手论文[ProofWriter](https://aclanthology.org/2021.findings-acl.317/)和[原RuleTaker项目](https://github.com/allenai/ruletaker)提供背景，不把论文模型结果当本项目收益。

在方法freeze前只读官方README和32train schema行（1048689B/SHA1037a07baac41fecee3db6151110cffb47876bc694c549fdb806fb4741ed2690），没有dev/test成员内容访问，也没有训练fit/goldlabel评分。初版只支持+/-导致train20/32成功，12条含~负前提拒绝，负记录保留；官方README说明OWA负前提为显式hardnegative，CWA才是NAF。补齐OWA-only语义后train32/32独立表示一致，CWA policy明确拒绝，单元测试证明缺少正事实不会触发负前提。早期私有spy测试因strictdict与guard子类不匹配失败的日志也保留，后续必要输入fieldguard通过；不是正式重跑。

完整389检查388pass/1既有权限skip，source/protocol/input冻结 `3598bfb23c3dc83f10ae8348f444a43f042f6a72`，exactCI `40463571353`成功后才首次读取OWA/depth-5/meta-dev.jsonl前64**物理行**，不跳blank/挑class/depth。该prefix在任何dev预测/scoring前另落盘冻结size/SHA，见first-access-input-SHA.json。共1freshworker、600s、0retry，新training/model/API0。此为首次项目dev暴露，非封存test或统计泛化证明；正式后不调旧suffix/参数追正。

## 方法与明确的输入信息

Wholeoriginal JSON先被严格解码，因此labels作为字节存在于对象中；在每theory所有预测exclusive持久化之前，不使用answer/QDep值，proof/allProofs/intermediates/theory/text语言字段不用于编译或reasoning。foreachtheory完整预测和certificateSHA先保存，然后独立audit，再访问goldanswer和QDep评分。必要spy/真实Store测试验证这些边界，原JSON仅以原source保存在CAS非eligible original.json中，不被引擎当axioms。

编译器只接受受限S-expression quoted(subject,relation,object,sign)，规则1..3前提/有限range-restrictedhead，显式world=OWA，+/-ground，~仅premise转显式negative，ground/head/query~拒绝。rule变量someone/something映射?v，mixedspelling同rule拒绝；名字保持case、ASCIIletters/spaces，unsupported不静默归一。Unaryis attribute使用u_SHA24(subject,z_unit)，binaryrelation用r_SHA24(subject,object)，constant用c_SHA24，各namespace分离且碰撞检查，无eval、模糊解析、模型或English语义判断。

有些source/query若不在受限语法内，会保持unsupported/null并算错/abstain；不会换budgets或删除这些问题。本轮实际verdict分布 `{'refuted': 384, 'supported': 384, 'unknown': 592}`，prediction failure `{}`，auditfailure `{}`。

## 原source和派生表示的证据关系

facts.logic.jsonl/rules.logic.jsonl是派生源，不把其offset称原benchmark字符串offset。每compiledrecord绑定原JSONpointer、representationSHA和派生lineoffset/length/SHA；original.json保留该theory整原行bytes/SHA。独立translator使用另外的atomregex/JSONquotedtokens/rulesplit，从实际Store原JSON重新构造每个derivedrecord并比所有mapping/filebytes；证明的是给定representation到派生byte的一致性，不是原English到representation的正确性。

接着既有v0.68 source-set引擎构造完整eligiblefile集合、work100000、不改1MiBpayloadcap和旧signedengine。DAG定位到实际derivedfile record，再独立fullclosure/querytranslation审计；只有原translation和closure均通过且complete supported/refuted/unknown才允许True/False/Unknown label。inconsistent/incomplete/unsupported/error为null并保持失败分母。完整unknown只指给定formal公理内未知，不是科学false或全球知识否定。

原representation bindings **1217**，derivedrecord DAG bindings **27004**。原翻译与闭包是两个层次，不用byte恢复替代semantic/NLI验证。64理论每个source独立Store，读后恢复原JSON和全部derivedfile，CAS账本不变；其中恢复完成theory数见validation，不由H1达95%就虚称全恢复通过。

## 完整问题分母与分类/深度结果

| goldclass |全部问题 |正确且独立接受 |模型形式预测该label数（不等于正确数） |
|---|---:|---:|---:|
| True | 384 | 384 | 384 |
| False | 384 | 384 | 384 |
| Unknown | 592 | 592 | 592 |

混淆矩阵gold→acceptedlabel或abstain：`{'False': {'False': 384, 'True': 0, 'Unknown': 0, 'abstain': 0}, 'True': {'False': 0, 'True': 384, 'Unknown': 0, 'abstain': 0}, 'Unknown': {'False': 0, 'True': 0, 'Unknown': 592, 'abstain': 0}}`。class标签是人工规则benchmark，不能叫真实科学支持率/临床判断。H1 allcorrect/allquestions>=.95且各class非空，H2 allaccepted==allquestions并64原/derived恢复和独立translation；门槛在dev揭示前固定，不做模型baseline比较、production速度gate或statisticalsignificance声称。

| goldQDep（只预测之后读取） |问题数 |正确且接受 |
|---|---:|---:|
| 0 | 417 | 417 |
| 1 | 305 | 305 |
| 2 | 220 | 220 |
| 3 | 157 | 157 |
| 4 | 133 | 133 |
| 5 | 128 | 128 |

| 原prefix theory序号 |datasetID |全部问题 |正确 |独立接受 |编译失败 |独立translation失败 |
|---|---|---:|---:|---:|---|---|
| 0 | AttNoneg-OWA-D5-331 | 14 | 14 | 14 | None | None |
| 1 | RelNeg-OWA-D5-740 | 24 | 24 | 24 | None | None |
| 2 | AttNoneg-OWA-D5-1364 | 16 | 16 | 16 | None | None |
| 3 | AttNeg-OWA-D5-849 | 24 | 24 | 24 | None | None |
| 4 | RelNoneg-OWA-D5-777 | 24 | 24 | 24 | None | None |
| 5 | RelNoneg-OWA-D5-829 | 24 | 24 | 24 | None | None |
| 6 | AttNeg-OWA-D5-694 | 20 | 20 | 20 | None | None |
| 7 | AttNeg-OWA-D5-270 | 20 | 20 | 20 | None | None |
| 8 | AttNoneg-OWA-D5-1022 | 22 | 22 | 22 | None | None |
| 9 | AttNoneg-OWA-D5-1376 | 16 | 16 | 16 | None | None |
| 10 | RelNeg-OWA-D5-574 | 24 | 24 | 24 | None | None |
| 11 | AttNoneg-OWA-D5-791 | 18 | 18 | 18 | None | None |
| 12 | AttNoneg-OWA-D5-583 | 12 | 12 | 12 | None | None |
| 13 | RelNeg-OWA-D5-437 | 24 | 24 | 24 | None | None |
| 14 | RelNoneg-OWA-D5-992 | 24 | 24 | 24 | None | None |
| 15 | AttNeg-OWA-D5-1071 | 22 | 22 | 22 | None | None |
| 16 | AttNoneg-OWA-D5-1103 | 12 | 12 | 12 | None | None |
| 17 | RelNeg-OWA-D5-224 | 24 | 24 | 24 | None | None |
| 18 | RelNoneg-OWA-D5-983 | 24 | 24 | 24 | None | None |
| 19 | AttNoneg-OWA-D5-1205 | 22 | 22 | 22 | None | None |
| 20 | RelNoneg-OWA-D5-281 | 24 | 24 | 24 | None | None |
| 21 | AttNeg-OWA-D5-766 | 20 | 20 | 20 | None | None |
| 22 | AttNoneg-OWA-D5-878 | 18 | 18 | 18 | None | None |
| 23 | AttNoneg-OWA-D5-284 | 16 | 16 | 16 | None | None |
| 24 | RelNeg-OWA-D5-278 | 24 | 24 | 24 | None | None |
| 25 | RelNeg-OWA-D5-78 | 24 | 24 | 24 | None | None |
| 26 | AttNeg-OWA-D5-1176 | 24 | 24 | 24 | None | None |
| 27 | RelNoneg-OWA-D5-637 | 24 | 24 | 24 | None | None |
| 28 | AttNoneg-OWA-D5-111 | 18 | 18 | 18 | None | None |
| 29 | AttNoneg-OWA-D5-214 | 18 | 18 | 18 | None | None |
| 30 | RelNeg-OWA-D5-242 | 24 | 24 | 24 | None | None |
| 31 | RelNoneg-OWA-D5-341 | 24 | 24 | 24 | None | None |
| 32 | RelNeg-OWA-D5-29 | 24 | 24 | 24 | None | None |
| 33 | AttNeg-OWA-D5-233 | 20 | 20 | 20 | None | None |
| 34 | RelNoneg-OWA-D5-789 | 24 | 24 | 24 | None | None |
| 35 | RelNoneg-OWA-D5-781 | 24 | 24 | 24 | None | None |
| 36 | RelNoneg-OWA-D5-616 | 24 | 24 | 24 | None | None |
| 37 | RelNeg-OWA-D5-294 | 24 | 24 | 24 | None | None |
| 38 | RelNeg-OWA-D5-317 | 24 | 24 | 24 | None | None |
| 39 | AttNoneg-OWA-D5-1302 | 14 | 14 | 14 | None | None |
| 40 | RelNeg-OWA-D5-668 | 24 | 24 | 24 | None | None |
| 41 | AttNeg-OWA-D5-1009 | 20 | 20 | 20 | None | None |
| 42 | RelNoneg-OWA-D5-398 | 24 | 24 | 24 | None | None |
| 43 | RelNeg-OWA-D5-947 | 24 | 24 | 24 | None | None |
| 44 | AttNoneg-OWA-D5-1087 | 24 | 24 | 24 | None | None |
| 45 | AttNeg-OWA-D5-842 | 14 | 14 | 14 | None | None |
| 46 | RelNeg-OWA-D5-129 | 24 | 24 | 24 | None | None |
| 47 | AttNoneg-OWA-D5-301 | 20 | 20 | 20 | None | None |
| 48 | RelNeg-OWA-D5-30 | 24 | 24 | 24 | None | None |
| 49 | RelNeg-OWA-D5-483 | 24 | 24 | 24 | None | None |
| 50 | AttNoneg-OWA-D5-863 | 18 | 18 | 18 | None | None |
| 51 | AttNeg-OWA-D5-1015 | 20 | 20 | 20 | None | None |
| 52 | AttNoneg-OWA-D5-961 | 20 | 20 | 20 | None | None |
| 53 | AttNeg-OWA-D5-872 | 20 | 20 | 20 | None | None |
| 54 | AttNeg-OWA-D5-305 | 22 | 22 | 22 | None | None |
| 55 | RelNeg-OWA-D5-890 | 24 | 24 | 24 | None | None |
| 56 | RelNoneg-OWA-D5-884 | 24 | 24 | 24 | None | None |
| 57 | RelNoneg-OWA-D5-691 | 24 | 24 | 24 | None | None |
| 58 | AttNeg-OWA-D5-108 | 20 | 20 | 20 | None | None |
| 59 | AttNoneg-OWA-D5-400 | 20 | 20 | 20 | None | None |
| 60 | RelNeg-OWA-D5-731 | 24 | 24 | 24 | None | None |
| 61 | AttNoneg-OWA-D5-672 | 12 | 12 | 12 | None | None |
| 62 | AttNoneg-OWA-D5-515 | 20 | 20 | 20 | None | None |
| 63 | RelNoneg-OWA-D5-312 | 24 | 24 | 24 | None | None |

## CPU、全部source与完整成本

完整worker wall **15.925013s** / CPU **10.468750s** / peakRSS **48484352B**，父完整subprocess wall **16.070613s**。每query prediction/audit、theorycompile/ingest/translation/recovery整段费用见raw-worker，observer费用计入，无OFF对照/速度收益或生产推理主张。平台CPU计时0为粒度，非无费用。

已测constructor eligible源应用返回 **256340B**；closureaudit eligible返回 **16545034B**；原JSON到derived翻译复核总应用返回 **2599292B**，其中原JSON另计；完整原JSON恢复 **2342952B**，derived恢复各fileB另在recovery。sourcepayloadcap只loader，不含audit/recovery/metadata/SQLite/OS/SSD，失败返回B未装计量null而非0。物理IO、coldcache、跨机均未测。

整库66recursivePython+1HTML源码 **426112B**；全部186当前experimental scripts保守 **1549067B**，含共享/未执行历史，不当动态import集合；protocol/tests/input另列。全部64source/CAS/snapshot/mapping/prediction/certificate/pertheoryaggregate/prefix等残留工作文件 **23002203B**，archive和schema/官方docs等准备目录再 **215291314B**，逐size/SHA完整保留，不能只计最终label。raw-worker与父/driverlog/report本身另是publicderived输出，不算0成本。当前model0/newtraining0不抹除旧science/model/train/历史snapshot费用。依赖/OS二进制、allocator/metadataRAM未分配项显式保留，payloadcap不等于总processRAM。

## 可运行交付、图与未实现项

```powershell
python -m unittest discover -s tests
```

proofwriter_representation.py只做显式OWA形式输入编译，audit_proofwriter_representation.py给原JSON→派生源独立audit，run_proofwriter_representation.py提供官方archive固定prefix驱动。无需模型，但正式CLI需本地官方archive对应SHA和frozencommit，不存在work/out目录；ownedtests/sdist安装示例无需外部语料。scripts属sdist/experiment，不默认进SDK/UI，66runtime只version、HTML不改。

![官方OWA形式表示与全部失败分母](proofwriter-representation.png)

图已实际视觉检查，class/分母/source费用范围清楚。本报告tag前状态，localactualoutsidewheel/currentnative与actualsdist新旧smoke/finalbuildsourceaudit、ReleaseCI/7baseactualSHA/全源码/outsideactualreleaseinstall/proof8重下载齐备后，以published-verification.json判发行完成，不回写原formal。后续若做English解析，必须另冻受限语法/独立语义映射与未知数据，不能复用本轮给定representation得分冒充NL成绩。E3净收益/E4整体/可靠科学NLI/回答/真实长会话/无限上下文仍未完成，0新远程API，原科学/benchmark原文/model/私研/模板/个人报告/密钥不公开。
