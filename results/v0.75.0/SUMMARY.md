# v0.75.0 实验报告：依赖既有快照的紧凑证明传输

## 主结果和边界

H0全部1152原canonical恢复及独立原source/DAG：**True**；H1主Zstd完整保守列明文件成本：**True**；H2主Zstd每轮workerwall/CPU/parentwall：**False**；联合 **False**。主codec始终Zstd3，secondaryZlib9不替换headline。追加1152actualframe/schema/原DAG及1152恢复文件byte对比通过。

主Zstd每轮frame减少77640B，计入35476B新增源码及所有列明产物后减少42136–42177B；workerwall增加44.44%–50.66%，CPU增加44.66%–49.73%，parentwall增加44.12%–50.34%。完整列明绝对成本约1184万B，节省约0.36%，不能仅展示frame比例夸大整体收益。

这是v074已见owned证明的schema传输实验，没有新科学/语言问题评分，没有重跑推理引擎。Compact必须依赖既有原Store+外部SID才能恢复目录；不是contextless/general压缩，也不证明E3净收益、科学NLI、回答或无限上下文。v074大目录wall214–243x与proof25.84x负结果保留；本版只改传输表示，不做metadata缓存，可能更慢，不能混成同一个提速解释。

## 冻结、输入与实际基线

452检查451pass/1权限skip，source/protocol/input freeze `c01fd01694b48f61438e6235cd47db485fb4b156`，exactCI `40495737876`成功后唯一12freshworker×96knownroot=1152。固定ABCD/BADC/CDAB，AplainZstd/BcompactZstd/CplainZlib/DcompactZlib，每worker600s/0retry。完整96原roots来自v074所有四规模/三重复/八query，不去重挑大包，不当96独立科学样本。输入去掉旧单一finalnewline，原publishedSHA/length保持；候选在freeze前未编码这96。

Baseline直接调用**既有未改scripts.proof_frame plain encoder/decoder**，不用强迫普通压缩先parseJSON或读取Store。Candidate新增RKVSWC1 frame，eligible_paths替换为count+canonicalSHA，保持其他字段与global_verdict=null；实际Snapshot完整校验、实际目录count/hash核对后恢复原v073 canonical bytes，再比较外部trustedrootSHA。90B header大小一致；候选oldreader拒绝，未静默升级默认SDK/UI。CLI身份/byte恢复不是独立语义验证，实际原DAG核验另做。

独立header/catalogchecker不调用compact或expand，自己按原证书和实际目录重建expectedmapping，再调用旧独立原source有限闭包/DAG核验；共享JSON/codec/旧DAG依赖如实说明，不称全实现完全独立。SHA绑定在可信外部root/SID下有意义，不把帧自hash当身份认证或科学真实性。

## 主次结果及完整成本

| round |codec |frame delta B |all new dedicated source premium B |full conservative listed delta B |worker wall ratio |worker CPU ratio |parent full wall ratio |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | zstd | -77640 | 35476 | -42177 | 1.4444548474778207 | 1.4705357142857143 | 1.4413620784282786 |
| 1 | zlib | -292518 | 35476 | -257020 | 1.6672670739691278 | 1.6623970722781336 | 1.6631737836699159 |
| 2 | zstd | -77640 | 35476 | -42136 | 1.4444193897775368 | 1.4466101694915254 | 1.4411864134830332 |
| 2 | zlib | -292518 | 35476 | -257066 | 1.590871972116997 | 1.5935251798561152 | 1.5871733641271262 |
| 3 | zstd | -77640 | 35476 | -42136 | 1.5066236093212166 | 1.4973166368515205 | 1.503383493543619 |
| 3 | zlib | -292518 | 35476 | -257056 | 1.5313281144783077 | 1.5281195079086116 | 1.528239025363689 |

H1每个Zstd配对轮full listed delta<0才通过：candidate全部frame/restored+outer rawreport/parent/log，减baseline同项，再加**35476B全新codec/checker/driver/analyzer/tests/protocol/publicinput源码**，全部保守计candidate，不能以同文件加载为由给新增code免费。Frame-only/core-only不替换预先完整headline。源common各方法均列明：{'full_runtime_Python_HTML_B': 426112, 'all_existing_old_experimental_scripts_B': 1639679, 'actual_required_old_Store_contexts_B': 3036285, 'canonical_raw_input_root_files_B': 3182064, 'input_meta_B': 70010}，合计8354150B；原12Store全部实际文件SHA/bytes保持，候选的上下文不是免费索引。

双方都为原source审核依赖旧Store，baseline在恢复byte前不需Store；candidate在byte展开前额外依赖Store并完整重验目录。若只讨论不核原source的baseline则其上下文需求更小，不能隐去这种功能条件。公共旧runtime/旧scripts、输入和原Store为本比较列明common，**不是整个workspace/所有OS历史总占用**；旧science/human/model/train/source/history/下载缓存均继续保留在既有逐版ledger，本版不抹除或把未分配项当零。

## 每轮整体CPU、wall、RAM与残留

