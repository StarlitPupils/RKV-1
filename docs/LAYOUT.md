# v0.12 FITS 类型分流与区域分块协议

本轮规则在读取新增验证文件的压缩结果前固定。只支持一个完整的、无扩展的2D
float32/64 FITS主图像；保留原始头、像素、NaN payload、填充和文件名。不应用
BSCALE/BZERO、不解析或重写浮点值。不支持/不完整的格式走普通路径。
这是一条FITS白名单规则，不是通用类型识别，也不处理ECG通道、代码或数学类型。

## 冻结矩阵与验证划分

开发记录：v0.11 已见的 Spitzer float32。新增验证记录在算法规则/矩阵确定后下载：
Astropy固定commit的完整 `tutorials/FITS-images/stacked_M13_blue.fits`（11,586,240 B，
float64，1392×1040）和 `allsky/allsky_rosat.fits`（478,080 B，float32，480×240）。
事先仅检查公开头和文件大小以确认输入类型，未测其压缩率。
这两份是未参与本轮规则设计的新记录；仍是同一托管项目的天文数据，不能称跨领域
或严格盲测。另测既有ECG和固定噪声，检验未识别格式回退及其成本。

全部20条件、统一v6：Zlib6/Zstd3 ×64KiB/1MiB ×五种方法：

1. fixed / none：普通固定块。
2. fixed / global shuffle：整文件按人工声明字宽重排，作为已有类型变换对照。
3. fixed / typed：只对完全位于已识别FITS图像内部的固定块重排，跨头/图像/填充边界的块不重排。
4. segmented / none：在头、图像、填充的原始边界断块，各区域内部按最大块长分块，不重排。
5. segmented / typed：同样断块，只在图像区域按BITPIX选择4/8字节重排。

每块先尝试普通codec，再按预定规则尝试重排，仅在节省超过块标签成本时选用；
完整归档和顶层策略/偏移等所有成本仍须单独比较。规则不按文件名或测量结果硬编码。
没有XOR/Blosc候选；本轮隔离布局/类型因素，不能据此评价所有科学压缩器。

## v6与校验

v6新增顶层 `layout`（fixed / fits-segments-v1），其余平块字段沿用v4。
顶层 `transform=fits-byte-shuffle-v1` 是编码策略；每块只存实际none/byte-shuffle-4-v1/
byte-shuffle-8-v1，解码不依赖FITS解析器。也支持显式普通数值策略作为对照。
v6拒绝CSV、独立单元、Blosc。固定布局仍要求标准块数和尾块长度；分段布局允许
文件中较短块，所有块的原始长度之和必须等于文件长度，引用总数最多500,000。
顺序拼接恢复原文件。分段读取器构建每文件unsigned-64前缀偏移数组，以二分查找
范围触及块；完整归档元数据和数组的实际逻辑内存字节均报告，RSS另测。
固定布局不构建该索引。局部读取仍整块解码/验SHA，没有省略完整性检查。

默认none仍v2、显式数值仍v4、Blosc仍v5、单元仍v3、CAS1不变。分段布局或FITS
类型策略自动写v6，旧读取器拒绝。base复用须同v6布局/策略，复用前恢复校验块。

## 计量与预定验收

沿用独立进程、一次完整预热+五轮正式、条件/轮次打乱。范围五轮、两种读取器
生命周期，各非空类别32正式+4预热查询；请求在所有条件/模式完全相同。
查询跨64KiB网格不一定跨实际分段边界。全部本机温OS缓存，未测冷缓存/跨机器。

成本情景：完整归档；再给typed或segmented候选全额分配整个layouts.py源文件一次，
给实际选择数值策略的配置保守分配整个numeric.py源文件一次。未知格式回退也不
抹去候选实现成本。公共Python/core/codec尚未全额分配，不称完整部署大小。
本轮没有专用DLL、模型或字典。所有条件同v6，不能把历史版本计时差当作布局收益。

新验证记录的联合验收按每个相同codec/最大块长分别判断：segmented/typed相对
fixed/none和fixed/global-shuffle，分配一次专用资源后成本都不增加，且完整恢复、
常驻p95、重开p95逐轮配对加速中位都>=1，各指标至少4/5轮更快，才标记该工作点
通过。编码成本独立报告，不据此宣称综合支配。仅空间收益单列，不冒充联合通过。
阈值是预定工程筛选规则，不是统计显著性。无论结果是否通过，保留原始记录，
不回调规则/删除失败数据，不据单机小样本切换默认策略。

## 执行与持久性口径

```powershell
python -m pip install -e ".[zstd]"
python -m scripts.run_layout --out results/local-layout
python -m unittest discover -s tests -v *> tests-local.log
python -m scripts.analyze_layout results/local-layout --test-log tests-local.log
python -m rkv1 pack data/layout/m13_64 m13.rkv --codec zstd --chunk-size 65536 --layout fits-segments-v1 --transform fits-byte-shuffle-v1
python -m rkv1 verify m13.rkv
python -m rkv1 unpack m13.rkv restored
python -m rkv1 compare data/layout/m13_64 restored
```

结果目录须不存在。分析绘图可另装plots extra并加--plot；分析器会核对源码身份，
因此不能修改rkv1模块后复用旧结果。专用成本查dedicated-resources.json；通用
runtime-footprint.json中的历史transform字段不是本轮layouts/numeric专用计费依据。
打包沿用临时文件flush/fsync后发布；归档解包沿用关闭文件、校验后发布目录，
未逐文件fsync。此前部分说明对此描述过强，本版校正文字，不把未执行的持久性
操作计入实测语义。没有掉电持久性证明，当前比较是这些相同写入/恢复语义下的结果。
