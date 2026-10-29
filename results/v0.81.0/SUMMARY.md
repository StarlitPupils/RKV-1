# v0.81.0 实验报告：有界子树 metadata 缓存

## 预定门槛与结果

H1 exact canonical packet/原bytes/完整记录/操作后cache上界/生命周期 **True**；H2 primary4096 C/A额外常驻对象图初始最终<=一半 **True**；H3 primary4096 C/A完整算法phase wall/CPU及整个parent wall均不回退 **False**；联合 **False**。36freshworker/288落盘packet/576成员/144负控制通过，追加36fresh完整root/42129叶metadata/42165所有原文件逐byte恢复/576原bytes成员复核。正式0重试，不挑最佳轮或改8请求数。

本版是已见owned目录的metadata成员机制。A retained全树，B ephemeral重遍历，C bounded固定65536B cache-owned graph操作后保守上界。headline只比较C/A，B/A及C/B完整诊断均保留。省额外状态不等于同幅总RAM下降、生产加速、磁盘压缩或科学NLI/回答改善。v079固定8metadata净增340600B、v080重算phase慢5.4–5.6x负结果保持。

## 冻结、固定请求和真实IPC

504检查503pass/1权限skip，freeze `e953fa06a62afbaf1c8d91ee28900bcaa8b10e6a`，exactCI `40815544104` 成功后唯一36worker，9/64/512/4096各3轮，ABC/BCA/CAB，8迟到双path请求、600秒0retry。必要preflight仅<=17叶/真实9source，4KiB仅淘汰正确性测试，不是正式cap或4096性能预检。

先创建source/Store/完整Scope元信息，再全部constructor（C含initial无path anchor-only全扫描）。READY后父任务fresh真实Store认证root，才生成请求、exclusive SHA和时间线并送child，child原bytes独立verify/canonical写packet后DONE。各case请求SHA/真实父子生成先后/报告SHA/退出和finally、全文件守恒均核实；同count/round三方法SID和全部packet bytes严格相等。协议可预测且请求靠近叶两端、有利复用，不能叫未知问题或新科学。

## 完整配对结果

