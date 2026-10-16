# 数据来源与固定版本

v0.19读取已固定QASPER dev v0.1/v0.2/v0.3官方原文件，每版281论文，原名/字节均
保留，源SHA见version_data.py。原论文投影文本相同，原JSON成员变化281/9条，
不把数据集标注/元数据发布称为论文正文修订。64个不同问题由v0.1论文ID排序固定
选择，qas不进FTS；本轮跨论文来源命中不是QASPER原给定论文问答评分。另有2048
合成记录100更新压力控制，不算真实科学数据。详见MEMORY-HISTORY.md。

v0.18复用v0.17固定/Gear两组SciFact合成更新快照，未新增原始科学数据或真实版本
家族。五个预定阶段每次查询全部188条标注主张和3个旧探针，重复轮次不增加样本。
22个历史快照整源SHA/大小核验；查询不包含新模型生成。详见MEMORY-QUERIES.md。

下载后必须匹配 `rkv1/datasets.py` 的固定 SHA-256；URL 中的 `latest` 发生变化时
下载会失败，必须审查变更后发布新版本。来源清单放在语料目录外，避免计入原始语料。
仓库不分发用户研究文档或科学数据原文，仅保存下载器、哈希和实验统计。

| 语料 | 作者与来源 | 许可 | 用途 |
|---|---|---|---|
| Iris | R. A. Fisher；[UCI](https://archive.ics.uci.edu/dataset/53/iris)，DOI 10.24432/C56C76 | CC BY 4.0 | 小型科学 CSV |
| Wine Quality red | Cortez, Cerdeira, Almeida, Matos, Reis (2009)；[UCI](https://archive.ics.uci.edu/dataset/186/wine+quality)，DOI 10.24432/C56S3T | CC BY 4.0 | 科学测量 CSV |
| SciFact | Wadden et al. (2020), [Fact or Fiction: Verifying Scientific Claims](https://aclanthology.org/2020.emnlp-main.609/)；[官方仓库](https://github.com/allenai/scifact) | [官方许可](https://github.com/allenai/scifact/blob/master/LICENSE.md)：claims 为 CC BY 4.0，corpus abstracts 为 ODC-By 1.0 | 科学文本压缩；v0.15证据检索/判断，v0.16索引/v0.17工作副本更新成本对照 |
| QASPER train/dev v0.3 | Dasigi, Lo, Beltagy, Cohan, Smith, Gardner (2021)，[原论文](https://aclanthology.org/2021.naacl-main.365/)，[官方数据页](https://allenai.org/data/qasper) | 官方数据卡 CC BY 4.0；文本来源 S2ORC | 43,368,073 bytes 科学论文 JSON；本版仅压缩，不训练或问答 |
| Wine Quality red/white | 同上 UCI Wine Quality 作者与来源，两个原始 CSV | CC BY 4.0 | E2 数值 CSV 列重排，348,625 bytes |
| HTRU2 | Robert Lyon (2015)；[UCI 官方数据页](https://archive.ics.uci.edu/dataset/372/htru2)，DOI 10.24432/C5DK6R | CC BY 4.0 | 脉冲星候选特征，原 CSV 1,730,114 bytes；17,898 行；CR-only 原换行保留，CSV v1 回退 |
| Superconductivty Data | Kam Hamidieh (2018)；[UCI 官方数据页](https://archive.ics.uci.edu/dataset/464/superconductivty+data)，DOI 10.24432/C53P47 | CC BY 4.0 | 21,263 个超导材料样本的特征与化学式；保留 train.csv/unique_m.csv 合计 28,151,383 bytes；仅压缩，不训练/预测临界温度 |

v0.1.0 的 SciFact 包含 corpus、train/dev/test claims，只对文件字节做压缩；
没有用 test 标签，也没有训练或推理评测。后续 E4 必须冻结数据分割，避免调参泄漏。
下载器保留源字节，不清理空行、不规范化 CSV，也不修正数据集中既有数值。

合成重复数据：固定种子 20261014，生成 1 MiB 伪随机字节，复制成 4 个文件。
这只是跨文件去重机制对照，不代表真实科学数据分布，不能拿它的压缩率替代真实语料结果。

v0.7.0 增加 QASPER 官方原始 train/dev v0.1、v0.2、v0.3：分别41,339,485、
43,368,694、43,368,073 bytes，总计128,076,252 bytes。同一科学语料的真实发布
序列，不是三个独立语料家族。原始版本文件名和所有字节保留，不重新序列化JSON。
官方S3 URL、压缩包和成员SHA固定在 rkv1/version_data.py，随结果保存；许可沿用
[官方数据卡 CC BY 4.0](https://huggingface.co/datasets/allenai/qasper)。仅存储/恢复，
没有用这些发布版本进行模型调参或问答评测。

v0.9.0增加独立家族Evidence Inference：[官方仓库](https://github.com/jayded/evidence-inference)、
[官方发布历史](https://github.com/jayded/evidence-inference/releases)。选择在测量前固定为
v1.2（2019-09-17）→v1.3（2019-10-09）→v1.4（2019-10-17）三个真实发布中的
`annotations/annotations_merged.csv`及`annotations/prompts_merged.csv`两张原始主表，
分别6,248,459 / 6,249,392 / 6,249,392 bytes，总计18,747,243 bytes。
这是临床试验论文结果/证据标注数据，不进行医疗建议、模型训练或推理评估。
范围不含论文全文、补充表和整仓库；不解析或重写CSV。prompts表三版原字节相同，
annotations表三版摘要不同；同长度不代表内容相同，也不把净长度差当作编辑字节数。
主表commit、原始路径和每文件SHA固定在`rkv1/evidence_versions.py`，随实验保存。
许可见[官方v1.4 MIT LICENSE](https://github.com/jayded/evidence-inference/blob/411fd36aa28425253dd6063f382c41e3191f7b41/LICENSE)。

v0.10.0数值原型固定两组独立数据库中的单条原始记录（不代表整库）：

| 选择范围 | 官方来源与引用 | 原始 bytes | 许可 |
|---|---|---:|---|
| EEGMMIDB 1.0.0，S001/S001R01.edf | [官方数据页](https://physionet.org/content/eegmmidb/1.0.0/)，DOI 10.13026/C28G6P；Schalk等，BCI2000，IEEE TBME 51(6):1034–1043 (2004) | 1,275,936 | Open Data Commons Attribution License v1.0 |
| PTBDB 1.0.0，patient001/s0010_re.dat/.xyz/.hea | [官方数据页](https://physionet.org/content/ptbdb/1.0.0/)，DOI 10.13026/C28C71；Bousseljot/Kreiseler/Schnabel，Biomedizinische Technik 40 Suppl 1:317 (1995) | 1,154,687 | Open Data Commons Attribution License v1.0 |

PhysioNet平台引用：Pollard等，PhysioNet as a global platform for biomedical research，
[Nature Health (2026)](https://doi.org/10.1038/s44360-026-00096-z)。
EEG保留整个EDF+，包括16,896-byte嵌入头和注释通道；ECG保留两个WFDB format16
信号文件及原始头文件。原始int16信号为little-endian，见
[EDF原始规格](https://www.edfplus.info/specs/edf.html)和
[WFDB signal格式](https://physionet.org/physiotools/wag/signal-5.htm)。
数据按原路径/大小/SHA固定，字节不重排为新的“真值”，没有数值解析、滤波或采样
转换；变换仅发生在编码容器内部，恢复后原文件字节完全相同。

另有262,147-byte固定种子随机字节负对照，生成器与SHA随报告保存；它测试所测
codec的回退与元数据成本，不是第三个真实科学数据库或普遍不可压缩性证明。

v0.11.0 增加 [Astropy 官方示例数据项目](https://www.astropy.org/astropy-data/)
固定 commit `1b964d39b378390b24c58fb5633cef238d22a35a` 的三个完整 FITS 示例：

| 名称 | 固定原始来源 | 文件 bytes | 图像位模式 | 图像字数 / NaN |
|---|---|---:|---|---:|
| Spitzer | [photometry/spitzer_example_image.fits](https://github.com/astropy/astropy-data/blob/1b964d39b378390b24c58fb5633cef238d22a35a/photometry/spitzer_example_image.fits) | 2,113,920 | float32，大端，1025×513 | 525,825 / 3 |
| Bolocam | [galactic_center/gc_bolocam_gps.fits](https://github.com/astropy/astropy-data/blob/1b964d39b378390b24c58fb5633cef238d22a35a/galactic_center/gc_bolocam_gps.fits) | 1,644,480 | float32，大端，640×638 | 408,320 / 20,399 |
| MSX | [galactic_center/gc_msx_e.fits](https://github.com/astropy/astropy-data/blob/1b964d39b378390b24c58fb5633cef238d22a35a/galactic_center/gc_msx_e.fits) | 181,440 | float64，大端，149×149 | 22,201 / 0 |

原文件 SHA、尺寸/头/填充、特殊值整数位模式普查随 provenance 保存。没有浮点解析、
重采样、精度或端序转换；原始提供者署名与科学元数据保留。公开示例可能是既有处理后
产品，不称原始探测器字流。Bolocam约4.996% NaN；不能把这类分布的压缩收益外推
所有科学数组。三份均为天文示例且来自同一托管项目，不代表三个独立科学领域。
不假设示例数据统一受软件仓库许可证覆盖；仅记录公开来源和原头署名。
RKV发布物不再分发原始FITS/信号文件，运行器从固定官方URL下载并核对SHA。

v0.12按预先固定规则增加同一Astropy commit的两份新验证记录，原始文件与SHA
见rkv1/layout_data.py。此前只检查头/尺寸确认类型，未测新文件压缩率：

| 新记录 | 固定来源 | 原始 bytes | 类型/形状 | 特殊分布 |
|---|---|---:|---|---|
| M13叠加蓝光图像产品 | [stacked_M13_blue.fits](https://github.com/astropy/astropy-data/blob/1b964d39b378390b24c58fb5633cef238d22a35a/tutorials/FITS-images/stacked_M13_blue.fits) | 11,586,240 | float64，1392×1040，大端 | 1,447,680像素；无NaN，1个正零 |
| ROSAT全天示例产品 | [allsky_rosat.fits](https://github.com/astropy/astropy-data/blob/1b964d39b378390b24c58fb5633cef238d22a35a/allsky/allsky_rosat.fits) | 478,080 | float32，480×240，大端 | 115,200像素，26,100正零，约22.66%；无NaN |

这些仍是同一托管项目的天文图像，不算跨科学领域验证，也不称严格盲测；ROSAT
零值比例必须随结果披露。头/图像/填充不重新序列化，未读取数值后重写真值。
提供者署名保留于原始FITS，不假设统一数据许可证；原文件不进入发行包。

## v0.13 文件数合成对照

`scripts.run_sync.fanout` 将固定种子262,147 B噪声连续切成129个不大于2048 B的
文件，另加一个空文件。原始合成文件不打包；结果记录逐文件SHA与完整归档SHA。
它用于观察逐文件同步成本，不是公开科学新语料，也不并入科学压缩收益。
科学案例复用已列PTB ECG和M13完整原始文件，未更换或重新导出字节。

## v0.14 新领域与文本对照

完整原始文件按仓库相对路径保存，未转换或重写。提交、每文件SHA与下载上限固定于
`rkv1/crossdomain_data.py`；结构与特殊位模式普查随各provenance记录，不参与编码。

| 输入 | 固定官方来源 | 原始 bytes | 选择和范围 |
|---|---|---:|---|
| SAC地震波形 | [ObsPy](https://github.com/obspy/obspy/blob/a629e8c021052904b6b8d62699d03f2a3721ae63/obspy/signal/tests/data/CRLZ.HHZ.10.NZ.SAC) | 131,704 | 固定树中最大.sac，按尺寸选择；632B头、32,768个float32样本 |
| DCD分子轨迹 | [MDAnalysis](https://github.com/MDAnalysis/mdanalysis/blob/51b8271d254ec5ce43e0daf8c33952147f2b2d3c/testsuite/MDAnalysisTests/data/adk_dims.dcd) | 3,931,724 | 典型adk_dims测试样例，3,341原子、98完整存储帧，原头500帧不修复 |
| Python源码 | [SciPy](https://github.com/scipy/scipy/blob/e29dcb65a2040f04819b426a04b60d44a8f69c04/scipy/integrate/_ivp/rk.py) | 22,800 | 完整Runge-Kutta实现源码；非数值网格对照，不执行 |
| LaTeX数学文档 | [LaTeX amsmath](https://github.com/latex3/latex2e/blob/04688cfadaddae62cdaf0530e4ffa7ec5a19cc82/required/amsmath/testmath.tex) | 81,184 | 完整testmath示例/测试源；非数值网格对照，不编译 |

科学样例来自地球物理和分子动力学两个新领域，但每领域仅一份分发测试文件，不是
完整原始数据库/模拟运行或严格盲测。DCD完整分发字节不等于头声明的500帧轨迹。
文本对照不算新增科学数值样本，也不代表代码/数学语义压缩已实现。已见ECG/噪声
另列，不混入新科学输入合计；DCD在合计中占主导。

上游软件许可来源：[ObsPy LGPL v3](https://github.com/obspy/obspy/blob/a629e8c021052904b6b8d62699d03f2a3721ae63/LICENSE.txt)、
[MDAnalysis LGPL v3+及组件许可](https://github.com/MDAnalysis/mdanalysis/blob/51b8271d254ec5ce43e0daf8c33952147f2b2d3c/LICENSE)、
[SciPy BSD-3-Clause](https://github.com/scipy/scipy/blob/e29dcb65a2040f04819b426a04b60d44a8f69c04/LICENSE.txt)。
testmath头列LPPL-1.3c和AMS/LaTeX署名。仓库许可不作为每个第三方科学样例独立授权
的额外断言；RKV仅发布固定来源/哈希和评测记录，不再分发这些原始输入。
