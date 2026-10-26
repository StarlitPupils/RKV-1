# v0.44.0 实验报告：额外CAS工作量的排他调用角色归因

## 结论

两布局各3轮、6个fresh worker的重仪表诊断完成。600proof、1710原record绑定、156历史源文件恢复、全部原始CAS计数与memory整树均等v0.43同轮同布局cacheOFF/meterON。12795次原Store.block事件逐项守恒、600scope全部恢复。假设“额外decoded输出中至少80%归manifest_validation+index_view”三轮门槛 **True**。

| 轮 | separated−clustered全部decoded B | manifest+view角色差B | 归因比率 | ≥80% |
|---|---:|---:|---:|---|
| 1 | 209821140 | 212414238 | 1.0123586117204395 | True |
| 2 | 209821140 | 212414238 | 1.0123586117204395 | True |
| 3 | 209821140 | 212414238 | 1.0123586117204395 | True |

这是原调用入口的排他计数归因，不是CPU栈采样、不能证明某项校验可删除，亦没有实施优化/cache或测试提速。v0.43两个时间联合门槛失败的负结果保持；本版不把重仪表时间拿来比较速度，不声称E3净收益、自然多跳/真实长期会话或模型回答收益。

三轮确定工作量相同：分散布局3978次解码中3691次、212414238B发生在index_view；直接source_hit仍287次、16215734B。clustered287次全部为source_hit、18808832B。manifest_validation和other_trace在本计量范围内CAS事件为0，不能推成这些阶段没有CPU/SQLite/metadata费用。额外差值归因比率1.01236，超过100%由source_hit的反向2593098B变化抵销解释，而非重复计数。

## 为什么做这项诊断

v0.43原字节行不变而分散到三文件后，cacheOFF/meterON每100trace从clustered287次block/18808832 decoded B升到separated3978次/228629972B；65536B单trace LRU在separated仅少1.54% decoded，时间反向。旧仪表没记录角色，不能回填成index replay原因。本版先验80%假设及差值公式独立冻结，防止根据看到的角色分布事后定义成功。

250本地检查249通过/1Windows权限跳过后，代码/协议/输入引用在`f0ae98910bb28e452d4c4260d150b230a8377f77`冻结，candidateCI `40331351687`成功后唯一正式6worker执行，重试0。旧64 runtime仅发行版本号变化，旧v0.43 base_worker、source/gold/auditor、CASTraffic、evidence_path/固定chunk/4096B入证/3hop/默认replay budget字节不改。cache全程OFF、没有新训练/模型/字典/远程API。

## 角色scope和守恒

PathRoles仅在一次trace内包装同Memory实例_manifest（manifest_validation）、_verified_hits（source_hit）和memory_index.view上下文（index_view），默认other_trace。角色嵌套finally恢复；Store.block入口最内角色为唯一归属。每次在原Store.block恰好一次调用前/后抓原CASTraffic整数差，附block ID/expected_size/返回长度或异常类型，不绕过原stored/raw SHA、EOF、codec、size和原record/JSON成员验证。

每条event的整数计数之和严格等该trace总meter，每trace总meter逐字段等旧v0.43同case。600scope均正常退出、方法/全局view恢复、observer inactive，正式event全部error null/返回length=expected_size；单元损坏例拒绝且保留异常/已发生部分计数。独立原证audit/历史源恢复/ingest/derived写入不在计量scope，scope外读取不再计数；新trace新observer，不跨请求复用内容。

readB=payloadB+84×opens、decoded=raw+compressed、readcalls=2×opens、event数=decode成功数合同通过；unknown-key等零事件trace的计数保持整数零，非未观测。物理SSD/全系统IO/SQLite C层/metadata/stat/预取未覆盖部分仍null。应用CAS decoder输出是工作量，不是原科学文件净压缩量或实际SSD读取。

## 精确计划与原证据

固定顺序clustered/separated、separated/clustered、clustered/separated，6fresh worker，每worker96主问题=93complete+2missing+1cycle、4控制和2负审计。总576主问题=558complete+12missing+6cycle、24控制、12篡改负审计、600proof、1710接受绑定，不能把576全部算成功回答。

每worker13epoch全ingest后才生成并fsync问题；结构/seed原本公开已知，非新科学或未知迟到问题。指定SID/known root/显式引用链不等于自然语言多跳。各proof/问题SHA/全部源/完整memory文件集合与字节SHA逐一等旧v0.43，156历史文件（clustered39+separated117）逐字节恢复，独立auditor再读实际locator/原record SHA/JSON成员。HEAD、旧快照/索引/derived保持，失败不覆盖重跑。

## 全部角色原值

| 轮 | 布局 | 排他角色 | block调用数 | 应用CAS返回B | decoded输出B |
|---|---|---|---:|---:|---:|
| 1 | clustered | manifest_validation | 0 | 0 | 0 |
| 1 | clustered | index_view | 0 | 0 | 0 |
| 1 | clustered | source_hit | 287 | 814700 | 18808832 |
| 1 | clustered | other_trace | 0 | 0 | 0 |
| 1 | separated | manifest_validation | 0 | 0 | 0 |
| 1 | separated | index_view | 3691 | 8528272 | 212414238 |
| 1 | separated | source_hit | 287 | 641280 | 16215734 |
| 1 | separated | other_trace | 0 | 0 | 0 |
| 2 | clustered | manifest_validation | 0 | 0 | 0 |
| 2 | clustered | index_view | 0 | 0 | 0 |
| 2 | clustered | source_hit | 287 | 814700 | 18808832 |
| 2 | clustered | other_trace | 0 | 0 | 0 |
| 2 | separated | manifest_validation | 0 | 0 | 0 |
| 2 | separated | index_view | 3691 | 8528272 | 212414238 |
| 2 | separated | source_hit | 287 | 641280 | 16215734 |
| 2 | separated | other_trace | 0 | 0 | 0 |
| 3 | clustered | manifest_validation | 0 | 0 | 0 |
| 3 | clustered | index_view | 0 | 0 | 0 |
| 3 | clustered | source_hit | 287 | 814700 | 18808832 |
| 3 | clustered | other_trace | 0 | 0 | 0 |
| 3 | separated | manifest_validation | 0 | 0 | 0 |
| 3 | separated | index_view | 3691 | 8528272 | 212414238 |
| 3 | separated | source_hit | 287 | 641280 | 16215734 |
| 3 | separated | other_trace | 0 | 0 | 0 |

