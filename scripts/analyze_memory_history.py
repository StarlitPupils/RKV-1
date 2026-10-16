"""Audit separate real-release and synthetic-history campaigns, without APIs."""
import argparse
import json
from pathlib import Path
import re

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from scripts.run_memory_history import PROFILES,LONG_QUERY_STAGES,questions,real_inputs
from scripts.run_units import save
from scripts.summarize_units import table


def same_queries(xs,ys,expected):
    assert len(xs)==len(ys)==len(expected)
    for x,y,(cid,question) in zip(xs,ys,expected):
        assert x['query_id']==y['query_id']==cid
        assert x['question_sha256']==y['question_sha256']==digest(question.encode())
        assert x['keys']==y['keys'] and x['evidence_identity_sha256']==y['evidence_identity_sha256']
        assert x['source_paper_hit5']==y['source_paper_hit5']
        assert len(x['ranks'])==len(y['ranks']) and all(abs(a-b)<=1e-10 for a,b in zip(x['ranks'],y['ranks']))
        assert x['all_original_records_verified']
    return len(xs)


def analyze(root,test_log,native_library):
    read=lambda name:json.loads((root/name).read_text('utf-8'))
    assert read('source-checksums.json')==implementation_checksums()
    rows=[json.loads(line) for line in (root/'trials.jsonl').read_text('utf-8').splitlines()]
    assert rows==read('trials.json')['trials'] and len(rows)==12
    lookup={(r['campaign'],r['round'],r['profile']):r for r in rows};assert len(lookup)==12
    source=read('source-resource.json');native=read('native-resource.json')
    assert sum(v['bytes'] for v in source['files'].values())==source['total_bytes']
    for name,v in source['files'].items():assert Path(name).stat().st_size==v['bytes'] and digest(Path(name).read_bytes())==v['sha256']
    assert native_library.stat().st_size==native['bytes'] and digest(native_library.read_bytes())==native['sha256']
    meta=native_library.with_name('native.json');assert meta.stat().st_size==native['metadata_bytes'] and digest(meta.read_bytes())==native['metadata_sha256']
    provenance=read('dataset-provenance.json');assert provenance['official_QASPER_dev_releases']==real_inputs()
    assert [x['projected_paper_text_changed'] for x in provenance['changes']]==[None,0,0]
    formal=historical=snapshots=negative=warmups=0
    for row in rows:
        campaign=row['campaign'];expected_count=3 if campaign=='qasper' else 101
        assert row['generation_calls']==0 and row['all_historical_snapshots_fully_reopened']
        assert [s['index'] for s in row['stages']]==list(range(expected_count))
        base=lookup[campaign,row['round'],'rebuild'];assert row['final_CAS_tree']==base['final_CAS_tree']
        for stage,b in zip(row['stages'],base['stages']):
            n=stage['index'];assert stage['source_truth']==b['source_truth'] and stage['full_source_bytewise_verified']
            assert stage['build']['snapshot_id']==b['build']['snapshot_id']
            assert stage['storage']['cas']==b['storage']['cas']
            snapshots+=1
            if campaign=='qasper':
                inp=provenance['official_QASPER_dev_releases'][n]
                assert stage['source_truth']=={inp['filename']:{'bytes':inp['bytes'],'sha256':inp['sha256']}}
                assert stage['build']['indexed_records']==281 and stage['checkpoint']
            elif row['profile']=='incremental':
                assert stage['checkpoint']==(n in (0,43,80))
                d=stage['pre_commit_candidate']
                if n==42:assert d['nonposition_changes']==d['nonposition_limit']==512
                if n==43:assert d['nonposition_changes']==513
                if n==80:assert d['relocation_ranges']==260 and d['nonposition_changes']<=d['nonposition_limit']
            else:assert stage['checkpoint']
            historical+=same_queries(stage['old_snapshot_queries'],b['old_snapshot_queries'],questions(campaign,0)[:4])
            if campaign=='stress':assert stage['original_future_probe_absent'] is True;negative+=1
            if campaign=='qasper' or n in LONG_QUERY_STAGES:
                query=stage['query'];assert query['generation_calls']==0 and query['warmup_queries']==1
                formal+=same_queries(query['queries'],b['query']['queries'],questions(campaign,row['round']));warmups+=1
            else:assert stage['query'] is None
    assert (formal,historical,snapshots,negative,warmups)==(1800,2496,624,606,72)
    log=test_log.read_bytes();text=log.decode('utf-8-sig');ran=re.search(r'Ran (\d+) tests',text);ok=re.search(r'^OK(?: \(skipped=(\d+)\))?\r?$',text,re.M)
    assert ran and ok and 'FAILED (' not in text
    validation={'formal_queries_audited':formal,'historical_queries_with_full_identity_audited':historical,
                'original_snapshot_future_probe_checks':negative,'historical_snapshots_fully_reopened':snapshots,'query_processes_and_warmups':warmups,
                'all_keys_BM25_and_complete_source_identities_match_full_rebuild':True,'all_same_representation_CAS_trees_byte_identical':True,
                'stress_checkpoint_versions':[0,43,80],'real_releases_checkpoint_every_version':True,'current_modules':len(implementation_checksums()),
                'different_QASPER_questions':64,'synthetic_control_queries':12,'generation_calls':0,
                'tests':{'run':int(ran[1]),'passed':int(ran[1])-int(ok[1] or 0),'skipped':int(ok[1] or 0),'failed':0,'log_sha256':digest(log)}}
    result={'campaigns':{},'validation':validation,'source_resource':source,'native_resource':native,'new_answer_quality':None,'cold_cache':None,'cross_machine':None}
    charge=source['total_bytes']+native['bytes']+native['metadata_bytes']
    for campaign,count in [('qasper',3),('stress',101)]:
        group={'stages':{},'totals':{}};result['campaigns'][campaign]=group
        for n in range(count):
            group['stages'][str(n)]={}
            for profile in PROFILES:
                ss=[lookup[campaign,r,profile]['stages'][n] for r in range(3)]
                bs=[lookup[campaign,r,'rebuild']['stages'][n] for r in range(3)]
                assert len({s['storage']['logical_file_bytes'] for s in ss})==1
                value={'logical_file_bytes':ss[0]['storage']['logical_file_bytes'],'counted_bytes':ss[0]['storage']['logical_file_bytes']+charge,
                    'shared_source_and_native_bytes_once':charge,'by_directory_bytes':ss[0]['storage']['by_directory_bytes'],
                    'new_index_bytes':[s['build']['new_index_bytes'] for s in ss],'checkpoint':[s['checkpoint'] for s in ss],
                    'pre_commit_candidate':ss[0]['pre_commit_candidate'],
                    'build_wall_s':summary([s['build_wall_s'] for s in ss]),'build_cpu_s':summary([s['build_cpu_s'] for s in ss]),
                    'paired_build_speedup_vs_rebuild':summary([b['build_wall_s']/s['build_wall_s'] for s,b in zip(ss,bs)])}
                if ss[0]['query'] is not None:
                    value['query_wall_s']=summary([q['wall_s'] for s in ss for q in s['query']['queries']])
                    value['paired_query_speedup_vs_rebuild']=summary([bq['wall_s']/q['wall_s'] for s,b in zip(ss,bs) for q,bq in zip(s['query']['queries'],b['query']['queries'])])
                    value['query_process_peak_rss_bytes']=summary([s['query']['peak_rss_bytes'] for s in ss])
                    value['query_process_wall_including_startup_s']=summary([s['query_process_wall_including_startup_s'] for s in ss])
                    if campaign=='qasper':value['source_paper_hit_at_5']=sum(q['source_paper_hit5'] for q in ss[0]['query']['queries'])/64
                group['stages'][str(n)][profile]=value
        for profile in PROFILES:
            trials=[lookup[campaign,r,profile] for r in range(3)]
            group['totals'][profile]={'final_counted_bytes':group['stages'][str(count-1)][profile]['counted_bytes'],
                'all_commits_wall_s':summary([sum(s['build_wall_s'] for s in t['stages']) for t in trials]),
                'checkpoint_versions':[[s['index'] for s in t['stages'] if s['checkpoint']] for t in trials],
                'build_process_peak_rss_bytes':summary([t['build_process_peak_rss_bytes'] for t in trials])}
    text='''# v0.19 真实发布与100更新压力对照

真实组为QASPER官方dev三次发布，每版281论文，保留原文件名/全部字节；只索引论文
标题、摘要和正文，问答标注不投影。正文跨版本相同，原成员变化281/9条；不是论文
内容修订。控制组为2048合成记录、四note、100次更新，不能算真实科学数据。

同Gear64KiB/Zlib、同冻结Rust扫描库，比较每快照完整重建与v3基础相对增量，三轮
新库/进程，全部历史保留。默认固定/v3未改变，本轮隔离索引策略，不测默认固定
提交性能。两条件统一计四份完整源及实测DLL/元数据一次，公共运行时未全额分配。

## 全历史成本与提交

'''
    text+=table(['组','策略','最终计入B','全部提交wall中位s','各轮完整基础数'],[
        [c,p,v['final_counted_bytes'],f"{v['all_commits_wall_s']['median']:.3f}",str([len(x) for x in v['checkpoint_versions']])]
        for c,g in result['campaigns'].items() for p,v in g['totals'].items()])
    text+='\n## 逐阶段查询与检查点\n\n'
    text+=table(['组','版本/更新','策略','非位置变更/位移区间','新索引B（三轮）','查询中位/p95 ms','对完整重建配对加速','查询进程峰值MiB'],[
        [c,n,p,str((v['pre_commit_candidate']['nonposition_changes'],v['pre_commit_candidate']['relocation_ranges'])) if v['pre_commit_candidate'] else 'initial',
         str(v['new_index_bytes']),f"{v['query_wall_s']['median']*1000:.2f}/{v['query_wall_s']['p95']*1000:.2f}",
         f"{v['paired_query_speedup_vs_rebuild']['median']:.3f}×",f"{v['query_process_peak_rss_bytes']['median']/1048576:.2f}"]
        for c,g in result['campaigns'].items() for n,plans in g['stages'].items() for p,v in plans.items() if 'query_wall_s' in v])
    text+='''
比值先按同问题/同轮配对再取中位，不是两组中位之比。RSS含整个进程和输入；commit
含源扫描/构建/验证/HEAD发布，候选计数诊断在计时外且两条件均执行。仅本机温缓存。

1800正式查询和2496完整身份历史查询匹配完整重建；606未来探针阴性；624历史快照
全源大小/SHA重读，当前源逐字节一致。同表示CAS树相同，查询前后持久树不变。
真实组64个不同问题，控制12词项/探针和所有重复不算新增科学样本。QASPER原任务
给定论文，本轮跨281篇全局检索；来源论文命中@5只作诊断，不是答案评分或SciFact
召回的同任务对照。0次模型生成，无新推理或长会话结论。

真实发布保留版本文件名，路径变化导致每次完整检查点；正文未变不能推导更新成本
应为零。控制在42的512变化未超25%仍重放，43到513触发检查点；80的260区间
超256触发检查点。必须结合阈值前查询与全历史字节判断，不称任意更新恒定成本。

归档/CAS/记忆清单格式不变；QASPER新来源kind需v0.19，旧读取器无法解析；旧文本/
SciFact兼容。无模型API、GC、长期对话、跨域泛化、E3、多跳、冷缓存/跨机器、并发
写入或真实掉电结论。原始科学语料/问答原文/私有研究文件不发布。
'''
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation)
    with (root/'SUMMARY.md').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13,4.5),constrained_layout=True)
    group=result['campaigns']['stress']['stages']
    for profile in PROFILES:
        axes[0].plot(range(101),[group[str(n)][profile]['counted_bytes']/1e6 for n in range(101)],label=profile)
        axes[1].plot(LONG_QUERY_STAGES,[group[str(n)][profile]['query_wall_s']['median']*1000 for n in LONG_QUERY_STAGES],marker='o',label=profile)
    for ax in axes:
        ax.grid(alpha=.2);ax.legend();ax.set_xlabel('Synthetic update (all history retained)')
        for n in (43,80):ax.axvline(n,color='gray',linestyle=':',alpha=.6)
    axes[0].set_ylabel('Retained files + allocated source/native (MB)');axes[1].set_ylabel('Median search (ms)')
    axes[0].set_title('100-update storage control');axes[1].set_title('Checkpoint-adjacent query cost')
    fig.suptitle('v0.19: synthetic stress is separate from three real QASPER releases\nSame Gear/Rust commits; warm cache, one host; exact sources and global BM25')
    path=root/'history-costs.png';assert not path.exists();fig.savefig(path,dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--native-library',type=Path,required=True);p.add_argument('--plot',action='store_true')
    a=p.parse_args();r=analyze(a.root,a.test_log,a.native_library)
    if a.plot:plot(a.root,r)
