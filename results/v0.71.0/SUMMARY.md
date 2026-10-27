# v0.71.0 实验报告：重复证明的可逆共享布局与普通codec完整对比

## 结论和对象

**H1主Zstd完整保守空间False / H2主Zstd整进程时间False / 联合False**。12freshworker、768root frame roundtrip、每轮64已见theory共1394query的原certificate SHA重构全部通过；追加768actualframe header/layout独立审计与实际decode也通过。额外独立perquery比较 **16728**，formalworker另有同量比较；这些都是字节身份核验，不是新增科学NLI/English准确率或语义sourceDAG审核。

本轮优化对象是v0.70已经产出的证明JSON重复元数据，不改English parser/reasoner、不重算1394题准确率、不称生产推理收益。原v0.70受限English1394/1394仅限既定grammar；E3整体净压缩/E4整体/可靠科学回答/真实长会话/无限上下文未完成。若机械恢复通过而完整空间或时间gate失败，负结论保留，不能用某个codec的payload好看来替换预定主门槛。

## 冻结、正式次数与基线公平性

source/protocol/input冻结 `5b34dcf9dc6df45fae38d01b760a40b02ee0f1fa`，exactCI `40468374340`成功后才对64root做新frame编码。输入是v070全部64理论/1394旧完整certificate，原SHA逐query核对后用canonicalarray保存，总14009738B，source-root size/SHA和每querySHA在manifest固定；不挑容易proof或最好压缩样本。已见机械负载，非未知科学验证。

406检查405pass/1既有Windows权限skip，新增11必要owned检查含golden、zlib/zstd roundtrip、独立payloadaudit、actualpinnedStore旧DAG、tamper/bounds/trailing/externallytrustedSHA和CLIexclusive。初次privateZstd trailing测试抛ZstdError而非统一ValueError，日志保留，codec错误规范化后通过，未运行正式数据追参数。

3round固定ABCD/BADC/CDAB；Aplain/zlib、Bshared/zlib、Cplain/zstd、Dshared/zstd；12freshworker×64roots=768frame roundtrip。每worker600s、0retry，caseorder seed20261027+round，配对method顺序相同。zlib9/zstd3预先固定，primary Zstd、secondary zlib也先固定，不根据结果更换。

Plain路径直接压缩原bytes，不额外parse/canonicalizeJSON，避免给普通codec人为加负担。Shared路径必须解析并确认所有非query字段一致后再共享；解码必须重构原bytes。每worker包含input read/SHA、encode/decode、perquerySHA、实际frame和restored写出、格式metadata写出和所有fileledger；父完整subprocess另计startup/report写出。操作区间CPU受粒度影响，局部0不当免费CPU，H2用整个worker与parent。

## 布局、格式与信任边界

相同source/work/closure的proof template一次存储；每query只存query/verdict/support_proof/refute_proof四字段，顺序不变。只允许exactRKVSETLOGIC1 envelope且其余字段逐deep-equality相同；不同source/closure/work不能误共享。不能拿shared摘要替代原evidence，也不跨request保留cache。

RKVPRF1 header90B，littleendianstruct<8sBBQQ32s32s，magic hex52 4b 56 50 52 46 31 0a、method0plain/1shared、codec0zlib/1zstd、rootlength/payloadlength、rootSHA/payloadSHA各32rawB。Body仅一个compressedpayload；sharedpayload是canonicaltemplate+orderedqueryoverrides。root/transformedJSON32MiB、query最多256，输入/输出长度在decompress和expand阶段验证；zlib eof/unused/unconsumed检查，zstd已知framecontentsize+拒绝额外frame。bounds是payload限制，不是总CPU/RAM/OS或DoS保证。

Decoder必须接收外部可信expectedrootSHA。自带SHA只能证明一致性，不能自证来源可信；coherent篡改并重算内部hash仍须被旧外部SHA拒绝。codec不验证source语义、不使scientificflag变True。header/root/query恢复的是原bytes，任何源语义保证仍来自旧v070独立验证，新增语义审核数0。现有Archive拒绝本实验magic，默认SDK/UI/原格式不改。

Ownedgolden原canonicalroot1236B/SHA d62aee45dd6dab6d6556150b816a80662cd747ca56eb5695a056ac066bc24e14，共享818B/SHA4fe711601c141530590b076dc09f9fa5413768f4a230cb8c2ad827c7b53dfe15。它们只是codec布局例，不能当科学压缩数据。实际768frame另用独立struct/json/zlib/zstd解析，按冻结原root重建expectedlayout payload逐byte比较，再运行实际decoder恢复原root及所有querySHA；不只信encode端报告。

