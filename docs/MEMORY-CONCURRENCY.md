# 单 writer / 四 reader 快照一致性：v0.33 冻结协议

## 问题与判定

运行中的读取者能否在单个 writer 连续提交时，每次读到一个完整且可回溯的版本？
这是合成资料上的机械正确性实验；不测模型，不是生产并发、无限上下文、长期对话或吞吐收益证明。
不做故障注入、断电、进程崩溃、多 writer、垃圾回收、索引策略或预算调整。

固定 3 个独立新目录，每轮 1 个初始版本 + 80 次依次更新，4 个独立 reader 进程。
默认 fixed chunker / Zlib / compact-budget-v3 / 原默认 replay budget，不添加并发补丁。
2048 条 SciFact 形状的合成 JSONL；前 4 条为 sentinel，另外 2044 条不变。
每个更新同时改变 4 条 sentinel 中的固定宽度 epoch 编号，其余字节保持不变。
使用 ensure_ascii=True、固定 JSON key 排序/分隔符及 CRLF，保留雪字转义和引号。
源代码中 corpus(epoch) 是唯一数据生成定义；不含真实论文或问题标签。

## 进程与操作

每轮用全新独立 Memory。reader 启动时预先生成 0–80 版本的完整源 SHA，
先显式读初始 SID 一次作为排除的预热/自检，再发 READY。父进程等四个 READY，
启动独立 writer 并发 START。协调文件位于 Memory 树外。

reader 不加人为延迟，循环 search('RKV33EPOCH',top_k=20)，q%10==0 显式指定初始 SID，
其余默认读取 HEAD。writer 重写源文件后依次调用 add，记录每次 add 的实际时间区间。
reader 看到 STOP 后再完成 20 个查询才退出；末次当前读须见 epoch80。
所有子进程清除 RKV_LLM_* 环境，CREATE_NO_WINDOW；不调用模型或外部服务。

每次查询独立计 search wall 与额外审计 wall；不将审计算进 API 延迟，也不忽略总开销。
审计要求恰好 4 个 sentinel：每个 locator SID 等于本次 result SID，key/path/offset/
length/SHA 与该 SID 的原 JSONL 完全相等，title/sentences 等于原记录。
额外通过 CAS 读该 SID 完整源文件、检查完整 SHA 属于预先固定的 81 个源版本，
四条投影全属于该源 epoch。显式初始读只能是 epoch0；同一 reader 当前读 epoch 不倒退。
不将查询结束后再次读取的可变 HEAD 当作本次结果应该等于的 SID。

父进程在停止后显式读取全部成功提交的历史 SID，重复完整源/4 locator/投影审计；
初始 Memory 的除 HEAD.json 以外所有文件均须仍在且 SHA 不变，answers 目录为空。
记录完整 CAS/index/manifest/source 成本；没有清理旧历史来降低存储。

## 终止、负结果和门槛

READY/START 30s 超时，reader 90s 或 20000 查询封顶，writer 父等待 100s；
清理仅针对本 campaign 创建的进程，STOP 后等 reader 35s，必要时终止并记录失败。
首个 reader/ writer 异常即停止该 worker 并写错误；不重试失败 add 或 query。
不同轮仍照固定顺序执行；不加并发强度/预算或调间隔追求结果。

每轮门槛：80 次 writer 成功、所有 reader 正常退出且逐条审计无错、
81 个历史版本全部审计通过、初始不可变文件不变、final HEAD 等于最后成功 SID、
每个 reader 至少一个当前查询区间与至少一个实际 add 区间重叠、最后当前读 epoch80。
三个新目录须全部通过。重叠仅是同机 perf_counter 区间重叠，不证明指令级同时访问。
查询次数/具体交错/延迟允许随调度变化；不是可重复的固定并发时序，也不将零观察错误
外推成零缺陷率。报告逐轮各 reader 数量/重叠/延迟/错误、writer 成本和保留存储。

## 交付与边界

冻结此协议、driver、运行库 checksum 后再测。公开原始逐次 JSON（合成身份/位置），
结果图表、源码、测试、报告、README 与 release notes；不带私有资料/真实源语料/密钥。
源数据可按 corpus() 精确再生，完整源 SHA 随环境 JSON 保存。
记录实际 Python/OS/CPU 数/计时器，预热每 reader 1 次共 12 次排除，新增远程模型调用 0。
同一 Windows CPU 本机；冷缓存、跨机器、生产负载、模型质量均未测。
任何异常都保留原错误与部分结果。通过之后也只决定是否需要修正当前快照机制，
不自动放宽 E2/E3/E4 门槛或改变默认。