差值比例是两个布局的有符号角色差除以有符号总差，并非同一布局的分区占比；若其他角色差为负，前两角色比率可超过100%，不表示事件重复分配。全部四角色在每个布局内仍严格守恒。角色名仅标注原调用边界，不将manifest/view的全部CPU或SQLite物理读都误纳入CAS字节。

![原始CAS调用的排他角色](path-roles.png)

标准图已实际打开检查，两个计量单位和图例明确、无覆盖；显示第1轮，两布局各三轮原值全留表/JSON。冻结analyzer原图顶部无留白；额外plot-only脚本增加12% headroom及总量标签，原图本地保留、原始分数/冻结源不改。初图/末图/附加程序SHA及额外绘图成本在figure-postprocess.json；这不是重跑诊断。本版只描述归因，不从柱图或时间得出性能提升。

## 完整诊断成本

| 轮 | 布局 | block事件 | trace内unique请求之和 | trace内重复调用 | 重仪表trace wall s | trace CPU s | parent完整wall s | 观察peakRSS B | 完整memory B | 其他worker文件B |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | clustered | 287 | 99 | 188 | 0.355753 | 0.312500 | 1.369114 | 39043072 | 1171964 | 371201 |
| 1 | separated | 3978 | 419 | 3559 | 1.550778 | 1.406250 | 2.660551 | 41844736 | 955146 | 362216 |
| 2 | clustered | 287 | 99 | 188 | 0.359346 | 0.312500 | 1.385676 | 39284736 | 1171964 | 371217 |
| 2 | separated | 3978 | 419 | 3559 | 1.547498 | 1.531250 | 2.659409 | 41721856 | 955146 | 362207 |
| 3 | clustered | 287 | 99 | 188 | 0.362656 | 0.218750 | 1.395060 | 39276544 | 1171964 | 371216 |
| 3 | separated | 3978 | 419 | 3559 | 1.544645 | 1.515625 | 2.669069 | 41881600 | 955146 | 362224 |

unique定义为每trace内部(block_id,expected_size)集合，跨trace再相加；重复请求不等于可安全跳过验证，也不声称对应任何缓存上界。它仅帮助后续设计资源生命周期假设。本版JSON事件存储、dict快照/角色patch和仪表开销全部在诊断内，不当免费的产品功能。

全部child+roles+parent JSON共11649519B，driver日志0B；各worker源文件、questions/partial/full-ledger、原memory旧snapshot/index/manifest/HEAD/derived/残留在derived-metrics.json逐项保留，derived每布局仍同v0.43。6目录属评测重复，不等于部署需要六副本。角色sidecar在worker主报告后输出，原workerwall/RSS观察点不覆盖全部序列化/末尾进程；父完整wall紧包subprocess.run到退出包含该成本。

完整递归64 Python+HTML共413548B、所有专用/复用评测程序逐个bytes/SHA在source-resource.json。没有训练/权重/字典/新模型调用；解释器/依赖/平台未分配成本不能免费。原worker完整CPU、ingest/trace/独立audit/derived费用保留原JSON，重仪表parent wall和RSS仅作费用，不与旧版计时做性能对比。native只既有CSV/Gear功能smoke，非本候选性能证据。

附加plot-only程序2489B及其元数据另计在figure-postprocess.json，不混入已冻结评测源码集合；附加绘图wall 0.536244s/CPU 0.546875s（含matplotlib导入，排除解释器启动和写本记录）。发行验证会额外核该程序与最终tag一致。

独立分析/全部原证和历史恢复/文件与计数核对/绘图额外wall 3.762160s、CPU 2.140625s，观察RSS 91258880B，排除解释器启动和写本计时记录，不计在线查询性能。

## 复现、发行及下一步

使用全新work/out运行python -m scripts.run_path_roles，再以冻结Git commit和原测试日志运行scripts.analyze_path_roles。600s/worker、exclusive+fsync侧车、真实退出码/child和rolesSHA/父完整process计时都保留，不重跑覆盖旧记录。

原始JSON/标准图/本报告/冻结协议/输入清单引用/源码账本随版交付。CI后Release实际5资产SHA/递归Python+HTML/actual sdist角色程序和所有结果对tag核验，actual wheel+current native物理仓库外安装，actual sdist角色scope/原proof/事件守恒/还原及scope外不计、旧格式/历史源/CLIsmoke；最后上传proof重下载通过后才完整交付。

若归因支持，下一步可另冻一次请求内验证/SQLite视图复用候选，必须先定义保留原完整性/新请求重验/异常清理及全部RAM/源码/CPU边界；本版没有偷偷实施。无新增模型API授权（旧24已用完）；真实科学语料/段/帧/恢复副本/私有研究模型/模板/个人报告/密钥不发布。物理SSD、冷缓存、跨机、真实长会话、回答质量与无限上下文仍未验证。