## 预定完整成本与时间门槛

H1主Zstd每轮shared complete-cost B严格小于plain。Both包含实际64frame/90Bheaders/actualformatmetadata +完整RKV Python/HTML +全部旧experimental源码 +共同trustedinputmanifest +实测codecpackage/CPython binaries。Shared再保守支付整个新codec/auditor/driver/analyzer/tests/protocol源码premium **41344B**，即使plain也复用部分header/helper。共同oldscript不重复计新files；inputmanifest共同所需不单罚shared。这个预定保守scenario把测量driver/tests/protocol也算给candidate，不能事后改成只计核心模块来追正。

另列runtime-code-only premium **6881B** 供评估边界，但不是H1。共同runtime/旧script/manifest/actualdependency成本 **11235724B**，codecwholepackage/CPython源二进制公共费用 **9105619B** 已记录，两边共用并未免费。未覆盖的OS/allocator/其余stdlib memory/二进制仍未分配，不能把源码B当总RSS。

H2主Zstd三轮shared/plain workerwall、workerCPU、parentfullwall每项<=.95，zero/undefined为False；不以encode-only替代。联合=H1且H2，机械正确性另验收。zlib可能有不同方向，完整保留secondary不择优换headline。

| round |method |codec |framesB |metadataB |完整保守总B |workerwall s |workerCPU s |parentwall s |peakRSS B |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | plain | zlib | 251822 | 7669 | 11495215 | 0.368140 | 0.296875 | 0.457477 | 32772096 |
| 1 | shared | zlib | 147916 | 7670 | 11432654 | 0.631753 | 0.546875 | 0.720737 | 34230272 |
| 1 | plain | zstd | 157268 | 7669 | 11400661 | 0.337251 | 0.296875 | 0.425649 | 34070528 |
| 1 | shared | zstd | 151137 | 7670 | 11435875 | 0.618108 | 0.562500 | 0.708123 | 33841152 |
| 2 | plain | zlib | 251822 | 7669 | 11495215 | 0.372100 | 0.312500 | 0.460125 | 32821248 |
| 2 | shared | zlib | 147916 | 7670 | 11432654 | 0.618820 | 0.578125 | 0.710669 | 33837056 |
| 2 | plain | zstd | 157268 | 7669 | 11400661 | 0.327234 | 0.281250 | 0.415249 | 33906688 |
| 2 | shared | zstd | 151137 | 7670 | 11435875 | 0.617624 | 0.609375 | 0.704841 | 34512896 |
| 3 | plain | zlib | 251822 | 7669 | 11495215 | 0.370858 | 0.375000 | 0.476203 | 33075200 |
| 3 | shared | zlib | 147916 | 7670 | 11432654 | 0.625641 | 0.578125 | 0.715071 | 33746944 |
| 3 | plain | zstd | 157268 | 7669 | 11400661 | 0.329456 | 0.296875 | 0.414715 | 33587200 |
| 3 | shared | zstd | 151137 | 7670 | 11435875 | 0.619337 | 0.531250 | 0.709463 | 34250752 |

| round |codec |shared-plain仅frame B |runtime-only完整差B |保守完整差B |shared/plain全进程ratio |空间/时间gate |
|---|---|---:|---:|---:|---|---|
| 1 | zlib | -103906 | -97024 | -62561 | {'parent_full_process_wall_s': 1.5754608755605481, 'worker_cpu_s': 1.8421052631578947, 'worker_wall_s': 1.7160685375101163} | True / False |
| 1 | zstd | -6131 | 751 | 35214 | {'parent_full_process_wall_s': 1.6636327093753147, 'worker_cpu_s': 1.894736842105263, 'worker_wall_s': 1.8327833479542102} | False / False |
| 2 | zlib | -103906 | -97024 | -62561 | {'parent_full_process_wall_s': 1.5445125488553388, 'worker_cpu_s': 1.85, 'worker_wall_s': 1.6630468548565593} | True / False |
| 2 | zstd | -6131 | 751 | 35214 | {'parent_full_process_wall_s': 1.6973952248744728, 'worker_cpu_s': 2.1666666666666665, 'worker_wall_s': 1.887405821635915} | False / False |
| 3 | zlib | -103906 | -97024 | -62561 | {'parent_full_process_wall_s': 1.501608556613503, 'worker_cpu_s': 1.5416666666666667, 'worker_wall_s': 1.6870078635393806} | True / False |
| 3 | zstd | -6131 | 751 | 35214 | {'parent_full_process_wall_s': 1.7107220300832693, 'worker_cpu_s': 1.7894736842105263, 'worker_wall_s': 1.8798803233095602} | False / False |

