"""Audit retained-store reader comparison and the forced-copy ablation."""
import argparse
import json
from pathlib import Path
import re

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from scripts.run_projection_queries import CASES,PLANS
from scripts.run_memory_projection import questions
from scripts.analyze_memory_history import same_queries
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root,test_log,native_library):
    read=lambda n:json.loads((root/n).read_text('utf-8'))
    checks=read('source-checksums.json');reference=read('reference-checksums.json')
    assert checks==implementation_checksums() and reference==json.loads(Path('results/v0.21.0/source-checksums.json').read_text('utf-8'))
    data=read('trials.json');rows=[json.loads(s) for s in (root/'trials.jsonl').read_text('utf-8').splitlines()]
    assert rows==data['trials'] and len(rows)==180 and data['historical_snapshot_instances_fully_reopened']==30 and data['all_persistent_fixture_files_unchanged']
    lookup={(r['case'],r['stage'],r['plan'],r['round']):r for r in rows};assert len(lookup)==180
    source=read('source-resource.json')['implementations'];native=read('native-resource.json');fixtures=read('fixture-provenance.json')
    old_source=json.loads(Path('results/v0.21.0/source-resource.json').read_text('utf-8'));assert source['v021']=={k:old_source[k] for k in ('files','total_bytes')}
    for name,info in source.items():
        assert info['total_bytes']==sum(v['bytes'] for v in info['files'].values())
        assert set(info['files'])=={'rkv1/'+n for n in (reference if name=='v021' else checks)}|{'rkv1/memory_demo.html'}
    for name,meta in source['v022']['files'].items():assert Path(name).stat().st_size==meta['bytes'] and digest(Path(name).read_bytes())==meta['sha256']
    assert digest(native_library.read_bytes())==native['sha256'] and native_library.stat().st_size==native['bytes']
    assert digest(native_library.with_name('native.json').read_bytes())==native['metadata_sha256']
    prior=json.loads(Path('results/v0.21.0/trials.json').read_text('utf-8'))['trials'];prior_lookup={(r['case'],r['plan'],r['round']):r for r in prior}
    for case,variants in fixtures.items():
        for kind,f in variants.items():
            p=prior_lookup[case,kind,0]
            assert f['tree']==p['stages'][-1]['tree'] and f['logical_file_bytes']==p['stages'][-1]['storage']['logical_file_bytes']
            assert f['stages']==[{'index':s['index'],'snapshot_id':s['build']['snapshot_id'],'source_truth':s['source_truth']} for s in p['stages']]
    formal=history=negative=warmups=0
    for row in rows:
        case,n,plan,r=row['case'],row['stage'],row['plan'],row['round'];base=lookup[case,n,'v021',r]
        fixture=fixtures[case]['budget-v3' if plan=='budget-v3' else 'projection-v4']
        assert row['snapshot_id']==fixture['stages'][n]['snapshot_id']
        assert row['tree_before']==row['tree_after']==fixture['tree']
        assert row['generation_calls']==0 and not row['cross_query_cache'] and not row['native_module_loaded']
        assert row['implementation_checksums']==(reference if plan=='v021' else checks)
        formal+=same_queries(row['queries'],base['queries'],questions(case,r))
        history+=same_queries(row['historical_queries'],base['historical_queries'],questions(case,0)[:4])
        frozen=prior_lookup[case,'projection-v4',r]['stages'][n]
        same_queries(row['queries'],frozen['query']['queries'],questions(case,r))
        same_queries(row['historical_queries'],frozen['old_snapshot_queries'],questions(case,0)[:4])
        assert row['warmup_queries']==1;warmups+=1
        if case=='synthetic-fixed':assert row['original_future_probe_absent'];negative+=1
    assert (formal,history,negative,warmups)==(6336,720,108,180)
    log=test_log.read_text('utf-8');match=re.search(r'Ran (\d+) tests',log);assert match and 'FAILED' not in log and 'OK (skipped=1)' in log
    validation={'formal_queries_audited':formal,'historical_identity_queries_audited':history,'original_future_probes':negative,
        'fresh_query_processes_and_warmups':warmups,'historical_snapshot_instances_fully_reopened':30,
        'all_keys_BM25_and_complete_source_identity_match_actual_v021_and_prior_results':True,'all_six_retained_roots_byte_identical_to_v021':True,
        'each_worker_entire_persistent_tree_unchanged':True,'query_native_module_never_loaded':True,'current_modules':len(checks),
        'reference_modules_match_actual_v021_release_measurement':True,'new_scientific_questions':0,'generation_calls':0,
        'tests':{'run':int(match[1]),'passed':int(match[1])-1,'skipped':1,'failed':0,'log_sha256':digest(test_log.read_bytes())}}
    result={'cases':{},'source_bytes_delta_once':source['v022']['total_bytes']-source['v021']['total_bytes']}
    for case in CASES:
        group={'stages':{},'costs':{},'totals':{}};result['cases'][case]=group
        native_bytes=native['bytes']+native['metadata_bytes'] if case=='official-gear' else 0
        for plan in PLANS:
            stored=fixtures[case]['budget-v3' if plan=='budget-v3' else 'projection-v4']['logical_file_bytes']
            source_bytes=source['v021' if plan=='v021' else 'v022']['total_bytes']
            group['costs'][plan]={'retained_logical_file_bytes':stored,'source_bytes_once':source_bytes,'native_fixture_generation_bytes_once':native_bytes,'counted_bytes':stored+source_bytes+native_bytes}
            group['totals'][plan]={'all_stages_batch_wall_s':summary([sum(lookup[case,n,plan,r]['batch_wall_s'] for n in range(len(fixtures[case]['projection-v4']['stages']))) for r in range(3)])}
        for entry in fixtures[case]['projection-v4']['stages']:
            n=entry['index'];group['stages'][str(n)]={}
            for plan in PLANS:
                ss=[lookup[case,n,plan,r] for r in range(3)]
                v={'query_wall_s':summary([q['wall_s'] for s in ss for q in s['queries']]),'query_cpu_s':summary([q['cpu_s'] for s in ss for q in s['queries']]),
                   'peak_rss_bytes':summary([s['peak_rss_bytes'] for s in ss]),'process_wall_including_startup_s':summary([s['process_wall_including_startup_s'] for s in ss])}
                for baseline in ('v021','lazy-copy','budget-v3'):
                    v['paired_speedup_vs_'+baseline]=summary([bq['wall_s']/q['wall_s'] for s in ss for q,bq in zip(s['queries'],lookup[case,n,baseline,s['round']]['queries'])])
                group['stages'][str(n)][plan]=v
    text='''# v0.22 保留库上的v4查询准备消融

实际发布v0.21、当前批量/延后绑定但强制复制、当前直接读取、当前v3参考，三轮。
复用v0.21 round0六个完整保留库，15状态，没有新提交/来源/索引/迁移或GC。
全部正式/历史key顺序、BM25和当前完整来源身份匹配实际v0.21及既有发布记录。

## 每阶段完整查询

'''
    text+=table(['组','阶段','读取计划','中位/p95 ms','对v0.21配对加速','对copy消融配对加速','对v3配对加速','进程峰值MiB'],[
        [case,n,p,f"{v['query_wall_s']['median']*1000:.2f}/{v['query_wall_s']['p95']*1000:.2f}",f"{v['paired_speedup_vs_v021']['median']:.3f}×",f"{v['paired_speedup_vs_lazy-copy']['median']:.3f}×",f"{v['paired_speedup_vs_budget-v3']['median']:.3f}×",f"{v['peak_rss_bytes']['median']/1048576:.2f}"]
        for case,g in result['cases'].items() for n,plans in g['stages'].items() for p,v in plans.items()])
    text+='\n## 原库全部历史与读取器源码计费\n\n'
    text+=table(['组','读取计划','不变保留库B','全RKV源/HTML一次B','旧生成原生库一次B','计入B'],[
        [case,p,v['retained_logical_file_bytes'],v['source_bytes_once'],v['native_fixture_generation_bytes_once'],v['counted_bytes']]
        for case,g in result['cases'].items() for p,v in g['costs'].items()])
    text+='''
6336正式查询（4608官方既有问题重复、1728合成），720初始快照历史身份查询，
108未来词项探针阴性。180新进程，各1预热排除；每进程前后整库逐文件大小/SHA
不变。六根最终再核对，30历史快照实例整源SHA/大小重读；含v3/v4重复。无新增
科学问题或模型调用；官方正文相同，不是真正文修订，控制不算真实科学样本。

wall/CPU含整个search及资源释放；进程启动/输入与整树核验另列，RSS含整个worker
及相同准备问题输入和核验，不称查询增量RAM。不在worker载入官方整JSON选题，
因此不与v0.21历史RSS/时序直接相除，速度比均同轮同题。当前方案批量检查全部
重绑定（含非命中），只读基础仅投影命中；有FTS删除/upsert仍复制并完整重放，
保留基础/overlay/源树/CAS/原记录/投影SHA及位移校验，不加跨查询缓存。

原存储空间完全不变，新源码分配单列。全部RKV Python/HTML各按实际reader计一次，
Gear加整个旧fixture生成库/元数据一次；查询不加载原生模块。Python/SQLite/OS、
pyc、安装/文件系统元数据未全额分配，非完整部署净压缩。本版不测提交吞吐/新
压缩收益。v3默认/v4显式与原清单格式不变，旧v0.21能读取当前新建v4文件。
本机温缓存；无真实正文修订、冷缓存/跨机器、E3、多跳、长期对话、掉电、并发写入、
GC或新推理质量结论。原始语料/问题原文/私有研究不发布。
'''
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation)
    with (root/'SUMMARY.md').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),constrained_layout=True)
    for ax,case in zip(axes,('official-fixed','official-gear','synthetic-fixed')):
        stages=(0,1,2) if case.startswith('official') else (1,3,4,8)
        for offset,plan in zip((-.27,-.09,.09,.27),PLANS):
            ax.bar([i+offset for i in range(len(stages))],[result['cases'][case]['stages'][str(n)][plan]['query_wall_s']['median']*1000 for n in stages],width=.17,label=plan)
        ax.set_title(case);ax.set_xticks(range(len(stages)),[str(n) for n in stages]);ax.set_xlabel('Retained stage');ax.set_ylabel('Median complete query ms');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('v0.22 read-only locator preparation on byte-identical v0.21 stores\nActual released reader / batch + forced copy / batch + direct / default v3; warm cache, one host')
    target=root/'projection-query-costs.png';assert not target.exists();fig.savefig(target,dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--native-library',type=Path,required=True);p.add_argument('--plot',action='store_true')
    a=p.parse_args();r=analyze(a.root,a.test_log,a.native_library)
    if a.plot:plot(a.root,r)
