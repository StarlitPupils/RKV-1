# 数据来源与固定版本

下载后必须匹配 `rkv1/datasets.py` 的固定 SHA-256；URL 中的 `latest` 发生变化时
下载会失败，必须审查变更后发布新版本。来源清单放在语料目录外，避免计入原始语料。
仓库不分发用户研究文档或科学数据原文，仅保存下载器、哈希和实验统计。

| 语料 | 作者与来源 | 许可 | 用途 |
|---|---|---|---|
| Iris | R. A. Fisher；[UCI](https://archive.ics.uci.edu/dataset/53/iris)，DOI 10.24432/C56C76 | CC BY 4.0 | 小型科学 CSV |
| Wine Quality red | Cortez, Cerdeira, Almeida, Matos, Reis (2009)；[UCI](https://archive.ics.uci.edu/dataset/186/wine+quality)，DOI 10.24432/C56S3T | CC BY 4.0 | 科学测量 CSV |
| SciFact | Wadden et al. (2020), [Fact or Fiction: Verifying Scientific Claims](https://aclanthology.org/2020.emnlp-main.609/)；[官方仓库](https://github.com/allenai/scifact) | [官方许可](https://github.com/allenai/scifact/blob/master/LICENSE.md)：claims 为 CC BY 4.0，corpus abstracts 为 ODC-By 1.0 | 科学文本压缩；未来证据检索 |
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