| round |method |codec |frame B |worker wall s |worker CPU s |peakRSS B |all worker retained B |parent complete wall s |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | plain | zstd | 194292 | 18.078056399943307 | 17.5 | 57249792 | 3376356 | 18.17949069989845 |
| 1 | compact | zstd | 116652 | 26.11293619987555 | 25.734375 | 56954880 | 3298716 | 26.203228499973193 |
| 1 | plain | zlib | 405780 | 17.4827987998724 | 17.078125 | 56279040 | 3587844 | 17.581197699997574 |
| 1 | compact | zlib | 113262 | 29.148494799854234 | 28.390625 | 55877632 | 3295326 | 29.24058710015379 |
| 2 | plain | zstd | 194292 | 18.833026399835944 | 18.4375 | 56422400 | 3376356 | 18.94612310011871 |
| 2 | compact | zstd | 116652 | 27.202788500115275 | 26.671875 | 56422400 | 3298716 | 27.30489520006813 |
| 2 | plain | zlib | 405780 | 17.70873859990388 | 17.375 | 55918592 | 3587844 | 17.815453900024295 |
| 2 | compact | zlib | 113262 | 28.172335900133476 | 27.6875 | 57028608 | 3295326 | 28.27621389995329 |
| 3 | plain | zstd | 194292 | 17.798996600089595 | 17.46875 | 56987648 | 3376356 | 17.902029199991375 |
| 3 | compact | zstd | 116652 | 26.81638849992305 | 26.15625 | 56627200 | 3298716 | 26.913615200202912 |
| 3 | plain | zlib | 405780 | 18.03506560018286 | 17.78125 | 56963072 | 3587844 | 18.136059700045735 |
| 3 | compact | zlib | 113262 | 27.61760300002061 | 27.171875 | 55975936 | 3295326 | 27.71623419993557 |

H2每轮Zstd workerwall、workerCPU与完整parent比值均<=1才True，zero baseline为null不能通过。每case encode/decode/独立audit原始wallCPU分别在raw；文件写入/序列化/ledger在worker/parent总费用内，不称免费。OS cache未控制，冷缓存/跨机/SSD/全系统IO未测；不从B或CPU推生产推理收益。所有原frame/restored本地保留，不以删除残留改善完整B。

## 准备、依赖与后置实际核验

最终96root复制和原Store全文件SHA验证准备wall **0.044599900022149086s**/CPU **0.03125s**；controller另计preflight验证wall/CPU在context。早先private复制未完整计时，保留null，不重跑回填，早先复制root文件及其metadata仍保留计费。新format私有owned12unit+4score检查时间/日志与所有源码SHA在privatepreparationledger。未计OS/allocator/其余依赖不得当零。

实际已安装zstandard/zlib依赖文件版本/bytes/SHA在shared-codec-dependencies.json，双方共同，不是净字节优势；其余CPython/OS未分配明确保留。整库66Python+HTML426112B，全部实际scripts保守1654982B，完整所有worker frame/restored残留40674726B，outer rawreports/parent/log1342474B，私有准备35433B。模型/新训练/API0，不抹除旧训练模型成本。

分析额外从真实持久化frame/restored复核1152身份/完整尺寸/SHA，重新独立header/catalog/原sourceDAG核验1152，并校验全部共同旧Store文件ledger未变；额外分析CPU/wall/peakRSS另计。没有用原precheck/SHA替代实际展开/原证据核验，没有抽一帧代全部。

## 运行、交付与后续

```powershell
python -m unittest discover -s tests
python -m scripts.compact_witness encode witness.json proof.bin --method compact --codec zstd
python -m scripts.compact_witness decode proof.bin restored.json --store STORE --snapshot PINNED_SID --expected-root-sha256 TRUSTED_CANONICAL_SHA
```

来源json需为自有原v073 canonical证书，Store须含同SID原source；可用公开scripts.catalog_fixture/Witness/Store生成owned例子。正式1152batch使用被冻结的已有v074输入metadata；rawscientific/human/model不上传。decode输出exclusive拒绝覆盖；原source语义审核调用audit_compact_witness.verify或audit_selected_witness.audit，不以CLI本身声称科学verified。

![紧凑证明的完整账本](compact-witness.png)

图已实际视觉检查，主Zstd frame-only与完整费用/时间、次Zlib分项一致。报告不是已发布：initialbuild退出0、物理外actualwheel/currentnative+新旧actualsdist、finalbuild/sourceaudit、tagReleaseCI、实际7assetSHA/递归PythonHTML/allsource/外actualpublishedinstall/finalproof8齐后才算交付。v074运输失败/分段缓存/上传重试费用与最终核验SHA保留，不重跑科学实验来修收尾。

后续可独立研究pinned metadata复用，或train-only受监督human结构模板候选；不能修已见NatLang dev追正，不混metadata复用解释schema收益。旧24API用完无新授权，仅CPU离线；E3净收益/E4整体/开放NL科学NLI/真实长会话/回答/无限上下文未完成。额度实际100/ordinarydenied/窗口结束准确保存partial并删除续跑，不跨授权窗。

## 分析收尾故障与资源记录限制

全部1152实际frame/原DAG与恢复byte审核、原始aggregate/源码费用文件已完成后，worker依赖记录假设zlib有__file__而退出。本机zlib实际为builtin，已从真实worker环境记录origin并保守列出CPython可执行文件/DLL容器与zstandard文件，没有捏造独立zlib文件。只从已完成JSON恢复依赖/图/报告，未重formal、未重复1152审核。原失败完整分析CPU/wall未完整保存，保持null而非0；analysis-timing只覆盖恢复依赖/绘图报告阶段，其审核计数引用已完成前阶段，不能冒充全分析总耗时。因此完整postanalysis资源时间记录尚不完整，formalworker/parent的CPU/wall门槛记录不受此后置收尾错误影响。
