# v0.76.0 实验报告：训练集结构模板在人工改写来源上的迁移

## 结果与全部问题分母

H1learned全题正确接受>=95%且三class每轮齐：**False**；H2全题接受+32实际原/derived恢复：**False**；H3完整human来源与训练无重复：**True**；联合 **False**。每worker32理论、532问题；baseline正确0、learned正确0、control正确0。所有失败留分母，不以逻辑Unknown代替source未理解，不选最好轮或改模板。

训练1681理论、16619human句子形成1099无歧义模板；在新测试308human句子中，冻结template key命中0。预测后诊断确认测试groundentities均已在8个训练名字词表内，未知实体理论数0，不能归因于名字词表缺失。该诊断只做冻结key查表和reference词表对比，没有重新编译source/运行query或改模型；单独诊断CPU/wall未完整计时保留null，不当零成本。

模型是监督结构模板字典，不是神经或通用NLI模型。它只把训练时出现的规范化句式/实体槽映射到训练标注结构；给定形式reference仅用于预测后评测验收。无人工形式标注的生产环境不能据此自动保证语言抽取正确，原文byte引用/形式DAG也不保证科学真理。0模型API，E3净收益/E4整体/真实长会话/回答/无限上下文未完成。

## 冻结与一次训练时间线

461检查460pass/1权限skip；source/protocol/input freeze `7a4b49f55351b3ebe15b4733f7f428bb3d5a660e`，exactCI `40504257793`成功后一次真实train campaign。官方完整OWA/NatLang train共1681物理行、26528789B、SHA `eb9bef061af62346fbb441a49d84406a6ee86cb31dafc7aa0d7f2bf66d41ff5b`，问题answer未作fit字段；训练实际fit {'wall_s': 1.4331822998356074, 'cpu_s': 1.390625}。训练fullworker内部finally/parent/peakRSS单列，包含archive214185889B完整SHA校验/解压/解析/写出。private owned9unit是机制检查不是一次真实fit。

Learned/control同B **511529B**，控制由固定key循环+1 target派生、无第二fit；内容相同target key仍有 **2/1099**，如实保留，不再打乱追更差control。模型完整SHA另封存后，才首次打开官方NatLang test前32物理行，原prefixSHA/bytes在test-firstaccess-input-SHA.json；未用已见NatLang dev32选model。输入全部理论/问题/源未覆盖/多fact/否定/variable都保留，无测试后补规则或挑prefix。

训练统计：`{'training_rows': 1681, 'valid_training_rows': 1681, 'invalid_training_rows': 0, 'all_training_sentences': 16619, 'eligible_training_sentences': 16619, 'ambiguous_template_keys': 0, 'unambiguous_template_keys': 1099, 'control_permutation_identical_target_keys': 2}`。未知/不显式提及groundname/非ASCII或超边界训练句组在相应分母计数；歧义key明确排除，不把它的标签猜给测试。训练groundentity词表最多4096、key100000、model64MiB、train64MiB/10000row；这些不是总RSS保证。源解释仍受1024record/64rule、1MiBderivedsource、100000work，未调预算。

## 数据分离、模型与控制方法

三个fresh role×3轮=9worker，ABC/BCA/CAB，每个600s/0retry。Same32input/sourceSHA/questionID/gold allroles，role内三轮投影一致；重复不是独立科学数据集。Baseline为既有冻结HumanSourceCompiler，不loadmodel；learned/control全modelSHA验证及解析/深拷贝/compiler构建一次每worker，跨本worker32理论复用同只读模型。Symbol字典仅检测hash/名字身份冲突，不把测试实体或句式加入训练model词表/结构。旧source parser、question grammar、原humanReference/DAGchecker代码不改；注入factory在作用域结束恢复，无默认SDK/UI集成。

原源只用sentences，query只用question；任何mapping/canonicaltext/representation/answer/QDep不得在预测落盘前访问。9项owned检查含多fact一human、实体重复/方向、否定/变量、歧义/未知/未提及名字拒绝、modelSHA同Bcontrol、完整fieldguard和32ownedtheory worker只load一次/旧baseline不loadmodel。所有288份theory预测持久化再gold文件已独立检查 **288**。后置审计0实际human与formalCounter对齐、0实际原source/DAG、0理论原json及derived逐byte恢复，counts是实际执行数，不以prefixSHA推32恢复。Sourcefail没有Store不代表0输入读取。

## 质量、失败与类分母

| role |gold classes total/correct |correct/all |accepted |sourcefail theories |postreference failed theories |
|---|---|---:|---:|---:|---:|
| baseline | {'False': {'correct': 0, 'total': 133}, 'True': {'correct': 0, 'total': 133}, 'Unknown': {'correct': 0, 'total': 266}} | 0/532 | 0 | 32 | 0 |
| learned | {'False': {'correct': 0, 'total': 133}, 'True': {'correct': 0, 'total': 133}, 'Unknown': {'correct': 0, 'total': 266}} | 0/532 | 0 | 32 | 0 |
| control | {'False': {'correct': 0, 'total': 133}, 'True': {'correct': 0, 'total': 133}, 'Unknown': {'correct': 0, 'total': 266}} | 0/532 | 0 | 32 | 0 |

