"""Audit annotation-free unit retrieval, including transfer losses and full costs."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import re
import subprocess

from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.qasper_audit import BUDGETS
from scripts.analyze_known_source import dist, mean
from scripts.run_context_selection import PLANS, SEED
from scripts.run_known_source import SCORE_FIELDS
from scripts.run_paragraph_retrieval import dataset, TASKS, RETRIEVERS, KS, parent_metrics
from scripts.run_units import save
from scripts.summarize_units import table


def paired(rows,delta,*,papers):
    groups=defaultdict(list)
    for r in rows:groups[r['paper_key'] if papers else r['question_id_sha256']].append(delta(r))
    values=[mean(v) for _,v in sorted(groups.items())];rng=random.Random(SEED)
    boot=sorted(mean(rng.choices(values,k=len(values))) for _ in range(1000))
    ds=[delta(r) for r in rows]
    return {'instances':len(rows),'wins':sum(d>0 for d in ds),'losses':sum(d<0 for d in ds),'ties':sum(d==0 for d in ds),
            'instance_macro_delta':mean(ds),'resampling_units':len(values),'unit_macro_delta':mean(values),
            'unit_bootstrap_95_percent':[boot[24],boot[974]],'resampling_unit':'paper' if papers else 'claim'}


def analyze(root,log,frozen):
    read=lambda name:json.loads((root/name).read_text('utf-8'))
    checks=read('source-checksums.json');assert len(checks)==54 and checks==implementation_checksums()
    for name,sha in checks.items():assert digest(subprocess.check_output(['git','show',frozen+':rkv1/'+name]))==sha
    for rel in ('docs/PARAGRAPH-RETRIEVAL.md','scripts/run_paragraph_retrieval.py'):
        assert Path(rel).read_bytes()==subprocess.check_output(['git','show',frozen+':'+rel])
    resources=read('source-resource.json');assert resources['total_bytes']==sum(v['bytes'] for v in resources['files'].values())
    assert set(resources['files'])=={'rkv1/'+n for n in checks}|{'rkv1/memory_demo.html'}
    for name,v in resources['files'].items():assert digest(Path(name).read_bytes())==v['sha256'] and Path(name).stat().st_size==v['bytes']
    post=read('postconditions.json');assert all(post[k] for k in ('all_Memory_and_auxiliary_trees_unchanged','all_full_original_files_bytewise_restored','checksums_unchanged')) and post['remote_model_calls']==0
    env=read('environment.json');assert env['score_fields']==list(SCORE_FIELDS) and env['generation_calls']==0
    provenance=read('dataset-provenance.json');builds=read('build.json');result={'tasks':{}};formal=0;bindings=0
    old_scifact=json.loads(Path('results/v0.15.0/retrieval.json').read_text('utf-8'))['trials']
    old_scifact={r['claim_id']:r for r in old_scifact if r['round']==0}
    for task in TASKS:
        qasper=task.startswith('qasper');family=task if qasper else 'scifact';build=builds[family]
        trials=[read(f'{task}-round{r}.json') for r in range(3)];first=trials[0]['queries'];idx={r['question_id_sha256']:r for r in first}
        _,_,jobs=dataset(task);labels={c['question_id_sha256']:c for c in jobs}
        assert len(first)==len(idx)==len(jobs) and set(idx)==set(labels)
        assert build['full_original_source_bytewise_verified'] and build['auxiliary_build']['papers']==build['memory_build']['indexed_records']
        assert build['auxiliary_build']['logical_file_bytes']==build['auxiliary_tree']['bytes']
        prior={}
        if qasper:
            old=json.loads(Path(f'results/v0.29.0/{task.split("-")[1]}-round0.json').read_text('utf-8'))['queries']
            prior={r['question_id_sha256']:r for r in old};assert set(prior)==set(idx)
        for rr,t in enumerate(trials):
            assert t['round']==rr and t['task']==task and t['warmup_read_operations']==2 and t['Memory_and_sidecar_trees_unchanged'] and t['generation_calls']==0
            assert len(t['queries'])==len(idx) and {r['question_id_sha256'] for r in t['queries']}==set(idx)
            for r in t['queries']:
                c=labels[r['question_id_sha256']];base=idx[r['question_id_sha256']]
                assert r['question_sha256']==c['question_sha256'] and r['gold_keys']==c['gold_keys']
                if qasper:
                    assert r['paper_key']==c['paper_key'] and r['has_nonempty_answerable_reference']==bool(c['gold_sets']) and r['fully_text_mapped_reference']==c['fully_text_mapped_reference']
                for plan in RETRIEVERS:
                    v=r['retrievers'][plan];b=base['retrievers'][plan]
                    assert v['keys']==b['keys'] and len(v['keys'])==len(set(v['keys'])) and len(v['keys'])<=20
                    assert v['evidence_identity_sha256']==b['evidence_identity_sha256']
                    assert len(v['ranks'])==len(b['ranks']) and all(abs(a-bb)<=1e-10 for a,bb in zip(v['ranks'],b['ranks']))
                    assert v['parent_metrics']==b['parent_metrics']==parent_metrics(c['gold_keys'],v['keys'])
                    if plan=='best-unit':
                        assert v['winning_source_units']==b['winning_source_units'] and [u['key'] for u in v['winning_source_units']]==v['keys']
                        assert all(type(u['sentence']) is int and u['sentence']>=-1 for u in v['winning_source_units'])
                    if qasper:
                        assert v['scores']==b['scores'] and v['selection_source_identity_sha256']==b['selection_source_identity_sha256']
                        for selector in PLANS:
                            for budget in BUDGETS:
                                key=selector+'/'+str(budget);s=v['scores'][key];assert len(s)==len(SCORE_FIELDS) and 0<=s[3]<=budget
                                assert (s[0] is not None) if c['gold_sets'] else (s[0] is None)
                                if plan=='whole-paper':assert s==prior[r['question_id_sha256']]['scores']['open-top5'][key]
                                bindings+=1
                whole=r['retrievers']['whole-paper']
                if qasper:
                    old=prior[r['question_id_sha256']]
                    assert whole['keys']==old['keys'] and whole['evidence_identity_sha256']==old['evidence_identity_sha256']
                    assert len(whole['ranks'])==len(old['ranks']) and all(abs(a-b)<=1e-10 for a,b in zip(whole['ranks'],old['ranks']))
                    assert whole['selection_source_identity_sha256']==old['selection_source_identity_sha256']['open-top5']
                elif task=='scifact-dev':assert whole['keys'][:10]==old_scifact[r['claim_id']]['keys']
                formal+=1
        allrows=[r for t in trials for r in t['queries']];group={'instances':len(first),'plans':{},'parent_pairs':{},
            'peak_rss_bytes':dist(t['peak_rss_bytes'] for t in trials),'process_wall_s':dist(t['process_wall_including_startup_s'] for t in trials),
            'Memory_bytes':build['storage']['logical_file_bytes'],'auxiliary_bytes':build['auxiliary_build']['logical_file_bytes'],
            'all_source_bytes_once':resources['total_bytes'],'coverage_pairs':{},'budget_regressions':{}}
        for plan in RETRIEVERS:
            vals=[r['retrievers'][plan] for r in first];allvals=[r['retrievers'][plan] for r in allrows]
            info={'parent':{},'coverage':{},'read_wall_s':dist(v['read_wall_s'] for v in allvals),'read_cpu_mean_s':mean(v['read_cpu_s'] for v in allvals),
                'counted_bytes':group['Memory_bytes']+group['all_source_bytes_once']+(group['auxiliary_bytes'] if plan=='best-unit' else 0)}
            for k in KS:
                key=str(k);info['parent'][key]={name:mean(v['parent_metrics'][key][name] for v in vals) for name in ('gold_document_recall','any_gold_hit','all_gold_hit')}
                if qasper:
                    paper=defaultdict(list)
                    for r in first:paper[r['paper_key']].append(r['retrievers'][plan]['parent_metrics'][key]['gold_document_recall'])
                    info['parent'][key]['paper_macro_recall']=mean(mean(v) for v in paper.values())
            if qasper:
                eligible=[r for r in first if r['has_nonempty_answerable_reference']]
                for selector in PLANS:
                    group['budget_regressions'].setdefault(plan,{})[selector]={}
                    for lo,hi in zip(BUDGETS,BUDGETS[1:]):
                        ids=[r['question_id_sha256'] for r in eligible if r['retrievers'][plan]['scores'][selector+'/'+str(lo)][0] and not r['retrievers'][plan]['scores'][selector+'/'+str(hi)][0]]
                        group['budget_regressions'][plan][selector][f'{lo}-to-{hi}']={'count':len(ids),'question_ids_sha256':ids}
                    for b in BUDGETS:
                        key=selector+'/'+str(b);s=lambda r:r['retrievers'][plan]['scores'][key];paper=defaultdict(list)
                        for r in eligible:paper[r['paper_key']].append(s(r)[0])
                        def component(r):
                            v=r['retrievers'][plan];t=v['selection_timing'][key];return v['read_wall_s']+t[0]+t[2]
                        info['coverage'][key]={'reference_questions':len(eligible),'complete_count':sum(s(r)[0] for r in eligible),
                            'question_macro_complete':mean(s(r)[0] for r in eligible),'paper_macro_complete':mean(mean(v) for v in paper.values()),
                            'best_reference_paragraph_recall':mean(s(r)[1] for r in eligible),'failure_categories':dict(Counter(s(r)[2] for r in first)),
                            'body_utf8_bytes':dist(s(r)[3] for r in first),'context_json_bytes':dist(s(r)[4] for r in first),
                            'selector_wall_s':dist(r['retrievers'][plan]['selection_timing'][key][0]+r['retrievers'][plan]['selection_timing'][key][2] for r in allrows),
                            'read_plus_selector_component_wall_s':dist(component(r) for r in allrows)}
            group['plans'][plan]=info
        for k in KS:
            key=str(k);group['parent_pairs'][key]=paired(first,lambda r:r['retrievers']['best-unit']['parent_metrics'][key]['gold_document_recall']-r['retrievers']['whole-paper']['parent_metrics'][key]['gold_document_recall'],papers=qasper)
        if qasper:
            eligible=[r for r in first if r['has_nonempty_answerable_reference']]
            for selector in PLANS:
                for b in BUDGETS:
                    key=selector+'/'+str(b)
                    group['coverage_pairs'][key]=paired(eligible,lambda r:int(r['retrievers']['best-unit']['scores'][key][0])-int(r['retrievers']['whole-paper']['scores'][key][0]),papers=True)
        result['tasks'][task]=group
    assert formal==12873 and bindings==129528
    txt=log.read_text('utf-8');assert re.search(r'Ran 205 tests',txt) and 'OK (skipped=1)' in txt and 'FAILED' not in txt
    validation={'frozen_commit':frozen,'all_54_modules_protocol_driver_match_freeze':True,'formal_question_pairs':formal,'formal_read_operations':formal*2,
        'QASPER_context_bindings':bindings,'warmup_read_operations_excluded':24,'all_rounds_keys_ranks_source_identity_and_scores_equal':True,
        'QASPER_whole_paper_all_scores_keys_ranks_identity_and_selection_match_v029':True,'SciFact_dev_whole_paper_top10_keys_match_v015':True,
        'all_original_files_bytewise_restored_and_Memory_auxiliary_trees_unchanged':True,'no_gold_to_candidate_or_selectors':True,'remote_model_calls':0,
        'new_model_answer_quality':None,'cold_cache':None,'cross_machine':None,'tests':{'run':205,'passed':204,'skipped':1,'failed':0,'log_sha256':digest(log.read_bytes())}}
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation);plot(root,result);report(root,result,validation,provenance,resources,builds)


def plot(root,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.8));x=list(range(4));tasks=list(TASKS)
    for plan,color,shift in zip(RETRIEVERS,('#496e9a','#26846f'),(-.18,.18)):
        axes[0].bar([i+shift for i in x],[100*result['tasks'][t]['plans'][plan]['parent']['5']['gold_document_recall'] for t in tasks],width=.36,label=plan,color=color)
        axes[1].plot([8,24,48],[100*result['tasks']['qasper-dev']['plans'][plan]['coverage']['lexical/'+str(b)]['question_macro_complete'] for b in BUDGETS],'-o',label=plan+' / dev',color=color)
        axes[1].plot([8,24,48],[100*result['tasks']['qasper-train']['plans'][plan]['coverage']['lexical/'+str(b)]['question_macro_complete'] for b in BUDGETS],'--o',label=plan+' / train',color=color)
    axes[0].set_xticks(x,[t.replace('-','\n') for t in tasks]);axes[0].set_ylabel('Mean gold document recall@5 (%)');axes[0].set_ylim(0,100);axes[0].legend(fontsize=8)
    axes[1].set_xlabel('Body UTF-8 budget (KB, decimal)');axes[1].set_ylabel('Complete reference exposed (%)');axes[1].set_xticks([8,24,48]);axes[1].legend(fontsize=8)
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Frozen lexical granularity comparison; evidence coverage is not model accuracy')
    fig.tight_layout();fig.savefig(root/'paragraph-retrieval.png',dpi=170);plt.close(fig)


def report(root,result,validation,provenance,resource,builds):
    text='''# v0.30 实验报告：标题/段落先行的开放检索与任务迁移

## 动机、冻结候选与判定范围

v0.29将来源已知/开放检索分开，定位为主要瓶颈。本轮只测一个预先冻结候选，
不接收目标论文身份：对标题单独一行、每个原段落单独一行，contentless FTS5
porter unicode61，沿用原问题STOP/前64唯一词/OR MATCH，无权BM25；按每篇最佳
单元分数、paper key、原句ID排序，取20篇不同论文。不是语义embedding/学习模型，
不在dev上调窗口/权重/融合。默认Memory/search/answer/CLI/HTTP不变。

辅助目录绑定精确snapshot、source-files和整DB SHA；每次查询验证原Memory索引、
辅助索引、命中原记录SHA/解析key-kind/投影指纹，不省验证换速度。旧索引遇到新
HEAD拒绝，须显式重建或选保留历史。新artifact不是Memory格式变更，只有显式API。
哈希用于完整性，不是对同时恶意改写DB和manifest的密码认证。

'''
    text+=f"协议/驱动/全部54模块冻结`{validation['frozen_commit']}`，205测试运行、204通过、1权限跳过。见[冻结协议](../../docs/PARAGRAPH-RETRIEVAL.md)。\n\n"
    text+='## 实际结论与下一步\n\n'
    for task,g in result['tasks'].items():
        v=g['parent_pairs']['5'];a=g['plans']['whole-paper'];b=g['plans']['best-unit']
        text+=f"- {task}文档召回@5：{100*a['parent']['5']['gold_document_recall']:.3f}%→{100*b['parent']['5']['gold_document_recall']:.3f}%，实例差{100*v['instance_macro_delta']:+.3f}pp，{v['wins']}赢/{v['losses']}输。查询wall中位{a['read_wall_s']['median']*1000:.2f}→{b['read_wall_s']['median']*1000:.2f}ms；候选额外aux {g['auxiliary_bytes']}B。\n"
    text+='''
QASPER dev的@5论文组区间跨零，train为正；24KB lexical完整参考分别260→284、
471→487，但train论文区间跨零。SciFact train/dev四个K均退步，claim组区间均为
负，新增任务没有支持迁移。不能仅用QASPER平均改善称通用检索收益。

候选全计aux后，QASPER dev/train计入总字节12191525/35931532B，已大于原JSON
11398686/31969387B；查询也更慢，未达到压缩与推理综合最优目标。即便不分配
完整公共运行时，仍不能声称本候选带来整个记忆系统净压缩。它只保留为显式实验
能力，不切换默认，不在当前gold上继续调权重/融合追求正结果。

下一项优先把同一冻结规则迁移到新来源任务，例如已准备但未做任务评分的公开
PubMedQA PQA-L；只做明确的自定义来源检索诊断，问题/答案字段不得进入证据索引。
不声称官方PubMedQA答案准确率，不把不同来源等同严格独立论文或盲测；先核对
原文身份/标注隔离和跨数据重叠边界，保留进一步退步的可能性。

'''
    text+='''```python
from rkv1.memory import Memory
from rkv1.memory_paragraph import ParagraphIndex
m = Memory('MEMORY')
index = ParagraphIndex.create(m, 'EXPLICIT-SIDECAR')['index']
result = index.search(m, 'scientific question', top_k=20)
```

## 数据、迁移和分母

'''
    text+=table(['任务','查询实例','唯一文本','目标claim/doc对','QASPER非空参考分母'],[[t,provenance[t]['question_instances'],provenance[t]['unique_question_strings'],provenance[t]['gold_claim_document_pairs'],provenance[t]['reference_questions']] for t in TASKS])
    text+=f"\n跨split同问句文本重叠：{provenance['overlaps']}。\n"
    text+='''
QASPER是已用公开任务，不是新独立来源/盲测/test。SciFact同已有5183篇abstract
来源，train505有证据claim用于新任务迁移；dev188复现旧基线，不称新语料。
train809/dev300全体中无证据304/112条预先排除正目标召回分母，不奖励空目标，
无官方test标签。SciFact只报文档召回/任一及全部目标命中，不评回答/证据句正确率。
其多文档recall先按claim平均，不把每个文档当独立样本。QASPER含无可答参考题的
目标论文召回与非空参考题覆盖分别计；未映射表格仍保留覆盖分母、无参考为null。

输入SHA/原tar SHA/公开源/许可见dataset-provenance.json，原文和问句/答案不发布。
Memory及辅助FTS只由原title/body构建，qas/claims/参考只供调度和独立评分，检索器
只接收问题，选择器只接收问题和已验证hits，均不接收gold身份/段落。

12轮新进程，12873正式题对、25746读取，24预热排除；QASPER129528上下文绑定。
三轮各条件keys/BM25/原文身份/原句选择/评分全一致。whole-paper逐题复现v0.29
QASPER全部六分数/原文/选择SHA及v0.15 SciFact dev前10 keys。相交命中来源逐字段
一致，所有原文件起止逐字节恢复、Memory和aux持久树逐文件大小/SHA均不变。

## 开放文档召回与迁移结果

![检索粒度与覆盖](paragraph-retrieval.png)

'''
    text+=table(['任务','K','whole recall%','unit recall%','赢/输/平','实例差pp','组差区间pp'],[
        [t,k,*[f"{100*g['plans'][p]['parent'][str(k)]['gold_document_recall']:.3f}" for p in RETRIEVERS],
         f"{v['wins']}/{v['losses']}/{v['ties']}",f"{100*v['instance_macro_delta']:.3f}",f"[{100*v['unit_bootstrap_95_percent'][0]:.3f}, {100*v['unit_bootstrap_95_percent'][1]:.3f}]"]
        for t,g in result['tasks'].items() for k in KS for v in [g['parent_pairs'][str(k)]]])
    text+='\n组区间：QASPER按论文均值重采样，SciFact按claim重采样，1000次seed20261025、排序索引24/974；仅描述该公开任务，不把重复轮次/段落当独立样本。任一/全部目标命中与论文宏平均见derived-metrics.json。\n'
    text+='\n## QASPER同预算上下文完整参考\n\n'
    text+=table(['任务','选择器/预算','whole完整参考','unit完整参考','赢/输/平','问题差pp','论文差区间pp'],[
        [t,k,*[f"{g['plans'][p]['coverage'][k]['complete_count']}/{g['plans'][p]['coverage'][k]['reference_questions']}" for p in RETRIEVERS],
         f"{v['wins']}/{v['losses']}/{v['ties']}",f"{100*v['instance_macro_delta']:.3f}",f"[{100*v['unit_bootstrap_95_percent'][0]:.3f}, {100*v['unit_bootstrap_95_percent'][1]:.3f}]"]
        for t,g in result['tasks'].items() if t.startswith('qasper') for k,v in g['coverage_pairs'].items()])
    text+='\n预算仅正文UTF8，标题/ID/JSON另计，不是完整prompt/token/账单；原句ID/locator不变。更好文档召回不必然改善有限预算覆盖；增加不同论文也改变段落排序IDF和竞争。不是模型准确率或官方QA/Evidence F1。\n'
    text+='\n## 24KB失败分解及预算回归\n\n'
    for t,g in result['tasks'].items():
        if not t.startswith('qasper'):continue
        text+=f'\n### {t}\n\n'
        reasons=sorted({reason for p in RETRIEVERS for selector in PLANS for reason in g['plans'][p]['coverage'][selector+'/24000']['failure_categories']})
        text+=table(['选择器','分类',*RETRIEVERS],[[s,r,*[g['plans'][p]['coverage'][s+'/24000']['failure_categories'].get(r,0) for p in RETRIEVERS]] for s in PLANS for r in reasons])
    text+=table(['任务','检索器','选择器','8k→24k真→假','24k→48k真→假'],[[t,p,s,v['8000-to-24000']['count'],v['24000-to-48000']['count']] for t,g in result['tasks'].items() for p,selectors in g['budget_regressions'].items() for s,v in selectors.items()])
    text+='\n所有失败、回归SHA和输题保留；同一预算均值改善不能推出逐题支配，预算改变也可能换选。\n'
    text+='\n## 实际空间、构建与查询成本\n\n'
    text+=table(['语料库','原Memory B','额外aux B','aux单元数','Memory构建wall/CPU s','aux构建wall/CPU s'],[[f,b['storage']['logical_file_bytes'],b['auxiliary_build']['logical_file_bytes'],b['auxiliary_build']['units'],f"{b['build_wall_s']:.4f}/{b['build_cpu_s']:.4f}",f"{b['auxiliary_build']['wall_including_checks_s']:.4f}/{b['auxiliary_build']['cpu_s']:.4f}"] for f,b in builds.items()])
    text+=f"\n全部54模块/HTML一次{resource['total_bytes']}B，候选模块{resource['candidate_module_bytes']}B另列。同实测安装两条件全计源；基线不计aux，候选全计index+manifest，不把新索引免费。SciFact两个任务共用同一个原库/aux，不将其当两套同时部署空间累加。\n\n"
    text+=table(['任务','检索器','计入总B','查询wall中位/p95 ms','CPU均值ms','整个进程RSS中位MiB'],[[t,p,v['counted_bytes'],f"{v['read_wall_s']['median']*1000:.3f}/{v['read_wall_s']['p95']*1000:.3f}",f"{v['read_cpu_mean_s']*1000:.3f}",f"{g['peak_rss_bytes']['median']/1048576:.2f}"] for t,g in result['tasks'].items() for p,v in g['plans'].items()])
    text+='\naux每查询收整DB SHA和原Memory校验/原记录重读，不省校验。query/selector/离线gold评分分开；词法prepare每预算完整计一次，读取+选择为组件和，不是模型端到端。全进程RSS含标注/所有策略/结果，不分摊为某策略独立RAM。公共Python/SQLite/Zlib/OS、安装/pyc/文件系统未全额分配；计入总B不是完整部署净压缩。\n'
    text+='\n## 决策与限制\n\n'
    text+='''完整报告保留全部任务/预算的正负结果；候选规则不按这些gold调整，不替换
默认检索器，不自动混合分数或补充oracle来源。学习/语义模型0、远程模型调用0，
不读取密钥；旧24次预算不扩大。若迁移或预算有退步，先分析失败与独立迁移，
不调权重重试追求正结果。真实模型质量、E3、多跳、长期对话、形式证明、冷缓存/
跨机器、掉电/并发/GC仍未测。单机暖缓存表现不能外推为这些能力或通用最优。

技术语义依据：[SQLite FTS5官方文档](https://www.sqlite.org/fts5.html)。contentless
正文列不存原内容，元数据另表；BM25数值更小表示更匹配，因此用升序排序。
'''
    (root/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--frozen',required=True)
    a=p.parse_args();analyze(a.root,a.test_log,a.frozen)
