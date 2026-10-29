# 下一轮整合方案草案：固定跨度准入的有界 metadata 缓存

状态：代码已采用，必要owned测试后全回归/冻结/CI待完成；真实正式worker=0，未发布。历史初版方案与初次测试失败均留私有日志。

## 已有证据与可证伪假设

v082保真诊断确认已见4096任务中，每个查询开始142个相关缓存key在实际lookup前全部消失。固定64KiB所有节点LRU曾慢于全树15.9–18.5倍。提出单个先验候选D：仅span>=64的完整metadata子树hash允许进入原64KiB owned-graph LRU；阈值64来自此前未实施假设，不扫描阈值或cap，不靠4096预检挑结果。这是已见任务上的工程候选，不能声称独立泛化或新科学。

## 一轮做完整的内容

同一显式held Scope/独立anchor、8个迟到双path请求、原CAS和原metadata全校验；四法A全树/B逐请求重算/C旧全部node有界LRU/D固定span准入同场测。所有基线源码冻结；新D必须保留closed/SID/range/size/checksum错误拒绝和原bytes独立核验。不要只删除旧index文件宣称压缩。

先实现小型owned fixture必要测试：准入边界63/64/65、不准入hash仍正确、hit/miss/eviction/oversize、错误SID/range/stamp拒绝、Scope关闭/异常cleanup、实例隔离、A/B/C/D精确同packet和原bytes。预检只<=17叶；边界测试可直接模拟node，不使用4096实测挑参数。新增状态字段、计数器、skip计量与源码本身均计费，不能继承旧base_B而漏收subclass slots。

正式建议4规模9/64/512/4096×3轮×4角色=48fresh workers，固定轮内顺序ABCD/BADC/CDAB，384packet/768成员/192控制；父READY后独立root认证再生成请求并SHA/时间线。后置48fresh root、56172叶、56220全文件恢复、768成员原bytes、跨法同query/packetSHA、全部rawparent/finally/stdio/文件守恒。以上先逐项核算、源码协议/输入freeze/exactCI，随后只跑一次0retry；错误保留不覆盖。

Primary4096 H1精确证明/原bytes/生命周期/资源记录全部通过；H2 D/A初末额外状态<=0.5且操作后cache-owned graph<=65536B；H3 D/A完整constructor+8issue/read/verify/canonical/write的phasewall/CPU和parentwall各三轮均<=1，零CPU分母为null不通过。D/C、D/B、命中/重算节点只作诊断，不换容易对照当headline。完整RSS、共同Scope O(N)、key排序、插入provisional、observer、源文件及旧快照/派生/模型残留分别计入，不把额外状态降幅称总RAM降幅。

## 报告与边界

一次报告同时给四法正确性、完整成本/负结果、阶段wall/CPU与父进程、RAM/cache全账本、原始JSON、标准图实际视觉检查、已见数据限制和下一步判断。旧v079–082原结果/协议不可重写；没有新模型API或下载授权，CPU离线，真实长期会话/开放NL科学NLI/回答收益/无限上下文仍未完成，冷缓存/跨机/物理SSD全系统IO未测。

正式结果后再做完整本地发行及实际GitHub资产SHA/源码/仓库外安装/proof重下载，一版收尾后才下一版。需要完整额度窗口执行；当前实际额度窗结束15:20:58；剩余实际quota不足时准确保存未完成状态，不跨窗。

正式round角色顺序ABCD/BADC/CDAB；各round规模顺序沿v081为9/64/512/4096、64/9/4096/512、512/4096/9/64。A=retained B=ephemeral C=bounded D=span。0retry，600秒/worker。D复制整份NodeLRU，仅put在同样SID/range/value校验后新增span<64不准入；全部复制源码成本单列。其他算法/8请求/64KiB均不变。新全角色driver统一关闭stdin/stdout资源，不以旧资源警告改变研究headline。
