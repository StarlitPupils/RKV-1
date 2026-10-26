"""Recompute every fixed-boundary gate, including files outside stats groups."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from scripts.run_memory_interruptions import CASES, ROUNDS, EXIT_CODE, corpus, save


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--freeze',required=True);p.add_argument('--test-log',required=True)
    args=p.parse_args();out=Path(args.out);env=json.loads((out/'environment.json').read_text('utf-8'));checks=implementation_checksums()
    assert len(checks)==57 and checks==env['implementation_checksums']
    for name,sha in checks.items():
        assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))==sha
        if name!='__init__.py':assert Path('rkv1',name).read_bytes()==subprocess.check_output(['git','show','v0.34.0:rkv1/'+name])
    for rel,sha in env['protocol_and_driver_sha256'].items():
        assert digest(Path(rel).read_bytes())==sha==digest(subprocess.check_output(['git','show',args.freeze+':'+rel]))
    assert env['source_sha256_by_epoch']=={str(n):digest(corpus(n)) for n in range(3)}
    log=Path(args.test_log).read_text('utf-8');assert 'Ran 223 tests' in log and 'OK (skipped=1)' in log
    trials=[json.loads((out/f'round-{n}.json').read_text('utf-8')) for n in range(1,ROUNDS+1)]
    rows=[];errors=[];audits=0
    for n,t in enumerate(trials,1):
        assert t['round']==n and [c['stage'] for c in t['cases']]==list(CASES)
        for c in t['cases']:
            stage=c['stage'];assert c['round']==n
            before=c['initial_inventory'];after=c['after_exit_inventory'];final=c['final_inventory']
            for inv in (before,after,final):
                assert len(inv['files'])==inv['file_count'] and sum(v['bytes'] for v in inv['files'].values())==inv['logical_file_bytes']
            old={k:v for k,v in before['files'].items() if k!='HEAD.json'}
            immutable_exit=all(after['files'].get(k)==v for k,v in old.items())
            immutable_final=all(final['files'].get(k)==v for k,v in old.items())
            staged=all(final['files'].get(k)==v for k,v in after['files'].items() if k!='HEAD.json')
            pending={k:v for k,v in after['files'].items() if k.startswith('.memory-head-')}
            pending_kept=all(final['files'].get(k)==v for k,v in pending.items())
            pending_count_good=len(pending)==(1 if stage==CASES[5] else 0)
            assert (immutable_exit,immutable_final,staged,pending_kept,pending_count_good)==(
                c['initial_immutable_files_unchanged_after_exit'],c['initial_immutable_files_unchanged_after_recovery'],
                c['all_staged_non_HEAD_files_unchanged_after_recovery'],c['pending_HEAD_files_retained_unchanged'],c['expected_pending_HEAD_count_observed'])
            marker=c['marker'];control=c['worker_result']
            hook=(c['exit_code']==0 and control is not None and control['stage']==stage and marker is None) if stage==CASES[-1] else (
                c['exit_code']==EXIT_CODE and marker is not None and marker['stage']==stage and marker['exit_code']==EXIT_CODE)
            assert hook==c['hook_matched']
            if marker and stage in CASES[1:3]:
                rel='cas/'+marker['details']['relative_path'];assert rel not in before['files']
                if stage==CASES[1]:assert rel not in after['files']
                else:assert after['files'][rel]=={'bytes':marker['details']['published_bytes'],'sha256':marker['details']['published_sha256']}
            if marker and stage==CASES[3]:
                sid=marker['details']['snapshot_id'];assert f'cas/snapshots/{sid}.rkvs' in after['files'] and f'manifests/{sid}.json' not in after['files']
            if marker and stage==CASES[4]:assert 'manifests/'+marker['details']['snapshot_id']+'.json' in after['files']
            if marker and stage==CASES[5]:
                d=marker['details'];assert after['files'][d['pending_name']]=={'bytes':d['pending_bytes'],'sha256':d['pending_sha256']}
            expected=1 if stage in CASES[-2:] else 0;assert c['expected_visible_epoch']==expected
            values=[c['initial_audit'],*c['observed_after_exit'].values(),*[r['audit'] for r in c['recovery'].values() if r is not None],*c['history']]
            for a in values:
                if a is None:continue
                assert a['verified_records']==4 and a['source_sha256']==env['source_sha256_by_epoch'][str(a['epoch'])] and a['source_bytes']==env['source_bytes'];audits+=1
            current=c['observed_after_exit'].get('current');initial=c['observed_after_exit'].get('initial')
            state_good=(current is not None and current['epoch']==expected and initial is not None and initial['epoch']==0 and initial['snapshot_id']==c['initial_snapshot_id'])
            if expected==0:state_good=state_good and current['snapshot_id']==c['initial_snapshot_id']
            recovery_good=(all(c['recovery'].get('epoch'+str(i)) is not None and c['recovery']['epoch'+str(i)]['audit']['epoch']==i for i in (1,2))
                           and [h['epoch'] for h in c['history']]==[0,1,2])
            gate=(not c['timeout'] and hook and not c['errors'] and immutable_exit and immutable_final and staged and pending_kept and pending_count_good
                  and state_good and recovery_good and c['final_stats'] is not None and c['final_stats']['by_directory_bytes']['answers']==0)
            assert gate==c['gate_passed']
            errors.extend({'round':n,'stage':stage,**e} for e in c['errors'])
            extra=[]
            for label,inv in [('after_exit',after),('final',final)]:
                stats=c['after_exit_stats' if label=='after_exit' else 'final_stats']
                if stats is None:extra.append(None);continue
                covered={k:v for k,v in inv['files'].items() if k=='HEAD.json' or k.split('/')[0] in ('cas','indexes','manifests','answers')}
                assert sum(v['bytes'] for v in covered.values())==stats['logical_file_bytes']
                extra.append(inv['logical_file_bytes']-stats['logical_file_bytes'])
            rows.append({'round':n,'stage':stage,'gate_passed':gate,'exit_code':c['exit_code'],'visible_epoch':current['epoch'] if current else None,
                         'exit_logical_file_bytes':after['logical_file_bytes'],'final_logical_file_bytes':final['logical_file_bytes'],
                         'exit_stats_uncovered_bytes':extra[0],'final_stats_uncovered_bytes':extra[1],
                         'pending_HEAD_files':len(pending),'pending_HEAD_bytes':sum(v['bytes'] for v in pending.values()),
                         'recovery_add_ms':1000*c['recovery']['epoch1']['wall_s'] if c['recovery'].get('epoch1') else None,
                         'future_add_ms':1000*c['recovery']['epoch2']['wall_s'] if c['recovery'].get('epoch2') else None,
                         'process_wall_ms':1000*c['process_wall_s'],'errors':c['errors']})
    aggregate=[]
    for stage in CASES:
        r=[x for x in rows if x['stage']==stage]
        aggregate.append({'stage':stage,'passed':sum(x['gate_passed'] for x in r),'cases':len(r),
                          'exit_bytes':[x['exit_logical_file_bytes'] for x in r],'final_bytes':[x['final_logical_file_bytes'] for x in r],
                          'uncovered_bytes':[x['final_stats_uncovered_bytes'] for x in r],
                          'recovery_add_median_ms':statistics.median(x['recovery_add_ms'] for x in r if x['recovery_add_ms'] is not None),
                          'future_add_median_ms':statistics.median(x['future_add_ms'] for x in r if x['future_add_ms'] is not None)})
    metrics={'cases':rows,'by_stage':aggregate,'case_count':len(rows),'passed':sum(r['gate_passed'] for r in rows),'errors':errors,
             'hard_exit_cases':sum(r['exit_code']==EXIT_CODE for r in rows),'success_controls':sum(r['exit_code']==0 for r in rows),
             'complete_source_locator_audits':audits,'verified_original_record_bindings':audits*4,
             'historical_SID_audits':sum(len(c['history']) for t in trials for c in t['cases']),
             'retained_pending_HEAD_files':sum(r['pending_HEAD_files'] for r in rows),'retained_pending_HEAD_bytes':sum(r['pending_HEAD_bytes'] for r in rows)}
    save(out/'derived-metrics.json',metrics);save(out/'source-checksums.json',checks)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+n for n in checks}|{'rkv1/memory_demo.html'}
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),'native_specific_bytes':0,
                                   'scope':'All57 Python modules andHTML, excludes common runtime/OS/FS/harness, not complete deployment cost.'})
    save(out/'validation.json',{'freeze':args.freeze,'all57_runtime_modules_and_protocol_and_drivers_match_freeze':True,
                               'runtime_except_version_byte_identical_to_v034':True,'independently_recomputed_cases':len(rows),'passed':metrics['passed'],
                               'all_full_file_inventories_and_stats_coverage_reconciled':True,'errors':errors,
                               'tests':{'run':223,'passed':222,'skipped':1,'failed':0,'log_sha256':digest(Path(args.test_log).read_bytes())},
                               'remote_model_calls':0,'cold_cache':None,'cross_machine':None,'power_loss':None,'model_quality':None})
    labels=[str(n) for n in range(1,len(CASES)+1)];x=list(range(len(CASES)))
    fig,axes=plt.subplots(1,3,figsize=(14.5,4.5),constrained_layout=True)
    axes[0].bar(x,[r['passed'] for r in aggregate],color='#2a9d8f');axes[0].set_xticks(x,labels);axes[0].set_ylim(0,3.7)
    axes[0].set_xlabel('Fixed boundary / control (report table 1-8)');axes[0].set_ylabel('Passed fresh-root cases / 3')
    axes[1].bar(x,[statistics.median(r['exit_bytes'])/1024 for r in aggregate],label='after exit',color='#e9c46a')
    axes[1].plot(x,[statistics.median(r['final_bytes'])/1024 for r in aggregate],'o-',label='after recovery + future add',color='#264653')
    axes[1].set_xticks(x,labels);axes[1].set_xlabel('Fixed boundary / control');axes[1].set_ylabel('All logical file KiB (including pending HEAD)');axes[1].legend()
    bars=axes[2].bar(x,[statistics.median(r['uncovered_bytes']) for r in aggregate],color='#e76f51')
    axes[2].bar_label(bars);axes[2].set_xticks(x,labels);axes[2].set_ylim(0,115)
    axes[2].set_xlabel('Fixed boundary / control');axes[2].set_ylabel('Final bytes outside Memory.stats groups')
    fig.suptitle('Owned-child hard exit and single-shot recovery: process boundaries, not power loss')
    fig.savefig(out/'interruption-recovery.png',dpi=160);plt.close(fig)
    text=f'''# v0.35.0 实验报告：固定写入边界的进程硬退出与恢复

## 结论及实际范围

原计划 **{metrics['passed']}/{len(rows)}** 个案例通过：3轮，每轮7个固定硬退出点与1个成功控制，
共{metrics['hard_exit_cases']}次os._exit(77)及{metrics['success_controls']}个正常返回控制。
{audits}次完整源/四locator审计、{audits*4}条原文绑定、{metrics['historical_SID_audits']}次恢复后的历史SID审计完成。
父进程在每次退出后只进行一次epoch1恢复add和一次epoch2未来add，没有重复直到成功。
观察到错误{len(errors)}条，所有失败记录若存在均保留，不以重跑替换原始案例。

发现的非零成本：{metrics['retained_pending_HEAD_files']}个根目录临时HEAD，共{metrics['retained_pending_HEAD_bytes']}B，
来自已fsync、尚未发布名称时硬退出。恢复没有自动清理；这些文件也没有被Memory.stats原分组覆盖。
本报告使用完整递归文件账本收费，并单列stats差额，未把未提交工作产物当作不存在。
这不是断电、内核崩溃、外部强杀、生产负载或模型智能验证。冷缓存和跨机器未测，远程模型调用0。

## 背景与冻结控制

v0.33发现Windows HEAD读/替换共享冲突，v0.34修正后在原单writer/四reader负载3/3通过。
本版不再修改运行库逻辑；57个Python模块除版本字符串与实际v0.34标签逐字节相同。
冻结提交`{args.freeze}`包含本协议、driver及原审计器。运行前/后核验全部runtime、driver、协议SHA。
源生成复用2048记录/4sentinel合成JSONL，epoch0/1/2完整SHA固定，默认fixed/Zlib/compact-budget-v3与原预算。
不并发读取，不调整预算，不加重试、不清理暂存文件，不因结果扩大/缩小案例数。

## 退出点与原始观测

每个case独立新目录：先提交epoch0，保存SID、全部文件SHA；源改epoch1，启动唯一拥有的子进程。
hook仅在子进程内安装，目标边界写树外marker并flush/fsync后os._exit(77)，跳过Python finally。
10s超时及预期退出码/marker不匹配均为失败；只允许终止本实验创建的子进程。
成功控制不安装退出hook，完成add后退出0。marker/log开销不当成生产应用性能。

|编号|固定边界/控制|预期可见epoch|通过/3|退出后全部文件B（三轮）|最终全部文件B（三轮）|最终stats未覆盖B|
|---|---|---:|---:|---|---|---|
'''
    for i,r in enumerate(aggregate,1):text+=f"|{i}|{r['stage']}|{1 if i>=7 else 0}|{r['passed']}|{r['exit_bytes']}|{r['final_bytes']}|{r['uncovered_bytes']}|\n"
    text+='''
编号1在add前；2/3在首个新CAS对象的原发布前/后；4在CAS快照完成、索引前；
5在索引/manifest完成、HEAD开始前；6在HEAD临时文件fsync后、名称发布前；
7在HEAD名称发布后、Memory.add返回前；8是完整成功控制。
原始marker包含实际触发边界、对象/快照或临时HEAD身份；分析器独立检查相应文件是否已存在，
而不是只信worker输出的布尔值。前三阶段可能留下对象/快照但不能提前改变可见HEAD。

## 恢复和证据核验

退出点1–6须仍为最初SID/epoch0，7/8须已是epoch1。每个case都显式读最初SID。
随后对原epoch1源和相同label'e1'只调用一次add，允许重用已验证对象或已完成索引；再改epoch2、
label'e2'调用一次add。恢复后显式审计0/1/2三个历史版本。
每次查询恰为四sentinel、同一SID，key/path/offset/length/SHA/title/sentences均与原JSONL一致，
再读完整CAS源核对预生成SHA。所有初始非HEAD文件，以及退出时已有的非HEAD暂存/不可变文件，
恢复后都必须保留相同SHA；answers为空。没有将本地原文件的当前内容冒充历史证据。

![全部原案例门槛与完整文件成本](interruption-recovery.png)

## 时间、空间与部署成本

|编号|恢复add中位ms|后续add中位ms|
|---|---:|---:|
'''
    for i,r in enumerate(aggregate,1):text+=f"|{i}|{r['recovery_add_median_ms']:.3f}|{r['future_add_median_ms']:.3f}|\n"
    text+=f'''
这些只是每点三个新目录的观测值，不是加速/吞吐对照。进程wall包含启动、导入、hook、marker同步、
应用写入和退出；恢复add wall与额外来源审计分别记录，不将仪器化成本冒充免费生产路径。
完整文件逻辑B不等于物理分配块、目录/MFT/日志/设备写缓存成本；以上未测。
每个case最终保留epoch0/1/2，不删除任何退出残留。stats原API仍按cas/indexes/manifests/answers/HEAD分组；
根目录临时HEAD不在这些组中，所以完整树比stats多94B的案例必须照实收费。
未加入自动回收器或新的恢复格式，不能宣称硬退出不会产生垃圾文件。
完整递归源码账本57模块+HTML共{sum(v['bytes'] for v in files.values())}B，逐项与SHA集合核对；
无新增自有DLL、权重或字典，公共Python/Windows/SQLite/Zlib/OS等未全额分配，不是完整部署成本。

## 测试、复现与未覆盖项

完整套件223项，222通过、1Windows权限项跳过。正式24case与单元套件分开计数。
原始round-1/2/3.json提供每case全部文件身份/字节、marker/退出码、退出后与恢复后的SID/审计、
恢复结果、时间、stats及全部错误；environment.json固定源/模块/协议/driver SHA和Python/平台。
无真实科学语料、私有文档、个人报告或密钥；合成源可通过corpus()再生。

```powershell
python -m scripts.run_memory_interruptions --work <不存在的新工作目录> --out <不存在的新结果目录>
python -m scripts.analyze_memory_interruptions --out <结果目录> --freeze <冻结提交> --test-log <完整单元测试日志>
```

未覆盖任意机器指令时刻终止、外部kill、目录同步/断电、磁盘满/损坏、网络盘、多writer/GC、
老Windows/FS降级路径或长期稳定性。本机明确选中的Python hook是有限模型，不是全崩溃状态枚举。
24/24只支持本轮协议，不能外推成恢复系统的形式证明；单writer中断通过也不构成生产就绪。

## 后续

若原计划全通过，回到E3：先冻结本地小型预测器/熵编码候选的确定性概率与训练/验证分离，
计权重/字典/解码器/运行库/训练与编码解码CPU，再测逐字节恢复和净成本；模型可能没有净收益，
不能把预测器loss或payload减小当完整压缩提升。若本轮有失败则下一版先针对原错误最小修正，
不重跑覆盖。长期对话、多跳推理、真实回答质量与无限上下文目标仍未实现，0新模型预算不变。
'''
    (out/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n')
    print(json.dumps({k:metrics[k] for k in ('case_count','passed','hard_exit_cases','success_controls','complete_source_locator_audits','retained_pending_HEAD_bytes')}))


if __name__=='__main__':main()
