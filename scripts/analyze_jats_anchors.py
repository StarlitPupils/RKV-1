"""Report content-key benefit and its deletion, context and metadata costs."""
import argparse
import json
from pathlib import Path

from scripts.analyze_jats_fragments import analyze
from scripts.run_jats_anchors import MODES
from scripts.summarize_units import table


def report(root, log, frozen):
    r=analyze(root,log,frozen,modes=MODES,test_count=184,write_report=False)
    groups=r['budget_groups']; plans=json.loads((root/'plans.json').read_text('utf-8'))['plans']
    lookup={(g['case'],g['mode'],g['policy']):g for g in groups}
    text='''# v0.25 内容锚定JATS片段实验报告

## 假设、基线与交付

v0.24固定18个原XML的927单元全无元素id，位置键无法避免段落插入级联，v4的
range乐观下界仅1/12修订可过预算。本轮新增显式content审计模式，冻结同一输入/
预算及whole、position对照，测试可证伪假设：内容指纹键减少级联，但改写会产生
删除+插入两个操作，重复段落/父上下文与较长元数据可能抵消优势。

key=父论文ID+title/abstract/body角色+派生text UTF-8 SHA256+相同role/text出现序号。
仍分别绑定完整父SHA与原连续range SHA。同text不同原标记可重绑定；text改写不
视为同key。无关唯一段落插入保持其他内容键，但重复段落序号不代表永久物理
段落ID，不声称语义身份。没有缩短SHA、调高预算或重写原XML来获得收益。

这是独立审计API，Memory默认/来源kind/清单均不改。已有position/xml-id模式和
默认mode的输出不变；新增合成测试覆盖插入、大小写改写、重复与markup重绑定。

## 方法与正确性

复用同六篇18版本/12真实修订，0新增独立论文/QA/模型请求。position/content
两规则共1854范围审计（同一原范围重复）、whole/position/content×3轮×18文件
共162解析、9新进程；固定/Gear各13状态，26历史CAS快照全源恢复并核SHA，持久树
不变。184测试运行，183通过、1符号链接权限跳过。输入原路径/版本名保留。

144个规划仅比较相邻状态，是最短回放必要条件，不代表实际累计overlay/检查点
数。保留25%变化、32changes、256KiB记录、2MiB CAS等门槛。range-only是未实现
局部解码器的乐观下界；当前完整父校验逐记录全读，无缓存，重绑定父身份也收费。

## 同批预算对照

'''
    text+=table(['分块','键规则','策略','range下界可过/12','完整父校验可过/12','变化upsert中位','重绑定中位','下界失败原因'],[
        [g['case'],g['mode'],g['policy'],g['range_only_lower_bound']['admissible_adjacent_transitions'],g['current_full_parent_verifier']['admissible_adjacent_transitions'],
         g['upserted']['median'],g['rebound']['median'],str(g['range_only_lower_bound']['reasons'])] for g in groups])
    text+='\n## 每次真实转换的v4操作与门槛\n\n'
    for case in ('fixed','gear'):
        text+='\n### '+case+'\n\n'
        rows=[]
        for stage in range(1,13):
            for mode in ('position','content'):
                p=next(p for p in plans if p['case']==case and p['stage']==stage and p['mode']==mode and p['projection_rebinding'])
                rows.append([stage,mode,p['removed'],p['upserted'],p['rebound'],p['range_only_lower_bound']['record_bytes'],p['range_only_lower_bound']['cas_bytes'],p['range_only_lower_bound']['reason'] or 'admissible',p['current_full_parent_verifier']['reason'] or 'admissible'])
        text+=table(['阶段','规则','删','增/改','重绑定','下界记录B','下界CAS B','range门槛','完整父门槛'],rows)
    text+='\n## 解析与资源代价\n\n'
    text+=table(['模式','18文件wall中位s','CPU中位s','含启动进程wall中位s','进程峰值MiB'],[
        [m,f"{v['all_18_files_parser_wall_s']['median']:.6f}",f"{v['all_18_files_parser_cpu_s']['median']:.6f}",f"{v['process_wall_including_startup_s']['median']:.6f}",f"{v['peak_rss_bytes']['median']/1048576:.2f}"] for m,v in r['parsing'].items()])
    text+='\n'+table(['分块','候选','全部历史CAS B','13状态未压缩定位候选 B','全部RKV源一次B','原生库一次B'],[
        [c['case'],c['mode'],c['retained_CAS_bytes'],c['uncompressed_descriptor_metadata_candidate_bytes'],c['RKV_source_once'],c['native_once']] for c in r['partial_resource_accounting']])
    text+='''
metadata去text逐条canonical JSON求和，完整父上下文可由已计CAS快照关联；content
键的64hex文本SHA全额收费。未计实际FTS/Memory清单/overlay/运行时/pyc/安装/文件
系统成本，不能与v0.23完整系统算净压缩率。所有51模块/HTML源计一次，Gear加完整
旧实测库/元数据。解析含双遍XML与描述/SHA生成，输入预加载，启动另列；CPU为
本机计时分辨率，RSS含输入/输出，未测query或科学质量。

## 数据支持的结论与下一门槛

'''
    for case in ('fixed','gear'):
        a=lookup[case,'position','v4']['range_only_lower_bound']['admissible_adjacent_transitions']
        b=lookup[case,'content','v4']['range_only_lower_bound']['admissible_adjacent_transitions']
        full=lookup[case,'content','v4']['current_full_parent_verifier']['admissible_adjacent_transitions']
        text+=f'{case}：内容锚的v4 range乐观通过{b}/12，位置键{a}/12，当前完整父校验{full}/12。'
        text+='这些是同一批数据的必要条件计数，不能称实际增量索引收益。\n\n'
    text+='''
固定/Gear只多出2/1个乐观可行转换，仍有9/10个不通过，父上下文读取也未解决；
内容键没有提供足够证据支持生产集成。暂缓片段Memory新格式与局部解码开发，
保留整篇默认及原预算。后续优先扩大离线科学检索任务/上下文覆盖评测，定位
实际任务瓶颈；不再在这六篇上调门槛或追加键规则追求正结果。若未来独立工作负载
显示更大潜力，再以可信父上下文、同粒度重建、完整索引/清单/CAS/资源与整个
查询成本为新验收门槛。现有审计API及负结果仍保留，便于复核。

所有数字见原始plans/parser-trials/identity-audit及核验JSON。仅本机温缓存；无新
科学QA、E3、多跳、长期会话、冷缓存、跨机器、掉电/并发/GC或普遍数学证明结论。
'''
    (root/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n')
    return r


def plot(root, r):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.6),constrained_layout=True)
    for ax,case in zip(axes,('fixed','gear')):
        gs=[g for g in r['budget_groups'] if g['case']==case];x=list(range(len(gs)))
        ax.bar([i-.18 for i in x],[g['range_only_lower_bound']['admissible_adjacent_transitions'] for g in gs],width=.35,label='Range-only lower bound')
        ax.bar([i+.18 for i in x],[g['current_full_parent_verifier']['admissible_adjacent_transitions'] for g in gs],width=.35,label='Current full-parent audit')
        ax.set_xticks(x,[g['mode']+'\n'+g['policy'] for g in gs]);ax.set_ylim(0,13);ax.set_yticks(range(0,13,2));ax.set_title(case+' 64 KiB');ax.set_ylabel('Admissible adjacent transitions / 12');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('v0.25: content anchors versus positional keys on the same real revisions\nNecessary conditions only; no integrated Memory index or query-speed claims')
    fig.savefig(root/'content-anchor-preflight.png',dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--frozen',required=True);p.add_argument('--plot',action='store_true')
    a=p.parse_args();r=report(a.root,a.test_log,a.frozen)
    if a.plot:plot(a.root,r)
