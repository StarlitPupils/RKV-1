"""Audit independent true-body revisions, including whole-record limits."""
import argparse
import json
from pathlib import Path
import re

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from scripts.run_paper_revisions import CASES,PLANS,questions,inputs,schedule
from scripts.analyze_memory_history import same_queries
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root,test_log,native_library):
    read=lambda n:json.loads((root/n).read_text('utf-8'))
    checks=read('source-checksums.json');assert checks==implementation_checksums()
    rows=[json.loads(s) for s in (root/'trials.jsonl').read_text('utf-8').splitlines()]
    assert rows==read('trials.json')['trials'] and len(rows)==18
    lookup={(r['case'],r['plan'],r['round']):r for r in rows};assert len(lookup)==18
    source=read('source-resource.json');native=read('native-resource.json');provenance=read('dataset-provenance.json')
    assert provenance['inputs']==inputs() and provenance['states']==json.loads(json.dumps(schedule()))
    changes=provenance['changes'];assert len(changes)==18
    transitions=[c for c in changes if c['projection_changed'] is not None]
    assert len(transitions)==12 and all(c['projection_changed'] and c['old_plus_new_record_bytes']>256<<10 for c in transitions)
    assert set(source['files'])=={'rkv1/'+n for n in checks}|{'rkv1/memory_demo.html'}
    assert sum(v['bytes'] for v in source['files'].values())==source['total_bytes']
    for name,v in source['files'].items():assert Path(name).stat().st_size==v['bytes'] and digest(Path(name).read_bytes())==v['sha256']
    assert native_library.stat().st_size==native['bytes'] and digest(native_library.read_bytes())==native['sha256']
    assert digest(native_library.with_name('native.json').read_bytes())==native['metadata_sha256']
    formal=history=negative=snapshots=warmups=0
    for row in rows:
        base=lookup[row['case'],'rebuild',row['round']]
        assert row['generation_calls']==0 and row['all_historical_snapshots_full_source_verified'] and row['final_CAS_tree']==base['final_CAS_tree']
        assert [s['index'] for s in row['stages']]==list(range(13))
        for s,b in zip(row['stages'],base['stages']):
            n=s['index'];assert s['checkpoint'] and s['full_current_source_bytewise_verified']
            assert s['source_truth']==b['source_truth'] and s['build']['snapshot_id']==b['build']['snapshot_id'] and s['storage']['cas']==b['storage']['cas']
            assert s['build']['indexed_records']==6 and len(s['source_truth'])==6
            if n and row['plan']!='rebuild':assert s['build']['checkpoint_reason']=='budget-record-bytes'
            if row['plan']=='projection-v4':assert s['build']['overlay_rebindings']==s['build']['overlay_upserts']==0
            formal+=same_queries(s['query']['queries'],b['query']['queries'],questions(row['round']))
            history+=same_queries(s['old_snapshot_queries'],b['old_snapshot_queries'],questions(0)[:4])
            assert s['query']['warmup_queries']==1 and s['negative_control_absent'];warmups+=1;negative+=1;snapshots+=1
    assert (formal,history,negative,snapshots,warmups)==(4212,936,234,234,234)
    log=test_log.read_text('utf-8');match=re.search(r'Ran (\d+) tests',log);assert match and 'FAILED' not in log and 'OK (skipped=1)' in log
    validation={'formal_queries_audited':formal,'historical_identity_queries_audited':history,'negative_controls':negative,
        'historical_snapshot_instances_fully_reopened':snapshots,'fresh_query_processes_and_warmups':warmups,
        'all_keys_BM25_and_complete_source_identity_match_rebuild':True,'all_CAS_trees_match_within_representation':True,
        'all_true_body_revision_transitions':12,'all_budget_profiles_checkpoint_each_revision_for_record_bytes':True,
        'current_modules':len(checks),'new_independent_papers':6,'new_scientific_QA_questions':0,'generation_calls':0,
        'tests':{'run':int(match[1]),'passed':int(match[1])-1,'skipped':1,'failed':0,'log_sha256':digest(test_log.read_bytes())}}
    result={'cases':{}}
    for case in CASES:
        group={'stages':{},'totals':{}};result['cases'][case]=group
        native_bytes=native['bytes']+native['metadata_bytes'] if case=='gear' else 0
        for n in range(13):
            group['stages'][str(n)]={}
            for plan in PLANS:
                ss=[lookup[case,plan,r]['stages'][n] for r in range(3)];bs=[lookup[case,'rebuild',r]['stages'][n] for r in range(3)]
                assert len({s['storage']['logical_file_bytes'] for s in ss})==1
                group['stages'][str(n)][plan]={'logical_file_bytes':ss[0]['storage']['logical_file_bytes'],'counted_bytes':ss[0]['storage']['logical_file_bytes']+source['total_bytes']+native_bytes,
                    'source_bytes_once':source['total_bytes'],'native_bytes_once':native_bytes,'by_directory_bytes':ss[0]['storage']['by_directory_bytes'],
                    'new_index_bytes':[s['build']['new_index_bytes'] for s in ss],'checkpoint_reasons':[s['build']['checkpoint_reason'] for s in ss],
                    'replay_meter':ss[0]['build']['replay_budget'],'build_wall_s':summary([s['build_wall_s'] for s in ss]),'build_cpu_s':summary([s['build_cpu_s'] for s in ss]),
                    'query_wall_s':summary([q['wall_s'] for s in ss for q in s['query']['queries']]),
                    'query_cpu_s':summary([q['cpu_s'] for s in ss for q in s['query']['queries']]),
                    'paired_query_speedup_vs_rebuild':summary([bq['wall_s']/q['wall_s'] for s,b in zip(ss,bs) for q,bq in zip(s['query']['queries'],b['query']['queries'])]),
                    'query_process_peak_rss_bytes':summary([s['query']['peak_rss_bytes'] for s in ss]),
                    'query_process_wall_including_startup_s':summary([s['query_process_wall_including_startup_s'] for s in ss])}
        for plan in PLANS:
            ts=[lookup[case,plan,r] for r in range(3)]
            group['totals'][plan]={'final_counted_bytes':group['stages']['12'][plan]['counted_bytes'],
                 'all_commits_wall_s':summary([sum(s['build_wall_s'] for s in t['stages']) for t in ts]),
                 'checkpoint_counts':[sum(s['checkpoint'] for s in t['stages']) for t in ts],
                 'build_process_peak_rss_bytes':summary([t['build_process_peak_rss_bytes'] for t in ts])}
    text='''# v0.23 独立真实正文修订：整篇JATS记录基线

eLife固定官方提交中按数值ID前六篇三版本论文，18原文件，12次投影确实变化。
不是QASPER标注发布，也不是人工科学QA。六篇v1后逐篇v2/逐篇v3，13状态。
固定/Gear×完整重建/预算v3/投影v4，各三轮，全部原文和历史保留，无GC。

**粒度负结果：旧+新整篇记录全部超过256KiB，预算v3/v4每次都检查点，没有
增量索引收益。v4指纹表还有额外字节。Gear CAS复用与索引收益分开报告。**

## 全历史成本与提交

'''
    text+=table(['分块','策略','最终计入B','总提交wall中位s','基础数（三轮）'],[
        [case,p,v['final_counted_bytes'],f"{v['all_commits_wall_s']['median']:.3f}",str(v['checkpoint_counts'])]
        for case,g in result['cases'].items() for p,v in g['totals'].items()])
    text+='\n## 每阶段索引与查询\n\n'
    text+=table(['分块','阶段','策略','新索引B（三轮）','检查点原因','查询中位/p95 ms','对重建配对加速','进程峰值MiB'],[
        [case,n,p,str(v['new_index_bytes']),str(v['checkpoint_reasons']),f"{v['query_wall_s']['median']*1000:.2f}/{v['query_wall_s']['p95']*1000:.2f}",f"{v['paired_query_speedup_vs_rebuild']['median']:.3f}×",f"{v['query_process_peak_rss_bytes']['median']/1048576:.2f}"]
        for case,g in result['cases'].items() for n,plans in g['stages'].items() for p,v in plans.items()])
    text+='''
4212正式、936历史完整身份查询的排序、BM25绝对差<=1e-10、title/sentences/当前
精确locator均匹配完整重建。234人为不存在标记阴性控制，不称科学反例。234历史
快照实例全源SHA/大小重读，当前源逐字节一致；同分块CAS树一致，查询不改持久树。
234新进程，各一预热排除。新6篇/12正文转换，18诊断词项非gold QA；0模型调用。

原始XML完整保存、整文件offset0定位。FTS只投影标题、普通摘要与正文段落，过滤
图表/评审等；原始数式/表格仍保留，文本投影不等于完整科学语义。新kind需v0.23，
旧v0.22不解码JATS；归档v1–v6/CAS1/应用清单v1–v4不变。默认仍预算v3，v4显式。
writer没有为获得收益放宽预算；下一实验应独立定义更细证据记录及完整身份。

query计整个search与释放，启动另列；commit含全源读取/解析/预算/校验/HEAD发布，
源准备不计。worker RSS含整个进程与选题输入，不能和v0.22小输入历史峰值直接比。
全部RKV Python/HTML计一次，Gear加整个精确旧DLL/元数据；公共Python/SQLite/OS、
pyc、安装/文件系统元数据未全额分配，非完整部署净压缩。不得把Gear CAS节省称为
v4增量索引收益，也不把同一论文两个转换当两个独立论文。
仅本机温缓存；无新QA质量、E3、多跳、长期对话、形式证明、冷缓存/跨机器、掉电/
并发或GC结论。原始科学输入/正文/私有研究不发布，固定来源和SHA可复建。
'''
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation)
    with (root/'SUMMARY.md').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
    for ax,case in zip(axes,CASES):
        for offset,p in zip((-.24,0,.24),PLANS):
            ax.bar([i+offset for i in range(3)],[result['cases'][case]['stages'][str(n)][p]['query_wall_s']['median']*1000 for n in (0,6,12)],width=.23,label=p)
        ax.set_title(case+' — whole-file evidence records');ax.set_xticks(range(3),['all v1','all v2','all v3']);ax.set_ylabel('Median complete query ms');ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
    fig.suptitle('v0.23: six actual eLife body revisions, same exact original XML\nAll budgeted revisions checkpoint; no incremental-index saving; warm cache, one host')
    target=root/'revision-costs.png';assert not target.exists();fig.savefig(target,dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--native-library',type=Path,required=True);p.add_argument('--plot',action='store_true')
    a=p.parse_args();r=analyze(a.root,a.test_log,a.native_library)
    if a.plot:plot(a.root,r)
