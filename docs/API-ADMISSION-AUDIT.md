# v085下一项草案：API漏检的排名与原记录准入分离审计

状态：v084完整发行核验已完成，本候选公开采用，必要owned检查5项已通过；待全回归/源码协议输入冻结/CI后唯一正式诊断；当前真实16case未做，未发布。0新模型API/训练/下载，v08448调用额度已经用完。

先验来自v08448已见输出：16retrieved中12annotated，5未取回标注论文、7取回，后者2判断错。冻结目标不是新科学质量验证，而是独立重建旧BM25排序与原record准入，核对16问题/43原返回记录/16savedselectedIDs与原SID/SHA完全一致，并对12annotated每个gold来源分类no_candidate/byte_rejected/count_stop/recovered。另列rank、原recordB、选择前已用/剩余B、是否该record单独就>4096，避免把所有byte_rejected误称纯预算因果。排序越低可能先被别的记录耗预算；注释并非所有相关证据。

H1独立词法数值/顺序（同环境1e-12，排名完全相同）、最终IDs/实际原recordB与v084完全一致，gold与未标注分母/原files/所有SHA核对。H2强先验：5个缺标注原论文中，单条raw记录本身超过完整4096B者严格过半；若不满足就False，不改预算/选集/原JSON格式或再挑阈值。这个命题比“byte_rejected”更窄，仍是已见事后诊断，不能推出换codec/加预算/改句子单元必然提高API答案。不设置新生产时间门槛，所有复算CPU/parent/worker/RAM与源/模型/43记录读取和全文件账本另计。

只原16 API问题一次确定性诊断，无mechanical重复当独立科学样本，0新生成；旧48predictions/slot/prompt/response全部不改。oldmodel10MB/Store/CAS/SID/corpusSHA和16questions/gold以及v084tag-derived/raw输入SHA先freeze，代码/tests/协议/精确次数/完整timer先冻结并CI后才能做。owned检查仅17paper和合成budget边界，不在16真实问题上预检挑参数。独立source定位读取仍做全校验，admitted recordB不是全系统/SSD读取量。图包括goldrank与rawrecordB相对4096，分类分母、源证据缺失与模型读错分开，完整报告发布各gate齐才交付。

正式次数精确定稿：1 fresh worker只读原16问题，每问题一次词法分数和原记录准入、原selected+gold实际Store读取，原API43返回binding必须一致；12gold分类，其中5missing分母固定。恢复完整corpus原文件一次并校SHA；父完整subprocess wall/自己CPU、worker完整wall/CPU/RSS和finally，source read返回B和所有残留文件另计；0retry、600秒上限。相同问题复算不是新科学试验，不重跑原48API或更改其时钟。H2严格大于5/2，即>=3，而非>=2。

后置独立分析另一次fresh Snapshot恢复完整corpus1次、重算原16问题旧词法排序/准入并独立核48个原record binding（43selected+5额外missing gold）；worker本体同样48binding/fullcorpus1，两个阶段分开计入应用读取/CPU/RAM，不冒充独立科学样本。分析自身完整finally/parentwall要保存，不使用局部收尾时间替代。
