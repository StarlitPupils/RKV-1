"""Validate the frozen concurrency campaign and report its observed scope."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from scripts.run_memory_concurrency import ROUNDS, UPDATES, READERS, DOCUMENTS, corpus, expected_hashes, save


def quantile(values,p):
    if not values:return None
    values=sorted(values);x=(len(values)-1)*p;a=int(x);b=min(a+1,len(values)-1)
    return values[a]+(values[b]-values[a])*(x-a)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--freeze',required=True);p.add_argument('--test-log',required=True)
    args=p.parse_args();out=Path(args.out);env=json.loads((out/'environment.json').read_text('utf-8'))
    checks=implementation_checksums();assert checks==env['implementation_checksums'] and len(checks)==57
    for name,sha in checks.items():
        assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))==sha
        if name!='__init__.py':assert Path('rkv1',name).read_bytes()==subprocess.check_output(['git','show','v0.32.0:rkv1/'+name])
    for path,field in [('scripts/run_memory_concurrency.py','driver_sha256'),('docs/MEMORY-CONCURRENCY.md','protocol_sha256')]:
        assert digest(Path(path).read_bytes())==env[field]==digest(subprocess.check_output(['git','show',args.freeze+':'+path]))
    assert env['source_bytes']==len(corpus(0)) and env['source_hashes_by_epoch']=={str(g):h for h,g in expected_hashes().items()}
    log=Path(args.test_log).read_text('utf-8');assert 'Ran 220 tests' in log and 'OK (skipped=1)' in log
    trials=[json.loads((out/f'round-{i}.json').read_text('utf-8')) for i in range(1,ROUNDS+1)]
    rows=[];round_rows=[];errors=[];valid_queries=0;retained_total=0;overlap_total=0;history_total=0
    for n,trial in enumerate(trials,1):
        assert trial['round']==n and len(trial['readers'])==READERS
        writer=trial['writer'];complete=[e for e in writer['events'] if 'snapshot_id' in e]
        assert [e['epoch'] for e in complete]==list(range(1,len(complete)+1))
        expected=env['source_hashes_by_epoch']
        for e in complete:
            assert e['source_sha256']==expected[str(e['epoch'])] and e['start_s']<=e['add_start_s']<=e['end_s']
        for h in trial['history']:
            assert h['source_sha256']==expected[str(h['epoch'])] and h['verified_records']==4
        history_total+=len(trial['history'])
        for i,reader in enumerate(trial['readers']):
            good=[q for q in reader['queries'] if 'verified_records' in q];current=[q for q in good if not q['retained']];retained=[q for q in good if q['retained']]
            assert [q['query'] for q in reader['queries']]==list(range(len(reader['queries'])))
            assert [q['epoch'] for q in current]==sorted(q['epoch'] for q in current)
            for q in good:
                assert q['verified_records']==4 and q['source_sha256']==expected[str(q['epoch'])] and q['source_bytes']==len(corpus(0))
                assert q['search_wall_s']>=0 and q['audit_wall_s']>=0 and q['end_s']>=q['start_s']
                assert q['retained']==(q['query']%10==0)
            assert all(q['epoch']==0 and q['snapshot_id']==trial['history'][0]['snapshot_id'] for q in retained)
            overlap=sum(any(q['start_s']<e['end_s'] and q['end_s']>e['add_start_s'] for e in complete) for q in current)
            assert overlap==trial['current_searches_overlapping_actual_add_intervals_by_reader'][i]
            if reader['error']:errors.append({'round':n,'reader':i,**reader['error']})
            valid_queries+=len(good);retained_total+=len(retained);overlap_total+=overlap
            rows.append({'round':n,'reader':i,'queries':len(reader['queries']),'verified':len(good),'retained':len(retained),'current':len(current),
                         'distinct_current_epochs':len({q['epoch'] for q in current}),'last_current_epoch':current[-1]['epoch'] if current else None,
                         'current_add_interval_overlaps':overlap,'search_p50_ms':1000*quantile([q['search_wall_s'] for q in good],.5) if good else None,
                         'search_p95_ms':1000*quantile([q['search_wall_s'] for q in good],.95) if good else None,
                         'extra_audit_p50_ms':1000*quantile([q['audit_wall_s'] for q in good],.5) if good else None,'error':reader['error']})
        if writer['error']:errors.append({'round':n,'writer':True,**writer['error']})
        errors.extend({'round':n,**e} for e in trial['parent_errors']+trial['history_errors'])
        gate=(len(complete)==UPDATES and writer['error'] is None and not trial['parent_errors'] and not trial['history_errors']
              and len(trial['history'])==UPDATES+1 and trial['initial_immutable_files_unchanged'] and trial['answers_files']==0
              and all(c==0 for c in trial['child_return_codes']) and len(trial['child_return_codes'])==READERS+1
              and all(not r['error'] and r['exit_reason']=='writer-stop-plus-20' and r['excluded_warm_queries']==1 for r in trial['readers'])
              and all(r['last_current_epoch']==UPDATES and r['current_add_interval_overlaps']>0 for r in rows if r['round']==n)
              and trial['final_head']==complete[-1]['snapshot_id'])
        assert gate==trial['gate_passed']
        walls=[1000*(e['end_s']-e['add_start_s']) for e in complete]
        round_rows.append({'round':n,'completed_updates':len(complete),'history_verified':len(trial['history']),'gate':gate,
                           'writer_add_p50_ms':quantile(walls,.5),'writer_add_p95_ms':quantile(walls,.95),
                           'initial_logical_bytes':trial['stats_before']['logical_file_bytes'],
                           'retained_logical_bytes':trial['stats_after']['logical_file_bytes'],
                           'initial_immutable_files':trial['initial_immutable_files'],'storage_by_directory_bytes':trial['stats_after']['by_directory_bytes']})
    metrics={'rounds':round_rows,'readers':rows,'verified_queries':valid_queries,'retained_queries':retained_total,
             'current_queries':valid_queries-retained_total,'overlapping_current_queries':overlap_total,'verified_record_bindings':4*valid_queries,
             'post_run_history_verifications':history_total,'post_run_history_record_bindings':4*history_total,'excluded_warm_queries':ROUNDS*READERS,
             'errors':errors,'all_rounds_gate_passed':all(r['gate'] for r in round_rows)}
    save(out/'derived-metrics.json',metrics);save(out/'source-checksums.json',checks)
    resources={str(p).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').glob('*')) if p.suffix in ('.py','.html')}
    save(out/'source-resource.json',{'files':resources,'all_rkv_python_and_html_bytes':sum(x['bytes'] for x in resources.values()),
                                   'benchmark_native_specific_bytes':0,'scope':'Runtime source ledger only; Python/SQLite/Zlib/OS/filesystem/hardware and harness costs are not a complete deployment accounting.'})
    validation={'frozen_commit':args.freeze,'all_57_modules_protocol_driver_and_generated_source_hashes_match':True,
                'runtime_other_than_version_byte_identical_to_v032':True,'formal_rounds':ROUNDS,'formal_reader_processes':ROUNDS*READERS,
                'writer_updates_requested':ROUNDS*UPDATES,'all_rounds_gate_passed':metrics['all_rounds_gate_passed'],
                'errors':errors,'tests':{'run':220,'passed':219,'skipped':1,'failed':0,'log_sha256':digest(Path(args.test_log).read_bytes())},
                'remote_model_calls':0,'cold_cache':None,'cross_machine':None,'inference_quality':None}
    save(out/'validation.json',validation)
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    labels=[f"R{r['round']}/P{r['reader']}" for r in rows];x=list(range(len(rows)))
    axes[0,0].bar(x,[r['current'] for r in rows],label='current HEAD',color='#277da1')
    axes[0,0].bar(x,[r['retained'] for r in rows],bottom=[r['current'] for r in rows],label='retained SID0',color='#90be6d')
    axes[0,0].set_xticks(x,labels,rotation=60);axes[0,0].set_ylabel('Verified queries');axes[0,0].legend()
    axes[0,1].bar(x,[r['current_add_interval_overlaps'] for r in rows],color='#43aa8b');axes[0,1].set_xticks(x,labels,rotation=60)
    axes[0,1].set_ylabel('Current query / add interval overlaps')
    for n,trial in enumerate(trials,1):
        events=[e for e in trial['writer']['events'] if 'snapshot_id' in e]
        axes[1,0].plot([e['epoch'] for e in events],[1000*(e['end_s']-e['add_start_s']) for e in events],label=f'round {n}',alpha=.8)
    axes[1,0].set_xlabel('Update epoch');axes[1,0].set_ylabel('Writer add wall (ms)');axes[1,0].legend()
    axes[1,1].bar([r['round'] for r in round_rows],[r['retained_logical_bytes']/1048576 for r in round_rows],color='#577590')
    axes[1,1].set_xticks([1,2,3]);axes[1,1].set_xlabel('Fresh root / round');axes[1,1].set_ylabel('Retained Memory logical MiB')
    fig.suptitle('Synthetic single writer / four readers: observed correctness and cost')
    fig.savefig(out/'snapshot-concurrency.png',dpi=160);plt.close(fig)
    text=f'''# v0.33.0 实验报告：单写入 / 多读取的快照一致性

## 结论与适用范围

冻结的三轮门槛 **{sum(r['gate'] for r in round_rows)}/3** 通过。正式审计查询
{valid_queries} 次，其中当前 HEAD {valid_queries-retained_total} 次、显式初始快照 {retained_total} 次；
原句/位置绑定 {4*valid_queries} 条。当前查询与实际 add 区间重叠 {overlap_total} 次。
观察到的 worker/父进程/历史审计错误共 {len(errors)} 条。所有错误均在 JSON 中保留，不重试失败操作。

这项结果只覆盖本机、合成资料、单 writer / 四 reader 的三个有界调度样本。
它不估计生产错误率，也不证明任意并发顺序、多个 writer、断电恢复或无限上下文可行。
没有模型调用，不能据此声称回答质量、多跳推理或长期会话收益。冷缓存/跨机器未测。

## 背景与冻结假设

v0.32 的代码/数学词法通道科学净空间 0/36、联合 0/36，不能用原生化改变该表示输出的字节数。
因此本版没有继续在这些源文件上搜索规则，而是检查动态证据记忆尚未直接覆盖的并发读取边界。
假设是：默认 search 在一次调用开始选定 HEAD 后，应绑定到一个不可变 SID；writer 提交新的 SID
不应让同一次结果混入其他 epoch。显式指定旧 SID 则须继续读旧内容。

运行库共 57 模块，除版本字符串外与实际 v0.32 标签逐字节相同；本版添加实验 driver、独立
审计测试、分析脚本和协议，没有给写入/读出路径打并发修复补丁。冻结提交 `{args.freeze}`。
协议与 driver SHA、全部运行库 SHA 和所有 81 个合成源 SHA 在 environment.json 保存并于分析时核对。

## 数据、流程与审计方法

每轮新建独立源目录及 Memory，默认 compact-budget-v3 / fixed / Zlib，原 replay budget 不变。
每个源文件 {len(corpus(0))}B、{DOCUMENTS} 条 JSONL，4 条 sentinel 每版同时改变四位 epoch，
其余 2044 条背景不变。使用排序键、固定分隔符、ASCII 转义和 CRLF，包含雪字与引号转义。
这是可按 corpus() 再生的合成结构，未将它包装成公开科学任务质量数据。

每轮四个 reader 先用初始 SID 各执行一次排除的预热/审计；共 {ROUNDS*READERS} 次，
不计正式查询。全部 READY 后才释放 START，writer 连续提交 80 次更新。
reader 每十次有一次显式初始 SID，其他读取当前 HEAD；STOP 后再完成 20 次并要求最后当前读到80。
独立进程清除模型配置环境，所有循环和超时预先固定，失败不重试，不因结果改变预算。

每个查询要求完整 sentinel 集合、四个相同结果 SID、正确原始 key/path/offset/length/SHA，
title 和 sentences 必须等于该 SID 的原 JSONL；再从 CAS 读完整源并验证预生成完整源 SHA。
显式旧 SID 必须保持 epoch0，当前读 epoch 不得倒退。审计时间独立记账，未伪装成免费验证。
查询结束后不再次使用可变 HEAD 决定本次预期版本，避免把正常更新误判为不一致。

writer 停止后，全部成功提交历史 SID 再做完整源与四 locator 审计。
独立于正式 reader 的历史复查共 {history_total} 次 / {4*history_total} 条记录绑定。
原始 Memory 中除 HEAD.json 外所有文件要求仍存在且 SHA 不变，answers 必须为空。
下述区间重叠使用同机 perf_counter：只说明操作持续区间重叠，不证明任何特定指令恰好同时访问。

## 逐轮结果与真实成本

|轮|成功更新|历史复查|门槛|add中位ms|add P95 ms|初始B|保留全部历史B|
|---|---:|---:|---|---:|---:|---:|---:|
'''
    for r in round_rows:text+=f"|{r['round']}|{r['completed_updates']}|{r['history_verified']}|{r['gate']}|{r['writer_add_p50_ms']:.3f}|{r['writer_add_p95_ms']:.3f}|{r['initial_logical_bytes']}|{r['retained_logical_bytes']}|\n"
    text+='''
|轮/reader|正式审计|旧SID|当前|当前不同epoch|重叠|最后epoch|search中位ms|search P95 ms|额外审计中位ms|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
'''
    for r in rows:text+=f"|{r['round']}/{r['reader']}|{r['verified']}|{r['retained']}|{r['current']}|{r['distinct_current_epochs']}|{r['current_add_interval_overlaps']}|{r['last_current_epoch']}|{r['search_p50_ms']:.3f}|{r['search_p95_ms']:.3f}|{r['extra_audit_p50_ms']:.3f}|\n"
    text+='''
![快照实验操作数量、区间重叠、写入延迟与保留空间](snapshot-concurrency.png)

查询频率与具体交错由 OS 调度决定，不要求三轮次数相同，也不将较多查询当质量提升。
所有延迟是含同机争用的观测值，没有串行基线或因果隔离，不能据此声称并行加速。
保留空间包含实际 CAS、全部历史索引/manifest、HEAD 和 answers；分目录原数见 derived-metrics.json。
没有删除历史版本或不收费的隐式全量副本来降低成本。源文件和数据生成/审计/协调的额外 CPU、
工作盘空间不属于 Memory 的目录统计；OS/Python/SQLite/Zlib/硬件不是零成本。
source-resource.json 单列全部运行库源码与 HTML，未将它称为完整部署占用。

## 验证、可复现执行与边界

本版完整单元套件 220 项，219 通过、1 Windows 权限项跳过，0 失败。
新增审计测试不仅覆盖有效结果，还故意损坏投影/位置/SID/记录集合及完整源身份，确认验证器拒绝。
原测试仍覆盖旧归档 v1–v6、Memory 历史、来源格式、预算和显式候选边界。
本实验没有使用 Gear 原生库；发布库只作为兼容功能资产，不能冒充本次性能依据。

```powershell
python -m unittest discover -s tests -v
python -m scripts.run_memory_concurrency --work <不存在的工作目录> --out <不存在的结果目录>
python -m scripts.analyze_memory_concurrency --out <结果目录> --freeze <冻结提交> --test-log <完整测试日志>
```

environment.json 记录 Python/OS/CPU 数与计时器，round-1/2/3.json 公开逐次查询、writer、
完整 SID/源 SHA、历史复查、错误、子进程状态和目录字节。它们都是合成身份和运行记录，
不含真实科学语料、私有文档或模型密钥。Release CI/实际资产和仓库外安装记录随发行资产另附。

未覆盖多 writer、删除/GC、进程被杀、磁盘满、文件系统损坏、远程共享盘、断电、冷缓存、
异机与不同解释器/文件系统。零观察错误不是全局线性一致性的形式证明；本次重叠不是对每个
publication 指令的穷举调度。E3 神经预测、推理质量、多跳与长期对话目标仍未完成。

## 后续路线

若三轮门槛通过，下一项冻结单 writer 的故障注入：在固定提交边界终止子进程，检查可见 HEAD
与历史证据，再独立恢复写入；明确区分进程中断与真正断电。若不通过，保留本版原始失败，
下一版依据具体错误提出最小修正及固定复测，不能把失败重新运行后覆盖成通过。
不调整已评估科学任务预算，不因本次正确性结果默认切换检索或压缩表示。
'''
    (out/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n')
    print(json.dumps({'verified_queries':valid_queries,'errors':len(errors),'rounds_passed':sum(r['gate'] for r in round_rows)},ensure_ascii=False))


if __name__=='__main__':main()
