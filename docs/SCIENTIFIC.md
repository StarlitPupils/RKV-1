# v0.11 浮点原始字节与 Blosc 对照

E2 在 v0.10 的 int16 原型上补三个完整浮点 FITS 示例和一个专业字节压缩后端。
使用 python-blosc **1.11.4** 的 bytes API / C-Blosc；不是 Blosc2、NDArray 操作，
也不是对所有科学压缩器的排名。默认压缩策略不变，未引入数值 Rust 内核。

## 可复现运行

为了避免 python-blosc 在存在 NumPy 的环境中自动加载可选 NumPy，正式测量使用
不含 NumPy 的独立 Python 3.13 环境，仅安装本项目 scientific extra 的固定依赖。
发行包大小与实际加载身份一并记录，不把已经导入的依赖从成本中删去。

```powershell
python -m venv .scientific-env
.\.scientific-env\Scripts\python.exe -m pip install -e ".[scientific]"
.\.scientific-env\Scripts\python.exe -m scripts.run_scientific --out results/local-scientific
.\.scientific-env\Scripts\python.exe -m unittest discover -s tests -v *> tests-local.log
.\.scientific-env\Scripts\python.exe -m scripts.validate_scientific results/local-scientific --test-log tests-local.log
```

绘图单独使用装有 Matplotlib 的环境，避免改变测量环境与依赖清单：

```powershell
python -m pip install -e ".[plots]"
python -m scripts.summarize_scientific results/local-scientific
```

输出目录必须不存在；原始记录、派生指标和图像不覆盖旧结果。完整跑完前不改
`rkv1/*.py` 或测量环境依赖，运行器在开始/结束核对整个实现与专用依赖的 SHA。
正式默认五轮，验证脚本检查这一发布协议；临时小轮数 smoke 可直接调用 API。
本机 native 测试另用既有 CSV/Gear DLL，科学实验不会加载它；没有该库的环境会
跳过相关可选 native 测试，须如实记录，而非照抄本次通过数量。

```powershell
python -m rkv1 pack data/scientific/spitzer32 spitzer.rkv --codec blosc-zstd-bitshuffle-4 --chunk-size 65536
python -m rkv1 verify spitzer.rkv
python -m rkv1 unpack spitzer.rkv restored
python -m rkv1 compare data/scientific/spitzer32 restored
python -m rkv1 read spitzer.rkv spitzer_example_image.fits --offset 8640 --length 128 --out excerpt.bin
```

## 数据与真值

