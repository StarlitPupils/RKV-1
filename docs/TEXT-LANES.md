# v0.32 E2 ASCII词法字节通道：结果前冻结协议与实验帧草案

E2代码/数学表示尚未完成；v0.31后停止在已测检索gold上调权重。本轮只测一个
非语义候选：按ASCII标识符、十进制拼写、ASCII空白、其他字节四类的最长正则片段
分流。保留每片段类型和原始长度，四通道保存所有原字节；不执行代码，不解析AST，
不规范化表达式、数值、换行、空白、注释或字符串。UTF8字节也照原样恢复。

标识符`[A-Za-z_][A-Za-z_0-9]*`；数字`[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?`；
空白为空格/Tab/CR/LF/VT/FF；余者按连续字节分组。按此顺序匹配，四个首字节集合
互斥，完整覆盖任意bytes。这是字节词法而非Python/TeX完整tokenizer，不声称新颖
语义压缩或全局最优。字典/模型0，codec实现和公共运行时费用另列未全额分配。

## 同帧、同codec与严格恢复

新增独立实验帧`RKVTEXT1`，不是主RKV归档v1–v6，不改变Memory/CAS/默认。
小端header `<8sBBQQQ32s`共66B：magic、method(0原样/1四通道)、codec(1 Zlib/
2 Zstd/3 LZMA)、原长度、变换后长度、compressed长度、原SHA256。payload只有
一个codec流。通道变换先`<5Q`40B记录control长度及四pool长度，再control和四pool。
control为每token 1B类型(0–3)+原长度canonical unsigned LEB128；无0长token。
pool各自按原出现顺序拼接。逐token取回原字节，所有pool必须恰好耗尽。

原大小上限64MiB，变换长度≤3N+40，编码帧总长度严格绑定；解码拒绝未知类型/
codec、非canonical长度、越界/未使用pool、SHA/长度错误及多余压缩帧/字节。
Zstd要求有内容长度且等于声明，window≤192MiB+40、无外部dictionary；额外数据
显式拒绝。LZMA memlimit256MiB；Zlib/LZMA输出最多声明+1后核对eof/unused。
编码Zlib6、Zstd3(写content size/checksum)、LZMA preset6，全对象，不搜块/级别。

三条件：plain原样压缩；lanes强制通道；auto实际尝试两者、按完整帧B较小选，
同分plain。auto计两次codec与变换全部CPU/wall，不把回退当免费。实际header只有
选中method，不加外层免费标签。Python API `text_frame.encode/decode`；主Archive
必须拒绝此magic，没有主格式范围读/生产收益声明。

## 固定输入和测量

[text-lanes-inputs.json](text-lanes-inputs.json)固定六文件：SciPy v1.14.1两份科学
Python、SymPy1.13.3两份数学Python、LaTeX2e release-2024-11-01两份数学排版.dtx。
每project两文件，共三个家族，不当六个独立科学领域。commit/原路径/完整SHA/
官方源/许可证链接固定，raw文件不发布、不执行，不在看压缩率后挑选。另262144B
SHAKE256固定二进制噪声作为负对照，不当真实科学数据或独立随机样本。

7输入×3codec×3条件×3轮=189编码+189恢复工作点；每阶段独立新进程(共378)，
seed20261025+r打乱工作点，编码/恢复阶段必依赖顺序。没有热身，记录codec在阶段
前是否已由公共模块预加载；若未加载则lazy导入收费，整个子进程wall/RSS另列。
源pin校验/读取、纯encode、帧写入flush/fsync、帧读取、纯decode、恢复写入fsync、
逐字节审计分别计时。pack/restore阶段wall也列出，不能把纯codec计算当完整I/O。
每次帧和恢复文件各1次实际fsync，同文件边界；目录/掉电未测。decode新进程从
实际帧读回，原文只用于独立字节审计；SHA验证属于真实decoder，不省校验提速。

所有三轮帧SHA/大小/选择/控制账本一致，全部189恢复逐字节+SHA一致；源文件和
协议/全部57模块/HTML起止SHA不变。失败必须保留，不静默重试/降级。控制40B、
control token/长度、四pool、66B frame header、codec payload和auto双尝试全列。

## 成本口径与可证伪门槛

分别列：A完整帧B；B专用模块源码分配(plain收text_frame一次，lanes/auto再收
text_lanes一次)；C同实际RKV安装全部57模块/HTML一次。B与C是替代场景，不能
叠加重复计源；codec/Python/OS/安装/pyc/文件系统未全额分配，不称完整部署成本。
每文件单对象各自全收源；六科学文件共享源一次的固定N=6情景另报，噪声不混入
科学corpus。不扩大N摊薄追求正结果。共享字典/模型/原生库特定B均0。

每文件/codec/候选对同轮plain配对，若B口径严格净省且三轮encode/decode wall
中位均不慢才算联合通过；单独的空间/CPU/恢复/RSS权衡仍完整报告，不预设正。
Corpus只比较N=6共享净空间，不冒充所有单文件/端到端通过。重复轮不是独立输入，
不做通用因果/最优证明。未进主归档/Memory，无检索或推理质量结果，模型调用0。
冷缓存/跨机器、目录掉电/并发、E3神经压缩等未测。是否原生化只在明确净空间/
热点/部署成本支持后决定，不从Python慢推导Rust一定有综合收益。

```python
from rkv1.text_frame import encode, decode
frame, metadata = encode(b'alpha = 1.00e-3\r\n', codec='zstd', mode='auto')
assert decode(frame) == b'alpha = 1.00e-3\r\n'
```

数据准备可用驱动`--fetch`从固定官方URL取字节并核SHA，任何源代码都不执行。
原科学源、压缩帧/恢复文件(可逆含原语料)和私有资料只留本机；发布无原文JSON/
图表/报告、代码和本协议。Zstd严格额外数据语义依据[官方API文档](https://python-zstandard.readthedocs.io/en/latest/decompressor.html)，本机实际版本0.24.0经测试。
