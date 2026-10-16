"""Offline audit of frozen query plans; no generation or parameter selection."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from scripts.run_memory_queries import PLANS,STAGES,SEED,questions,sha
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root,test_log):
    read=lambda name:json.loads((root/name).read_text('utf-8'))
    checks=read('source-checksums.json');assert checks==implementation_checksums()
    reference=read('reference-checksums.json')
    assert reference==json.loads(Path('results/v0.17.0/source-checksums.json').read_text('utf-8'))
    data=read('trials.json');rows=[json.loads(line) for line in (root/'trials.jsonl').read_text('utf-8').splitlines()]
    assert rows==data['trials'] and len(rows)==90
    assert data['historical_snapshots_fully_reopened']==22 and data['all_persistent_fixture_files_unchanged']
    lookup={(r['round'],r['representation'],r['stage'],r['plan']):r for r in rows}
    assert len(lookup)==90
    fixtures=read('fixture-provenance.json');assert set(fixtures)=={'fixed','gear'}
    old=json.loads(Path('results/v0.17.0/trials.json').read_text('utf-8'))
    old_keys={q['claim_id']:q['keys'] for q in old['trials'][0]['stages'][0]['query']['queries']}
    audited=0
    for row in rows:
        assert not row['native_module_loaded'] and not row['cross_query_cache'] and row['generation_calls']==0
        assert row['implementation_checksums']==(reference if row['plan']=='v017' else checks)
        expected=questions(row['round']);queries=row['queries'];assert len(queries)==len(expected)==191
        assert row['warmup_queries']==1
        base=lookup[row['round'],row['representation'],row['stage'],'v017']
        assert row['snapshot_id']==fixtures[row['representation']]['stages'][row['stage']]['snapshot_id']
        for q,b,(cid,question) in zip(queries,base['queries'],expected):
            assert q['claim_id']==b['claim_id']==cid
            assert q['question_sha256']==b['question_sha256']==hashlib.sha256(question.encode()).hexdigest()
            assert q['keys']==b['keys'] and q['evidence_identity_sha256']==b['evidence_identity_sha256']
            assert len(q['ranks'])==len(b['ranks']) and all(abs(x-y)<=1e-10 for x,y in zip(q['ranks'],b['ranks']))
            assert q['all_original_records_verified'] and q['wall_s']>=q['reported_internal_wall_s'] and q['cpu_s']>=0
            if row['stage']==0 and cid in old_keys:assert q['keys']==old_keys[cid]
            audited+=1
    assert audited==17190
    resource=read('source-resource.json')
    for version,entry in resource['implementations'].items():
        assert sum(f['bytes'] for f in entry['files'].values())==entry['total_bytes']
        if version=='v018':
            for name,v in entry['files'].items():assert Path(name).stat().st_size==v['bytes'] and sha(Path(name))==v['sha256']
    log=test_log.read_bytes();text=log.decode('utf-8-sig');ran=re.search(r'Ran (\d+) tests',text);ok=re.search(r'^OK(?: \(skipped=(\d+)\))?\r?$',text,re.M)
    assert ran and ok and 'FAILED (' not in text
    validation={'formal_queries_audited':audited,'warmup_queries':90,'fresh_query_processes':90,
                'different_scientific_claims':188,'synthetic_probes':3,'all_keys_ranks_and_complete_evidence_identity_match_v017':True,
                'all_22_historical_snapshots_fully_reopened':True,'all_persistent_fixture_files_byte_identical_before_after':True,
                'all_46_current_modules_match_measurement':True,'all_reference_modules_match_v017_release':True,
                'no_cross_query_cache':True,'no_native_query_module_loaded':True,'generation_calls':0,
                'tests':{'run':int(ran[1]),'passed':int(ran[1])-int(ok[1] or 0),'skipped':int(ok[1] or 0),'failed':0,'log_sha256':hashlib.sha256(log).hexdigest()}}
    result={'stages':{},'source_resource':resource,'validation':validation,'new_model_quality':None,'cold_cache':None,'cross_machine':None}
    for representation in fixtures:
        result['stages'][representation]={}
        for stage in STAGES:
            result['stages'][representation][str(stage)]={}
            for plan in PLANS:
                trials=[lookup[r,representation,stage,plan] for r in range(3)]
                bases=[lookup[r,representation,stage,'v017'] for r in range(3)]
                eager=[lookup[r,representation,stage,'scoped-eager'] for r in range(3)]
                records=[q for trial in trials for q in trial['queries']]
                pairs=[b['wall_s']/q['wall_s'] for trial,base in zip(trials,bases) for q,b in zip(trial['queries'],base['queries'])]
                incremental=[b['wall_s']/q['wall_s'] for trial,base in zip(trials,eager) for q,b in zip(trial['queries'],base['queries'])]
                result['stages'][representation][str(stage)][plan]={
                    'wall_s':summary([q['wall_s'] for q in records]),'cpu_s':summary([q['cpu_s'] for q in records]),
                    'paired_speedup_vs_v017':summary(pairs),'paired_speedup_vs_scoped_eager':summary(incremental),
                    'process_peak_rss_bytes':summary([r['peak_rss_bytes'] for r in trials]),
                    'process_wall_including_startup_s':summary([r['process_wall_including_startup_s'] for r in trials]),
                    'batch_wall_s':summary([r['batch_wall_s'] for r in trials]),'queries':len(records)}
    text='''# v0.18 查询资源复用与延后定位

固定/Gear两种既有v3存储，五个预定阶段，三种查询计划，各三轮。每个组合新进程，
一次预热后查询全部188条标注主张＋3探针。17,190正式查询的key顺序、BM25与完整
原文定位身份均匹配实际v0.17已发布Python模块；22个历史快照结束后全源SHA/大小
重读一致，两组持久树逐文件大小/SHA完全未变。没有新科学样本或模型质量结果。

v017=原发布实现；scoped-eager=只复用请求内资源，完整物化所有定位；scoped-deferred=
默认新实现，再只换算命中且未upsert替换的定位。全部范围的计数、非负、无重复记录
仍在查询前验证；全库FTS词项/BM25不变。无跨查询缓存、无新原生查询库。

## 同轮结果

'''
    text+=table(['表示','阶段','计划','查询中位ms','p95 ms','对v017配对加速','对scoped-eager配对加速','进程峰值MiB'],[
        [rep,stage,plan,f"{v['wall_s']['median']*1000:.2f}",f"{v['wall_s']['p95']*1000:.2f}",
         f"{v['paired_speedup_vs_v017']['median']:.3f}×",f"{v['paired_speedup_vs_scoped_eager']['median']:.3f}×",
         f"{v['process_peak_rss_bytes']['median']/1048576:.2f}"]
        for rep,stages in result['stages'].items() for stage,plans in stages.items() for plan,v in plans.items()])
    text+='''
外部wall覆盖完整search调用及资源清理；进程启动另列。比值先按同轮同问题配对再
取中位，不是两组中位之比。cProfile仅为诊断，不与无剖析器正式耗时混算。RSS含
整个解释器/输入加载，是每进程峰值，不是单请求增量。仅本机Windows温缓存。

本轮不写索引/源文件，不测提交或新的压缩率。两份专用源码各全额计一次，大小和
SHA见source-resource；公共Store/core/Python/SQLite/OS未全额分配，不称完整部署
净收益。Gear存储可以用Python生成相同字节；查询没有加载之前提交用的Rust库。

源格式/归档/CAS/记忆v1-v3兼容不变；没有自动迁移、GC、跨查询可信缓存或校验跳过。
合成更新复用v0.17，不是新的真实版本家族；不同主张仍188。E3、长会话、多跳、
新问答质量、并发修改、冷缓存/跨机器、目录/掉电持久性均未测。
'''
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation)
    with (root/'SUMMARY.md').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    return result


def plot(root,result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13,4.5),constrained_layout=True)
    labels=['original','append','insert 13B','delete first','final']
    for ax,(rep,stages) in zip(axes,result['stages'].items()):
        for offset,plan in zip((-0.25,0,0.25),PLANS):
            ax.bar([i+offset for i in range(5)],[stages[str(n)][plan]['wall_s']['median']*1000 for n in STAGES],width=0.24,label=plan)
        ax.set_xticks(range(5),labels,rotation=15);ax.set_ylabel('Median full search call (ms)');ax.set_title(rep+' v3 retained store')
        ax.grid(axis='y',alpha=0.2);ax.set_axisbelow(True);ax.legend(fontsize=8)
    fig.suptitle('v0.18 query ablation: exact evidence and global BM25 preserved\nWarm cache, one host; 188 claims + 3 probes, 3 rounds; no cross-query cache')
    path=root/'query-costs.png';assert not path.exists();fig.savefig(path,dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--plot',action='store_true')
    args=p.parse_args();result=analyze(args.root,args.test_log)
    if args.plot:plot(args.root,result)
