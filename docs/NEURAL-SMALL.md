# v0.36 E3冻结协议：小型整数神经预测与自包含算术帧

## 范围与依据

本版是本地CPU的第一个有界神经预测编码候选，不是最优神经压缩/LLM复现或默认归档升级。
先完成代码/测试并冻结此协议及运行库；训练一次后另行提交模型SHA，之后才评估。
训练与测试不交叉，既有科学检索gold和模型API预算不动，远程模型请求0。

[DeepZip](https://arxiv.org/abs/1811.08162)使用神经概率模型配合算术编码。
[Language Modeling Is Compression](https://arxiv.org/html/2309.10668v2)讨论预测与编码，以及计入模型后的大小权衡。
[Nacrith2026预印本](https://arxiv.org/abs/2602.19626v2)报告大型词表CDF精度和GPU模型配置，
其结果未在本机复现，不能替代本版实测。小MLP是工程控制选择，不冒称复现RNN/Transformer论文。
整数算术实现独立编写，未复制第三方算术编码源代码。

## 固定神经模型和确定性

4字节因果context，257输入符号（字节0–255和BOS256）。embedding257×4，拼接16维，
W1(16×8)、bias1(8)、ReLU，W2(8×256)、bias2(256)。共3468参数，signed int16体6936B。
序列开头4个BOS，每步按原字节更新context；无在线学习、无缓存概率/隐式外部状态。
Q=256，每层点积以Python整数计算、floor除256后加同尺度bias；hidden夹在[0,2^24]，
输出logit夹[-2048,2048]，按16刻度映射257个桶。
分数表从65536开始，每步 floor(previous×106449/100000)，共257项。
频率总32768，每字节至少1，其余32512按score比例整数floor，剩余按字节升序各补1。
全部CDF和32bit算术状态只用整数，解码不依赖NumPy、训练、浮点或外部模型服务。
量化近似不宣称保留float训练loss；最终测实际完整帧。

模型序列：8B `RKVMLP01` +上述E/W1/b1/W2/b2行主序3468个little-endian int16，总6944B。
全模型固定Zlib6压缩，神经帧每个对象都携带一份；不做未实现的共享摊销收益。

## 实验帧（不属于主Archive v1–v6）

magic `RKVNN001`，头 `<8sBBIQQQ32s32s32s>`，134B：magic、version1、method、
原长度、压缩模型长度、payload长度、payload bit长度、原文SHA、原模型SHA、payload SHA。
method0为neural，1/2/3为普通Zlib6/Zstd3/LZMA6；普通帧模型长度0/模型SHA全零/bit长度=8×payload B。
正文按model_zlib+payload排列。神经payload为32bit整数算术位流，正频率CDF总32768，
采用半区/四分之三区间归一化和终止位；最后字节padding必须0，最多32个虚拟尾零。
帧外额外字节、声明长度超限、模型/位流/原文SHA错误必须失败；原大小≤1MiB。
Zlib/LZMA流检查结束和额外数据，Zstd绑定声明大小/窗口和无外字典，禁止串联第二流。
主Archive必须拒绝实验magic；Memory/CAS、旧档案和所有默认保持。
不做auto回退，神经更大或更慢也要原样报告；不由payload节省直接推导完整收益。

## 训练前固定的资料和规则

原完整文件逐项匹配docs/text-lanes-inputs.json（v0.32已固定的SciPy/SymPy/LaTeX2e各两文件），
不执行或import输入代码。TRAIN每项目第一文件的前min(32768,len)B：
SciPy_linprog.py、SymPy_expr.py、LaTeX_amsmath.dtx；总95292B。
TEST每项目第二文件前8192B：SciPy_basic.py、SymPy_integrals.py、LaTeX_ltmath.dtx；
另取原固定SHAKE噪声的前8192B，合计4对象32768B。精确prefix SHA也记录。
这些是文件分离前缀，同项目不算未知领域，已见档案不声称全新数据；不能推广为完整源文件压缩。

seed20261026、1epoch、batch256、Adam lr.002/beta.9/.999/eps1e-8、全局L2梯度clip5，
NumPy2.4.4 float64；训练不同文件重置BOS，固定seed的全体样本排列，不用测试早停/选epoch。
NumPy导入前设置OMP/OPENBLAS/MKL/NUMEXPR线程环境为1，报告环境要求不冒称独立确认线程池。
参数初始化：E正态σ.1，W1σ.25，W2σ1/√8，bias0；取rint(weight×256)后clip到int16。
训练一次，300s到模型同步写出上限，超限或失败保留错误，不缩小资料/重训直到成功。
记录训练到模型fsync wall/RSS、训练loss、量化饱和数；NumPy依赖文件SHA/字节及额外账本CPU/RSS另计。
训练loss是训练批次更新前加权nats，不是测试压缩收益。float跨机器训练可复现未测；
同帧整数解码不要求重新训练。私有训练模型不随Release发布，仅发布hash/完整元数据与重建代码。

## 模型锁定后正式编码/恢复

训练完成提交模型SHA/字节、来源与训练记录到Git后，才运行3轮×4对象×4method=48编码恢复对，
96个全新阶段子进程，每阶段180s上限。固定seed+round排列16cell，pack/restore依次执行，不重跑。
每对实际写帧+fsync一次、恢复文件+fsync一次，总96个fsync；逐字节读回恢复文件及prefix SHA核对。
源码/协议/输入/模型SHA在前后不变，三轮帧/bit长度/模型账本应一致。
记录输入/模型读取、lazy import前状态、纯codec、写入fsync、额外审计、阶段wall及完整进程wall/RSS。
NumPy不应在编解码子进程导入，SciPy/SymPy输入不执行。无排除的预热调用。

## 门槛与完整成本

对三个科学prefix分别和三个普通codec比较，共9个空间工作点：
自包含完整帧（已经收费权重/头/bitstream）+专用源码分配严格更小才过空间；
再同时要求三轮编码/恢复stage wall中位值不差才过联合。噪声3比较另报。
专用源码方案B：plain只分配公共neural_frame.py，neural再加neural_small.py和arithmetic.py；
方案C为全部递归RKV Python+HTML，二者互斥不相加。权重已在帧内不重复加；另列直接codec payload大小。
训练脚本/训练输入、NumPy安装字节、训练/导入/依赖账本CPU/RSS另列，不把它们称0或免费。
普通codec现有依赖与公共Python/OS/文件系统/硬件未全额分配，完整部署成本未测，必须明确范围。
只3个科学前缀、3轮重复不是独立新样本；不做跨域显著性、模型智能或生产吞吐声明。
负结果只否决这个候选，不否决所有神经方法。不搜规则/训练量/位宽/对象数追正结果，不追加Rust库成本。

## 交付

源码/必要恢复与损坏测试、先冻协议/再冻模型/再评估、原始JSON、图表、详实报告、README及Release。
所有原始科学源/前缀、编码帧、恢复副本、私有模型留本地，不提交私有研究或密钥。
CI成功后发布，再下载实际资产核验SHA/源码及模型账本、物理仓库外安装和神经帧smoke、proof重下载。
冷缓存/跨机器/长期对话/模型回答质量未测。新增模型API请求0，当前额度窗口不跨重置。
