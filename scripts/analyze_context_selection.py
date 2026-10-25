"""Audit exact paired contexts and paper-clustered descriptive intervals."""
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
from scripts.run_context_selection import PLANS, SEED, load
from scripts.run_units import save
from scripts.summarize_units import table


def mean(xs):
    xs=list(xs);return sum(xs)/len(xs) if xs else None


def paired(rows,budget):
    rows=[r for r in rows if r['has_nonempty_answerable_reference']];b=str(budget)
    delta=lambda r:int(r['scores']['lexical'][b]['complete_reference_exposed'])-int(r['scores']['source-order'][b]['complete_reference_exposed'])
    bypaper=defaultdict(list)
    for r in rows:bypaper[r['paper_key']].append(delta(r))
    values=[mean(v) for _,v in sorted(bypaper.items())];rng=random.Random(SEED)
    bootstrap=sorted(mean(rng.choices(values,k=len(values))) for _ in range(1000))
    return {'question_denominator':len(rows),'wins':sum(delta(r)>0 for r in rows),'losses':sum(delta(r)<0 for r in rows),
        'ties':sum(delta(r)==0 for r in rows),'question_macro_delta':mean(delta(r) for r in rows),
        'eligible_papers':len(values),'paper_macro_delta':mean(values),'paper_bootstrap_95_percent':[bootstrap[24],bootstrap[974]]}