所有query原预测、failure/acceptedwrong/referencefail/闭包/源绑定在rawtheory records。Control是固定置换诊断，不保证各句都错，不能把它称完全独立随机negative，也不调它的目标分布。Learner弱或全0不代表所有ML方法不行，只说明这个明确有限模板法未达到预定覆盖门槛。任何识别的已见句式不等于开放语义理解。

## 来源重叠审核

NatLangtest member此前未读，但整个ProofWriter家族旧depth5train/dev/test已暴露，不能称全家族新科学。测试全部预测后，逐训练/测试完整human源字符串multiset lower+whitespace归一（不去掉实体、不改标点）指纹对比，完整source重复 **0/32**；canonicalaxiom集合指纹重复 **0/32**，训练canonical无法计算0行另留。H3仅要求完整human来源无重复；单句/模板key重叠是该方法依赖，不能冒充完全新语言现象。无去重删测试题、无重跑或以不重复subset替换primary。

## CPU/RAM、模型/源/历史完整列账

| round |role |worker wall s |worker CPU s |parent full wall s |peakRSS B |loaded full model B |actual recovered theories |all worker retained B |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | baseline | 0.5665857000276446 | 0.265625 | 0.6978646998759359 | 34758656 | 0 | 0 | 893671 |
| 1 | learned | 0.6046954998746514 | 0.34375 | 0.7353453999385238 | 40284160 | 511529 | 0 | 897028 |
| 1 | control | 0.5919538999442011 | 0.28125 | 0.7292430000379682 | 40460288 | 511529 | 0 | 897067 |
| 2 | baseline | 0.5597331000026315 | 0.203125 | 0.6918515998404473 | 34680832 | 0 | 0 | 893688 |
| 2 | learned | 0.582844499964267 | 0.265625 | 0.7143134998623282 | 40415232 | 511529 | 0 | 896977 |
| 2 | control | 0.5837187001015991 | 0.453125 | 0.7211968000046909 | 40501248 | 511529 | 0 | 896982 |
| 3 | baseline | 0.561237100046128 | 0.296875 | 0.68870780011639 | 34832384 | 0 | 0 | 893789 |
| 3 | learned | 0.7381009999662638 | 0.296875 | 0.8687687001656741 | 39944192 | 511529 | 0 | 896885 |
| 3 | control | 0.5981189999729395 | 0.390625 | 0.733134200097993 | 40464384 | 511529 | 0 | 897067 |

Model/json/词表/target/ambiguouskey均完整计费，不是免费记忆压缩；候选全模型与control各511529B，私有train/raw/model/metadata/timing全部 **27553680B**；所有worker source/CAS/snapshots/原json/派生source/证书/预测/聚合 **8063154B**，outer train/worker/parent/log **4727677B**，私有准备41407B。archive214MB和旧science/human/model/train/上下文/帧/恢复/下载残片与range费用保留，不把currentAPI0当历史0。

整库实际递归66Python+HTML **426112B**，全部实验scripts保守 **1671414B**，模型/专用source/test/protocol/input逐SHA。metadata/allocator/OS未分摊不当0，CPU粒度0不是免费；sourcebudget不是SSD/fullsystemIO/RAM上限。没有速度gate，拒绝更快不是推理收益，物理IO/冷缓存/跨机未测。原模型编译/加载/前向/审核/恢复细项及完整parent保留；本分析内部finally和父驱动即失败也记时，不用恢复绘图阶段冒充原大审核CPU。

## 可运行交付与下一步

```powershell
python -m unittest discover -s tests
```

公开typed_templates提供train/受SHA保护load_model/LearnedCompiler；worker复用旧human原文件审计流程，训练只准使用训练标注，正式需owner私有官方archive/input/modelSHA。原train/model/测试human/科学帧和恢复副本不上传。训练原文与派生模板模型保持私有，不能声称这已证明最优压缩。

![训练模板的全部问题分母](typed-templates.png)

图已实际视觉检查，三role零接受与32源失败全部分母一致。报告/实验不是发行完成：initialbuild退出0→物理仓库外actualwheel/currentnative+新旧actualsdist→finalbuild/sourceaudit→commit/push/tagReleaseCI→实际7assetsSHA/递归PythonHTML/allsource/外actualpublishedinstall/finalproof8齐后才交付。不得跨当前quota实际窗口或在额度100/ordinarydenied后继续，准确保存partial并删除续跑。

后续若模板覆盖失败，应选择独立更强且明确授权的语义模型/离线方法与新heldout协议，不能补已见测试句式造positive。旧24API用完无新增调用；本版仍不是科学NLI/可靠长会话/回答/无限上下文，所有负结果/失败分母保留。

## 本轮结论后的资源选择

不能在已见测试上继续补模板追正；下一种更强语义候选需要新的独立协议/heldout和明确模型资源。旧24API预算已用完，当前没有新增调用或预训练模型下载授权。用户资源选择待定期间，继续既有纯CPU/离线范围内的元数据开销工作；不把未授权模型试验称已开始。
