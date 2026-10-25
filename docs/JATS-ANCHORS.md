# v0.25 内容锚定键预检（结果前冻结）

v0.24的927单元均无可用id，位置键/v4的range乐观下界只有1/12转换可过，完整父
校验0/12。本轮只改变身份候选，预算/排除集合/父身份/原range验证不变，不接入
Memory，也不扩API请求或独立科学任务。仍复用固定六篇18文件/12转换。

新增显式`fragments(raw, mode='content')`：key=parent_key+role+text_SHA256+occurrence。
text_SHA256为既有itertext().strip()派生文本的UTF-8 SHA，重复序号按同一role/
同一文本SHA的文档顺序计数。父全文件SHA和原range SHA仍分别保留，不能用text
指纹代替原字节。同text但不同原标记可以同锚，必须重绑定当前原range；改写
文本意味着旧key删除+新key插入，可能比位置键的单upsert增加操作。无关段落插入
不改变其他唯一文本键，但重复段落的插入/删减可能改变重复序号的物理对应，
不声称是作者赋予的语义永久ID。title/abstract/body角色隔离，不跨论文去重。

对照whole / position / content；不重复xml-id，因为既有固定数据全无id。原
v0.24两种模式的描述必须保持逐字段一致，默认mode仍xml-id，不暗改旧API输出。
新增合成单元测试独立覆盖无关插入、文本大小写改变、重复段落与同text不同原标记。

完全复用JATS-FRAGMENTS.md的身份审计、13状态CAS、相邻必要条件、v3/v4规则、
32变化/256KiB记录/2MiB CAS以及range乐观下界/完整父校验两种工作量。正式状态
标签为v025-anchors，各记录候选共享同一CAS；不与v0.24快照标签SHA硬比。新脚本
run_jats_anchors.py调用参数化公共驱动。18文件×position/content逐条verify；
whole/position/content×3轮×18文件=162解析，9新进程；144相邻规划、26历史CAS。
输入和模式/文件顺序规则不改。保留原版本文件名，所有path变更如实计入。

在结果前不预设通过数，必须报告每个转换的删除/upsert/rebound变化，尤其内容
锚可能因为编辑创造两个操作而更差。只将通过计数当下一步集成筛选，不能声称
实际索引节省、查询加速或科学QA提高。全部51模块/HTML源一次、Gear完整精确库
另计；纯JSON定位候选须计增加的SHA键长度。不按结果缩短指纹或提高预算。

仅本机温缓存，0新独立论文/QA/模型调用。默认Memory预算v3/显式v4及所有已发布
格式保持；新mode是独立审计API。若content仍无足够潜力，应报告失败并重新评估
细粒度索引路线，不能为了继续版本号而强行集成。