def analyze(root,log,frozen):
    read=lambda n:json.loads((root/n).read_text('utf-8'))
    checks=read('source-checksums.json');assert checks==implementation_checksums() and len(checks)==53
    for name,sha in checks.items():assert digest(subprocess.check_output(['git','show',frozen+':rkv1/'+name]))==sha
    provenance=read('dataset-provenance.json');resources=read('source-resource.json');build=read('build.json')
    assert resources['total_bytes']==sum(v['bytes'] for v in resources['files'].values())
    assert set(resources['files'])=={'rkv1/'+n for n in checks}|{'rkv1/memory_demo.html'}
    for name,v in resources['files'].items():assert Path(name).stat().st_size==v['bytes'] and digest(Path(name).read_bytes())==v['sha256']
    result={'splits':{}};formal=0;context_checks=0
    old=json.loads(Path('results/v0.26.0/trials.json').read_text('utf-8'))['trials'][0]['queries']
    old={r['question_id_sha256']:r for r in old}
    for split,count,papers in [('dev',1005,281),('train',2593,888)]:
        raw=read(split+'-trials.json');trials=raw['trials'];assert len(trials)==3 and raw['full_original_source_verified_at_start_and_end']
        assert sorted(t['round'] for t in trials)==[0,1,2] and all(t['split']==split for t in trials)
        _,_,cases=load(split);labels={c['question_id_sha256']:c for c in cases}
        first=trials[0]['queries'];index={r['question_id_sha256']:r for r in first};assert len(index)==count and set(index)==set(labels)
        assert build[split]['full_original_source_bytewise_verified'] and build[split]['build']['indexed_records']==papers
        for t in trials:
            assert t['warmups']==1 and t['persistent_tree_unchanged'] and t['generation_calls']==0 and len(t['queries'])==count
            assert {r['question_id_sha256'] for r in t['queries']}==set(labels)
            for r in t['queries']:
                c=labels[r['question_id_sha256']];b=index[r['question_id_sha256']]
                assert r['paper_key']==c['paper_key'] and r['question_sha256']==c['question_sha256']
                assert r['has_nonempty_answerable_reference']==bool(c['gold_sets']) and r['fully_text_mapped_reference']==c['fully_text_mapped_reference']
                for key in ('keys','evidence_identity_sha256','scores','selection_identity_sha256','fully_text_mapped_reference','has_nonempty_answerable_reference'):
                    assert r[key]==b[key]
                assert all(abs(x-y)<=1e-10 for x,y in zip(r['ranks'],b['ranks'])) and len(r['ranks'])==len(b['ranks'])
                assert r['all_original_records_verified'];formal+=1
                for p in PLANS:
                    for budget in BUDGETS:
                        assert r['scores'][p][str(budget)]['visible_body_utf8_bytes']<=budget;context_checks+=1
                if split=='dev':
                    prior=old[r['question_id_sha256']]
                    assert all(r[k]==prior[k] for k in ('keys','evidence_identity_sha256'))
                    assert all(abs(x-y)<=1e-10 for x,y in zip(r['ranks'],prior['ranks']))
                    assert r['scores']['source-order']==prior['scores']
        group={'paired':{str(b):paired(first,b) for b in BUDGETS},'plans':{},'question_instances':count,'papers':papers}
        for plan in PLANS:
            group['plans'][plan]={}
            for budget in BUDGETS:
                key=str(budget);eligible=[r for r in first if r['has_nonempty_answerable_reference']];mapped=[r for r in eligible if r['fully_text_mapped_reference']]
                s=lambda r:r['scores'][plan][key]
                macro=defaultdict(list)
                for r in eligible:macro[r['paper_key']].append(s(r)['complete_reference_exposed'])
                group['plans'][plan][key]={'reference_question_denominator':len(eligible),'complete_count':sum(s(r)['complete_reference_exposed'] for r in eligible),
                    'question_macro_complete':mean(s(r)['complete_reference_exposed'] for r in eligible),'paper_macro_complete':mean(mean(v) for v in macro.values()),
                    'eligible_papers':len(macro),'fully_mapped_denominator':len(mapped),'fully_mapped_complete_count':sum(s(r)['complete_reference_exposed'] for r in mapped),
                    'best_reference_paragraph_recall':mean(s(r)['best_reference_paragraph_recall'] for r in eligible),
                    'failure_categories':dict(Counter(s(r)['failure_or_success_reason'] for r in first)),
                    'context_json_bytes':summary([s(r)['serialized_context_json_bytes'] for r in first]),
                    'selector_wall_s':summary([r['selection_timing'][plan][key]['prepare_wall_s']+r['selection_timing'][plan][key]['choose_wall_s'] for t in trials for r in t['queries']]),
                    'selector_cpu_s':summary([r['selection_timing'][plan][key]['prepare_cpu_s']+r['selection_timing'][plan][key]['choose_cpu_s'] for t in trials for r in t['queries']]),
                    'estimated_search_plus_selector_wall_s':summary([r['search_wall_s']+r['selection_timing'][plan][key]['prepare_wall_s']+r['selection_timing'][plan][key]['choose_wall_s'] for t in trials for r in t['queries']]),
                    'offline_score_wall_s':summary([r['selection_timing'][plan][key]['offline_score_wall_s'] for t in trials for r in t['queries']])}
        group['budget_regressions']={}
        for p in PLANS:
            group['budget_regressions'][p]={}
            for low,high in zip(BUDGETS,BUDGETS[1:]):
                bad=[r['question_id_sha256'] for r in first if r['scores'][p][str(low)]['complete_reference_exposed'] is True and r['scores'][p][str(high)]['complete_reference_exposed'] is False]
                group['budget_regressions'][p][f'{low}-to-{high}']={'count':len(bad),'question_id_sha256':bad}
        group['search_wall_s']=summary([r['search_wall_s'] for t in trials for r in t['queries']])
        group['peak_rss_bytes']=summary([t['peak_rss_bytes'] for t in trials])
        group['process_wall_including_startup_s']=[t['process_wall_including_startup_s'] for t in trials]
        group['actual_Memory_bytes']=build[split]['storage']['logical_file_bytes'];group['source_bytes_once']=resources['total_bytes']
        group['counted_bytes']=group['actual_Memory_bytes']+resources['total_bytes'];result['splits'][split]=group
    assert (formal,context_checks)==(10794,64764)
    textlog=log.read_text('utf-8');match=re.search(r'Ran (\d+) tests',textlog);assert match and int(match[1])==191 and 'OK (skipped=1)' in textlog and 'FAILED' not in textlog
    validation={'formal_queries':formal,'context_budget_bindings_checked':context_checks,'warmups_excluded':6,
        'dev_source_order_matches_v026_all_queries_and_budgets':True,'all_rounds_keys_BM25_and_original_and_selected_identity_and_scores_equal':True,
        'source_trees_unchanged_and_full_original_files_verified':True,'generation_calls':0,'new_model_answer_quality':None,
        'not_official_QASPER_F1':True,'measured_modules':53,'frozen_commit':frozen,'all_measured_modules_equal_frozen_commit':True,
        'tests':{'run':191,'passed':190,'skipped':1,'failed':0,'log_sha256':digest(log.read_bytes())}}
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation)
    return result


