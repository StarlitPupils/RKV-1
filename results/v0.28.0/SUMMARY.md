# v0.28 显式上下文控制与请求体合同实验报告

## 交付与依据

v0.27在8KB有迁移支持，24KB论文组区间跨零，48KB train净退步，因此只接入显式
选择器，默认source-order/24000正文UTF8字节保持。Python/CLI/本机HTTP可显式
选择source-order或lexical，预算限8000/24000/48000整数。无模型质量新结论。

新派生记录计正文、context JSON、完整POST body实际字节及实际发送SHA，保留
原locator和原句ID；body预算不等于完整prompt/token/费用。引用仍只能来自已
暴露的原句，错误不会重试或自动换选择器，失败输出不能升格原证据。

## 固定合成来源与测量性质

两个SciFact形状JSONL文档：doc1含7990B/15990B两段及一条含rareanchor/引号/
雪/café的短段；doc2不匹配。原UTF8/CRLF逐字节保留。fixture服务只回显可见
引用，不是语言模型；其SUPPORT只为测试绑定，绝不记科学正确率。正式13次均为
127.0.0.1本地HTTP请求，远程模型0次，未扩大旧24次预算。

## 六条件实际输入字节与可见原句

| 选择器 | body预算B | 实际body B | context JSON B | 完整POST B | 原句ID |
|---|---|---|---|---|---|
| source-order | 8000 | 7990 | 8086 | 8793 | [0] |
| source-order | 24000 | 23980 | 24105 | 24818 | [0, 1] |
| source-order | 48000 | 24037 | 24193 | 24916 | [0, 1, 2] |
| lexical | 8000 | 57 | 155 | 866 | [2] |
| lexical | 24000 | 8047 | 8174 | 8891 | [0, 2] |
| lexical | 48000 | 24037 | 24193 | 24916 | [0, 1, 2] |

所列POST已在接收端按实际raw bytes核对len/SHA，不是按字符/token估算。context
JSON含title/句ID/结构，POST还含system/claim/模型参数/嵌套JSON转义。48k两选择
器可产生同一prompt；不硬造差异。不把合成decoy的省字节称科学语料压缩收益。

## 默认、CLI与HTTP兼容

省略控制与显式source-order/24000生成逐字节相同POST；实际下载核验的v0.26
wheel在仓库外读同一Memory并发默认请求，POST也完全相同。该发行responder
memory_model.py SHA与v0.27相同，因此验证了前版原默认兼容。旧CLI明确拒绝新
flag，拒绝时0上游请求；Memory/CAS/归档与所有原来源格式无变化。

HTTP /api/status新增context_api_version=2、选择器/预算枚举与默认值。原
memory-v1仅question仍兼容；显式控制要求memory-v2 header，旧服务会拒绝新
header，避免静默忽略选项。新服务对v1携带控制返回400，v2错误selector/布尔
预算返回400且不调用上游；错误后v1正常请求成功，锁正常释放。保留loopback/
Origin/内容类型/长度/单请求锁，原页面仍使用旧默认。

## 拒绝路径、证据与派生隔离

4个非法Python控制在请求/写回前拒绝，3个HTTP错误无上游调用；一个fixture故意
返回未暴露句ID，回答被拒绝、只写失败派生记录，不重试。全部模型派生文件的
primary_evidence=False、record_type=derived-model-answer，不能隐式检索。
CAS/index/manifests/HEAD实际逐文件大小/SHA前后相同，原文件最终逐字节恢复。

首个本地尝试的后置检查误把inventory的汇总对象当文件清单，未接受该结果；
随后修正为实际路径清单、在新目录重跑本正式13请求。运行库/选择器规则没有
因该审计修正改变，失败尝试留.tools，不覆盖正式结果。

## 测试与成本

196项完整测试运行，195通过、1项Windows符号链接权限跳过；功能回归启用既有
原生库，但本轮合同不依赖Gear，不产生原生性能结论。CLI、HTTP v2、旧默认、
无效输入、原句引用及失败派生路径均覆盖。正式请求计数不包含单元测试fixture。

合成Memory当前逻辑字节51613B，目录{'cas': 840, 'indexes': 28812, 'manifests': 509, 'answers': 21358}；全部53模块/HTML源一次373623B。包含本次新增派生答案，不能把这个玩具库当科学压缩基准。公共运行时/安装/pyc/文件系统未全额分配，不是完整部署大小。

## 执行与下一步

```powershell
python -m rkv1 memory-answer MEMORY "claim" --context-selector lexical --context-body-budget 8000
```

真实服务配置沿用RKV_LLM_BASE_URL/RKV_LLM_MODEL，密钥仅本机环境变量；本轮未
调用真实服务。HTTP显式控制发送X-RKV-Client: memory-v2，并先检查/api/status
能力。新选项需要v0.28客户端/服务，不依赖私有扩展参数或隐式回退。

下一步优先明确论文/来源已知与开放检索两种工作负载，隔离检索遗漏和上下文
选择；是否开展新真实模型评测需另行明确预算。本次功能接入不证明无限上下文、
新回答正确率、E3、多跳、长期对话、形式证明、冷缓存/跨机器、掉电/并发或GC。