[Astropy 官方示例库](https://github.com/astropy/astropy-data/tree/1b964d39b378390b24c58fb5633cef238d22a35a)
固定同一 commit；选择和 SHA 在 `rkv1/scientific_data.py` 及 provenance 中。
Spitzer 和 Bolocam 为 BITPIX=-32，MSX 为 -64；按
[FITS 标准](https://fits.gsfc.nasa.gov/fits_standard.html)的大端位模式保留。
这是公开分发的科学示例/图像产品，可能经过既有处理，不称原始探测器观测。
三个示例同属天文领域且同一托管项目，不能算三个独立科学领域。

基准压缩**完整原文件**，包括 ASCII 头与 2880-byte 对齐填充；不解析后重新写文件、
不转端序/精度、不应用 BSCALE/BZERO。有限的主图像头检查器只用于固定输入核对，
不是通用 FITS 库。NaN/Inf/正负零统计用整数位掩码完成，不经过浮点转换。
Bolocam 约 5% NaN，必须披露；真实样本没有 Inf/有符号零的性能证据。
另复测 v0.10 的同一 ECG 原记录，及同一固定随机字节负对照，不跨版本直接比较时间。

原文件保留仪器/提供者署名；不假定整个示例库统一授权。发布物包含下载器、摘要、
来源与实验记录，不再分发 FITS 或 PhysioNet 原始信号。见 [DATASETS.md](DATASETS.md)。

## 矩阵与计时

每组 18 条件、全部 v5 容器：64KiB/1MiB 外层块 × 九个条件：

- Zlib6 和 Zstd3，各测 none、byte-shuffle-w-v1、xor-shuffle-w-v1；w 按原数据为 2/4/8。
- Blosc-Zstd 的无过滤、shuffle、bitshuffle；同样 w，clevel=3、内部 blocksize=65536、threads=1、releasegil=False。

库参考 [python-blosc API](https://blosc.org/python-blosc/reference.html)，固定版本实现见
[toplevel.py](https://github.com/Blosc/python-blosc/blob/v1.11.4/blosc/toplevel.py)。
C-Blosc 内嵌 Zstd 1.5.6，直接 zstandard 使用 C Zstd 1.5.7；clevel3 的映射、分块和
帧格式也不同。不能把跨后端收益单独归因于过滤器；同 Blosc 参数下三种过滤器为消融。
内部 64KiB 分块不等于本项目实现了按内部子块随机读；RKV 仍整外层块解码并验 SHA。

每条件一次完整预热，然后五轮正式，条件/轮次打乱；编码与恢复各使用新进程。
编码计入首次 Blosc 导入/设置，恢复在遇到首个实际 Blosc 帧时计入导入/设置。
全部回退原文块时，解码不需要导入 Blosc。正式范围查询在四次/类别预热后计时，
不含首次导入，但进程峰值 RSS 仍计入；每组 32 个请求、五轮、两种读取器生命周期。
同轮所有配置/生命周期的请求逐字节相同。不存在的请求类别保持空，不造补查询。
跨 64KiB 网格请求不一定跨 1MiB 外层块。文件/块/manifest 校验及 flush/fsync 不删除。

## 资源成本与边界

所有条件比较完整归档，不以压缩 payload 代替总大小；每轮归档 SHA/选择账本须一致。
资源账本列整个已安装 Blosc distribution（包括未用内嵌 codec 和元数据），固定每文件
SHA；另计适配模块原始源文件一次，普通 Python 数值变换另计整个 numeric.py 一次。
NumPy 如被加载，资源记录也会将整个发行包计入。本次隔离环境未安装/加载 NumPy。

分别给出“这些依赖已安装，仅增加归档”与“为所测对象分配上述专用资源一次”的情景。
四组科学输入可共用一次库成本；那只是独立归档相加，不是 CAS 去重或普遍摊销规律。
这些情景均未完整分配公共 Python/core/Zstd/OS 依赖，不声称完整部署占用。
首次导入时间与安装体积是不同量，不能因为库已安装就从完整恢复计时中扣掉导入。

五轮为描述统计。CPU/RSS 原始样本全部保留，范围 RSS 含真值与记账对象，不是服务
纯增量内存。没有冷缓存、跨机器、跨日、能耗、数值 Rust、CAS+数值、推理质量结果。
E2 下一步按本版资源与时延证据缩小候选，再考虑语义布局/类型分流；E3/E4 未开始。

## v5 读取防护

v5 平块结构沿用 v4，只新增九个 `blosc-zstd-{none,shuffle,bitshuffle}-{2,4,8}` codec。
它们只允许外层 transform=none；v4 拒绝这些 codec，v5 不支持 CSV 或独立校验单元。
Blosc 写入不缩小时按现有规则存 none；噪声回退仍付编码尝试与顶层标签成本。

解码前验证 16-byte C-Blosc 头的版本、类型宽度、codec/过滤标志、压缩/原始大小、
块大小及 reserved/memcpy 标志，原始大小必须等于清单的受限可信长度（最多 8MiB）。
之后调用 C 库结构验证，再调用 bytes 解码接口，检查精确长度和原始块 SHA。
不使用无界原始指针 API。C 扩展的分配/输出上界依据见固定版本
[blosc_extension.c](https://github.com/Blosc/python-blosc/blob/v1.11.4/blosc/blosc_extension.c)。
这不是对任意恶意本地 C 库的沙箱保证；拒绝 BLOSC_* 环境覆盖以固定测量参数。
