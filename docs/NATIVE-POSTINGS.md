# v0.60 冻结协议：不改既有frame的显式Rust批量规范varint解码

v059 actual发行/66源码/物理外安装/最终proof均通过后采用。本协议先于正式27worker冻结。v058主typedZstd联合False与v059观察器偏置结果保留，非独立新科学验证。

目标：在原typed/LZMA数据布局与原校验完全相同下，只替换posting doc-delta/TF两两read_uvar为一次Rust批量返回；其余metadata/token计数规范varint仍由旧Python读取。原scripts/index_frame.py、postings_transform.py逐字节同v058，原Pythonbaseline保持，不改预算/参数/重新训练。另一个native_postings.py复制原inverse/frame检查，仅pair读取替换，ffi显式指定DLL path+SHA+ABI1，不静默fallback。运行库/default SDK/UI/归档不集成。

Rust独立小crate/no_std cdylib，无第三方依赖，无分配；固定release opt3/lto1/codegen1/panicabort/strip。batch最多2m u64，caller供valid不重叠buffer，null/对齐/count/cap检查，每byte有界、10byte/u64溢出/截断/非最小编码拒绝，出错output忽略。Python仍验doc delta正/ID/TF/总pair/token/UTF8/原JSONsize预算/EOF及原frame三SHA，native不负责最终model正确性。payload/callerbuffer/FFI RAM另计。

流程：必要合成Python和Rust unit检查；代码/协议/inputs+CI固定后，候选exactCI Windows产物只编译一次作测量二进制，下载actualartifact核CI身份/ABI/SHA及metadata，再单独冻结实际DLL SHA/完整B/编译器/编译参数/原commit到docs输入。此后不重编或替换以追正结果。currentRelease CI二进制可能不同，性能仅归于本次明确测量的DLL，发行currentbinary只做functional proof。

固定3既有数据（EntB/SciFact/人工结构控制）、同v058round1实际plain/LZMA和typed/LZMA frame，SHA全部固定；旧实际恢复JSON文件作为当前SDK原路径需保留并全额收费。3模式 A plainPython B typedPython C typedNative；固定ABC/BCA/CAB×3数据×3轮=27freshworker，600s/worker0retry，无profiler/无新encoding/问题/训练/API。原rawJSON和实际frame先核SHA，ready含decode+json.loads；C包含导入native模块/读取并核DLLSHA/CDLL/ABI/alloc/ffi，不把native构造预热到计时外；A/B使用旧decode。完整bytes/model等于原，source/frame/实际旧restored文件事后核SHA。

H1 native内核加速：两个真实索引C/B三配对中位ready wall/CPU/parent≤1才True（CPU零分母null失败）。H2完整路径联合：C相对A ready wall/CPU/parent≤1，且C frame+现有实际restored JSON+全runtime/commonframe/typed+整native Python/Rust Cargo source/全DLL/native metadata完整B均严格小于A。两真实索引均达标才联合True。H1与H2分开，可能内核更快但仍比plain慢。人工控制单列，不能省掉DLL/源码费用或事后换codec改主门槛。

独立audit27 child/parent与frame/source/restored/DLL身份，再实际Python/native解码各比较原bytes，测量额外调用/CPU/RSS单列。完整费用runtime递归66Python+HTML、全部专用source/Cargo、完整被测DLL+metadata、assessment/test/protocol、rawJSON/图/sidecar、旧3模型/frame/480MB历史artifacts/训练与CAS不删不免费。C内存同时payload bytes+重建对象+u64buffer，并不以无Rust分配声称零RAM。物理SSD/全系统IO/冷缓存/跨机未测。

CI在Win/Linux同时cargo test/build+native Python合成检查，常规Python无新DLL时native用例明确skip，必须以nativeCI补齐。Release新增postings current native两个zip及actual measured Windows zip（原5base→8base，finalproof第9）；actualcurrentDLL/metadata下载SHA/源commit/ABI、物理仓库外安装+实际sdist8profile/变坏拒绝/原SDK对恢复模型初始化、完整旧smoke及finalproof重下载才交付。原科学source/model/frame/restored不发布。E3净收益/E4整体/NLI/回答/真实长对话/无限上下文不因本轮byte/kernel收益完成。


完整测试先320项（本机无newDLL时315通过/5明确skip，含4native与1权限）；exact candidate CI Win/Linux各4Rust+6Python native全部通过，实际Windowsartifact下载后再本机完整320（319通过/1权限skip）才formal。旧Gear binary仅旧功能验证。新增CLI：python -m scripts.native_postings FRAME OUTPUT --library DLL --library-sha256 SHA；边界读、输出exclusive/fsync，坏输入/旧plain拒绝，不覆盖。measuredzip发布本次原CI artifact原bytes，current releasebinary另核source_commit/ABI/SHA，不把其速度当已测。
