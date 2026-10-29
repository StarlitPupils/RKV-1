# v0.87候选：证据干预的第二批问题复测

状态：候选公共采用，尚未冻结/正式/发行，新API调用0。上一批48次硬预算单独花完；用户已明确批准本批新增48次，512输出token/次，0重试。不给出密钥，也不从聊天重新找密钥。当前窗口仍受1793272390的Codex quota边界约束，不能跨窗续跑。

## 问题与固定设计

v084为16题9/16对4/16与4/16，描述性配对p=.125。下一项不调旧16题提示或预算，而在原270题池中以固定标签分层和SHA选另外16题（6支持、6反驳、4无标注），检验同一证据干预能否在未使用过API的另一批问题上重复。此dev已由项目用过，不能称未知数据或新的科学泛化。筛选不读取v086检索结果或任何API response；题池先前已经排除v015/v084所有28个ID、规范化问题和train重合。

完整复用v084冻结的only-evidence提示、请求字段和严格解析/原文引用核验器；BM25 model、原Store SID、12篇/4096原记录B完全不改。三个条件empty/retrieved/固定SHA环donor rotated，每题各一次，48个slot固定顺序。donor不可按标签、相关性或结果挑坏；原有source重叠于预测后独立审计并保留。每次最多512输出token，0自动重试；失败占slot且后续停止，missing留48分母。

## 门槛与时钟

H1：48响应全部持久化、schema/原source字节/引用审计通过，预测过程不读gold，所有预测落盘后才评分，完整失败分母及parent/worker/finally/usage保留。H2沿用原门槛：retrieved16题正确数及12annotated判定+完整rationale同时严格高于empty和rotated；任何缺失则不通过。独立组别混淆矩阵、6/6/4分层、配对win/loss/tie及exact p仅描述，不切换headline或把schema当NLI。

新旧两批分开报告；合并32题只可列预声明的附表，不能用合并替代新批失败。模型alias可能在两批间变化，记录实际返回model/id/created/usage和时间，远端weights/runtime/RAM SHA未知null，不把不同时刻服务视作固定模型权重。

## 授权与交付门槛

用户已批准新增48次，但仍须公共代码/协议/原输入SHA/必要测试/exactCI冻结、真实模型配置确认和独立guard后唯一正式；每call前查本窗口quota，reservation fsync后不可复用slot，HTTP/timeout/transport错误零补发。原prompt/科学原文/原HTTP response/模型/key只私存。

完整本地包/外安装/CI/实际7资产SHA与递归源码/外实际发行安装/proof重下载完成才称交付。旧模型/Store/历史API及全部失败/派生/source/RAM费用不归零；不能把reference美元带当实际账单。
