# v0.45 冻结协议：单trace固定SID的v3已验证SQLite视图复用

v0.44实际发行、源码、仓库外actual安装与最终proof全部通过后实施。只增加assessment候选，不集成默认Memory/Archive或叠加块缓存；旧64 runtime仅版本，旧v043 base_worker、source/gold/auditor/4096B入证/3hop/固定65536chunk/默认replay预算不调。已见合成布局机制，非新科学或自然推理。

## 原验证与请求一致性边界

QueryView单次使用、固定显式SID，仅接受manifest v3。trace计时内进入原QueryResources，原_manifest完整验证，再进入原memory_index.view构建/验证一次只读视图；有delta为原in-memory replay副本，无delta为原readonly base连接。临时包装同Memory.lookup，沿原key校验和LOCATORS SQL，拒绝缺省/其他SID；每hop仍原_verified_hits与原Store.block读取原record、核stored/raw SHA/codec/EOF/size、原record SHA及JSON成员。无decoded块缓存，不预先建好视图后只测查询。正常/异常退出恢复lookup、关闭SQLite、清空QueryResources/引用，不跨trace保留；新实例新请求重新验证。v1/v2/v4明确拒绝，默认原lookup不变，单线程/无并发writer，不称生产化。

连接构建后启用PRAGMA query_only=ON，写SQL明确拒绝。请求开始验证后的不可变视图在这一trace内保持一致；不承诺每hop重验全部未选中源/索引。如果外部在请求中途篡改未再选择的文件，当前trace未必观察到；不能宣称与旧per-lookup重复观测时刻完全相同。任何被选择的原record仍每次读取核SHA，必须拒绝损坏；新trace对坏base/delta/选中源必须拒绝。不能用归因结果删掉验证。

## RAM和成本

ON报告view_builds=1、lookup_calls=proof.lookup_calls、view_storage、峰值SQLite page_count×page_size逻辑页B、Python metadata引用图B/快照与delta数，退出lookup_restored/resources_cleared/view_closed true、active false。metadata图只遍历manifest、QueryResources映射和Snapshot.files等Python容器/引用对象，不含所有patch bookkeeping/SQLite原生缓存/allocator；逻辑页不是实际额外总RAM。worker观察RSS另计，65536仍是chunk而非view总RAM上限。observe/建view/校验/关连接及侧车成本全部收费，无源块cache或免费metadata。OFF的view观测null，非零。

## 完整计划与门槛

layout clustered/separated×view OFF/ON×meter OFF/ON各3轮=24fresh worker，A/B/C/D=clustered off/off,on/off,off/on,on/on，E/F/G/H为separated对应，固定ABCDEFGH、BADCFEHG、GHCDEFAB。2304主问题=2232complete+48missing+24cycle，96控制、48负审计、2400proof、6840接受绑定、624历史文件恢复。每worker13epoch全ingest后生成/fsync问题，规则与seed已知。所有proof/同layout四条件memory整树/来源须等旧v043；case顺序、问题SHA、原SID/locator/record成员继续核验，HEAD/旧文件保持、derived仍收费。单worker600s、失败不覆盖重跑。

预定机制门槛：separated每轮meterON的ON应用CAS read与decoded输出均严格<OFF；clustered两计数预期完全相等（旧诊断无view CAS replay），三轮均相等才通过控制合同。不能要求全布局严格减少后事后放宽。meterOFF分布局评三对ON/OFF中位trace wall、trace CPU、parent完整wall三者均≤1才过时间联合，CPU分母0则null且失败，不加epsilon/追加轮次。meterON时间仅诊断，不用少计仪表冒充算法加速。RAM/源码/费用及所有负方向独立报告；通过也仅是两布局合成机制。

meterON1200trace沿原CASTraffic守恒；OFF1200应用计数null。viewON1200状态/清理/lookup合同通过，OFF1200 view null。OFF/meterON总计逐case等v043 cacheOFF/meterON，证明scope没有改旧基线。全部parent紧包subprocess.run退出的完整wall/exclusive+fsync侧车/报告SHA/真实退出码保留。全部source/current/旧snapshot/index/manifest/HEAD/derived/残留、questions/partial/ledger/log/rawJSON/侧车/图表/CPU/observer/RAM/完整递归Python+HTML及专用复用源码分别收费，不称完整平台TCO。

## 冻结和交付

必要检查覆盖proof/独立audit、一次view及每hop原record校验、旧SID/未来HEAD、缺省/换SID/作用域外拒绝、连接真关闭/异常清理、新请求坏base/delta/选中源及请求中选中源坏字节拒绝、v1/v2/v4明确拒绝。完整测试及代码/协议/输入引用冻结、exact CI成功后唯一正式24worker；独立analyzer核计数/旧proof/624源/整树，不调已见参数。

rawJSON/标准图实际视觉检查/详实报告/README/release/GitHub，CI后actual资产SHA/递归源码/仓库外actual wheel+current native/actual sdist候选scope与旧功能/最终proof重下载后完成。本机CPU离线0新模型API（旧24预算已用完）；私有研究模型/模板/个人报告/密钥、真实科学原语料/段/帧/恢复副本不发布。物理SSD/全系统IO/冷缓存/跨机/真实长期会话/回答质量未测或未证明，E3净收益/E4整体/无限上下文未验收。