| round |eligible |candidate |baseline |算法wall比 |算法CPU比 |完整parentwall比 |初始额外状态比 |最终额外状态比 |完整child peakRSS比 |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 9 | ephemeral | retained | 1.0854103192239366 | 1.0 | 0.9516548426340714 | 0.20580947136563876 | 0.20580947136563876 | 1.000288933834152 |
| 1 | 9 | bounded | retained | 1.0479204430701108 | 0.0 | 1.0920374156490877 | 1.0503854625550662 | 1.0619493392070485 | 1.001011268419532 |
| 1 | 9 | bounded | ephemeral | 0.9654601808276239 | 0.0 | 1.1475141687152597 | 5.103678929765886 | 5.159866220735786 | 1.0007221259387638 |
| 1 | 64 | ephemeral | retained | 1.4072236755849084 | None | 1.0311982736677707 | 0.03938563675641499 | 0.03938563675641499 | 0.9969883837659544 |
| 1 | 64 | bounded | retained | 1.2007197998374675 | None | 0.9949036205576587 | 1.1889456768006745 | 1.1911586490331418 | 0.9964147425785171 |
| 1 | 64 | bounded | ephemeral | 0.8532544048751821 | 1.0 | 0.9648034194422968 | 30.187290969899667 | 30.243478260869566 | 0.9994246260069045 |
| 1 | 512 | ephemeral | retained | 3.0167690715029964 | None | 1.0427835971359474 | 0.005053304759908872 | 0.005053304759908872 | 1.002369337979094 |
| 1 | 512 | bounded | retained | 8.553864746848273 | None | 1.1367590085861263 | 0.20384253969970864 | 0.20384253969970864 | 0.999581881533101 |
| 1 | 512 | bounded | ephemeral | 2.8354390223798664 | 3.0 | 1.0901197637825208 | 40.33846153846154 | 40.33846153846154 | 0.9972191323692993 |
| 1 | 4096 | ephemeral | retained | 4.673040368520145 | 6.5 | 1.0128526109967766 | 0.0006225540289448063 | 0.0006225540289448063 | 0.9554374093765103 |
| 1 | 4096 | bounded | retained | 15.906750774050703 | 22.0 | 1.1464321755696996 | 0.02518283100094195 | 0.02518283100094195 | 0.9473175447075882 |
| 1 | 4096 | bounded | ephemeral | 3.4039403727830497 | 3.3846153846153846 | 1.131884504342111 | 40.45083612040134 | 40.45083612040134 | 0.9915014164305949 |
| 2 | 9 | ephemeral | retained | 1.0960597710840525 | None | 0.8423777332473317 | 0.20580947136563876 | 0.20580947136563876 | 0.993968117190866 |
| 2 | 9 | bounded | retained | 1.0843337591362143 | None | 0.8103147299246944 | 1.0503854625550662 | 1.0619493392070485 | 1.002154243860405 |
| 2 | 9 | bounded | ephemeral | 0.9893016674298332 | 0.0 | 0.9619374989898706 | 5.103678929765886 | 5.159866220735786 | 1.0082358040745556 |
| 2 | 64 | ephemeral | retained | 1.302933285615182 | None | 0.9970222516011612 | 0.03938563675641499 | 0.03938563675641499 | 0.9971383602804407 |
| 2 | 64 | bounded | retained | 1.110607089048706 | None | 0.9955444313752305 | 1.1889456768006745 | 1.1911586490331418 | 0.9945628845328374 |
| 2 | 64 | bounded | ephemeral | 0.8523898355427547 | None | 0.9985177660543108 | 30.187290969899667 | 30.243478260869566 | 0.9974171330176496 |
| 2 | 512 | ephemeral | retained | 2.7259597585617175 | None | 1.11156505637453 | 0.005053304759908872 | 0.005053304759908872 | 0.9993041057759221 |
| 2 | 512 | bounded | retained | 7.582931127671136 | None | 1.1023941071213263 | 0.20384253969970864 | 0.20384253969970864 | 0.9995824634655532 |
| 2 | 512 | bounded | ephemeral | 2.781747274094785 | 2.5 | 0.9917495164132673 | 40.33846153846154 | 40.33846153846154 | 1.0002785515320334 |
| 2 | 4096 | ephemeral | retained | 5.63399953006218 | 4.666666666666667 | 1.027608720926987 | 0.0006225540289448063 | 0.0006225540289448063 | 0.943836405529954 |
| 2 | 4096 | bounded | retained | 18.501976262518212 | 13.333333333333334 | 1.1511434852056341 | 0.02518283100094195 | 0.02518283100094195 | 0.9485407066052227 |
| 2 | 4096 | bounded | ephemeral | 3.283986121013044 | 2.857142857142857 | 1.1202157608853383 | 40.45083612040134 | 40.45083612040134 | 1.0049842335469434 |
| 3 | 9 | ephemeral | retained | 1.0643453958315359 | None | 0.9670010173202949 | 0.20580947136563876 | 0.20580947136563876 | 0.9975592246949031 |
| 3 | 9 | bounded | retained | 1.0691627019831635 | None | 0.9707530856723007 | 1.0503854625550662 | 1.0619493392070485 | 0.9951184493898062 |
| 3 | 9 | bounded | ephemeral | 1.0045260741207642 | None | 1.003880107967625 | 5.103678929765886 | 5.159866220735786 | 0.9975532527345999 |
| 3 | 64 | ephemeral | retained | 1.4475652283310485 | None | 0.991744032735536 | 0.03938563675641499 | 0.03938563675641499 | 0.9949935631526248 |
| 3 | 64 | bounded | retained | 1.211279374551696 | None | 0.9804839661185182 | 1.1889456768006745 | 1.1911586490331418 | 1.000143041052782 |
| 3 | 64 | bounded | ephemeral | 0.8367701509024398 | None | 0.9886461967550648 | 30.187290969899667 | 30.243478260869566 | 1.0051753881541114 |
| 3 | 512 | ephemeral | retained | 3.1883217133175936 | None | 1.0338986043440828 | 0.005053304759908872 | 0.005053304759908872 | 0.9981856245638521 |
| 3 | 512 | bounded | retained | 7.815574764618392 | None | 1.1389130864716992 | 0.20384253969970864 | 0.20384253969970864 | 0.9984647592463364 |
| 3 | 512 | bounded | ephemeral | 2.4513130942755246 | 6.0 | 1.1015713549533601 | 40.33846153846154 | 40.33846153846154 | 1.0002796420581654 |
| 3 | 4096 | ephemeral | retained | 5.520925065141996 | 7.0 | 1.0384046168946048 | 0.0006225540289448063 | 0.0006225540289448063 | 0.9469521604938271 |
| 3 | 4096 | bounded | retained | 18.41885959914756 | 19.5 | 1.1280568094613372 | 0.02518283100094195 | 0.02518283100094195 | 0.9474344135802469 |
| 3 | 4096 | bounded | ephemeral | 3.3361908342934252 | 2.7857142857142856 | 1.0863364733824483 | 40.45083612040134 | 40.45083612040134 | 1.0005092686901609 |

H3同时要求C/A构造+8次issue/read原bytes/verify/canonical/写packet的phase wall和CPU<=1，以及完整parent<=1，各3轮。共同source/ingest、Scope初始化、等父请求、RAM图观察均在phase外单计，但进入worker/parent；父自己的fresh root/请求生成CPU/wall单列。不能用共同大ingest或observer差异掩盖phase回退。0CPU分母null不能pass，不用B/A或小规模替换headline。

