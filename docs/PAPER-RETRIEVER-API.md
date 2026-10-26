# v0.55 冻结候选协议：固定模型、显式SID的实验性论文证据调用接口

状态：在v054 actual发行proof完整核验后，将私有候选集成实验runtime；全库测试/代码协议/输入/CI冻结先于唯一正式机制运行。8项私有合成检查及重复假查询smoke不是本正式评估。

目标是让用户可以从实际wheel调用 `rkv1.experiments.paper_retriever.PaperRetriever(store_root, snapshot_id, model_path, model_sha256=...)`，query只接受claim文本和固定方法。显式SID/模型SHA由调用方指定，不自动读HEAD/寻找服务，不新增远程调用或生成答案。当前仅接受scifact-whole-original-record-v1模型，不混用EntailmentBank短句模型。

排序token/BM25/6+6图扩展/入证函数从v053同SHA assessment数学逐字复制进入自包含wheel模块，必要合成方法等价检查；两个实现今后变更必须分别冻结测试，不能把旧脚本科学耗时冒充新接口性能。固定最多12篇/4096原整行B，只允许调用方收紧；query非空字符串≤4096字符/不含NUL，bool/越界budget/未知方法拒绝。默认Memory/CLI/UI不集成，接口在experiments明确实验性质。

模型最多32MiB原payload，显式expectedSHA匹配后加载，拒绝JSON重复key/NaN/错误来源kind/参数、坏locator、overlap、坏posting/token长度与非对称图/control degree。payloadcap不等于RSScap，完整模型永久保存在该实例内存，构造CPU/瞬态raw/modelPython对象都计费用。已有实例固定已加载模型，磁盘模型后续变化不影响它，fresh loader按原expectedSHA拒绝变更；model_info与返回hit不泄露可变内部结构。

每query新snapshot元数据验证原manifest/sourceSHA和全部locator范围；每selected原range仍走CAS stored/raw/codec/size校验，再核原recordSHA、docID、title/abstract schema与hash。返回原科学文本/locator供本地使用，selected_source_identity_verified只说明selected原文身份，不验证所有未选块、科学蕴含或生成答案。新请求不保留decoded缓存；请求之间的selected CAS损坏必须拒绝。旧SID在新快照提交后继续固定，newSID/sourceSHA与旧模型不符则拒绝。

必要测试8项：三方法与冻结assessment同rank/admit/原locator字节；旧SID稳定与新SID模型不配拒绝；跨请求新CAS损坏拒绝；输入限额/metadata拷贝；SHA/JSON重复/NaN/schema/32MiB+1拒绝；坏locator/graph/posting拒绝；实例模型pin与fresh loader拒绝；返回hit可变对象不污染下一请求。完整runtime测试预计285检查（以真实test log为准，不硬写已通过）。

正式机制评估冻结后3freshworker，各方法1次；使用已见SciFact v053 model/source/round1 report/query-check同SHA，0新训练/0新科学质量试次，894次新接口机制查询。每worker新Store zlib/fixed65536/bounded相同label，显式SID要等v053；每query selected/B/原title/abstractSHA/locator/proof逐项等原评测，并保存原文SHA隔离文本。所有298实际检索主张都验，188/110分母继承；三worker0重试/600s，父完整wall、constructor/fullmodelRAM/ingest/query/原Store全部文件/源副本/原模型训练成本/66递归Python+HTML分别记账。新source读取是机制一致性绑定，不能称新未知数据或回答收益。

父/worker JSON独占+fsync，保存失败不补轮；旧0.53/0.54负结果不变，不改已见参数追正。标准图若报告只画一致性与实测CPU/wall范围，实际视觉检查；不得用旧/new不同阶段时间做加速宣传。正式机制运行必须在exact candidate CI成功后开始；固定3worker/894机制查询/2559selected绑定，独立审计额外2559绑定和3整源恢复，失败不补轮。代码/协议冻结不等于版本交付。

每版报告/rawJSON/协议/README/release，CI后实际资产SHA/新的66递归Python+HTML、实际物理外wheel/currentnative+新公共API功能/旧sdist候选、finalproof重下载完成。以前65计数须按真实模块集动态更新，不能只改数字漏测新增模块。原科学source/claims/fullhits/model/postings/恢复副本/私有研究/模板/个人报告/密钥不公开。全部CPU离线，旧24模型API耗尽，无新调用授权。E3净收益失败/E4整体/真实长会话/verdict/NLI/回答质量/无限上下文未完成。
