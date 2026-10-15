# v0.10 数值字节原型与原始波形实验

本版进入E2二进制数值子方向的首批实验：一条EEG和一条ECG原始记录，加固定种子
随机字节负对照。科学实测限于16位整数波形；4/8字节宽度和浮点特殊位模式仅作
正确性测试，不声称完成浮点科学数组评测。Python原型，无新增Rust数值内核。

## 格式与兼容

显式数值策略自动写RKV manifest **version=4**，平块布局和字段沿用v2，但只允许
`none`及`byte-shuffle-{2,4,8}-v1`、`xor-shuffle-{2,4,8}-v1`。
默认none仍写v2，现有CSV仍写v2、独立单元仍写v3，CAS格式保持1。
v0.9及更早读取器拒绝v4；v0.10读取器继续读v1/v2/v3。
本版v4不支持独立单元或CSV策略，不在旧格式编号中暗增变换语义。

每块原始长度L、字宽w、完整字区域E=floor(L/w)*w、字数N=E/w。
需至少两个完整字才能变换。`byte-shuffle`将原文`raw[j:E:w]`的字节列依次
串联，即第j列包含raw[j],raw[j+w],...，最后附加raw[E:]残尾。
具体Python切片为`raw[j:E:w]`，列j从0到w-1。

`xor-shuffle`先在完整字区域做相邻字的按位差：前w字节原样，其余
`coded[i] = raw[i] XOR raw[i-w]`；再执行同样的字节列重排。解码按列做前缀XOR，
恢复原字节顺序，再拼残尾。预测器和字网格每个块从零重启，无跨块依赖。
ECG多通道交错时，“前一个字”不保证是同通道前一个采样，本版不做通道重排。

没有解析浮点、修改端序、舍入、量化、过滤、去NaN或数值规范化；任意原始位模式
均按字节处理。原始EDF/WFDB头、注释和文本文件也完整保留，并参与同一策略；
不是只对挑出的信号payload计算压缩率。数据类型/维度/校准语义仍由恢复后的原始
头文件表达，解码器只需归档中自带的变换标识，不依赖外部数据源或语义sidecar。

v4每块`coded_size==raw_size`；原始块SHA、文件SHA和manifest SHA链保留。
Zstd有界单帧检查及Zlib有界解压不变。数值变换只在压缩payload节省超过本块变换
标识成本时选择，否则回退普通编码。顶层策略与偏移数字等全局开销仍可能造成
完整归档净增大，必须报告；噪声负对照用于暴露这一成本。

API为`pack(..., transform="byte-shuffle-2-v1")`。
`format_version=4`或CLI的`--format-version 4`允许none也写v4以进行同版本控制；
其他变换/布局与版本不匹配会在发布输出前拒绝。

先使用文末运行器下载并验证固定数据，再运行下面的归档示例。

```powershell
python -m rkv1 pack data/numeric/eeg eeg.rkv --codec zstd --chunk-size 65536 --transform byte-shuffle-2-v1
python -m rkv1 inspect eeg.rkv
python -m rkv1 verify eeg.rkv
python -m rkv1 unpack eeg.rkv restored
python -m rkv1 compare data/numeric/eeg restored
python -m rkv1 read eeg.rkv S001/S001R01.edf --offset 65530 --length 32 --out range.bin
```

现有Rust后端只加速CSV反变换/Gear扫描，不加速v4数值变换。本轮全部Python，无DLL
或模型成本；不能借已有Rust资产声称数值原生加速。

## 固定数据与协议

数据选择在正式性能测量前固定：EEGMMIDB 1.0.0的`S001/S001R01.edf`；
PTBDB 1.0.0的`patient001/s0010_re.dat/.xyz/.hea`，来自两数据库的首个记录，
不是按压缩结果挑选。SHA、原路径和原始字节大小固定在`rkv1/numeric_data.py`。
不下载整库、不转CSV或NPY、不重采样。官方来源、许可和引用见DATASETS.md。

每组12条件：Zlib6/Zstd3 × 64KiB/1MiB块 × none/byte-shuffle2/xor-shuffle2。
全部用同版本v4、同校验、同发布/fsync语义和完整归档成本。
每条件一次完整预热，再五轮独立进程编码/恢复；条件与轮次打乱，编码后独立进程
恢复并在计时外逐字节比较。编码时间含普通压缩与候选压缩两次尝试和最终发布。

每轮/模式/非空类别32正式范围请求、4预热；两种生命周期分别为常驻和每次重开。
同一轮所有条件/模式请求完全一致；跨块类别以64KiB网格定位，可能不跨1MiB块。
范围p95取各轮p95的中位；配对倍率为各轮比值的中位，两者不可互换。
每条件所有轮次归档字节相同，源/实现/读前后归档SHA不变。

报告同codec同块大小对照，以及本次候选集合内各自最小普通/变换归档，避免只跟
较弱基线比较。后者不是对全部专业科学压缩器的最优性结论；本轮未测Blosc、
Bitshuffle、FPZIP、FPC或更广泛codec/参数，未优化通道布局和预测距离。

成本分两种口径：同安装环境的完整归档；另将专用`numeric.py`整个原始源文件
全额计给候选一次的保守情景。后者不是编译模块、公共解释器/core/codec或物理部署
成本。没有专用第三方运行库、字典或权重，额外原生资源为0；记录共享运行时体积。

本机温OS缓存，范围RSS还包含真值和工作账本，不当作生产RSS。仍无冷缓存、跨机、
跨日、推理或诊断质量结果。源数据库只作为公开字节测试，不进行医学分析。

```powershell
python -m scripts.run_numeric --out results/local-numeric
python -m scripts.summarize_numeric results/local-numeric
```

运行器拒绝覆盖结果目录；原始数据放在data/numeric并按哈希验证，元数据在结果
目录，数据不进入源码发行包。测试位模式与合成噪声不算新增独立科学样本。
