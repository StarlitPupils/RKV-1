"""Offline audit of replay-budget policy controls; no requests or tuning."""
import argparse
import json
from pathlib import Path
import re

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.memory_budget import DEFAULT_BUDGET
from scripts.run_replay_budget import CASES,PLANS,COUNT_ONLY,questions,storage_mode
from scripts.run_memory_history import LONG_QUERY_STAGES
from scripts.analyze_memory_history import same_queries
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root,test_log,native_library):
    read=lambda name:json.loads((root/name).read_text('utf-8'))
    checks=read('source-checksums.json');assert checks==implementation_checksums()
    rows=[json.loads(line) for line in (root/'trials.jsonl').read_text('utf-8').splitlines()]
    assert rows==read('trials.json')['trials'] and len(rows)==48
    lookup={(r['case'],r['round'],r['plan']):r for r in rows};assert len(lookup)==48
    source=read('source-resource.json');native=read('native-resource.json')
    assert sum(v['bytes'] for v in source['files'].values())==source['total_bytes']
    assert set(source['files'])=={'rkv1/'+n for n in checks}|{'rkv1/memory_demo.html'}
    for name,v in source['files'].items():assert Path(name).stat().st_size==v['bytes'] and digest(Path(name).read_bytes())==v['sha256']
    assert native_library.stat().st_size==native['bytes'] and digest(native_library.read_bytes())==native['sha256']
    meta=native_library.with_name('native.json');assert meta.stat().st_size==native['metadata_bytes'] and digest(meta.read_bytes())==native['metadata_sha256']
    formal=historical=negative=snapshots=warmups=0
    for row in rows:
        case=row['case'];regression=case.startswith('regression');count=101 if regression else 5
        assert len(row['stages'])==count and row['generation_calls']==0 and row['all_historical_snapshots_full_source_verified']
        baseline=lookup[case,row['round'],'rebuild'];assert row['final_CAS_tree']==baseline['final_CAS_tree']
        assert row['legacy_persistent_bytes_match_v019']==(case=='regression-gear' and row['plan'] in ('legacy','rebuild'))
        for stage,base in zip(row['stages'],baseline['stages']):
            n=stage['index'];assert n==base['index'] and stage['source_truth']==base['source_truth'] and stage['full_current_source_bytewise_verified']
            assert stage['build']['snapshot_id']==base['build']['snapshot_id'] and stage['storage']['cas']==base['storage']['cas']
            if row['plan']=='rebuild':assert stage['checkpoint']
            if row['plan']=='legacy':assert stage['checkpoint']==(n in ((0,43,80) if regression else (0,)))
            if row['plan'] in ('bounded','count-only'):
                meter=stage['build']['replay_budget']
                if not stage['checkpoint']:
                    assert meter and meter['reason'] is None
                    assert meter['changes']<=meter['limits']['max_changes'] and meter['record_bytes']<=meter['limits']['max_record_bytes'] and meter['cas_bytes']<=meter['limits']['max_cas_bytes']
                if regression and n==42:assert stage['checkpoint'] and stage['build']['checkpoint_reason']=='budget-changes'
                if not regression and n==2:
                    if row['plan']=='bounded':assert stage['checkpoint'] and stage['build']['checkpoint_reason']==('budget-record-bytes' if case=='large-record' else 'budget-cas-bytes')
                    else:assert not stage['checkpoint']
                if meter:assert meter['limits']==(DEFAULT_BUDGET if row['plan']=='bounded' else COUNT_ONLY)
            historical+=same_queries(stage['old_snapshot_queries'],base['old_snapshot_queries'],questions(case,0)[:4])
            assert stage['original_future_probe_absent'];negative+=1;snapshots+=1
            if not regression or n in LONG_QUERY_STAGES:
                q=stage['query'];assert q['generation_calls']==0 and q['warmup_queries']==1
                formal+=same_queries(q['queries'],base['query']['queries'],questions(case,row['round']));warmups+=1
            else:assert stage['query'] is None
    assert (formal,historical,negative,snapshots,warmups)==(4032,10176,2544,2544,336)
    log=test_log.read_bytes();text=log.decode('utf-8-sig');ran=re.search(r'Ran (\d+) tests',text);ok=re.search(r'^OK(?: \(skipped=(\d+)\))?\r?$',text,re.M)
    assert ran and ok and 'FAILED (' not in text
    validation={'formal_queries_audited':formal,'historical_identity_queries_audited':historical,'original_future_probes':negative,
        'historical_snapshot_instances_fully_reopened':snapshots,'fresh_query_processes_and_warmups':warmups,
        'all_keys_BM25_and_complete_source_identity_match_rebuild':True,'all_CAS_trees_match_within_same_representation':True,
        'legacy_Gear_and_rebuild_persistent_bytes_match_v019':True,'all_bounded_retained_overlays_within_record_and_CAS_budgets':True,
        'current_modules':len(checks),'new_scientific_questions':0,'generation_calls':0,
        'tests':{'run':int(ran[1]),'passed':int(ran[1])-int(ok[1] or 0),'skipped':int(ok[1] or 0),'failed':0,'log_sha256':digest(log)}}
    result={'cases':{},'validation':validation,'source_resource':source,'native_resource':native,'new_model_quality':None,'cold_cache':None,'cross_machine':None}
    for case in CASES:
        group={'stages':{},'totals':{}};result['cases'][case]=group
        count=101 if case.startswith('regression') else 5;backend=storage_mode(case)[2]
        native_bytes=native['bytes']+native['metadata_bytes'] if backend=='rust' else 0
        for n in range(count):
            group['stages'][str(n)]={}
            for plan in PLANS:
                ss=[lookup[case,r,plan]['stages'][n] for r in range(3)];bs=[lookup[case,r,'rebuild']['stages'][n] for r in range(3)]
                legacy=[lookup[case,r,'legacy']['stages'][n] for r in range(3)]
                assert len({s['storage']['logical_file_bytes'] for s in ss})==1
                v={'logical_file_bytes':ss[0]['storage']['logical_file_bytes'],'source_bytes_once':source['total_bytes'],'native_bytes_once':native_bytes,
                   'counted_bytes':ss[0]['storage']['logical_file_bytes']+source['total_bytes']+native_bytes,
                   'by_directory_bytes':ss[0]['storage']['by_directory_bytes'],'checkpoint':[s['checkpoint'] for s in ss],
                   'checkpoint_reasons':[s['build'].get('checkpoint_reason') for s in ss],'replay_meter':ss[0]['build']['replay_budget'],
                   'new_index_bytes':[s['build']['new_index_bytes'] for s in ss],
                   'build_wall_s':summary([s['build_wall_s'] for s in ss]),'build_cpu_s':summary([s['build_cpu_s'] for s in ss]),
                   'paired_build_speedup_vs_rebuild':summary([b['build_wall_s']/s['build_wall_s'] for s,b in zip(ss,bs)])}
                if ss[0]['query'] is not None:
                    v['query_wall_s']=summary([q['wall_s'] for s in ss for q in s['query']['queries']])
                    v['paired_query_speedup_vs_rebuild']=summary([bq['wall_s']/q['wall_s'] for s,b in zip(ss,bs) for q,bq in zip(s['query']['queries'],b['query']['queries'])])
                    v['paired_query_speedup_vs_legacy']=summary([bq['wall_s']/q['wall_s'] for s,b in zip(ss,legacy) for q,bq in zip(s['query']['queries'],b['query']['queries'])])
                    v['query_process_peak_rss_bytes']=summary([s['query']['peak_rss_bytes'] for s in ss])
                    v['query_process_wall_including_startup_s']=summary([s['query_process_wall_including_startup_s'] for s in ss])
                group['stages'][str(n)][plan]=v
        for plan in PLANS:
            ts=[lookup[case,r,plan] for r in range(3)]
            group['totals'][plan]={'final_counted_bytes':group['stages'][str(count-1)][plan]['counted_bytes'],
                'all_commits_wall_s':summary([sum(s['build_wall_s'] for s in t['stages']) for t in ts]),
                'checkpoint_versions':[[s['index'] for s in t['stages'] if s['checkpoint']] for t in ts],
                'build_process_peak_rss_bytes':summary([t['build_process_peak_rss_bytes'] for t in ts])}
    text='''# v0.20 重放预算策略对照

同源码比较全量重建、旧25%/256策略、32变化数＋宽字节限消融、新三预算策略。
新默认预算32变化/256KiB重放原记录/2MiB逐次CAS解码工作；旧比例/位移上限仍保留。
限制工作量而非wall/RSS，所有来源校验与全库BM25保留，无新缓存或模型调用。

四组合成控制、各四策略三轮：已见100更新的Gear回归及默认固定64KiB复测；新增
96KiB大记录和固定1MiB块放大控制各5状态，均为定向试验而非盲测/真实科学数据。
Gear的旧策略/重建每阶段持久字节匹配v0.19，避免改变输入掩盖原问题；同轮四策略
共享代码，不直接把整版v0.19/v0.20历史耗时相除。

## 保留全部历史成本与提交

'''
    text+=table(['控制','策略','最终计入B','总提交wall中位s','各轮基础数'],[
        [case,p,v['final_counted_bytes'],f"{v['all_commits_wall_s']['median']:.3f}",str([len(a) for a in v['checkpoint_versions']])]
        for case,g in result['cases'].items() for p,v in g['totals'].items()])
    text+='\n## 逐阶段读写与预算\n\n'
    text+=table(['控制','阶段','策略','检查点原因（三轮）','新索引B（三轮）','查询中位/p95 ms','对旧策略配对加速','对重建配对加速','查询进程峰值MiB'],[
        [case,n,p,str(v['checkpoint_reasons']),str(v['new_index_bytes']),f"{v['query_wall_s']['median']*1000:.2f}/{v['query_wall_s']['p95']*1000:.2f}",
         f"{v['paired_query_speedup_vs_legacy']['median']:.3f}×",f"{v['paired_query_speedup_vs_rebuild']['median']:.3f}×",f"{v['query_process_peak_rss_bytes']['median']/1048576:.2f}"]
        for case,g in result['cases'].items() for n,plans in g['stages'].items() for p,v in plans.items() if 'query_wall_s' in v])
    text+='''
完整计入所有RKV Python源码及打包HTML一次，Gear组另计整个实测DLL/元数据；固定
组没有原生依赖。Python/SQLite/OS、pyc、安装/文件系统元数据未全额分配，非完整
部署净压缩；此口径与v0.19的四模块不同，不直接计算版本压缩升级百分比。

4032正式、10176历史身份查询与重建的key顺序、BM25（绝对差<=1e-10）、原文/完整
定位摘要一致；2544原始快照未来探针阴性，2544历史快照实例全源大小/SHA重读，
当前源逐字节一致。同表示CAS树相同，查询前后持久树不变。实例含多轮/多策略重复。
336新查询进程，各一次预热排除统计。query计整个search与清理，启动另列；commit
包含预算估计/验证/HEAD发布，源生成不计。RSS含整个进程/输入，配对比值逐问题/
轮计算后取中位。仅本机温缓存；四组控制不增加科学问题或模型质量证据。

新建库默认compact-budget-v3；旧v3库不自动切换，memory-budget只原子更新未来
writer策略，不重建旧视图/改HEAD，旧高代价快照仍可能慢。旧v0.19读取器可读新
v3视图，旧writer不能写新profile。物理归档/CAS/清单不变，无迁移或GC。定向控制
不能证明所有负载更优，预算不限制索引SHA、SQLite复制/排序、位移扫描与实际命中
读取等总耗时；空间、提交、查询和RSS分别判断。无E3、冷缓存/跨机器、掉电、并发
写入、长期对话或新模型调用。原始科学输入/私有研究不进入Release。
'''
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation)
    with (root/'SUMMARY.md').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13,4.5),constrained_layout=True)
    for case,ax in zip(('regression-fixed','regression-gear'),axes):
        stages=result['cases'][case]['stages']
        for offset,plan in zip((-.27,-.09,.09,.27),PLANS):
            ax.bar([i+offset for i in range(4)],[stages[str(n)][plan]['query_wall_s']['median']*1000 for n in (40,42,43,100)],width=.17,label=plan)
        ax.set_xticks(range(4),['40','42','43','100']);ax.set_yscale('log');ax.set_xlabel('Synthetic update');ax.set_ylabel('Median query (ms, log scale)')
        ax.set_title(case);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('v0.20 replay budget policies: same evidence and global BM25\nWarm cache, one host; old-view work cliff, no cross-query cache')
    path=root/'replay-costs.png';assert not path.exists();fig.savefig(path,dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--native-library',type=Path,required=True);p.add_argument('--plot',action='store_true')
    a=p.parse_args();r=analyze(a.root,a.test_log,a.native_library)
    if a.plot:plot(a.root,r)