## 64KiB定义、瞬时状态和CPU费用

NodeLRU的保守费用包含slotted实例/所有slot primitive值、OrderedDict实际backing/node、tuple keys及int、(32B digest,32B stamp) tuple全部bytes。相同int对象重复引用保守多算，实际对象图另独立去重；共同Scope文件metadata/SID先seen扣除共享对象。不是hash-payload-only。全prover含anchor/包装字段另计，初始O(N)Snapshot、每请求排序keys及eligible总B遍历仍存在，完整RSS独立，不能称总内存64KiB或全流程O(logN)。

每次cache API完成后上界<=65536；插入后再evict会产生更大的max_provisional_bound_B，raw trace明确保留，它不是峰值硬cap。stats primitive饱和使尺寸不变，O(1)维护依据实际dict sizeof和累计entry成本，校验stamp/命中/LRU/淘汰/维护CPU全部在phase内。stamp只防事故，不是对能任意改进程内存者的认证；最终完整root/原bytes仍对外部可信anchor SHA/SID/path核。

C仅不含requested leaf的子树可复用，包含leaf的分支仍展开求siblings；初始全扫描不可省，sid/count和owner固定、关闭拒绝并清cache entries。原source CAS损坏由原read_range拒绝，没有原bytes缓存或校验绕过。A/B没有C cache observer，记录null不是0。初始/最终trace的max_retained_bound_B均通过上限，provisional峰值及hit/miss/hash_nodes/rewrites/evictions均单列，不把计数自动换成I/O/生产收益。

RAM图观察在算法phase外，完整worker/parent和RSS仍包含；观察本身CPU另记。实际常驻状态图和RSS不是同一指标，global allocator/GC可能影响峰值。单file预算1MiB不是全包/物理IO预算；查询原payload B三法守恒，额外control read B在raw另列。

## 独立原证据与全部账本

实际288落盘packet用fresh真实Store逐file恢复与每leaf/root重算，576原bytes成员独立核，未借共享Scope view或旧成功替代。额外analysis应用读取4122342B，非worker或SSD读取。所有root/body/时序/原SHA/完整timer和源文件校验齐；分析finally/父timer另附，不报局部收尾当完整审核CPU。

实际整库67Python+HTML 429612B，全部scripts保守1729287B；专用code/tests/protocol/input SHA齐备。完整worker source/CAS/snapshot/请求/packet残留13754107B，outer raw/stdio/parent5356164B，私有准备16301B。v079 index、全部旧science/human/train/model/frames/restored/cache/失败仍保留。当前0模型/新训练/新远程API不抹除旧费用，未知OS/物理IO不当0。没有靠删除diagnostic index文件声称新压缩或磁盘净省。

## 复现与完整交付

```powershell
python -m unittest discover -s tests
```

scripts.run_bounded_membership.execute_case落实父READY后认证/请求；child worker需正确父输入，不是空stdin即可跑完整benchmark。固定input/context保留role/countorder与独占case路径。

![缓存常驻状态和完整算法阶段](bounded-membership.png)

图须实际视觉看。详报告/rawparent/图/README/release→localinitialbuild0→物理仓库外actualwheel-currentnative/actualsdist新C与全部旧机制→finalbuild/sourceaudit0→tagReleaseCI→actual7资产SHA/递归allsource/外actualpublished安装/proof8全部齐才算交付。init版本用bytes.replace保留255B，正式前Git/raw/manifest全源逐byte一致。

成员要求独立可信anchor，非SID-alone自证/fullcoverage/DAG/科学NLI/回答。E3净收益/E4整体/真实长会话/科学NLI/回答/无限上下文未完成。冷缓存跨机/物理SSD/全系统IO未知；旧24API耗尽，无新模型/API/下载授权，CPU离线。原science/model/frame/restored/私研/模板课程个人报告密钥不外发。若phase/RAM联合未过必须保留，不改cap/8请求或取最佳轮追正。


## 实际图与关键负结果补充

图已实际视觉检查。主4096三轮C/A常驻状态比0.025182831（初末同），C实际额外状态60474B；操作后cache保守max65272B<=65536，插入provisional max70552B明确超过cap且不隐藏。RSS比0.94732/0.94854/0.94743。phase wall比15.90675/18.50198/18.41886，CPU比22/13.3333/19.5，parent比1.14643/1.15114/1.12806。三轮C初始hash_nodes8191，8请求后73719=9*8191，hits始终0、misses73519、evictions73564；在该既定负载中完整遍历导致LRU不断淘汰，未复用任何子树，额外维护和校验反而变慢。该计数解释不等于所有cache均无用；不调cap/8请求回填本版结果。新admission策略必须另冻结另评，不以旧区段重跑冒充独立新科学。
