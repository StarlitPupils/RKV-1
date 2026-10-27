# v0.64 冻结协议：明确标注证据的CPU词面关系probe

v063actual发行proof及负迁移结论完整收尾后采用；本协议在真实关系训练与评分前冻结。本轮目标从找来源进入支持/反对关系的初步判别可行性，词面线性分类器不是可靠NLI、形式证明、科学结论或生成回答。0新模型API/不下载模型/stdlib CPU，不变原Science原文CAS/12wholepaper/4096B预算。

## 输入、训练、对照

既有SciFact固定corpus/train/dev及旧source检索base SHA清单不改。只在训练集使用显式SUPPORT/CONTRADICT rationale标注的claim-paper pairs；同normalized-questionSHA+paperID union标签去重；同pair有冲突单列ambiguous，不随便选标签；无gold行保持unknown，不能当NEI或负类。source title+整abstract为模型输入，不喂gold rationale sentence选择。source/train只训练，dev已见项目评估但此分类候选未运行，不能称全新独立泛化验证。

固定hashfeature：ASCII casefold all alnum tokens保留stop/否定；claim/document/minTF共享词三通道各128bucket，SHA256前8B little modulo128；logTF=1+log(tf)，先bucket累加再各通道L2归一；4标量（claim含否定词、doc含否定词、二者异或、queryset被doc覆盖分数）和bias，共389维。否定词仅no/not/never/without/neither/nor，不能当语法解析或反证规则。

A多数类；B pair-linear；C claim-only-linear（文档/共享channel与doc标量恒0）；D label-permuted pair-linear。3fit一次训练campaign，顺序B/C/D，固定200epoch全batch logistic，lr .5、L2=.01不惩罚bias，初始bias log((support+.5)/(refute+.5))、其余0；D用seed20261027一次打乱labels保留marginal。无循环找有效控制；若D恰好不变则control不可用、质量gateFalse。训练一次各fitCPU/wall/RSS/loss/model完整B/SHA/组件/原训练数据统计记账，三个fit不是一个模型收益；A只训练计数。先代码/协议/input/必要测试完整freeze+CI，真实训练一次后另冻4modelSHA，才跑dev。

## 正式推理与分母

固定原BM25 lexical真实检索，12wholepaper/4096原recordB与旧v053 selectedproof一致，不能给oracle goldpaper/rationale。12fresh worker（4方法×3轮），ABCD/BADC/CDAB，600s/worker0retry。每问题先rank/admit，再每selected原paper一次CAS read/原SHA/ID/title/abstract验证并形成相同source proof，预测仅原claim+实际返回整abstract，不读gold labels；所有predictions完成后才评分relationgold。110无gold保持unknown，不入二分类真负；实际选回但无该claim标注的paper也不当反对。必须分别报全部输出pairs、retrieved且有明确label pairs、全部有label gold pairs、missing gold、ambiguous和各SUPPORT/CONTRADICT分母。

## 冻结可证伪门槛

H1关系质量：B在retrieved且有明确gold的pairs上balanced accuracy严格胜A/C/D，并在all labeled-gold分母下correct个数不低于A/C/D；两class分母缺失或shuffle无效时False/null，不重采样补齐。多数类/claim-only/label-shuffle均是固定负控制，不把仅claim线索当证据使用。conditional accuracy和all-gold正确覆盖分开，unretrieved gold保留missing，不把oracle条件准确率当部署收益。

H2固定CPU/模型可行性：B实际model artifact完整≤1MiB，分类phase wall和CPU每1000实际输出pairs≤2.0s（0pairs为null失败），三个正式轮都满足才True。该CPU上限先于真实train/dev固定，不根据表现调宽。分类phase包含feature extraction/logit，对所有selectedpairs运行，原source读/解析/verify在同query及完整parent计时另列；H2只是预定局部可行性，不是比多数类/整个pipeline提速。原source索引、整库/专用源码、模型/metadata/全部训练成本和RAM/旧快照均另计，不省略以追门槛。

joint=H1&&H2仅该known-dev CPU弱关系probe门槛，不能称E4整体/NLI/回答/无限上下文通过。sigmoid score未经校准，scientific_entailment_verified始终False、generated_answer始终None，不由高分生成科学结论。出错日志/失败/退步全部保留，不改features/epoch/lr/阈值/预算追正。

## 独立核验与交付

9必要合成检查通过（7core、1独立audit、1actual toy Store四角色）（feature归一/否定/稳定、claim-only文档无关、finite-difference梯度、toy训练确定、shufflemarginal/多数类、模型SHA/nonfinite/参数/单class拒绝、显式标签去重/冲突/no-gold不作NEI）。actual toy Store检查还覆盖完整train-once三fit/多数类四模型文件、每个实际返回paper预测先于gold标签读取；独立feature/logit/gold/source/oldproof/confusion/终端训练objective审计器已实现。完整349检查348pass/1权限skip后freeze源码/协议/input，exactCI成功后真实训练campaign一次（3fit+1多数类计数）、另freeze4modelSHA，再唯一12worker；正式之前不称真实关系收益或已交付。

独立audit不得调用candidate预测器，需重算feature/logit与模型/标签分母、原source CAS bytes/ID/位置/SHA、sourceproof相同、四method跨轮确定、全部文件/parent/模型成本、12完整原source恢复。标准图分别显示conditional/allgold、balanced、全部source+分类wall/CPU，0轴/各分母明确，实际打开查看。每版代码/冻结协议/rawJSON/详实报告/README/release/GitHub/CI后actual7assets SHA/全source/物理外wheel/currentnative/actualsdist新旧smoke/finalproof8完全收尾。

官方一手schema与oracle/open区分：https://github.com/allenai/scifact/blob/master/doc/data.md ，https://github.com/allenai/scifact 。不调用其自动下载预训练模型脚本。原science/模型/原问题全文/映射/fullhits/私有研究课程个人报告密钥不发布，模型weights/中间训练样本本地。SSD物理/全系统IO/冷缓存/跨机未测。
