# v0.28 显式上下文控制与实际请求体合同（结果前冻结）

v0.27在8KB下有迁移支持，但24KB论文组区间跨零、48KB train净退步；只接入显式
实验选项，默认source-order/24000正文UTF8字节不变，不开启新真实模型预算。

## 接口与兼容性

Python answer增加context_selector（source-order/lexical）、context_body_budget
（8000/24000/48000整数）。CLI memory-answer对应--context-selector、
--context-body-budget。非法选择/预算/字符串/布尔值在查询/请求/派生写回前拒绝。
top_k默认5不改，用户明确改top_k的效果不属于v0.27 top5实验结论。

本机HTTP /api/status公布context_api_version=2、支持的选择器/预算及原默认值。
旧memory-v1只发question的调用保持；显式控制必须X-RKV-Client: memory-v2，
新服务对v1携带控制返回400，旧服务会拒绝v2 header，避免旧版静默忽略新选择。
保持127.0.0.1监听、Origin/内容类型/长度/单请求锁；前端旧页面仍走原默认。
Memory/CAS/归档格式无变化，新增的是HTTP能力版本，不是新Memory来源格式。

派生记录增加selector/body预算、已暴露body实际UTF8字节、context对象标准JSON
字节、完整POST request_body_bytes和选择耗时；prompt_sha256必须是实际发送体
的SHA。Authorization不进请求体/日志/记录。正文预算不含title/句ID/JSON/转义/
system/claim/API封装，也不等于token或收费金额。引用仍只允许已暴露的原句ID。

## 固定合成合同实验，禁止冒充科学QA

固定SciFact形状JSONL：doc1三段，7990B neutral、15990B general、一条含rareanchor/
引号/雪/café的短段；另有不匹配doc2。保留原CRLF、原UTF8。问题rareanchor，
baseline 8k只见0、24k见0/1、48k见0/1/2；lexical 8k见2、24k见0/2、48k见0/1/2。
本地fixture只回显可见引用，完全不是推理模型。mock的SUPPORT不计科学正确性。

六selector×budget条件+省略参数默认/显式原默认2次+CLI lexical 1次+HTTP v1默认/
v2 lexical 2次+错误句ID回复1次+真实旧发行CLI默认1次，共13个本地fixture上游
HTTP请求、0远程模型请求。旧发行用实际下载核验的v0.26 wheel；其memory_model.py
SHA与v0.27相同，核对默认POST逐字节一致。旧CLI明确拒绝新参数，旧Memory仍可读。

另有4非法Python参数、3非法/旧协议HTTP参数及旧CLI新flag拒绝，全部0上游请求；
错误引用只记失败派生记录，不重试、不改变选择器、不升格证据。HTTP控制错误后
再请求正常v1，验证锁释放。实际请求体len/SHA、body预算、context字节/原句ID、
原record locator逐一核对。不同selector在48k可产生同一prompt，不硬造差异。

原文起止逐字节验证；CAS/index/manifests/HEAD读前后逐文件大小/SHA不变；只新增
非primary的answers，不能隐式检索。源/引用保护、CLI、HTTP默认/新协议及拒绝路径
须覆盖测试。完整测试启用既有原生库，只作功能回归；本实验不依赖Gear性能。
全部53模块/HTML源与实际Memory字节计入，公共运行时未全额分配；fixture/测试
开销不是生产部署大小。记录端到端协议正确性，不作壁钟加速、模型权重或QA质量
结论，不重复计v0.27人工题为新任务证据。

原始科学语料/问题/标注、私有研究、课程报告不发布；这里只发布确定性合成来源
规则、SHA和无正文合同数据。新真实模型质量须另行明确调用预算；E3、多跳、长期
会话、冷缓存/跨机器等仍未验证。下一步再按缺口决定实验，不自动切换默认。
