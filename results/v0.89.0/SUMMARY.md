# v0.89 同批证据对照实验：传输失败、未完成，保留原分母

H1全48完成/接受及原来源/预算核验=False；H2oracle在24总分母上判定及完整依据均严格优于fresh实际检索=False。24个旧有标注问题每题两次fresh服务响应，48总预算，所有失败/缺失留分母。

|条件|尝试/24|接受/24|判定正确/24|判定+完整依据/24|
|---|---|---|---|---|
|retrieved|5|4|2|1|
|oracle|2|2|2|2|

## 固定方法与正确解释

实际检索在不读取targets/gold的独立函数内先完成，原BM25/model/SID/12wholepaper4096B不变。oracle使用标注paperID升序，超剩余原整行B或篇数则跳过，不切句子、不传gold verdict或句子标记；annotation-aware诊断不是可部署检索器。没有对源长或预测改善筛题。新fresh两条件同窗口交错顺序，不能拿新oracle对旧API结果当主比较。远端alias不等冻结权重，公开dev已被项目使用，不称未知科学泛化/NLI或无限上下文。

H2保持严格两指标优于，否则False；不因失败调预算、oracle排序、提示、问题或模型。零补发，失败占slot并停止后续，缺失留48分母。配对win/loss/tie和exact描述性p、各原批12题分别在JSON，不能以子组替代失败主门槛。oracle正结果也不证明实际检索器能找到这些论文，负结果不被隐藏。独立审计重读实际Store原范围并核SHA/docID/标题/全部abstract/原HTTPbytes/原prompt/citation/标注依据及oracle排序，原引用身份不当语义蕴含证明。

## 费用与限制

完整APIworker/parent/independentanalysis/finally CPU-wall/RSS及每调用wireB/usage/原响应SHA另存；历史pricebook的已知usage参考带{'known_calls': 6, 'unknown_or_missing': 42, 'known_historical_USD_band': {'low': 0.000532962, 'high': 0.001065924}, 'not_current_provider_price_or_bill': True}，不是当前报价或账单，unknown不归零。旧模型/Store/训练及旧24+48+48调用费用、全部快照/帧/恢复/派生/失败/运行库和专用源码保留；remoteweights/runtime/RAM/energy未知null。本机仅存储/检索，生成在用户API云端，不当本机推理收益。冷缓存/跨机/物理SSD/全系统IO/真实长期会话未测。原科学、prompt/rawresponse/model/密钥仅私存，public只有ID/SHA/计数/usage。

![同批证据干预](oracle-intervention.png)

图须实际视觉检查；完整本地包/外安装/CI/实际资产SHA与source/外实际发行install/proof重下载齐才交付。

## 原正式轮为什么停止及不能得出的结论

slot6即第7次预留请求遇到URLError，按冻结协议立即停止，7attempted、6份真实响应、1份失败、41份未尝试。没有重试任何已预留slot，没有补齐41请求或换服务追正；remaining41是未使用授权名额，不是已消费费用。本正式轮已关闭，后续仅核验/报告/发行。不能把含缺失的2/24或配对p=1当模型准确率、oracle无效的科学负结果或证明两策略相同。H1/H2=False主要因为48计划未完成，不是完成实验后证明无收益。

实际检索组5attempted/4accepted、oracle2attempted/2accepted，正确各2、完整依据1及2。两组缺失极不对称，不进行有效性比较或子组补救。6份usage参考历史USD带0.000532962–0.001065924，仅已知部分；失败请求服务端计费状态未知null，不把unknown42项或41未尝试都当实际支出。全部48分母及原响应SHA/usage/失败记录保留。

API父进程正常退出并保存完整parent/finally后，分析前官方额度只读接口暂时失败，原formal-v089.log保留；恢复官方读数确认仍在同窗口且原7slot/41missing已冻结，只运行未开始的独立审计prepare_v089.py，没有重跑API、问题、source选择或评分候选。所有审核/源码/协议仍绑定原sourcefreezeae7dba2d6e47b58c2b20ebbd6e85202d808e525c及exactCI40863907206。562检查561通过1权限skip，新增6项含真实Store48fake对照、goldverdict文件隔离、独立排序及篡改/预算/停止拒绝。

图已重新布局强调INCOMPLETE及接受数，展示改动耗时单列，不回填原正式计时；图需实际视觉检查。原实验代码/协议不修改，失败轮不覆盖。

## 完整时钟与分批缺失账本

|原批/条件|固定分母|判定正确（含未尝试保留）|判定加依据|
|---|---|---|---|
|v084:retrieved|12|0|0|
|v084:oracle|12|1|1|
|v087:retrieved|12|2|1|
|v087:oracle|12|1|1|

上述不是各批模型有效性估计，缺失由预先随机SHA顺序中的传输中断决定。全24主分母仍失败，不用各12子组补救。

APIworker全程wall25.9135118s、CPU1.0625s、peakRSS82767872B；完整parentwall27.1941413s，包含Python启动/退出及调用。审计独立parentwall0.9565151s，其childCPU/wall/RSS见prepare-v089-finally.json。两种时钟不能混称远端推理CPU，远端CPU仍未知null。未完成原因是传输停止，不能归因额度真实耗尽或把quota接口临时错误当额度允许；当前窗口实读正常后仅补独立分析。