差B负值才有利shared，ratio<1较快。即使framepayload少，源码/metadata/整个process可能推翻收益；没有修改codeclevel/querybudget/primarycodec或删除负round。

## 全部源码与残留账本

| candidate保守exclusive文件 |B |SHA |
|---|---:|---|
| docs/PROOF-FRAME.md | 7944 | d295778abf4571eb2e8f330cfec9d0f0ea4c1189fe61168a210fea7cd79432a3 |
| scripts/analyze_proof_frame.py | 10809 | 9ff191f6a5b6fa3cbdebd234a86aa6e3329075e59978228b17cd08170f0f5a94 |
| scripts/audit_proof_frame.py | 2223 | cd9266b6d019b481dedddeba58b524d4cc6aa727440b63ebc4ec9b6f5f7af0d5 |
| scripts/proof_frame.py | 6881 | 09b1292bfb3b9cbaac9cb58c830f0f2eb6f0c02c67824aaab31d0c13c28158da |
| scripts/run_proof_frame.py | 6194 | 88a1dbbdae15c197e9a4ea196030210e84cd1844a3d0c587f29695aaf710feb8 |
| tests/test_proof_frame.py | 7293 | 9fe92020b9a9e3e53f8e21675ca812cdd7b7ceb7f0cb6fe27da3be8c5fd6ff36 |

完整RKV递归66Python+1HTML字节 **426112B**，实际全部scripts保守总 **1596883B**（含未执行历史，不称动态import集合）。common/exclusive拆分在source-resource可复核，没有同一新文件双计common和premium。字典/模型0，旧model/train/science/English原文/archive/snapshots/proofs和source14MB数组不删除、不当免费。

12worker全部frame/restoredroot/metadata等残留 **170333319B**，逐文件size/SHA见derived/resource；rawparent/log/publicderivedJSON/分析结果本身另保留，analysis新增768独立layoutaudit+768actualdecode的CPU/wall/RSS在analysis-timing。每worker实际读rootB已知，但不是SSD/全系统IO，coldcache/crossmachine未测。所有原证明/root/frames/restored本地留存，不发布原科学/English或私有材料。

## 可运行交付与阶段

```powershell
python -m scripts.proof_frame encode input.json output.rkvproof --method shared --codec zstd
python -m scripts.proof_frame decode output.rkvproof restored.json --expected-root-sha256 trusted64hex
python -m unittest discover -s tests
```

Output使用exclusive写入，错误externalSHA不生成输出；ownedtests/actualsdist功能例无需private数据。正式benchmark需manifest中的私有冻结root数组，不是交付中缺失科学模型；原来源不会被公开包捆绑。scripts为experiment/sdist，66runtime只version、HTML不改，旧native仅安装功能复测、不继承旧native性能。

![证明布局与完整空间/时间](proof-frame.png)

图已实际视觉检查，差B的零线/负方向和主Zstd时间ratio范围清楚。本报告tag前，localinitialbuild→physicaloutsideactualwheel-currentnative/actualsdist新旧功能→finalbuild/sourceaudit退出0，再GitHubCI/actual7baseSHA/全源码/外部actualreleaseinstall/proof8下载齐备后，以published-verification.json判发行完成。沿用v070外部临时smokescript，先前Win206与图label纠正已保留，不重跑科学结果。

下一步取决于预定主空间和wholeprocess gate，不能用本布局字节恢复称科学推理/回答或无限上下文完成。E3净收益/E4整体/开放NL科学NLI/长会话仍未验收，0新training/API，原science/model/research/template/personalreport/keys不发布。

具体负结论：主Zstd frame少6131B，但只计核心format源码也净多751B；预定保守完整账本净多35214B，三轮workerwall约1.83–1.89倍、parentwall1.66–1.71倍。SecondaryZlib完整空间净少62561B但全process仍慢，不换primary或改预算追正。停止在该负载继续调同格式参数。
