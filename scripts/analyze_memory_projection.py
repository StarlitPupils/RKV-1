"""Audit frozen paper-projection strategy trials; no model or network calls."""
import argparse
import json
from pathlib import Path
import re

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.memory_budget import DEFAULT_BUDGET
from scripts.run_memory_projection import CASES,PLANS,questions,real_inputs
from scripts.analyze_memory_history import same_queries
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root,test_log,native_library):
    read=lambda name:json.loads((root/name).read_text('utf-8'))
    checks=read('source-checksums.json');assert checks==implementation_checksums()
    rows=[json.loads(line) for line in (root/'trials.jsonl').read_text('utf-8').splitlines()]
    assert rows==read('trials.json')['trials'] and len(rows)==27
    lookup={(r['case'],r['round'],r['plan']):r for r in rows};assert len(lookup)==27
    source=read('source-resource.json');native=read('native-resource.json')
    assert set(source['files'])=={'rkv1/'+n for n in checks}|{'rkv1/memory_demo.html'}
    assert sum(v['bytes'] for v in source['files'].values())==source['total_bytes']
    for name,v in source['files'].items():assert Path(name).stat().st_size==v['bytes'] and digest(Path(name).read_bytes())==v['sha256']
    assert native_library.stat().st_size==native['bytes'] and digest(native_library.read_bytes())==native['sha256']
    meta=native_library.with_name('native.json');assert meta.stat().st_size==native['metadata_bytes'] and digest(meta.read_bytes())==native['metadata_sha256']
    provenance=read('dataset-provenance.json');assert provenance['official_QASPER_dev_releases']==real_inputs()
    assert [r['projected_paper_text_changed'] for r in provenance['changes']]==[None,0,0]
    assert [r['raw_members_changed'] for r in provenance['changes']]==[None,281,9]
    formal=history=snapshots=negative=warmups=0
    for row in rows:
        case=row['case'];official=case.startswith('official');count=3 if official else 9
        assert row['generation_calls']==0 and row['all_historical_snapshots_full_source_verified']
        assert [s['index'] for s in row['stages']]==list(range(count))
        base=lookup[case,row['round'],'rebuild'];assert row['final_CAS_tree']==base['final_CAS_tree']
        assert row['legacy_rebuild_bytes_match_v019']==(case=='official-gear' and row['plan']=='rebuild')
        for s,b in zip(row['stages'],base['stages']):
            n=s['index'];assert s['source_truth']==b['source_truth'] and s['full_current_source_bytewise_verified']
            assert s['build']['snapshot_id']==b['build']['snapshot_id'] and s['storage']['cas']==b['storage']['cas']
            formal+=same_queries(s['query']['queries'],b['query']['queries'],questions(case,row['round']))
            history+=same_queries(s['old_snapshot_queries'],b['old_snapshot_queries'],questions(case,0)[:4])
            assert s['query']['warmup_queries']==1;warmups+=1;snapshots+=1
            if official:
                p=provenance['official_QASPER_dev_releases'][n]
                assert s['source_truth']=={p['filename']:{'bytes':p['bytes'],'sha256':p['sha256']}}
                assert s['build']['indexed_records']==281
                if row['plan']!='projection-v4':assert s['checkpoint']
                elif n:
                    assert not s['checkpoint'] and s['build']['overlay_rebindings']==281 and s['build']['overlay_upserts']==0
                    assert s['build']['replay_budget']['cas_bytes']==s['build']['replay_budget']['record_bytes']==0
            else:
                assert s['original_future_probe_absent'];negative+=1
                if row['plan']=='projection-v4':
                    assert s['checkpoint']==(n in (0,5,6))
                    if n in (1,2):assert s['build']['overlay_rebindings']==160 and s['build']['overlay_upserts']==0
                    if n==5:assert s['build']['checkpoint_reason']=='budget-changes'
            if row['plan'] in ('budget-v3','projection-v4') and not s['checkpoint'] and s['build']['replay_budget'] is not None:
                meter=s['build']['replay_budget'];assert meter['reason'] is None
                assert meter['changes']<=DEFAULT_BUDGET['max_changes'] and meter['record_bytes']<=DEFAULT_BUDGET['max_record_bytes'] and meter['cas_bytes']<=DEFAULT_BUDGET['max_cas_bytes']
    assert (formal,history,snapshots,negative,warmups)==(4752,540,135,81,135)
    log=test_log.read_text('utf-8');match=re.search(r'Ran (\d+) tests',log);assert match and 'FAILED' not in log and 'OK (skipped=1)' in log
    validation={'formal_queries_audited':formal,'historical_identity_queries_audited':history,'historical_snapshot_instances_fully_reopened':snapshots,
        'original_future_probes':negative,'fresh_query_processes_and_warmups':warmups,'all_keys_BM25_and_complete_source_identity_match_rebuild':True,
        'all_CAS_trees_match_within_representation':True,'official_Gear_rebuild_persistent_bytes_match_v019':True,
        'all_official_projection_overlays_zero_FTS_replay_work':True,'all_retained_FTS_overlays_within_v020_budgets':True,
        'current_modules':len(checks),'new_scientific_questions':0,'generation_calls':0,
        'tests':{'run':int(match[1]),'passed':int(match[1])-1,'skipped':1,'failed':0,'log_sha256':digest(test_log.read_bytes())}}
    result={'cases':{}}
    for case in CASES:
        group={'stages':{},'totals':{}};result['cases'][case]=group;count=3 if case.startswith('official') else 9
        native_bytes=native['bytes']+native['metadata_bytes'] if case=='official-gear' else 0
        for n in range(count):
            group['stages'][str(n)]={}
            for plan in PLANS:
                ss=[lookup[case,r,plan]['stages'][n] for r in range(3)];bs=[lookup[case,r,'rebuild']['stages'][n] for r in range(3)];old=[lookup[case,r,'budget-v3']['stages'][n] for r in range(3)]
                assert len({s['storage']['logical_file_bytes'] for s in ss})==1
                v={'logical_file_bytes':ss[0]['storage']['logical_file_bytes'],'source_bytes_once':source['total_bytes'],'native_bytes_once':native_bytes,
                   'counted_bytes':ss[0]['storage']['logical_file_bytes']+source['total_bytes']+native_bytes,'by_directory_bytes':ss[0]['storage']['by_directory_bytes'],
                   'checkpoint':[s['checkpoint'] for s in ss],'checkpoint_reasons':[s['build']['checkpoint_reason'] for s in ss],
                   'overlay_rebindings':[s['build'].get('overlay_rebindings',0) for s in ss], 'overlay_upserts':[s['build']['overlay_upserts'] for s in ss],
                   'replay_meter':ss[0]['build']['replay_budget'],'new_index_bytes':[s['build']['new_index_bytes'] for s in ss],
                   'build_wall_s':summary([s['build_wall_s'] for s in ss]),'build_cpu_s':summary([s['build_cpu_s'] for s in ss]),
                   'paired_build_speedup_vs_budget_v3':summary([b['build_wall_s']/s['build_wall_s'] for s,b in zip(ss,old)]),
                   'query_wall_s':summary([q['wall_s'] for s in ss for q in s['query']['queries']]),
                   'query_cpu_s':summary([q['cpu_s'] for s in ss for q in s['query']['queries']]),
                   'paired_query_speedup_vs_rebuild':summary([bq['wall_s']/q['wall_s'] for s,b in zip(ss,bs) for q,bq in zip(s['query']['queries'],b['query']['queries'])]),
                   'paired_query_speedup_vs_budget_v3':summary([bq['wall_s']/q['wall_s'] for s,b in zip(ss,old) for q,bq in zip(s['query']['queries'],b['query']['queries'])]),
                   'query_process_peak_rss_bytes':summary([s['query']['peak_rss_bytes'] for s in ss]),
                   'query_process_wall_including_startup_s':summary([s['query_process_wall_including_startup_s'] for s in ss]),
                   'source_paper_hit5_counts':[sum(q['source_paper_hit5'] is True for q in s['query']['queries']) for s in ss] if case.startswith('official') else None}
                group['stages'][str(n)][plan]=v
        for plan in PLANS:
            ts=[lookup[case,r,plan] for r in range(3)]
            group['totals'][plan]={'final_counted_bytes':group['stages'][str(count-1)][plan]['counted_bytes'],
                'all_commits_wall_s':summary([sum(s['build_wall_s'] for s in t['stages']) for t in ts]),
                'checkpoint_versions':[[s['index'] for s in t['stages'] if s['checkpoint']] for t in ts],
                'build_process_peak_rss_bytes':summary([t['build_process_peak_rss_bytes'] for t in ts])}
    text='''# v0.21 论文投影与精确定位分离对照

完整重建、v0.20预算v3、显式投影v4同源码三轮；真实QASPER三发布分别固定/Gear，
正文投影相同，不是真实论文正文修订。160论文9状态合成控制另列，非科学样本。
全部源/历史保留，无GC。指纹表、每版本精确定位overlay及所有RKV源码资源完整计费。

## 保留全部历史成本与提交

'''
    text+=table(['组','策略','最终计入B','总提交wall中位s','基础数（三轮）'],[
        [case,p,v['final_counted_bytes'],f"{v['all_commits_wall_s']['median']:.3f}",str([len(x) for x in v['checkpoint_versions']])]
        for case,g in result['cases'].items() for p,v in g['totals'].items()])
    text+='\n## 每阶段完整读写成本\n\n'
    text+=table(['组','阶段','策略','新索引B（三轮）','重绑定数','FTS upsert数','查询中位/p95 ms','对v3配对加速','峰值MiB'],[
        [case,n,p,str(v['new_index_bytes']),str(v['overlay_rebindings']),str(v['overlay_upserts']),f"{v['query_wall_s']['median']*1000:.2f}/{v['query_wall_s']['p95']*1000:.2f}",f"{v['paired_query_speedup_vs_budget_v3']['median']:.3f}×",f"{v['query_process_peak_rss_bytes']['median']/1048576:.2f}"]
        for case,g in result['cases'].items() for n,plans in g['stages'].items() for p,v in plans.items()])
    text+='''
4752正式查询、540历史完整身份查询的key顺序、BM25（绝对差<=1e-10）、title/
sentences/完整locator摘要均对齐重建。81初始快照未来词项探针阴性，135历史快照
实例全源SHA/大小重开核验，当前源逐字节一致。同表示CAS树相同；查询不改持久树。
135新查询进程各一次预热排除，wall含整个search/清理，启动另列；提交包含投影
SHA/预算/全源校验/HEAD发布，源准备不计。配对比值逐问题/轮后取中位，RSS含整个
进程/输入。实例含多策略/轮次重复。64官方既有问题不算新增科学样本，来源论文@5
仅全局检索诊断，不是QASPER答案质量；0新模型调用/科学问题。

所有RKV Python模块与HTML计一次，Gear另计整个旧实测库/原元数据；固定无原生
依赖。Python/SQLite/OS、pyc、安装及文件系统元数据未全额分配，非完整部署净压缩。
同源策略比较，不把旧版耗时或其他成本分配口径直接相除。完整基础和定位重绑定
都有额外读/写/内存成本，不能由节省FTS重建推导查询或所有负载更快。

v4显式选择，默认仍v0.20预算v3。新应用清单v4需新读取器，旧v0.20拒绝；旧清单
v1/v2/v3继续可读写，归档v1–v6/CAS1不变。无自动迁移/旧快照重建。重绑定最多4096；
FTS重放仍限32变化/256KiB记录/2MiB CAS并保留25%/256位移规则，不是wall/RSS保证。
仅本机温缓存；无真实正文修订、E3、多跳、长期对话、冷缓存/跨机器、掉电、并发
写入、GC或新模型质量结论。下一步独立真实正文修订及定位准备热点仍须验证。
原始科学语料/问答内容、私有研究文档不进入Release。
'''
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation)
    with (root/'SUMMARY.md').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(12,7),constrained_layout=True)
    for col,case in enumerate(('official-fixed','official-gear')):
        g=result['cases'][case];ax=axes[0,col]
        ax.bar(list(PLANS),[g['totals'][p]['final_counted_bytes']/1e6 for p in PLANS],color=['#4477aa','#ee7733','#228833'])
        ax.set_title(case+' — retained history');ax.set_ylabel('Counted MB');ax.grid(axis='y',alpha=.2)
        ax=axes[1,col]
        for offset,p in zip((-.24,0,.24),PLANS):
            ax.bar([n+offset for n in range(3)],[g['stages'][str(n)][p]['query_wall_s']['median']*1000 for n in range(3)],width=.23,label=p)
        ax.set_xticks(range(3),['v0.1','v0.2','v0.3']);ax.set_xlabel('Original QASPER dev release');ax.set_ylabel('Median complete query ms');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('v0.21: exact current locators, unchanged paper text\nSame inputs and global BM25; warm cache, one host; all history retained')
    target=root/'projection-costs.png';assert not target.exists();fig.savefig(target,dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--native-library',type=Path,required=True);p.add_argument('--plot',action='store_true')
    a=p.parse_args();r=analyze(a.root,a.test_log,a.native_library)
    if a.plot:plot(a.root,r)
