# v0.39 冻结协议：有界在线字节统计，无外置训练权重

本版是明确的新概率表示候选，使用原整数算术编码器。先实现/合成测试/冻结代码与本协议，再准备新固定段SHA并提交，最后才运行评分。不能根据新段内容改规则或扩大对象摊费用。前提v0.38实际发行资产/外部安装/proof已经完成。

## 假设和适用范围

零外置权重的在线一阶统计可能抵消原神经权重开销，但冷启动、稀疏状态和CPU可能使其失败。与在线零阶控制及zlib6/zstd3/LZMA6比较；不与不同输入上的旧NN分数直接排名。不是未知项目泛化或生产/推理收益。旧61模块除版本字面量逐字节不变，新增online_counts/online_frame两个独立模块，Archive/Memory默认不变。

## 预测规则

256字节，前一字节为行索引，BOS=256；一阶257行，零阶1行。每行256个uint16，初值1；uint32行sum初值256。每次有状态cdf(context)在给当前符号预测前，更新上一真实符号所属的过去行，计数+2、sum+2，首BOS不更新。每帧新实例；终止后末字节无需再更新（无下一次预测）。此回调是顺序接口，不能多次探测同一位置。

更新后row_sum>32768，则该行每计数改为max(1,(n+1)//2)，重算sum。更新前后计数不超过uint16界。初始等价于每字节1/2伪计数，rescale后不声称具有严格KT通用界。

CDF总32768、最小频率1：freq=1+floor(count*32512/row_sum)，余数向符号升序分配，累加成257整数CDF。完全使用确定性整数，无模型训练、NumPy或浮点推断。原arithmetic.py不变。logical state为零阶516B、一阶132612B；Python拥有的持久容器大小另记，临时CDF、对象共享内存由整体RSS反映，不能把逻辑计数表称全部RSS。

规则标识为online_counts.RULE的ASCII JSON，sort_keys=True、separators=(',',':')、无换行，SHA256绑定到帧头；各键和值由冻结源码唯一确定。固定参数含alphabet256、bos256、initial_count1、update2、row_rescale_above32768、rescale字符串max(1,(n+1)//2)、cdf_total32768、cdf_min1、remainder ascending-symbol、update_timing previous-symbol-before-next-prediction、version1。方法码区分order0/order1，不能改标识绕过旧解码规则。

## 实验帧

独立magic RKVONL01，版本1，134B HEADER沿用结构 `<8sBBIQQQ32s32s32s>`；方法0/1为order0/1，2/3/4为zlib6/zstd3/LZMA6。原model_n槽必须0；在线model_sha槽是规则SHA，普通方法全零；其他为raw长度、payload长度、有效位长、raw SHA、payload SHA。无嵌入权重或外置字典；规则字节已在专用源码，32B规则SHA已包含134B头，避免重复收费。

raw最大1MiB，实际每段8192B。检查方法/版本/长度/SHA、算术padding、单一普通codec流和尾随拒绝。旧v0.38神经reader、主Archive拒绝该magic；发布后实际旧wheel补验。新增入口显式实验，不自动择小、不替换默认。恢复必须只用当前帧和公开规则，无训练语料或前一个对象状态。

## 输入冻结和正式次数

沿用docs/text-lanes-inputs.json固定公开档案完整文件身份；只取SciPy linalg/_basic.py、SymPy integrals/integrals.py、LaTeX base/ltmath.dtx 的字节区间[32768:40960]，各8192B；这与原训练文件和旧评价前8192B无重叠。既有完整文件已读过，声明新的是区段评分而不是首次接触文件，更不是跨项目独立验证。

另有SHAKE256(b'RKV-1 online-counts v039 fixed noise seed20261026').digest(8192)和bytes(range(256))*32两个合成控制。准备只做完整SHA/范围/段SHA，不运行候选/基线；docs/online-counts-inputs.json提交后再评分，不公开原段。

5输入×5预定方法×3轮=75恢复对，150个新codec阶段进程，150次实际frame/restored文件flush+fsync；父调度随机顺序seed=20261026+轮号，逐轮串行，不热身/失败重试。每阶段timeout180s，保留所有失败/日志/部分轮，不能覆盖重跑。输入只读字节、不执行源项目、不导入NumPy。进程重启不叫冷缓存；本机常规缓存条件，跨机器未测。

## 事先门槛、统计和完整费用

机械门槛：75/75原字节及SHA一致，每个25条件的三轮完整frame SHA完全相等；原失败不得被新轮覆盖。严格拒绝及rescale属于单元/发布smoke，不能加进科学恢复分母。

对每条件列payload B、有效bits、header B、完整frame B；编码和解码各计codec wall/process CPU、文件读取/写入fsync、原字节审计、stage CPU/wall、父测完整process wall及peakRSS。状态拥有容器大小在pack计入codec阶段；内存初始化不免费，解码从新状态开始的CPU/RSS也全部实测。无训练或模型加载费用可隐藏。sourceB约定普通方法公共源码为online_frame.py+neural_frame.py+codecs.py；在线另加online_counts.py+arithmetic.py。完整C使用实际递归全部Python模块+HTML，同一对象加一次；B/C替代而非相加。声明Python/OS/第三方库不是完整TCO，codec依赖版本独立列，源码分配不是实际部署可裁剪证明。

大小三轮必须同字节数；时间只报告三轮中位数及各原值，不跑到赢。每个在线候选对三普通codec，在3科学段上共9比较：净B空间门槛为frame+sourceB ≤ 对照frame+sourceB；联合同时要求三轮中位数的codec编码+解码wall、codec编码+解码CPU、父测编码+解码process wall均不大于对应基线。单一进程CPU量化可能出现零值，直接按原值比较，不加epsilon或滤除。C门槛单列；峰值RSS/状态展示但不偷偷取消费用。噪声/重复合成单列，不为科学失败加分。

任何科学收益需明确是这3新段、当前表示/成本口径，不能升级为生产压缩或模型回答提升。若联合失败，不追加同表示原生化以追空间收益；下一个假设需另冻。保留payload/净B/C方向不一致案例。

## 交付

必要测试、冻结提交/输入提交、原始JSON、标准图和实际视觉检查、详实报告、README/版本说明；CI成功后Release，五个实际发行资产SHA/全部递归模块与HTML/源码/协议/记录核验，物理仓库外实际wheel和current native安装、在线帧/旧实际reader拒绝/历史smoke、最终proof重下载。原科学语料/段/帧/恢复副本、私有模型研究、课程模板、个人报告、密钥不发布。0新增模型API请求，冷缓存/跨机器/断电/长期会话/回答质量未测或未证明。
