"""Validate frozen known/open workload pairs and produce descriptive reports."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import re
import subprocess

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.qasper_audit import BUDGETS
from scripts.run_context_selection import load, PLANS, SEED
from scripts.run_known_source import WORKLOADS, SCORE_FIELDS
from scripts.run_units import save
from scripts.summarize_units import table


def mean(xs):
    xs=list(xs);return sum(xs)/len(xs) if xs else None


def dist(xs):
    v=summary(list(xs));v.pop('samples',None);return v


def pair(rows,left,right):
    """right-minus-left; papers, rather than repeated rounds, are resampled."""
    rows=[r for r in rows if r['has_nonempty_answerable_reference']]
    delta=lambda r:int(r['scores'][right[0]][right[1]][0])-int(r['scores'][left[0]][left[1]][0])
    groups=defaultdict(list)
    for r in rows:groups[r['paper_key']].append(delta(r))
    values=[mean(v) for _,v in sorted(groups.items())];rng=random.Random(SEED)
    boot=sorted(mean(rng.choices(values,k=len(values))) for _ in range(1000)) if values else []
    return {'reference_questions':len(rows),'wins':sum(delta(r)>0 for r in rows),'losses':sum(delta(r)<0 for r in rows),
        'ties':sum(delta(r)==0 for r in rows),'question_macro_delta':mean(delta(r) for r in rows),
        'papers':len(values),'paper_macro_delta':mean(values),'paper_bootstrap_95_percent':[boot[24],boot[974]] if boot else None}


def analyze(root,log,frozen):
    read=lambda name:json.loads((root/name).read_text('utf-8'))
    checks=read('source-checksums.json');assert checks==implementation_checksums() and len(checks)==53
    for name,sha in checks.items():assert digest(subprocess.check_output(['git','show',frozen+':rkv1/'+name]))==sha
    for rel in ('scripts/run_known_source.py','docs/KNOWN-SOURCE.md'):
        assert Path(rel).read_bytes()==subprocess.check_output(['git','show',frozen+':'+rel])
    resources=read('source-resource.json');assert resources['total_bytes']==sum(v['bytes'] for v in resources['files'].values())
    assert set(resources['files'])=={'rkv1/'+n for n in checks}|{'rkv1/memory_demo.html'}
    for name,v in resources['files'].items():assert Path(name).stat().st_size==v['bytes'] and digest(Path(name).read_bytes())==v['sha256']
    post=read('postconditions.json');assert all(post[k] for k in ('all_persistent_trees_unchanged','all_full_original_files_bytewise_restored','checksums_unchanged')) and post['remote_model_calls']==0
    env=read('environment.json');assert env['generation_calls']==0 and env['score_fields']==list(SCORE_FIELDS)
    provenance=read('dataset-provenance.json');build=read('build.json');result={'splits':{}};formal=0;bindings=0
    for split,count,papers in (('dev',1005,281),('train',2593,888)):
        trials=[read(f'{split}-round{r}.json') for r in range(3)]
        old=json.loads(Path(f'results/v0.27.0/{split}-trials.json').read_text('utf-8'))['trials'][0]['queries']
        old={r['question_id_sha256']:r for r in old};first=trials[0]['queries'];index={r['question_id_sha256']:r for r in first}
        _,_,labels=load(split);labels={c['question_id_sha256']:c for c in labels}
        assert len(index)==count and set(index)==set(labels)==set(old)
        assert provenance[split]['question_instances']==count and provenance[split]['papers']==papers
        assert build[split]['full_original_source_bytewise_verified'] and build[split]['build']['indexed_records']==papers
        for rr,t in enumerate(trials):
            assert t['round']==rr and t['split']==split and t['warmup_read_operations']==2 and t['persistent_tree_unchanged'] and t['generation_calls']==0
            assert len(t['queries'])==count and {r['question_id_sha256'] for r in t['queries']}==set(index)
            for r in t['queries']:
                base=index[r['question_id_sha256']];prior=old[r['question_id_sha256']];c=labels[r['question_id_sha256']]
                assert r['paper_key']==c['paper_key'] and r['question_sha256']==c['question_sha256']
                assert r['has_nonempty_answerable_reference']==bool(c['gold_sets']) and r['fully_text_mapped_reference']==c['fully_text_mapped_reference']
                assert r['target_in_open_top5']==(r['paper_key'] in r['keys'][:5])
                for key in ('keys','evidence_identity_sha256'):assert r[key]==prior[key]
                assert len(r['ranks'])==len(prior['ranks']) and all(abs(a-b)<=1e-10 for a,b in zip(r['ranks'],prior['ranks']))
                for key in ('keys','evidence_identity_sha256','known_source_identity_sha256','scores','selection_source_identity_sha256'):
                    assert r[key]==base[key]
                for work in WORKLOADS:
                    for plan in PLANS:
                        for b in BUDGETS:
                            key=plan+'/'+str(b);v=r['scores'][work][key];assert len(v)==len(SCORE_FIELDS) and 0<=v[3]<=b
                            assert v[0] is not None if c['gold_sets'] else v[0] is None
                            if work=='open-top5':assert v==[prior['scores'][plan][str(b)][f] for f in SCORE_FIELDS]
                            if work=='oracle-if-recalled':
                                if r['target_in_open_top5']:
                                    assert v==r['scores']['known-source'][key]
                                    assert r['selection_source_identity_sha256'][work][key]==r['selection_source_identity_sha256']['known-source'][key]
                                else:assert v[5:]==[0,0]
                            bindings+=1
                formal+=1
        allrows=[r for t in trials for r in t['queries']];eligible=[r for r in first if r['has_nonempty_answerable_reference']]
        group={'question_instances':count,'papers':papers,'reference_questions':len(eligible),'plans':{},'contrasts':{},'selector_pairs':{},'budget_regressions':{},
            'target_in_top5_reference_questions':sum(r['target_in_open_top5'] for r in eligible),
            'peak_rss_bytes':dist(t['peak_rss_bytes'] for t in trials),'process_wall_s':dist(t['process_wall_including_startup_s'] for t in trials),
            'read_wall_s':{w:dist(r['read_timing_wall_cpu_s'][w][0] for r in allrows) for w in ('open-top5','known-source')},
            'actual_Memory_bytes':build[split]['storage']['logical_file_bytes'],'source_bytes_once':resources['total_bytes']}
        for work in WORKLOADS:
            group['plans'][work]={};group['selector_pairs'][work]={};group['budget_regressions'][work]={}
            for plan in PLANS:
                regressions={}
                for low,high in zip(BUDGETS,BUDGETS[1:]):
                    ids=[r['question_id_sha256'] for r in eligible if r['scores'][work][plan+'/'+str(low)][0] and not r['scores'][work][plan+'/'+str(high)][0]]
                    regressions[f'{low}-to-{high}']={'count':len(ids),'question_ids_sha256':ids}
                group['budget_regressions'][work][plan]=regressions
                for b in BUDGETS:
                    key=plan+'/'+str(b);s=lambda r:r['scores'][work][key];by_paper=defaultdict(list)
                    for r in eligible:by_paper[r['paper_key']].append(s(r)[0])
                    mapped=[r for r in eligible if r['fully_text_mapped_reference']]
                    def total_wall(r):
                        read=r['read_timing_wall_cpu_s']['known-source' if work=='known-source' else 'open-top5'][0]
                        if work=='oracle-if-recalled':read+=r['read_timing_wall_cpu_s']['oracle-filter'][0]
                        t=r['selection_timing'][work][key];return read+t[0]+t[2]
                    group['plans'][work][key]={'complete_count':sum(s(r)[0] for r in eligible),'reference_questions':len(eligible),
                        'question_macro_complete':mean(s(r)[0] for r in eligible),'paper_macro_complete':mean(mean(v) for v in by_paper.values()),
                        'fully_mapped_reference_questions':len(mapped),'fully_mapped_complete':sum(s(r)[0] for r in mapped),
                        'best_reference_paragraph_recall':mean(s(r)[1] for r in eligible),
                        'failure_categories':dict(Counter(s(r)[2] for r in first)),
                        'body_utf8_bytes':dist(s(r)[3] for r in first),'context_json_bytes':dist(s(r)[4] for r in first),
                        'selector_wall_s':dist(r['selection_timing'][work][key][0]+r['selection_timing'][work][key][2] for r in allrows),
                        'selector_cpu_mean_s':mean(r['selection_timing'][work][key][1]+r['selection_timing'][work][key][3] for r in allrows),
                        'read_plus_selector_component_wall_s':dist(total_wall(r) for r in allrows)}
            for b in BUDGETS:group['selector_pairs'][work][str(b)]=pair(first,(work,'source-order/'+str(b)),(work,'lexical/'+str(b)))
        for plan in PLANS:
            for b in BUDGETS:
                key=plan+'/'+str(b);g={}
                for other in ('known-source','oracle-if-recalled'):
                    g[other+'-minus-open']=pair(first,('open-top5',key),(other,key))
                    for flag in (True,False):
                        g[other+('-recalled' if flag else '-not-recalled')]=pair([r for r in first if r['target_in_open_top5']==flag],('open-top5',key),(other,key))
                group['contrasts'][key]=g
        result['splits'][split]=group
    assert formal==10794 and bindings==194292
    txt=log.read_text('utf-8');assert re.search(r'Ran 200 tests',txt) and 'OK (skipped=1)' in txt and 'FAILED' not in txt
    validation={'frozen_commit':frozen,'all_53_modules_protocol_and_driver_match_freeze':True,'formal_question_pairs':formal,'formal_read_operations':formal*2,
        'context_bindings':bindings,'warmup_read_operations_excluded':12,'all_rounds_identity_and_scores_identical':True,'open_all_scores_keys_ranks_identity_match_v027':True,
        'known_and_oracle_source_ids_and_scores_match_when_recalled':True,'all_persistent_trees_and_full_original_bytes_unchanged':True,
        'remote_model_calls':0,'new_model_answer_quality':None,'cold_cache':None,'cross_machine':None,
        'tests':{'run':200,'passed':199,'skipped':1,'failed':0,'log_sha256':digest(log.read_bytes())}}
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation)
    plot(root,result);report(root,result,validation,provenance,resources,build)


def plot(root,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,5.4),sharey=True)
    for ax,(split,g) in zip(axes,result['splits'].items()):
        for work,color in zip(WORKLOADS,('#446b9a','#27846e','#ba7840')):
            for plan,style in zip(PLANS,('--','-')):
                ax.plot([8,24,48],[100*g['plans'][work][plan+'/'+str(b)]['question_macro_complete'] for b in BUDGETS],style+'o',color=color,label=work+' / '+plan)
        ax.set_title(split+' | '+str(g['reference_questions'])+' nonempty references');ax.set_xlabel('Body UTF-8 budget (KB, decimal)');ax.set_xticks([8,24,48]);ax.grid(alpha=.2)
    axes[0].set_ylabel('Complete reference exposed (%)')
    fig.legend(*axes[1].get_legend_handles_labels(),fontsize=8,loc='lower center',ncol=3)
    fig.suptitle('Provided-source workload differs from open retrieval; oracle is diagnostic only')
    fig.tight_layout(rect=(0,.13,1,.94));fig.savefig(root/'known-open-coverage.png',dpi=170);plt.close(fig)


def report(root,result,validation,provenance,resource,build):
    text='''# v0.29 实验报告：来源已知与开放检索的差距分解

## 问题与冻结设计

v0.26–27采用全库定位论文，而QASPER原任务给定论文。本轮把“调用者提供来源”
与“仅问题检索”分开：新增显式Memory.lookup，不把已知目标身份当作开放检索
能力。原选择器、三个预算、原语料、默认策略和所有原存储格式均不变。

三条件为open-top5、known-source、oracle-if-recalled。后者按标注目标从已召回
top5中过滤，未召回则空，是用到目标身份的事后诊断，不可部署为开放检索。
known直接接收paper_key，不接收问题/答案；两选择器只看问题和已验证正文。
实验结果是完整参考段落暴露，不是回答正确率或官方QASPER F1。

```python
from rkv1.memory import Memory
result = Memory('MEMORY').lookup('qasper:already-known-paper-id')
# result['scope'] == 'explicit-known-source'; rank为None，缺失key为[]。
```

key须为1–512字符且无NUL；snapshot可显式读取保留历史，不指定时读当前HEAD。
该Python能力尚未接入memory-answer/CLI/HTTP，不向既有回答流程自动提供来源。

'''
    text+=f"运行模块/驱动/协议在`{validation['frozen_commit']}`冻结，200测试运行、199通过、1项Windows符号链接权限跳过。协议见[KNOWN-SOURCE](../../docs/KNOWN-SOURCE.md)。\n\n"
    text+='## 主要结论与优先级\n\n'
    for split,g in result['splits'].items():
        key='lexical/24000';counts=[g['plans'][w][key]['complete_count'] for w in WORKLOADS]
        no_map=g['plans']['known-source'][key]['failure_categories']['no-fully-text-mapped-reference']
        omitted=g['plans']['known-source'][key]['failure_categories']['budget-omitted-reference']
        eight=g['selector_pairs']['known-source']['8000']
        text+=f"- {split}的24KB lexical：open {counts[0]}，known {counts[1]}，oracle-if-recalled {counts[2]}，共同分母{g['reference_questions']}。known减open净差{counts[1]-counts[0]}，可分解为去其他论文的诊断净差{counts[2]-counts[0]}，以及提供未召回来源的额外{counts[1]-counts[2]}；后者明显更大，来源定位是当前主要瓶颈。known仍有{no_map}题无整组全文映射参考、{omitted}题可映射但预算遗漏。\n"
        text+=f"- {split}已知来源8KB下，lexical相对原顺序净增{100*eight['question_macro_delta']:.2f}pp，同时{eight['wins']}赢/{eight['losses']}输；不能称逐题支配。\n"
    text+='''
dev已知来源24KB的lexical配对论文组区间仍跨零；train该区间为正，但已重复使用
公开任务，不能据此自动改默认。48KB known lexical距全文映射上限dev仍差2题、
train差10题；图表/非文本未映射上限本身也限制暴露率。没有新的模型质量结论。
因此下一优先项是冻结一个不接收目标身份的开放检索候选，计辅助索引/构建/查询
完整成本，与本版复现基线配对；避免继续只增加已知来源预算或在这些gold上搜参数。

'''
    text+='## 数据、分母与重复控制\n\n'
    text+=table(['split','论文','问题实例','唯一问题文本','有非空可答参考','至少一组全文映射'],[[s,p['papers'],p['question_instances'],p['unique_question_strings'],p['nonempty_answerable_reference_questions'],p['fully_text_mapped_reference_questions']] for s,p in provenance.items()])
    text+='''
沿用公开QASPER v0.3 dev/train，SHA见dataset-provenance.json；这是已用数据的任务
分解，不是新独立科学来源、盲测或test。参考未映射项仍保留分母，无非空可答参考
保持null；不奖励空集合。问题文本/证据/原JSON未公开，FTS不包含qas/答案标注。

两个split独立新建原默认固定/Zlib/v3，labels与v0.27相同。三轮新进程，每轮题序/
读取操作顺序随机，seed20261025+r；10794正式问题对、21588读取、194292上下文
绑定，12预热读取排除。所有轮次身份/评分/原句选择一致，open逐题keys、BM25、
原始来源身份与全部预算分数精确复现v0.27。起止整文件恢复、持久树大小/SHA不变。

## 全体非空参考的覆盖结果

![来源条件与预算](known-open-coverage.png)

'''
    text+=table(['split','正文预算B','选择器','open完整参考','known完整参考','oracle-if-recalled完整参考'],[
        [s,b,p,*[f"{g['plans'][w][p+'/'+str(b)]['complete_count']}/{g['reference_questions']}" for w in WORKLOADS]]
        for s,g in result['splits'].items() for b in BUDGETS for p in PLANS])
    text+='\n## 配对差与论文组描述区间\n\n'
    text+=table(['split','选择器/预算','对照（减open）','赢/输/平','问题差pp','论文差pp','论文bootstrap区间pp'],[
        [s,k,w,f"{v['wins']}/{v['losses']}/{v['ties']}",f"{100*v['question_macro_delta']:.3f}",f"{100*v['paper_macro_delta']:.3f}",f"[{100*v['paper_bootstrap_95_percent'][0]:.3f}, {100*v['paper_bootstrap_95_percent'][1]:.3f}]"]
        for s,g in result['splits'].items() for k,vs in g['contrasts'].items() for w,v in vs.items() if w.endswith('-minus-open')])
    text+='''
按论文组1000次bootstrap，seed20261025，排序分位索引24/974；区间只描述该公开集。
known减open包含明确额外的来源信息与只看一篇的预算优势，不是新检索器效应；
oracle减open只在原top5召回条件移除其他论文，既可能赢也可能输；这同时改变
预算竞争和临时词法FTS的IDF/排序语境，不能单独归因为纯预算效应。逐题、分层、论文
宏平均及全部原样本见derived-metrics.json和*-round*.json，三轮不当独立论文。

'''
    text+='## 24KB损失分类与来源召回分层\n\n'
    for s,g in result['splits'].items():
        text+=f"\n### {s}\n\n有参考{g['reference_questions']}题，其中目标在open top5共{g['target_in_top5_reference_questions']}题。\n\n"
        reasons=sorted({r for w in WORKLOADS for p in PLANS for r in g['plans'][w][p+'/24000']['failure_categories']})
        text+=table(['选择器','分类',*WORKLOADS],[[p,r,*[g['plans'][w][p+'/24000']['failure_categories'].get(r,0) for w in WORKLOADS]] for p in PLANS for r in reasons])
    text+='\n## 选择器迁移与非单调回归\n\n'
    text+=table(['split','条件','预算B','lexical赢/输/平','问题差pp','论文差区间pp'],[
        [s,w,b,f"{v['wins']}/{v['losses']}/{v['ties']}",f"{100*v['question_macro_delta']:.3f}",f"[{100*v['paper_bootstrap_95_percent'][0]:.3f}, {100*v['paper_bootstrap_95_percent'][1]:.3f}]"]
        for s,g in result['splits'].items() for w,vs in g['selector_pairs'].items() for b,v in vs.items()])
    text+=table(['split','条件','选择器','8k→24k真→假','24k→48k真→假'],[
        [s,w,p,v['8000-to-24000']['count'],v['24000-to-48000']['count']] for s,g in result['splits'].items() for w,ps in g['budget_regressions'].items() for p,v in ps.items()])
    text+='\n预算扩大后greedy换选可能失去原完整参考；所有回归SHA保留，不删题，不由均值提高推断逐题支配。\n'
    text+='\n## 时间、完整性与成本\n\n'
    text+=table(['split','实际Memory B','全部RKV源一次B','计入合计B','进程RSS中位MiB','open top20中位/p95 ms','lookup中位/p95 ms'],[
        [s,g['actual_Memory_bytes'],g['source_bytes_once'],g['actual_Memory_bytes']+g['source_bytes_once'],f"{g['peak_rss_bytes']['median']/1048576:.2f}",
         *[f"{g['read_wall_s'][w]['median']*1000:.3f}/{g['read_wall_s'][w]['p95']*1000:.3f}" for w in ('open-top5','known-source')]] for s,g in result['splits'].items()])
    text+=f"\nlookup所在memory.py相对v0.28净增加{resource['lookup_memory_module_delta_bytes']}B；所有53模块/HTML全额计一次，三条件共用同一个不变库，原生库特定成本0。构建wall/CPU与目录账本见build.json。\n\n"
    text+=table(['split','条件','选择器/预算','读取+选择组件和中位/p95 ms','context JSON中位/p95 B'],[
        [s,w,k,f"{v['read_plus_selector_component_wall_s']['median']*1000:.3f}/{v['read_plus_selector_component_wall_s']['p95']*1000:.3f}",f"{v['context_json_bytes']['median']:.0f}/{v['context_json_bytes']['p95']:.0f}"]
        for s,g in result['splits'].items() for w,vs in g['plans'].items() for k,v in vs.items() if k.endswith('/24000')])
    text+='''
lookup读取一个显式来源，open验证top20，不能把两者耗时比称同任务加速。lookup
没有绕开索引/CAS/记录SHA或重新解析，历史overlay/rebinding物化成本仍收费。
每预算完整收费一次词法prepare，选择与离线gold评分分离；oracle另计原search和
过滤。表中是逐query组件和，不是模型端到端延迟；整个进程RSS包含全部数据/
标注/策略/结果，不是某条件独立内存。CPU原样本保留，计时分辨率可能出现0。

正文预算不含标题/句ID/JSON/转义/问题/system/API结构。另列context紧凑JSON，
不等于真实wire/token/账单。共享Python/SQLite/Zlib/OS、安装/pyc/文件系统成本未
全额分配，不能声称整个系统净压缩。模型0次，冷缓存/跨机器保持null。

## 判定、限制与下一步

本轮提供可核验的来源条件分解及显式lookup，不改变默认检索/选择，不向开放任务
自动注入目标身份，不把oracle当可部署算法。仅当调用者明确指定来源时使用lookup。
已知来源仍可能因预算/排序遗漏、图表未映射而无法完整暴露参考，完整暴露也不保证
模型理解或回答正确。原句ID/精确locator保持，派生输出不升格为证据。

下一步先冻结一个不接收目标身份的开放检索候选，并补独立任务迁移验证；
不在既有gold上反复调规则追求正结果。真实模型新增评测仍需新增明确调用预算。
E3神经压缩、语义/图检索、多跳、长期会话、形式证明、冷缓存/跨机器、掉电/并发/
GC均不由本报告得出结论。每轮原始JSON、冻结SHA、图表与负结果保留。
'''
    (root/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--frozen',required=True)
    a=p.parse_args();analyze(a.root,a.test_log,a.frozen)
