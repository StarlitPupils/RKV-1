# v0.48 冻结协议：公共 batch API 的固定 1/3/32 键科学记录成本

仅在v0.47实际资产/完整65源码/仓库外安装/public API与actual sdist auditor/最终proof全通过后实施。本版不改已交付memory_batch.py或memory.py，65 runtime仅发行版本字面量；不调预算、SQL、校验或默认集成。v0.45/46科学速度属旧assessment实现，本轮单独检验新公共API，不能沿用旧分数。

## 假设、输入与工作负载

先验假设：一次请求的view/资源核验可随批量摊薄；单key为低摊薄控制，可能变慢，负方向保持。每个固定批量独立评时间联合门槛，不要求某个必胜/必败，不据结果设智能阈值或默认路由。

既有SciFact corpus.jsonl，8307875B/5183doc，SHA b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62。沿原来源archive SHA11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be，abstracts ODC-By-1.0；v0.30及更早用过，不称未知科学验证。无claim/label、自然语言问题、科学多跳或生成回答；0模型API，本机CPU离线。

沿v0.46 SHA256(ASCII rkv046:+key)、key排序，不换salt。每size=1/3/32取排序前32*size key切32组，组内互异；Random(20261026+round)打乱组顺序。size3的key组完全等原v0.46 spread，不宣称新独立证据；三个大小是32/96/1024个原文档的嵌套集合，最大1024doc，重复轮不是独立科学样本。新的只是公共实现和预定批量成本范围，不调已见selector追正。

docs/api-bundle-inputs.json在正式前记录全源SHA、九个plan SHA/数量/selected bytes范围。仅输入解析/计划/预算大小预备，无lookup/codec或结果评分；预备CPU/wall未测null，不回填。最大入证B依size为3348/9548/57875，均<公共API原默认1MiB，无需调整cap。全部真实科学原文、完整hit、恢复副本只留本地.tools，公共只有key/SID/locator/SHA/计数/成本。

## 冻结精确计划

size1/3/32 × API OFF原逐key.lookup / ON公共.lookup_many × meterOFF/ON ×3轮=36fresh worker。A–D=size1 off/off,on/off,off/on,on/on；E–H=size3对应；I–L=size32对应。固定ABCDEFGHIJKL/BADCFEHGLKJI/IJKLGHEFCDAB，每字母每轮恰一次。每worker一个默认v3 base-only科学源/32bundle，无更新/历史delta；全体1152bundle/13824原record绑定/36整corpus逐字节恢复、9组同轮同size四条件proof/全部memory树相同。不存在无证问答或失败回答分母；正式拒绝控制0，必要非法/预算检查沿v0.47单元，新增selector/auditor合成检查1项，完整260测试/exact冻结CI成功后唯一计划。单worker600s，失败/超时保留，不覆盖追加重测。

全部keys/SID相同、原record每次读取验证；ON默认1MiB、maxkeys32，API内部预算/固定SID/原selected校验不改。OFF的batch_result元数据null。ON576请求核admitted_source_bytes等实际原record长度、max_source_bytes=1MiB/maxkeys32、原方法scope保证（真关闭/清理由原unit覆盖）；不添加RAM图遍历或方法patch。原science_bundles.catalog/canonical/publicproof/ledger/排除文本逻辑复用且字节不改，新api_bundles仅预定size选择器和独立原JSON审计。

## 门槛与独立审计

三size各3对meterOFF ON/OFF query wall、query CPU、parent完整process wall比的中位数，三者均≤1才时间联合通过；CPU分母0为null且失败，不加epsilon/轮次/换计划。单key反向/任何size失败均照实报告，不把总体均值掩盖单key。不从跨版绝对时间推速度。API调用/原loop都在scope完整计时内，包含API校验、view/资源构建、原record读取/关闭和结果hit extraction；meter对象创建在timer外，parent仍包含，不事后剔除CPU/设置门槛。

base-only无delta，所以meterON预期所有CAS整数计数ON/OFF每对完全相等，三size三轮均相等是工作量控制，不称字节节省。576meterON守恒、576OFF继续null；readcalls=2opens、opens=decode attempts=success、readB=payload+84opens、decoded=raw+compressed。应用CAS B不是SSD/全系统IO，SQLite C层/metadata/OS缓存未覆盖。原record入证1MiB也不是实际IO/RSS上限。

独立auditor用全源原lineoffset/length/行SHA/JSON doc_id/title/abstract逐字段构造expected hit，私有proof重验，public hit/proof SHA/locator绑定全部核；各size的四条件case及文件树相同，原树/HEAD前后不改，无remember/派生答案。全源逐字节恢复36次，不叫历史会话。新publicJSON递归拒绝title/abstract/sentences/quote/body/text/object字段，实际package审核相同；公开metadata不含科学文本。

## 成本与交付

全部source副本/CAS/index/manifest/HEAD/残留、私有fullhits/plan/ledger、child/parent/日志/图/原始JSON、复用和专用源程序按实际B/SHA分别记账，完整65递归Python+HTML不能漏模块。36评测副本不是部署36份要求。input/plan/privatehits/ledger各一次fsync，child/parent exclusive+fsync，内部memory fsync未知null。原input准备未测CPU/wall保留null。

ingest/query/独立audit/full recovery/workerCPU、紧包subprocess.run启动到退出parent完整wall、分析图表额外费用单列。raw/catalog/私有proof累计也占worker内存，observed peak RSS纳入但不是完整增量生命周期外采样；SQLite逻辑页/资源图/原生allocator等本公共API未独立观测，不填零或借旧QueryView峰值。未分配平台/依赖不称完整TCO。训练/模型/字典/新模型调用0。

标准图实际视觉检查、详实报告/README/路线/release说明/GitHub，CI后Release，实际所有资产SHA/递归65Python+HTML/tag/新旧assessment程序、物理仓库外actual wheel+current native及API1/3/32预算/旧SID/兼容功能、actual sdist新selector/auditor合成smoke、最终proof上传后重下载全部通过才完成再下一版。

即使通过也仅为既有科学原文的指定来源批读取成本，非未知检索、语义/图、多跳回答、真实长会话、生产吞吐或无限上下文。E3净收益仍失败、E4整体未验收；冷缓存/跨机/SSD物理/全系统IO/回答质量未测或未证。旧24模型API用完无新授权；科学原文/帧/恢复副本、私有研究模型/课程模板/个人报告/密钥不发布。
