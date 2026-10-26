# v0.44 冻结协议：CAS额外工作排他角色归因

在v0.43实际发行/安装/最终proof核验完成后独立冻结。本版重仪表诊断，不改变缓存/默认运行库、不宣称速度或推理收益。原64 runtime仅版本；run_layout_paths.base_worker、布局manifest、原fixture/gold/auditor、CASTraffic与evidence_path不变。cache始终OFF，没有优化候选或新自然任务。

## 可证伪假设

v0.43 cacheOFF/meterON每100trace：clustered287 block/18808832 decoded B，separated3978/228629972B。其原因此前未测，不能回填归因。本版假设：分散布局相对同块的额外decoded输出中，至少80%属于manifest_validation+index_view。各轮比例=(separated两角色B−clustered两角色B)/(separated全部B−clustered全部B)，分母必须>0，三轮均≥0.80才通过。否则保留负结果，不能调80%/入证/模型/布局/次数。

## 计量scope与不变合同

assessment-only PathRoles在一个trace scope中临时包装同Memory实例_manifest、_verified_hits及memory_index.view上下文，设置嵌套角色manifest_validation、source_hit、index_view，默认other_trace。每次Store.block入口最内role为排他归属；在原block恰好一次调用前/后抓原CASTraffic整数计数差，记录key/expected_size/返回长度或异常类型。没有inspect.stack/跳过校验/cache；原stored/raw SHA/EOF/size/codec与原record/JSON成员绑定不变。

事件属于**调用边界角色**，不是CPU采样栈/真实SSD或全系统IO，也不证明某验证可安全删除。嵌套期间角色finally恢复；正常/异常退出还原实例方法、全局view、Store.block/原计量patch。独立audit、source恢复、ingest不在scope；新trace创建新observer。异常调用也留event/部分工作量，不把已解码后raw SHA失败写成0。

每trace事件整数计数逐项之和严格等总meter，role集合排他完整；原计量readB=payloadB+84×opens、decoded=raw+compressed、readcalls=2×opens等合同保留（正式无错误）。正式事件数=decode成功数、返回length=expected_size、error null，600scope全部恢复。物理SSD/全系统IO/冷缓存/跨机仍null。

## 唯一正式计划

两布局各3轮，共6 fresh worker；顺序clustered/separated、separated/clustered、clustered/separated。每worker96主问题（93complete+2missing+1cycle）、4控制和2负审计；总576主问题=558complete+12missing+6cycle、24控制、12负审计、600proof、1710接受绑定、156历史源文件（clustered39+separated117）。3hop/4096入证/旧65536 chunk、默认replay budget不改。

每个proof/问题SHA/源/完整memory树及traffic总计须等v0.43同轮同布局cacheOFF/meterON，独立audit与全部历史源恢复另核。questions仍在13epoch全部ingest后生成/fsync，确定结构/seed已知，不当新科学验证。600s/worker，exclusive+fsync child/roles/parent侧车、真实退出码/父完整process wall及报告SHA，失败不覆盖重跑。

必要测试：真实Store原block exactly once、原proof不变、角色排他/计数守恒、scope外不计、新scope损坏原源拒绝、错误event和异常清理；完整检查后定稿冻结代码/协议/输入及CI成功再跑6次。独立analyzer不使用角色假设做gold，按全部event原值分组与旧meter逐case对照。

## 成本/交付

重仪表的wall/CPU/parent完整计时、RSS仅报告诊断费用，**不用来比较cache或算法速度**。metadata/全部eventJSON/observer、完整runtime递归Python+HTML/专用及复用评测源码、全部memory旧snapshot/index/derived/残留、source/questions/partial/ledger/log/sidecar/图表/诊断分析成本单列；物理RAM总量及平台/依赖未分配部分不能当免费。无训练/字典/权重/远程模型API，新native只既有CSV/Gear功能检查。

图表实际视觉检查、详实报告/原始JSON/README/release说明/GitHub，CI后实际资产SHA/递归源码、物理仓库外actual wheel与current native、actual sdist角色程序scope/原proof/守恒功能smoke及最终proof重下载才交付。若归因支持，后续另冻请求范围资源/视图复用及安全/RAM合同；本版不偷偷改优化，也不叫生产/自然多跳/真实长会话/回答质量或无限上下文收益。E3净收益与E4整体仍未验收。
