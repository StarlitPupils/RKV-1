# v0.50 汇总审计追加说明（原冻结算法与正式数据保持）

原analyze_question_retrieval.py因开发期删除隐私字段的字符串替换误伤三个方法tuple，变成字符串('lexical')，尝试读round-1-l.json即FileNotFoundError，未生成任何aggregate或图。旧冻结文件和原错误日志保留，不回写代码或数据。

追加scripts/audit_question_retrieval.py，逐字复制原冻结审计器，仅三处恢复('lexical','graph','permuted_graph')：主审计循环、逐题比较报告集合、图标签。输入/排序/模型/训练/预算/门槛/metrics/原证验证全部不改；编译/差异核对后另作Git冻结，再审计同一9worker原始JSON。此修复不重训、不重复正式查询或改变gold。原冻结codeSHA继续用于原候选/原脚本/输入/模型核对，追加审计器的独立GitSHA/B/源码SHA和原失败日志SHA在最终measurement-context/source-resource收费。

复现原正式评估后应执行python -m scripts.audit_question_retrieval（原analyze入口保留其失败事实），参数同原协议。纯排名重放只做独立诊断，不算新科学评估。最终Release CI测试仍适用全部源码。
