"""All-dev paper retrieval and annotated-context exposure, without generation."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import subprocess

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.qasper_audit import BUDGETS
from scripts.run_qasper_coverage import load
from scripts.run_units import save
from scripts.summarize_units import table


def mean(values):
    values=list(values)
    return sum(values)/len(values) if values else None


def paper_macro(rows, fn, eligible=lambda r: True):
    groups=defaultdict(list)
    for r in rows:
        if eligible(r):groups[r['paper_key']].append(fn(r))
    return {'eligible_papers':len(groups),'mean':mean(mean(v) for v in groups.values())}


def analyze(root, log, frozen):
    read=lambda n:json.loads((root/n).read_text('utf-8'))
    checks=read('source-checksums.json');assert checks==implementation_checksums() and len(checks)==52
    for name,sha in checks.items():assert digest(subprocess.check_output(['git','show',frozen+':rkv1/'+name]))==sha
    all_trials=read('trials.json');trials=all_trials['trials'];assert len(trials)==3
    assert all_trials['formal_queries']==3015 and all_trials['warmups_excluded']==3 and all_trials['full_original_source_verified_at_start_and_end']
    _,cases=load();labels={c['question_id_sha256']:c for c in cases}
    assert len(labels)==1005
    first=trials[0]['queries'];baseline={r['question_id_sha256']:r for r in first};assert set(baseline)==set(labels)
    for t in trials:
        assert t['warmups']==1 and t['persistent_tree_unchanged'] and t['generation_calls']==0 and len(t['queries'])==1005
        assert {r['question_id_sha256'] for r in t['queries']}==set(labels)
        for r in t['queries']:
            b=baseline[r['question_id_sha256']];c=labels[r['question_id_sha256']]
            assert r['paper_key']==c['paper_key'] and r['question_sha256']==c['question_sha256']
            for field in ('keys','evidence_identity_sha256','scores','answerability','has_nonempty_answerable_reference','fully_text_mapped_reference','annotation_count','unmapped_evidence_strings'):
                assert r[field]==b[field]
            assert len(r['ranks'])==len(b['ranks']) and all(abs(x-y)<=1e-10 for x,y in zip(r['ranks'],b['ranks']))
            assert r['all_original_records_verified']
            assert r['has_nonempty_answerable_reference']==bool(c['gold_sets'])
            assert r['fully_text_mapped_reference']==c['fully_text_mapped_reference']
            for budget in BUDGETS:
                s=r['scores'][str(budget)]
                assert s['visible_body_utf8_bytes']<=budget
                if not c['gold_sets']:assert s['complete_reference_exposed'] is None and s['best_reference_paragraph_recall'] is None
                else:assert type(s['complete_reference_exposed']) is bool and 0<=s['best_reference_paragraph_recall']<=1
    source=read('source-resource.json');assert set(source['files'])=={'rkv1/'+n for n in checks}|{'rkv1/memory_demo.html'}
    assert source['total_bytes']==sum(v['bytes'] for v in source['files'].values()) and source['native_specific_bytes']==source['model_bytes']==0
    for name,v in source['files'].items():assert Path(name).stat().st_size==v['bytes'] and digest(Path(name).read_bytes())==v['sha256']
    build=read('build.json');assert build['build']['indexed_records']==281 and build['full_original_source_bytewise_verified']
    ranks=lambda r:next((i+1 for i,k in enumerate(r['keys']) if k==r['paper_key']),None)
    retrieval={}
    for k in (1,5,10,20):
        found=lambda r:bool(ranks(r) and ranks(r)<=k)
        retrieval[str(k)]={'question_instances':1005,'hits':sum(found(r) for r in first),'question_macro':mean(found(r) for r in first),'paper_macro':paper_macro(first,found)}
    retrieval['MRR20']={'question_macro':mean(1/ranks(r) if ranks(r) else 0 for r in first),'paper_macro':paper_macro(first,lambda r:1/ranks(r) if ranks(r) else 0)}
    refs=[r for r in first if r['has_nonempty_answerable_reference']]
    mapped=[r for r in refs if r['fully_text_mapped_reference']]
    coverage={}
    for budget in BUDGETS:
        key=str(budget);gs=lambda r:r['scores'][key]
        complete=lambda r:gs(r)['complete_reference_exposed']
        coverage[key]={'reference_question_denominator':len(refs),'complete_count':sum(complete(r) for r in refs),
            'question_macro_complete':mean(complete(r) for r in refs),'paper_macro_complete':paper_macro(refs,complete),
            'best_reference_paragraph_recall':mean(gs(r)['best_reference_paragraph_recall'] for r in refs),
            'fully_mapped_question_denominator':len(mapped),'fully_mapped_complete_count':sum(complete(r) for r in mapped),
            'fully_mapped_question_macro_complete':mean(complete(r) for r in mapped),
            'all_question_failure_categories':dict(Counter(gs(r)['failure_or_success_reason'] for r in first)),
            'visible_body_utf8_bytes':summary([gs(r)['visible_body_utf8_bytes'] for r in first]),
            'serialized_context_json_bytes':summary([gs(r)['serialized_context_json_bytes'] for r in first])}
    regressions={}
    for low,high in zip(BUDGETS,BUDGETS[1:]):
        bad=[r for r in refs if r['scores'][str(low)]['complete_reference_exposed'] and not r['scores'][str(high)]['complete_reference_exposed']]
        regressions[f'{low}-to-{high}']={'count':len(bad),'question_id_sha256':[r['question_id_sha256'] for r in bad]}
    log_text=log.read_text('utf-8');match=re.search(r'Ran (\d+) tests',log_text)
    assert match and int(match[1])==188 and 'OK (skipped=1)' in log_text and 'FAILED' not in log_text
    validation={'formal_queries':3015,'question_id_instances':1005,'corpus_papers':281,'warmups_excluded':3,
        'all_rounds_keys_BM25_identity_and_context_scores_identical':True,'all_original_hit_records_verified':True,
        'persistent_tree_unchanged':True,'original_source_full_bytewise_verified_at_start_and_end':True,
        'generation_calls':0,'new_model_answer_quality':None,'not_official_QASPER_F1':True,'measured_modules':52,
        'frozen_commit':frozen,'all_measured_modules_equal_frozen_commit':True,
        'tests':{'run':188,'passed':187,'skipped':1,'failed':0,'log_sha256':digest(log.read_bytes())}}
    result={'retrieval':retrieval,'coverage':coverage,'budget_regressions':regressions,'timing':{
        'search_top20_wall_s':summary([r['search_wall_s'] for t in trials for r in t['queries']]),
        'search_top20_cpu_s':summary([r['search_cpu_s'] for t in trials for r in t['queries']]),
        'scoring_wall_s':summary([r['scoring_wall_s'] for t in trials for r in t['queries']]),
        'process_wall_including_startup_s':[t['process_wall_including_startup_s'] for t in trials],
        'peak_rss_bytes':summary([t['peak_rss_bytes'] for t in trials])},
        'storage':{'logical_file_bytes':build['storage']['logical_file_bytes'],'by_directory_bytes':build['storage']['by_directory_bytes'],
            'source_bytes_once':source['total_bytes'],'counted_bytes':build['storage']['logical_file_bytes']+source['total_bytes'],
            'not_complete_deployment':True}}
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation)
    p=read('dataset-provenance.json');tm=result['timing'];st=result['storage']
    text=f'''# v0.26 全dev离线检索与证据上下文覆盖实验报告

## 实验问题与交付

片段索引预检不足以支持集成后，本轮转回E4任务诊断：现有原文证据链能否检索到
问题所属论文，且24KB正文预算能否实际暴露人工标注的证据段落？新增独立离线
评分器，不改变检索或上下文选择算法，不调用模型。

固定QASPER v0.3 dev原JSON 11398686B/SHA 2ae7ee62a65b1c4225791c70de80c2aad4e8998cf1fd4f09a53103db4f21af93。
281论文/1005 question_id，共{p['unique_question_strings']}个不同问题字符串；与先前64题
重叠{p['overlap_question_strings']}个字符串，新增{p['new_question_strings_vs_previous_64']}个不同字符串。
语料论文已使用，不算新独立论文；多问题/标注及三轮重复不是独立论文样本。
原QASPER给定论文，这里是281篇候选池定位＋上下文诊断，不是官方Answer/Evidence F1。

## 证据与标签分离

FTS仅title/abstract/full_text，原JSON成员完整存CAS，qas/答案/标注不进检索。
每次只输入question，不传gold论文或证据。独立评分器只用非空且unanswerable=False
的参考evidence组；只strip外侧空白后精确匹配原段落，图表/FLOAT SELECTED/无法
映射项仍在分母。找到论文不等于能回答；全不可答/无正证据标注题不奖励覆盖。

标注类型：{p['answerability']}。有非空可答参考{len(refs)}题，其中至少一整组可
映射文本{len(mapped)}题；无法映射字符串共{p['unmapped_evidence_strings_including_repeated_annotations']}次，含多标注重复。

## 论文召回与排序

'''
    text+=table(['topK','命中/1005','问题宏平均','论文宏平均/281'],[[k,retrieval[str(k)]['hits'],f"{retrieval[str(k)]['question_macro']:.4%}",f"{retrieval[str(k)]['paper_macro']['mean']:.4%}"] for k in (1,5,10,20)])
    text+=f"\nMRR@20：问题宏平均{retrieval['MRR20']['question_macro']:.6f}，论文宏平均{retrieval['MRR20']['paper_macro']['mean']:.6f}。只认来源论文，不具备全部相关论文标注，不能算完整precision或科学回答正确率。\n"
    text+='\n## 三种正文预算下的标注证据暴露\n\n'
    text+=table(['正文UTF8预算B','完整参考可见/有标注题','问题宏平均','论文宏平均(论文数)','完全可映射子集成功/分母','最佳参考段落召回','context JSON中位B'],[
        [b,f"{v['complete_count']}/{v['reference_question_denominator']}",f"{v['question_macro_complete']:.4%}",f"{v['paper_macro_complete']['mean']:.4%} ({v['paper_macro_complete']['eligible_papers']})",
         f"{v['fully_mapped_complete_count']}/{v['fully_mapped_question_denominator']}",f"{v['best_reference_paragraph_recall']:.4%}",round(v['serialized_context_json_bytes']['median'])] for b,v in coverage.items()])
    text+='\n算法完全沿用exposed_hits，top5论文依排名、段落依原顺序，遇到过长段落跳过；预算只扣正文UTF8字节。标题/ID/JSON/完整prompt及token数另有成本，不称24KB完整API预算。覆盖任一完整参考也不证明科学蕴含或回答质量。\n'
    text+='\n### 所有1005题的失败/成功分类\n\n'
    reasons=sorted({x for v in coverage.values() for x in v['all_question_failure_categories']})
    text+=table(['分类',*map(str,BUDGETS)],[[reason,*[coverage[str(b)]['all_question_failure_categories'].get(reason,0) for b in BUDGETS]] for reason in reasons])
    text+='\n### 预算增大反而失去完整证据\n\n'
    text+=table(['预算变化','完整覆盖真→假题数'],[[name,v['count']] for name,v in regressions.items()])
    text+='\n非单调检查是预先固定的诊断；原始SHA问题ID列表见derived-metrics。没有为消除回归修改算法或按结果删题。\n'
    text+=f'''
## 性能、实际字节与核验

3轮新进程/3015正式top20 search，3预热排除。检索wall中位/p95
{tm['search_top20_wall_s']['median']*1000:.3f}/{tm['search_top20_wall_s']['p95']*1000:.3f}ms；
独立评分wall中位{tm['scoring_wall_s']['median']*1000:.3f}ms。进程RSS中位
{tm['peak_rss_bytes']['median']/1048576:.2f}MiB，含输入/标注/结果；进程启动/准备另列。
top20会恢复更多完整原成员，不与历史top5/top10耗时直接算加速。

实际Memory逻辑字节{st['logical_file_bytes']}B，目录{st['by_directory_bytes']}；
全部52模块/HTML源一次{st['source_bytes_once']}B，合计计入{st['counted_bytes']}B。
无需Gear/embedding/模型专属资源；公共Python/SQLite/Zlib/OS、pyc/安装/文件系统
未全额分配，不是完整部署净压缩。原JSON同时含已存在标注，但标签不进FTS，不能
将对整个带标注文件的存储比当作无标注生产语料的压缩性能。

三轮每题keys/BM25绝对差<=1e-10/完整原记录身份SHA/覆盖结果全部一致；每次命中
仍由Memory检查原CAS与记录SHA/身份。整库读前后逐文件大小/SHA不变，全源起止
重开与原文件逐字节一致。188测试运行、187通过、1符号链接权限跳过。

## 结论与后续实验门槛

本轮把论文召回、图表/文本映射缺失和预算遗漏分开，提供整个1005题基线。下一
轮只在冻结本报告后提出新选择器，并对相同检索结果和严格相同正文预算配对，
保留完整来源/原句ID、JSON实际成本、所有失败题与非单调检查。改进应来自问题
相关证据选择，而非把gold证据直接塞入上下文。新规则须先冻结，再测留出/全量
泛化；不能由覆盖提升声称模型回答已改善。

0模型调用，0新增模型质量/E3/多跳/长期对话/形式证明/冷缓存/跨机器/掉电/并发/
GC结论。保留公开固定来源/SHA/无原文测量，问题/证据原文不随发行发布。
'''
    (root/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n')
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.7),constrained_layout=True)
    ks=(1,5,10,20);axes[0].plot(ks,[result['retrieval'][str(k)]['question_macro']*100 for k in ks],marker='o',label='Question macro (1005)')
    axes[0].plot(ks,[result['retrieval'][str(k)]['paper_macro']['mean']*100 for k in ks],marker='s',label='Paper macro (281)')
    axes[0].set_xticks(ks);axes[0].set_xlabel('Retrieved papers K');axes[0].set_ylabel('Source-paper hit rate %');axes[0].legend(fontsize=8);axes[0].set_ylim(0,100)
    bs=list(BUDGETS)
    axes[1].plot(bs,[result['coverage'][str(b)]['question_macro_complete']*100 for b in bs],marker='o',label='All nonempty answerable references')
    axes[1].plot(bs,[result['coverage'][str(b)]['fully_mapped_question_macro_complete']*100 for b in bs],marker='s',label='At least one fully text-mapped reference')
    axes[1].set_xticks(bs,['8k','24k','48k']);axes[1].set_xlabel('Body UTF-8 budget B, top5 papers');axes[1].set_ylabel('Complete reference exposed %');axes[1].set_ylim(0,100);axes[1].legend(fontsize=8)
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle('v0.26: all-dev QASPER retrieval and annotated evidence exposure\n281-paper candidate pool; no generation or official QA/F1 comparison')
    fig.savefig(root/'qasper-retrieval-coverage.png',dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--frozen',required=True);p.add_argument('--plot',action='store_true')
    a=p.parse_args();r=analyze(a.root,a.test_log,a.frozen)
    if a.plot:plot(a.root,r)
