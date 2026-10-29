# v0.82 冻结协议：已见有界cache失效的只读诊断replay

本版只复盘v081已评分owned案例，0新科学问题/0新训练/API，不测试任何新缓存策略或容量，也不把replay时钟当原性能。v081已完整发行核验，原H3/jointFalse保持。

## 对象与唯一流程

固定全部12个原C(bounded) case：3轮×9/64/512/4096，沿原count order。96原请求/96原落盘packet/192原bytes成员；fresh原file复核14055、eligible metadata叶14043。原report/request/96packet和旧程序SHA在input manifest冻结。原report必须与v081 tag发布文件逐byte相同；source/Store/packet不改、不重新生成来替换旧证据。

每case fresh replay process：读取原输入→fresh Store核全部原files against frozen owned fixture→原Scope/BoundedMembership constructor→initial trace与原C初始记录完全相同→对8原请求逐个临时观察issue并严格匹配原canonical packet SHA、原bytes与独立外部anchor→final trace与原C末记录完全相同→关闭prover并恢复原NodeLRU.get。只读旧Store，输出独占新目录，每case600s/0正式replay重试，失败保留不覆盖。总12case96request192成员；没有新question/source binding质量收益。

## 观察器与局限

CacheProbe仅在当前单进程/单target cache的query期间局部包装NodeLRU.get，调用原方法后记录实际hit/miss，不改put/get的返回或LRU语义。query开始捕获cache key集合、其中不含requested leaf的相关集合和span histogram；记录相关key真实lookup时存在/已丢失，结束核lookups=hits+misses且分别等于cache counters增量，unique集合包含关系成立。NodeLRU.put正常过程仅会LRU淘汰，不存在本诊断中的额外删除；初始已有且到真实lookup时miss称为“使用前已失去”，不是猜测另策略会加速。

finally即使异常也恢复原类方法，拒绝嵌套或并发observer。观察器额外持有key引用，改变对象存活、RSS和CPU，所有replay完整wall/CPU/RSS以及parent都新计费；不允许回填原v081计时/内存，不比较replay与旧原始phase推加速。所有root/trace/packet的保真匹配才允许解释观察。

H1：全部12case initial/final trace、96原packet SHA/192原bytes、所有files和时序input SHA、observer作用域finally恢复及计数/集合守恒正确。H2（事后诊断假设）：primary4096的每个原query初始相关key>0、都被实际lookup且全部在lookup前已失去，同时hits=0。其他规模完整列出作行为对照，不从分母排除。不设CPU/速度/生产收益gate，也不宣称新科学泛化。假设False必须保存。

这是观察到v081端点0hits后提出的诊断；不是未知数据/独立科学验证。没有逐node新policy sweep；n>=64 admission只是后续未实现假设，不能在本版顺带评分追正。

## 冻结与费用

3必要owned单元测试验证hit/miss、原key消失、nested/异常恢复和真实9source packet/counters保真；全回归507检查需通过。源/协议/旧输入SHA精确freeze和CI成功后唯一12case replay。独立后置重新核输入未变、原Git程序未变、96packetSHA和聚合/集合边界以及所有parent/finally退出。图实际视觉看、详报告/README/release，完整localinitialbuild/物理外actualwheel-currentnative/actualsdist新诊断+旧全部机制/finalbuild/sourceaudit、tagReleaseCI和actual7资产SHA/全67Python+HTML/allscripts/外published安装/proof8全齐才交付。

整库/全部新旧scripts、原source/CAS/metadata/请求/packet、replay输出、observer引用/临时对象/CPU/RSS、旧science/human/train/models/frames/restored/cache/失败全部分开记费。当前0model/API不抹除旧费，原scientific corpus/模型/恢复/帧/私研/模板课程个人报告密钥不公开；原owned fixture重建方式沿v081公开代码，私有临时数据不打包。物理SSD/全系统IO/coldcache/crossmachine未知null。E3净收益/E4整体/真实长期对话/科学NLI/回答/无限上下文未完成。

授权参考reset1793258458，实际100%/ordinary不允许/到参考reset或确认下一窗口立即保存准确partial删除续跑，不跨窗。时间不足优先收尾已启动版本。


评分前记录完备性补充：显式保存initial_keys/initial_relevant_keys/initial_keys_asked/initial_keys_lost_before_lookup四个range列表，允许后置独立核set包含关系及histogram，而不只相信聚合数。原等待CI的controller已在输出目录不存在、0真实replay时中止；此次只补只读输出字段，不改cache算法/参数/输入，需新source freeze和exactCI，旧等待日志保留。
