# v0.35 冻结协议：固定提交边界的硬退出与恢复

v0.34实际发行资产、物理外部安装和最终证明重下载已完成。
本协议与driver/运行库先冻结，再运行一次三轮原计划；本机CPU，0远程模型请求。

问题：单writer在固定提交边界os._exit(77)后，可见HEAD、旧证据和后续写入是否一致？
是进程内硬退出，无Python finally清理，不是外部kill/掉电/磁盘故障证明。
只新增子进程仪器化driver/审计，不修改v0.34运行库逻辑（版本字符串除外）。
复用v0.33 corpus(epoch)与audit：2048记录、4sentinel，固定epoch0/1/2，默认fixed/Zlib/
compact-budget-v3及原预算。3轮，每轮8个独立新目录，共24case。

固定7个硬退出点和1个成功控制（顺序也冻结，不因结果更改）：
1. before-add：子进程启动但Memory.add尚未调用，硬退出。
2. before-first-new-CAS-object：Store._publish遇到首个新RKVOBJ1对象，发布前退出。
3. after-first-new-CAS-object：同一对象原发布函数返回后退出（保留file fsync）。
4. after-CAS-snapshot-before-index：Store.add原函数返回后、Memory索引构建前退出。
5. after-index-manifest-before-HEAD：Memory._head针对HEAD被调用前退出。
6. after-HEAD-temp-fsync-before-name：Memory._replace_head针对HEAD被调用前退出。
7. after-HEAD-name-before-add-return：Memory._head原函数针对HEAD返回后退出。
8. success-control：不注入退出，完整add后退出0。

每个hook确认实际进入目标边界，写协调目录marker后flush/fsync，再os._exit(77)。
marker位于Memory树外，其开销不当作真实应用成本；公开退出码/边界匹配。
hook只在本case拥有的子进程中安装，清除RKV_LLM_*，CREATE_NO_WINDOW；不能终止用户进程。
父进程给每个子进程固定超时10s，超时/丢marker/错误码均失败，不重跑覆盖。

每case父进程先建epoch0并保存SID/不可变文件SHA，之后源改为epoch1，子进程add(label固定'e1')。
边界1–6预期可见HEAD仍是epoch0/初始SID；边界7/8应见epoch1。
每case都显式读初始SID，完整源SHA、4原句/locator/SID/epoch均审计；不能只看HEAD文件存在。
记录硬退出后的全部rglob真实文件清单/字节/SHA，与Memory.stats分目录结果并列。
尤其退出点6可能留下根目录.memory-head-*临时文件，stats原分组未覆盖根目录其他文件，
不能漏计这些工作产物或为了让空间好看先删除。所有退出前后原不可变文件应保持SHA。

固定恢复步骤（均非为正结果调参）：父进程对仍为epoch1的原源用完全相同label'e1' add一次，
允许重用已验证CAS/索引/manifest；须得到可读epoch1。然后源改epoch2、add(label'e2')一次，
须得到可读epoch2；再显式审计0/1/2三个历史SID。若此恢复操作失败，不再尝试直到成功。
最初不可变文件SHA保持，不清理退出留下的暂存/孤立文件；answers保持空。
退出后已存在的全部非HEAD文件（包括暂存CAS/index/manifest与根目录临时HEAD）也须在恢复后保持SHA。
全部24case须符合退出码/触发边界/预期HEAD/旧证据/恢复后两版本/不可变性才通过。
无并发reader，单writer，无GC、无多writer，无断电或目录同步结论。

交付：冻结protocol+driver+57模块SHA，再跑原24case；原始逐步JSON含全部失败、
实际文件字节与stats差额、恢复耗时（含仪器化代价单列），图表/详实报告/README/release。
合成数据可重生，不发原始科学文件/私有资料/密钥。图表用标准matplotlib并视觉检查。
源码成本必须递归枚举57模块+HTML（58项），逐项与source-checksums集合核对。
CI成功、实际五资产下载SHA、外部wheel/current native安装与新进程硬退出/恢复小smoke、
证明资产上传后再下载核验，才认为版本完成。

如果全通过，下一步回到E3的本地小型预测器/熵编码可行性协议：先论证确定性整数概率与
完整权重/运行库/训练和编码/解码CPU成本，冻结训练/验证分离再评估，不能把byte恢复当模型智能。
若失败，保留本版失败后才在下一版最小修正；不调预算追求通过。

运行脚本：python -m scripts.run_memory_interruptions --work <新目录> --out <新目录>。
原223项完整单元测试在冻结前运行，新增24case进程实验独立于单元测试计数，不重复算通过次数。
原始JSON含逐阶段完整文件账本与SHA，开发/预热/额外审计不冒充生产吞吐或模型收益。
