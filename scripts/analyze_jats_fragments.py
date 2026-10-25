"""Audit frozen fragment preflight; keep lower bounds apart from implementation."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

from rkv1.benchmark import summary
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.jats_fragments import fragments
from rkv1.memory import _json
from scripts.run_jats_fragments import MODES, units
from scripts.run_paper_revisions import inputs
from scripts.run_units import save
from scripts.summarize_units import table


def analyze(root, log, frozen, *, modes=MODES, test_count=182, write_report=True):
    read = lambda n: json.loads((root/n).read_text('utf-8'))
    checks = read('source-checksums.json'); assert checks == implementation_checksums()
    for name, sha in checks.items():
        assert digest(subprocess.check_output(['git', 'show', frozen+':rkv1/'+name])) == sha
    identity = read('identity-audit.json'); assert identity['inputs'] == inputs() and len(identity['files']) == 36
    raw_files = {v['path']: (Path('data/elife-revisions')/v['path']).read_bytes() for p in inputs()['papers'] for v in p['versions']}
    lookup = {(f['path'], f['mode']): f for f in identity['files']}
    verified = 0
    for (path, mode), f in lookup.items():
        rows = fragments(raw_files[path], mode=mode)
        assert len(rows) == f['units'] and digest(_json(rows)) == f['descriptor_sha256']
        assert f['parent_and_every_range_verified'] and f['lexical_projection_matches_whole']
        assert f['sha256'] == digest(raw_files[path]); verified += f['units']
    assert identity['verified_ranges_including_two_key_policies'] == verified
    trials = read('parser-trials.json')['trials']; assert len(trials) == 9
    assert {(r['mode'],r['round']) for r in trials} == {(m,r) for m in modes for r in range(3)}
    for trial in trials:
        assert len(trial['samples']) == 18 and {s['path'] for s in trial['samples']} == set(raw_files)
        for s in trial['samples']:
            assert s['descriptor_sha256'] == digest(_json(units(raw_files[s['path']], trial['mode'])))
            assert s['wall_s'] > 0 and s['cpu_s'] >= 0
    plans = read('plans.json')['plans']; assert len(plans) == 144
    assert {(p['case'],p['stage'],p['mode'],p['projection_rebinding']) for p in plans} == {
        (c,s,m,v) for c in ('fixed','gear') for s in range(1,13) for m in modes for v in (False,True)}
    groups = []
    for case in ('fixed','gear'):
        for mode in modes:
            for projection in (False,True):
                ps = [p for p in plans if p['case']==case and p['mode']==mode and p['projection_rebinding']==projection]
                group = {'case':case, 'mode':mode, 'policy':'v4' if projection else 'v3', 'transitions':12,
                    'upserted':summary([p['upserted'] for p in ps]), 'rebound':summary([p['rebound'] for p in ps])}
                for model in ('range_only_lower_bound','current_full_parent_verifier'):
                    for p in ps:
                        assert p[model]['admissible'] == (p[model]['reason'] is None)
                    group[model] = {'admissible_adjacent_transitions':sum(p[model]['admissible'] for p in ps),
                        'reasons':dict(Counter(p[model]['reason'] or 'admissible' for p in ps)),
                        'record_bytes':summary([p[model]['record_bytes'] for p in ps]),
                        'cas_bytes':summary([p[model]['cas_bytes'] for p in ps])}
                groups.append(group)
    history = read('cas-history.json'); assert len(history['stages']) == 26
    assert history['historical_full_source_snapshots_verified'] == 26 and history['persistent_trees_unchanged_by_reads']
    source = read('source-resource.json'); assert sum(v['bytes'] for v in source['files'].values()) == source['total_bytes']
    assert set(source['files']) == {'rkv1/'+n for n in checks}|{'rkv1/memory_demo.html'}
    for name, value in source['files'].items():
        assert Path(name).stat().st_size == value['bytes'] and digest(Path(name).read_bytes()) == value['sha256']
    costs = []
    native = read('native-resource.json'); native_bytes = native['bytes']+native['metadata_bytes']
    for case in ('fixed','gear'):
        stages = [s for s in history['stages'] if s['case'] == case]; assert [s['stage'] for s in stages] == list(range(13))
        for mode in modes:
            metadata = sum(s['simple_locator_metadata_bytes'][mode] for s in stages)
            cas_bytes = stages[-1]['stats']['logical_file_bytes']
            costs.append({'case':case,'mode':mode,'retained_CAS_bytes':cas_bytes,'uncompressed_descriptor_metadata_candidate_bytes':metadata,
                'RKV_source_once':source['total_bytes'],'native_once':native_bytes if case=='gear' else 0,
                'partial_accounting_only':True,'not_an_actual_Memory_index_size':True})
    parsing = {}
    for mode in modes:
        ts = [r for r in trials if r['mode'] == mode]
        parsing[mode] = {'all_18_files_parser_wall_s':summary([sum(s['wall_s'] for s in r['samples']) for r in ts]),
            'all_18_files_parser_cpu_s':summary([sum(s['cpu_s'] for s in r['samples']) for r in ts]),
            'process_wall_including_startup_s':summary([r['process_wall_including_startup_s'] for r in ts]),
            'peak_rss_bytes':summary([r['peak_rss_bytes'] for r in ts])}
    text_log = log.read_text('utf-8'); n = int(re.search(r'Ran (\d+) tests', text_log)[1])
    assert n == test_count and 'OK (skipped=1)' in text_log and 'FAILED' not in text_log
    validation = {'verified_ranges_including_two_key_policies':verified,'unique_source_files':18,'reused_independent_papers':6,
        'new_independent_papers':0,'new_scientific_QA':0,'generation_calls':0,'parser_processes':9,'parser_file_invocations':162,
        'adjacent_budget_plans':144,'real_revision_transitions':12,'retained_historical_CAS_snapshots_verified':26,
        'all_range_parent_identity_and_projection_checks_passed':True,'persistent_CAS_trees_unchanged_by_reads':True,
        'Memory_fragment_reader_integrated':False,'query_quality_or_latency_measurements':None,
        'source_modules':len(checks),'frozen_commit':frozen,'all_measured_modules_match_frozen_commit':True,
        'tests':{'run':n,'passed':n-1,'skipped':1,'failed':0,'log_sha256':digest(log.read_bytes())}}
    result = {'budget_groups':groups,'parsing':parsing,'partial_resource_accounting':costs}
    save(root/'derived-metrics.json',result);save(root/'validation.json',validation)
    if not write_report:
        return result
    text = '''# v0.24 原始JATS片段身份与预算预检实验报告

## 问题与本轮交付

v0.23真实论文修订的整篇旧+新XML超过256KiB，预算策略每次完整检查点。本轮先
实现父论文SHA绑定的精确片段审计API，固定两种身份规则，验证有无值得集成的
局部工作量。未将片段接入Memory，没有新来源kind/索引格式或默认迁移。

复用固定六篇/18版本、12真实修订转换，0新增独立论文/QA/模型请求。标题单独
一个单元，普通摘要及主正文p为连续原XML范围，包含内联标记/注释/CDATA；text
仅作派生词法投影。父文章ID及全文件SHA、range SHA和角色/选择器全部绑定。
position明确按位置；xml-id优先唯一元素id，无id回退序号，均不保证语义恒等。

新增SkippedEntityHandler拒绝外部DTD未加载时被跳过的实体，避免词法投影丢字。
正常公开输入全部仍可读；这是拒绝范围收紧，未改写历史标签。原始字节不变。

## 身份与正确性

'''
    text += table(['论文文件','单元数','id键数','投影文本B','连续原范围B','未压缩定位元数据JSON B'],[
        [f['path'],f['units'],f['id_key_count'],f['text_utf8_bytes'],f['covered_original_bytes'],f['locator_metadata_json_bytes']]
        for f in identity['files'] if f['mode']=='xml-id'])
    text += f'\n两种规则共{verified}条范围逐条以完整父文件verify；其中同一原范围在两规则重复，不能作独立科学样本。所有投影与整篇title/段落列表完全一致，所有历史26个CAS快照全源SHA/字节核对，读前后持久树不变。182测试运行、181通过、1符号链接权限跳过。\n'
    text += '''
## 相邻状态预算规划

只比较相邻状态，为最短回放的必要条件，不模拟累计overlay，也不表示实际13
状态的检查点数。路径保留原版本文件名，升级产生的所有定位变化均计入。下界
仅读原range，尚无集成解码器；当前审计器每次需读完整父文件，无跨记录缓存，
且v4相同text重绑定的父身份检查也收费。保留32变化/256KiB记录/2MiB CAS等门槛。

'''
    text += table(['分块','键规则','策略','range下界可过/12','当前完整父校验可过/12','下界记录B中位','完整父校验B中位','下界失败原因'],[
        [g['case'],g['mode'],g['policy'],g['range_only_lower_bound']['admissible_adjacent_transitions'],
         g['current_full_parent_verifier']['admissible_adjacent_transitions'],
         round(g['range_only_lower_bound']['record_bytes']['median']),round(g['current_full_parent_verifier']['record_bytes']['median']),
         str(g['range_only_lower_bound']['reasons'])] for g in groups])
    text += '\n所有144条逐转换规划与具体门槛原因见plans.json。不同分块只改变CAS块放大，不改变原记录/语义身份；不能把通过必要条件称为已省索引或查询加速。\n'
    text += '\n## 解析成本（18文件总量，三轮中位）\n\n'
    text += table(['模式','wall s','CPU s','含启动进程wall s','进程RSS MiB'],[
        [m,f"{v['all_18_files_parser_wall_s']['median']:.6f}",f"{v['all_18_files_parser_cpu_s']['median']:.6f}",
         f"{v['process_wall_including_startup_s']['median']:.6f}",f"{v['peak_rss_bytes']['median']/1048576:.2f}"] for m,v in parsing.items()])
    text += '''
每轮/模式一个新进程，18次解析，输入预加载，启动/准备另列。片段API目前先验证
整篇，再记录事件边界，包含第二遍解析及SHA/描述生成；whole是既有纯文本解析。
RSS含输入/结果，是整个进程峰值。三轮是重复测量，不是54篇独立数据。未测query。

## 资源与成本边界

'''
    text += table(['分块','记录候选','全部历史CAS B','13状态未压缩定位候选 B','全部RKV源一次 B','精确原生库一次 B'],[
        [c['case'],c['mode'],c['retained_CAS_bytes'],c['uncompressed_descriptor_metadata_candidate_bytes'],c['RKV_source_once'],c['native_once']] for c in costs])
    text += '''
定位候选逐描述canonical JSON求和，包含父SHA而不含派生text；全文件路径/父列表
可由已计CAS快照关联。尚未计FTS、实际Memory清单/overlay/安装/pyc/文件系统/
公共运行时；这是部分候选账本，不能与v0.23完整系统相除报告净压缩率。没有把
未落盘索引算成0B。全部Python/HTML源计一次，Gear额外全额精确旧DLL/元数据。

## 结论与下一步

这18文件的927个独特版本内投影单元没有元素id，xml-id全部回退位置键，因此
两规则的身份与预算结果相同，不能宣称原id解决了真实修订匹配。v3仍12/12被
变化数门槛拒绝；v4乐观range下界仅1/12可过，9次变化数、2次CAS字节门槛，
当前完整父校验全部不可过。父文件逐条验证的代价不能忽略。片段解析约为whole
的4.8倍（仅本次三轮中位），未压缩定位候选1114496B对20904B，增加约53倍；
候选未做字典化/父表归一，也不是最终索引大小。正确切段本身不足以证明值得集成。

下一优先项改为独立检验内容锚定键/重复段落规则，避免位置键的插入级联；仍用
这批真实转换和同一预算，先看必要条件再决定是否开发局部解码器。其后才设计
可信父上下文及新来源兼容，计完整索引/清单和同粒度查询成本。保留整篇默认与
原预算，不能为通过实验调阈值或直接把本候选接入默认。无净收益则保留负结果。

仅本机温缓存；不增加科学QA质量、E3、多跳、长期会话、冷缓存、跨机器、并发/
掉电/GC或普遍数学证明结论。数据公开固定来源/SHA，原论文/完整描述留本机。
'''
    (root/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n')
    return result


def plot(root, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1,2,figsize=(11,4.6),constrained_layout=True)
    for ax, case in zip(axes, ('fixed','gear')):
        gs = [g for g in result['budget_groups'] if g['case']==case]
        x = list(range(len(gs)))
        ax.bar([i-.18 for i in x],[g['range_only_lower_bound']['admissible_adjacent_transitions'] for g in gs],width=.35,label='Range-only lower bound')
        ax.bar([i+.18 for i in x],[g['current_full_parent_verifier']['admissible_adjacent_transitions'] for g in gs],width=.35,label='Current full-parent audit')
        ax.set_xticks(x,[g['mode']+'\n'+g['policy'] for g in gs]);ax.set_ylim(0,13);ax.set_yticks(range(0,13,2));ax.set_title(case+' 64 KiB')
        ax.set_ylabel('Admissible adjacent transitions / 12');ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
    fig.suptitle('v0.24: exact JATS ranges and necessary-condition budget planning\nNo integrated fragment Memory reader, index savings, query speed or new scientific QA')
    fig.savefig(root/'fragment-budget-preflight.png',dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--test-log',type=Path,required=True);p.add_argument('--frozen',required=True);p.add_argument('--plot',action='store_true')
    a=p.parse_args();result=analyze(a.root,a.test_log,a.frozen)
    if a.plot:plot(a.root,result)
