# v0.59 冻结协议：已见索引加载的观察器成本与函数调用诊断

## 目的与已见数据声明

v058主typed/zstd空间/时间/联合失败保持；固定LZMA来自v058预先列出的完整矩阵空间点，不改变主门槛。本版不优化算法或原生化；量清cProfile本身的成本及准确调用次数，避免把高频Python受观察器偏置的self-time当未剖析CPU占比或Rust可获加速。

v058后准备时两个原typed/LZMA frame各一次cProfile已看过（`.tools/v059-preparation/profile-probes.json`）；因此本版是已见输入的探索性工程诊断，不是独立科学验证。准备两次与正式18次分开记录，不隐去先看。该准备不改变原参数/数据、没有任何问题评分或模型API。

## 输入及固定次数

读取docs/index-profile-inputs.json：v058 round1 EntailmentBank、SciFact、owned structured control的实际typed/LZMA frame（3份）。frame SHA、原canonical JSON SHA/size、旧原报告SHA固定。不得重编码、重训、改codec、换前缀、提高预算或补轮。原JSON/frame/恢复副本留本地。

3数据×profiler OFF/ON×3轮=18新鲜worker；A OFF，B ON，固定轮序AB/BA/AB，各轮数据顺序按manifest；600s/worker、0重试。每worker先读取并核原索引及frame，ready阶段为原decode(frame)+json.loads(raw)，ON只在这一区间启停cProfile；OFF同模块/加载函数与计时点，functions及profiler_total为null，不写零。外层ready wall/CPU包含启停开销，生成pstats/序列化在ready外但计入worker及parent。异常finally关闭观察器，不绕开任何长度/三SHA/严格变换检查。

两种模式每worker都核完整原bytes、canonical JSON/model对象、源与frame未改变。parent从subprocess启动到退出完整计时；child SHA、返回码/timeout错误sidecar记录。失败保留并导致本轮未通过，不覆盖或重跑。

## 预定可证伪诊断

H1观察器轻量：每个真实原索引ON/OFF的配对ready wall、CPU、parent全wall三轮中位比都≤1.10，且两个索引都满足才True。CPU零分母为null并失败，不加epsilon。人工控制另列，不当新科学域。

H2 instrumented热点集中：在两个原索引的每一ON轮，原scripts/postings_transform.py内inverse与read_uvar的非累加self-time之和/全部pstats self-time≥0.50才True。是明确标注instrumented量的描述性阈值；准备已见，不能当无偏新发现。禁止把cumulative相加重复计时，也不由H2推出未剖析CPU比例、Amdahl加速上界或实际Rust收益。

机械调用契约：对T个token/P个posting，read_uvar精确4+2T+2P次，inverse恰1次；从原JSON的T/P独立计数核对，9ON全部满足。所有function self-time之和与pstats.total_tt守恒。OFF counters必须null。记录全部function rows（文件名/行/函数名/次数/时间，无原文/词表/索引内容）。

## 独立审计与费用

独立audit全部18child/parent及hash、profile rows非负/守恒/次数、源/frame原SHA/size，并额外18次从原实际frame用不带profiler原decode恢复原JSON。freeze/source/protocol/test/manifest逐个对比Git。图分别展示ON/OFF时间比及instrumented self fractions，0轴/清楚单位，实际打开查看。

代码完整recursive rkv1 Python+HTML、原frame wrapper/typed transform、全部新诊断源码/测试/协议/input逐文件B/SHA，实际rawJSON/日志/图/sidecar计账；原3shared model与3frame实际B、旧v058所有frame/恢复原文件与旧source训练快照继续保留，不当本版节省。观察RSS不是精确增量RAM；C缓冲/平台/解释器/依赖/pycache未完整分配。SSD/全系统IO/冷缓存/跨机为null。

## 发布与限制

测试四项：OFF null与原字节、ON精确调用与守恒、损坏拒绝及异常关闭、两个fresh synthetic worker和输入SHA拒绝；完整314检查后freeze，exact CI成功才正式18worker。运行库只版本号变，原frame/transform逐字节同v058；无新DLL/神经模型/生产集成。

原始JSON/标准图/详实报告/README/release/可运行脚本CLI发布，CI后实际5资产SHA/递归Python+HTML及新scripts与冻结相符、物理仓库外actual wheel/current native/actual sdist中合成ON/OFF调用与所有旧smoke/finalproof重下载。每版完全收尾再下一版。

0新问题/质量试次、0训练、0远程模型调用（旧24已耗尽）。该诊断不解决E3净收益失败，不验收E4整体/回答质量/NLI/真实长会话/无限上下文。下一版若原生化，另冻实现/编译选项/实际DLL SHA，再计整个DLL/metadata/源码与加载费用，用新鲜无profiler配对实测，不拿本版剖析代替。