def report(root,result):
    provenance=json.loads((root/'dataset-provenance.json').read_text('utf-8'))
    resource=json.loads((root/'source-resource.json').read_text('utf-8'))
    text='''# v0.27 同检索、同预算的词法证据选择实验报告

## 问题、冻结规则与实际交付

v0.26的24KB正文预算只暴露232/927条完整参考，134题已召回且证据可文本映射却
被预算遗漏。本轮新增显式lexical段落选择API，与原source-order配对；没有修改
Memory检索、默认模型选择器、字节预算或标注分母，不调用模型。零个gold字段
参与选择。不是官方QASPER回答或Evidence F1，也不是新的模型质量结果。

lexical只在同一次检索top5原论文段落上建query-local contentless FTS5 body索引，
沿用问题前64唯一非STOP词、OR MATCH、porter unicode61/default BM25，按score/
原doc排名/原段落序破同分；无匹配按源顺序回退。使用同样skip-if-too-large，
只选完整原段落。再按原文顺序呈现，citation_id、原句ID、完整locator不改。
新score_selected逐字段绑定回原hits，篡改文本/locator/句ID/重复选择会失败。
候选不自动替换现有默认source-order。

## 固定数据、重叠与适用范围

'''
    text+=table(['split','论文','问题实例','不同问题文本','有非空可答参考','至少一组可文本映射'],[
        [s,provenance[s]['papers'],provenance[s]['question_instances'],provenance[s]['unique_question_strings'],provenance[s]['nonempty_answerable_reference_questions'],provenance[s]['fully_text_mapped_reference_questions']] for s in ('dev','train')])
    text+=f"\n跨split论文ID重叠{provenance['cross_split']['paper_id_overlap']}，问题字符串重叠{provenance['cross_split']['question_string_overlap']}。train原文曾用于CAS存储，本轮是新增任务评测，不称新科学来源/官方test或严格盲测；规则在查看train覆盖结果前冻结，不在train gold调参，不训练模型。每split独立语料库。\n"
    text+='''
dev原SHA 2ae7ee62a65b1c4225791c70de80c2aad4e8998cf1fd4f09a53103db4f21af93，
train原SHA 9458bfe76074a8fa8d1685af02bcc73537aa6d338ad20591dfaff1946bc88bf4。
来源/CC BY4.0沿用官方v0.3发布。原QASPER给定论文；这里是候选池定位后的上下文
诊断，问题可能隐含给定论文背景，不能将低开放检索召回推广到所有科学检索。
FTS仅论文正文，qas/答案/标注仅在索引外评分；原JSON成员完整保留CAS。

每split三轮新进程、共10794正式查询/6预热排除；64,764个选择器/预算绑定评分。
每query共用一次top20检索，context只top5；评分规则/8000、24000、48000正文UTF8
预算及未映射图表分母沿用v0.26，无正证据标注保持null。dev原顺序基线逐题所有
keys/BM25/完整来源SHA及三个预算分数与已发布v0.26完全相同。

## 完整参考证据覆盖与配对赢输

'''
    for split,g in result['splits'].items():
        text+='\n### '+split+'\n\n'
        text+=table(['预算B','选择器','完整参考/分母','问题宏平均','论文宏平均(论文数)','可文本映射成功/分母','最佳参考段落召回','紧凑context JSON中位B'],[
            [b,p,f"{v['complete_count']}/{v['reference_question_denominator']}",f"{v['question_macro_complete']:.4%}",f"{v['paper_macro_complete']:.4%} ({v['eligible_papers']})",
             f"{v['fully_mapped_complete_count']}/{v['fully_mapped_denominator']}",f"{v['best_reference_paragraph_recall']:.4%}",round(v['context_json_bytes']['median'])]
            for b in map(str,BUDGETS) for p in PLANS for v in [g['plans'][p][b]]])
        text+='\n'+table(['预算B','赢/输/持平','问题宏平均差pp','论文宏平均差pp','论文组bootstrap描述95%区间pp'],[
            [b,f"{v['wins']}/{v['losses']}/{v['ties']}",f"{v['question_macro_delta']*100:+.4f}",f"{v['paper_macro_delta']*100:+.4f}",
             f"[{v['paper_bootstrap_95_percent'][0]*100:+.4f}, {v['paper_bootstrap_95_percent'][1]*100:+.4f}]"] for b,v in g['paired'].items()])
        text+='\n1000次固定seed按论文重采样，先按论文平均配对差，再取排序样本索引24/974。区间仅描述这批公开数据，不把题/重复轮当独立论文，也不据此声称普遍因果提升。\n'
        text+='\n24KB全部问题的失败/成功分类：\n\n'
        reasons=sorted({r for p in PLANS for r in g['plans'][p]['24000']['failure_categories']})
        text+=table(['分类',*PLANS],[[r,*[g['plans'][p]['24000']['failure_categories'].get(r,0) for p in PLANS]] for r in reasons])
    text+='\n## 预算非单调回归\n\n'
    text+=table(['split','选择器','8k→24k完整覆盖真→假','24k→48k完整覆盖真→假'],[
        [s,p,g['budget_regressions'][p]['8000-to-24000']['count'],g['budget_regressions'][p]['24000-to-48000']['count']]
        for s,g in result['splits'].items() for p in PLANS])
    text+='\n所有回归保留问题ID SHA列表，不删题；有序greedy在不同预算可能换选段落，不能从单个预算平均改善推断逐题支配。\n'
    text+='\n## 性能与字节成本\n\n'
    text+=table(['split','预算B','选择器','selector wall中位/p95 ms','selector CPU均值ms','search+selector组件和中位/p95 ms'],[
        [s,b,p,f"{v['selector_wall_s']['median']*1000:.3f}/{v['selector_wall_s']['p95']*1000:.3f}",f"{mean(v['selector_cpu_s']['samples'])*1000:.3f}",
         f"{v['estimated_search_plus_selector_wall_s']['median']*1000:.3f}/{v['estimated_search_plus_selector_wall_s']['p95']*1000:.3f}"]
        for s,g in result['splits'].items() for b in map(str,BUDGETS) for p in PLANS for v in [g['plans'][p][b]]])
    text+='''
lexical每query离线只排序一次以复用三预算，但每预算延迟完整加一次prep，不把
prep除以3；选择器选择时间/离线gold评分时间分开，表中不含gold评分。检索实际
共用，search+selector为逐query组件时间和，不是LLM/API端到端耗时。CPU分辨率
使不少单次值为0，故另列均值/保留原样本；不把0当无CPU成本。

'''
    text+=table(['split','实际Memory B','全部RKV源一次B','合计计入B','整个进程RSS中位MiB'],[
        [s,g['actual_Memory_bytes'],g['source_bytes_once'],g['counted_bytes'],f"{g['peak_rss_bytes']['median']/1048576:.2f}"] for s,g in result['splits'].items()])
    text+=f"\n全部53模块/HTML一次计入每策略，新selector模块{resource['selector_module_bytes']}B单列。双方共用同一个不变Memory，候选临时FTS不占持久索引，但计排序CPU/整个进程RSS。进程含数据/标注/所有策略/预算/结果，不能据此分摊出某策略独立RAM。共享Python/SQLite/Zlib/OS、pyc/安装/文件系统未全额分配，不是完整部署净压缩。\n"
    text+='''
预算只扣正文UTF8，不含标题、句ID、JSON/转义/问题/system/API结构，已另列紧凑
context对象字节；仍不是完整wire prompt或token成本。候选选更多短段落时JSON
开销可能增加，不能只按正文预算声称API输入不变。原标注只供评分，不发布原文。

## 核验、结论与后续门槛

三轮全部检索keys/BM25绝对差<=1e-10、原记录身份、所选引用身份SHA与全部评分
一致；同一次检索保证两策略源相同，所有预算与选择绑定核验通过。两个初始库
起止完整原文件逐字节恢复，查询前后持久树逐文件大小/SHA不变。191测试运行、
190通过、1符号链接权限跳过。默认模型选择器仍原顺序，0新增模型请求。

'''
    for s,g in result['splits'].items():
        a=g['plans']['source-order']['24000'];b=g['plans']['lexical']['24000'];p=g['paired']['24000']
        text+=f"{s}同24KB：完整参考从{a['complete_count']}/{a['reference_question_denominator']}变为{b['complete_count']}/{b['reference_question_denominator']}，赢{p['wins']}、输{p['losses']}，问题宏平均变化{p['question_macro_delta']*100:+.4f}pp。保留所有输题与字节/时间代价。\n\n"
    text+='''
8KB的两split论文组描述区间均为正；24KB两者区间跨零，不能表述为确定的普遍
提升；48KB的train净少11条成功，并有两次跨预算真→假回归（两对预算各1题）。
新增排序约4–5ms且存在输题，不满足默认替换依据。保留显式实验候选，下一版
只提供可选CLI/API入口和固定预算选择，默认仍source-order，并以本地模拟服务
验证原句引用、请求字节与配置兼容。实际模型质量仍需另行授权新预算，不能由
覆盖提升推出回答正确率。所有负结果随发行保留，不在此批gold上继续调参。

仅本机温缓存；没有新科学回答/E3/多跳/长期会话/形式证明/冷缓存/跨机器/掉电/
并发/GC或普遍数学证明结论。每题原始无原文记录、bootstrap/赢输和协议可复核。
'''
    (root/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n')


def plot(root,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),constrained_layout=True)
    for ax,(s,g) in zip(axes,result['splits'].items()):
        for p in PLANS:
            ax.plot(BUDGETS,[g['plans'][p][str(b)]['question_macro_complete']*100 for b in BUDGETS],marker='o',label=p)
        ax.set_xticks(BUDGETS,['8k','24k','48k']);ax.set_ylim(0,100);ax.set_title(s+f" ({g['papers']} papers, {g['question_instances']} questions)")
        ax.set_xlabel('Body UTF-8 budget B, same retrieved top5 papers');ax.set_ylabel('Any complete annotated reference exposed %');ax.legend();ax.grid(alpha=.2)
    fig.suptitle('v0.27: paired lexical paragraph selection, without gold-guided selection\nSame source hits and body budgets; no model calls or official QA/F1 comparison')
    fig.savefig(root/'paired-context-selection.png',dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--frozen',required=True)
    p.add_argument('--plot',action='store_true');a=p.parse_args();r=analyze(a.root,a.test_log,a.frozen);report(a.root,r)
    if a.plot:plot(a.root,r)
