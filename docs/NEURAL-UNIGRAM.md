# v0.37 冻结协议：同资料静态unigram诊断，不是新验证或调参

v0.36实际发行资产/物理外部安装/神经帧和最终proof已核验。先冻结本协议和新模块，再构建/冻结静态模型后测原案例。
目的：补上廉价固定训练统计这个缺失对照，区分当前小神经模型的条件预测收益与权重费用。
原E3神经模型、同概率/同码流不改；不重训、不扩大训练量、context/超参不调，不以已见测试选规则。
测试前缀已见，明确诊断，不能作为新独立科学验证或跨域收益。

唯一新模型：对v0.36相同3个训练前缀(95292B)数256字节频数，保底每符号1，剩余32512按经验count比例floor，
剩余按字节升序补1，频率总32768。与神经CDF同保底/总数/舍入规则，静态表不随测试更新。
模型magic RKVUMD01+256little-endian uint16，520B；固定Zlib6，每对象全额实带，无外部免费状态。
新独立帧magic RKVUNI01，沿用原HEADER134B，version1/method4；旧NeuralFrame/Archive都须拒绝新magic；新模块不修改neural_frame.py，未统一路由。
新unigram_frame.py只增加诊断模块，原60runtime除版本号必须字节不变，包括原神经帧、MLP、算术码器。
64位/浮点训练无参与；只用整数频数。NumPy训练依赖只属于原NN历史训练，不给unigram凭空收费。

数据原样：同3科学8192B前缀+同8192B噪声。NN模型仍f4848728bc05e305208cdc50f4ec10b80fee167736deecf334b03e0ebfc03813，
不得重训；unigram只构建一次，在评估前提交其SHA/字节/训练输入元数据，记录构建CPU/RSS及脚本成本。
3轮×4对象×5方法(neural,unigram,zlib,zstd,lzma)=60对/120新阶段进程/120实际帧和恢复fsync。
原4方法的48个帧SHA必须逐项复现v0.36，非新样本；同原数据/模型/格式就应相同。
各阶段仍180s，不重跑直到通过；失败照实保留。所有恢复逐字节匹配原prefix，模型账本/bit长度三轮相同。

成本：plain=公共neural_frame.py，NN=公共+arith+neural_small，unigram=公共+arith+unigram_frame；
另列全体递归runtime+HTML分配，两个方案不相加。每帧模型已收费不重复加；payload与完整帧/源码/CPU分开。
主要诊断门槛：NN vs unigram的payload是否更小，以及完整B成本/编码和恢复CPU各方向；保留混合结果。
对3个普通codec的净空间/联合仍按原定义，不能把只胜NN当胜普通codec或生产压缩收益。
不做模型共享/原生化来掩盖原位流已经更大的事实；不扩大N追正结果。
单元测试：频率正/总数/固定模型长度、empty训练拒绝、all256/Unicode/CRLF精确、损坏/截断/外数据、
新旧实验帧magic互拒且主Archive拒绝。旧v0.36实际发行包拒绝新帧在外部安装smoke复核。
预计新增1模块，实际递归集合61Python+HTML需机器核对，不能硬编码导致漏experiments子模块。

原始JSON、图表/视觉检查、详实报告/README/release notes、代码/CI/Release实际下载SHA、外部安装新static帧恢复/旧reader拒绝、proof重下载。
不发布科学源/前缀/帧/恢复副本、私有模型/研究/密钥；0模型API。冷缓存/跨机未测，模型智能/长期对话收益未证明。
额度普通允许且resetsAt仍1793012933才推进，耗尽或窗口变化保存并删除自动续跑，不跨重置。
