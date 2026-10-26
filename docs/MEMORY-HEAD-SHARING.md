# v0.34 Windows HEAD共享读取修正与同负载复测

v0.33冻结基线三轮均失败，原报告/资产/原始JSON不改。成功提交80/48/13次，
4次HEAD读取和2次HEAD替换PermissionError；不是数据串版通过即可忽略的异常。

本次修改Memory.current的HEAD打开方式与Windows HEAD名称发布。读取用CreateFileW(GENERIC_READ,
FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL)，
msvcrt.open_osfhandle转换为binary/noninheritable FD，交给fdopen关闭底层handle。
ctypes函数原型显式定义/缓存。POSIX仍用Path.open('rb')。
缺失、权限、格式及身份错误原样失败，不加重试、不返回缓存SID、不隐瞒异常。
writer的写出/flush/fsync保持原样；仅最后命名操作在Windows改为SetFileInformationByHandle
(FileRenameInfoEx=22,REPLACE_IF_EXISTS|POSIX_SEMANTICS=3)，允许旧句柄保留旧字节。
UTF16目标名称显式保留NUL空间，长度字段为不含NUL的字节数，布局用ctypes自然对齐。
不支持此API/文件系统时（错误1/50/87），关闭本次句柄后回到原来单次os.replace；
该兼容降级不承诺并发，并不对权限/共享异常重试。其他平台仍是原os.replace。
Memory/CAS/index格式、原源字节和默认预算不改。所有其他Memory方法不改。
公共Windows/Python运行时依赖单列，不能称其无成本；不添加发行原生库。

定向单元测试：保持旧HEAD句柄未读时替换文件，旧句柄读旧内容、新句柄读新内容；
关闭file对象后底层nativehandle确已关闭且不可继承；缺失/损坏HEAD明确失败。
全套223项测试，保留权限跳过情况，Windows特有两项在POSIX应跳过。

正式复测直接运行v0.33原driver scripts/run_memory_concurrency.py，逐字节不改；
原docs/MEMORY-CONCURRENCY.md也不改。其“不添加并发补丁”描述仅代表v0.33基线，
本版唯一受控干预由本文件声明。3新目录、80更新、4readers、2048记录、所有源SHA、
预算、预热、超时、查询规律、完整审计/历史/重叠门槛全部原样。
只运行3轮，不改变强度或预算，不重复直到通过，任何残余错误照实保留。
冻结本文件、新runtime及原driver之后运行，environment保留原协议/driver/runtimeSHA；
fix-context记录本版协议SHA、冻结提交和基线结果JSON SHA。

验收仍须三轮各80提交、4readers正常、81历史审计、无原文/SID/epoch错误、
初始不可变文件不变、final HEAD最后提交、各reader真实add区间重叠和末次当前epoch80。
相对v0.33仅比较原门槛/失败是否仍现；调度交错不同，不能根据时间/数量宣称吞吐加速。
空间全额保留历史，与失败基线完成版本数不同，不能直接当压缩改善。
若失败就保留原失败，不在本版追调；若通过，仍非多writer/生产并发/故障恢复证明。
下一项才是固定提交边界的进程中断，不能混称断电，0模型请求、冷缓存/跨机器未测。

冻结前开发记录：仅改读取共享的候选在保持旧句柄测试失败，未做正式实验；
加入POSIX替换后，定向测试还捕获了UTF16终止空间遗漏，已修正并保留失败日志。
这些是代码调试，未当作正式三轮数据或覆盖v0.33失败。最终代码须先过完整套件再冻结。
原budget故障注入测试改为针对跨平台的_replace_head边界，而非Windows已不再调用的
os.replace；故障后的HEAD/config/历史保持断言不变，不能跳过原有原子性检查。

机制依据（实测需独立验证，不把文档当项目结果）：
- https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew
- https://devblogs.microsoft.com/oldnewthing/20211022-00/?p=105822/
- https://docs.python.org/3.13/library/msvcrt.html#msvcrt.open_osfhandle
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information
- https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ne-minwinbase-file_info_by_handle_class
