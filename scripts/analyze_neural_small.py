"""Audit frozen self-contained neural frames, not loss-only compression proxies."""
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
from rkv1.neural_frame import HEADER,MAGIC,METHODS,_restore
from scripts.neural_inputs import load
from scripts.run_memory_concurrency import save


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--work',required=True);p.add_argument('--inputs',required=True);p.add_argument('--freeze',required=True);p.add_argument('--model-freeze-commit',required=True);p.add_argument('--test-log',required=True)
    args=p.parse_args();out=Path(args.out);work=Path(args.work);public=Path('results/v0.36.0')
    env=json.loads((out/'environment.json').read_text('utf-8'));model_freeze=json.loads((public/'model-freeze.json').read_text('utf-8'));train=json.loads((public/'training.json').read_text('utf-8'))
    for name in ('model-freeze.json','training.json'):assert (public/name).read_bytes()==subprocess.check_output(['git','show',args.model_freeze_commit+':results/v0.36.0/'+name])
    assert digest((public/'training.json').read_bytes())==model_freeze['training_report_sha256']
    assert env['model_freeze']==model_freeze and env['model_sha256']==model_freeze['model_sha256']==train['model_sha256']
    assert train['epochs']==1
    assert model_freeze['training_runs']==1 and train['test_evaluations']==0 and train['training_symbols']==95292
    checks=implementation_checksums();assert len(checks)==60 and checks==env['implementation_checksums']
    old=json.loads(Path('results/v0.35.0/source-checksums.json').read_text('utf-8'))
    for name,sha in checks.items():
        assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))==sha
        if name in old and name!='__init__.py':assert sha==old[name]
    assert set(checks)-set(old)=={'arithmetic.py','neural_frame.py','neural_small.py'}
    for rel,sha in env['protocol_driver_and_training_sha256'].items():assert digest(Path(rel).read_bytes())==sha==digest(subprocess.check_output(['git','show',args.freeze+':'+rel]))
    testlog=Path(args.test_log).read_text('utf-8');assert 'Ran 227 tests' in testlog and 'OK (skipped=1)' in testlog
    jobs=load(args.inputs,'test');truth={m['id']:(m,raw) for m,raw in jobs};assert env['inputs']==[m for m,_ in jobs]
    assert not ({m['id'] for m in train['training_inputs']} & set(truth))
    trials=[]
    for n in range(1,4):
        r=json.loads((out/f'round-{n}.json').read_text('utf-8'));assert r['round']==n and len(r['trials'])==16
        assert {(t['id'],t['method']) for t in r['trials']}=={(name,method) for name in truth for method in METHODS}
        for t in r['trials']:
            assert t['error'] is None,'Formal failure retained; inspect original log before producing an acceptance report'
            pack=t['pack'];restore=t['restore'];info=pack['info'];meta,raw=truth[t['id']]
            directory=work/f'round-{n}'/f"{t['order']:02d}-{t['method']}";frame=(directory/'frame.rkvnn').read_bytes()
            assert digest(frame)==pack['frame_sha256']==restore['frame_sha256'] and len(frame)==pack['frame_bytes']==restore['frame_bytes']
            assert (directory/'prefix.restored').read_bytes()==raw and restore['bytewise_and_SHA_equal'] is True
            fields=HEADER.unpack_from(frame);magic,version,method,length,model_bytes,payload_bytes,bits,raw_sha,model_sha,payload_sha=fields
            assert magic==MAGIC and version==1 and method==METHODS[t['method']] and length==len(raw)==8192 and raw_sha.hex()==meta['prefix_sha256']
            assert len(frame)==HEADER.size+model_bytes+payload_bytes==info['frame_bytes'] and info['header_bytes']==HEADER.size==134
            assert (model_bytes,payload_bytes,bits)==(info['model_zlib_bytes'],info['payload_bytes'],info['payload_bits'])
            assert digest(frame[HEADER.size+model_bytes:])==payload_sha.hex()
            if t['method']=='neural':
                assert model_sha.hex()==env['model_sha256'] and model_bytes==model_freeze['model_zlib6_bytes'] and info['model_raw_bytes']==6944
                assert digest(_restore(1,frame[HEADER.size:HEADER.size+model_bytes],6944))==env['model_sha256']
            else:assert model_bytes==0 and model_sha==bytes(32) and bits==payload_bytes*8
            for stage in (pack,restore):assert stage['fsyncs']==1 and stage['no_numpy_imported'] and stage['no_input_project_imported']
            trials.append(t)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+name for name in checks}|{'rkv1/memory_demo.html'}
    common=files['rkv1/neural_frame.py']['bytes'];candidate=common+files['rkv1/neural_small.py']['bytes']+files['rkv1/arithmetic.py']['bytes'];all_source=sum(x['bytes'] for x in files.values())
    rows=[]
    for meta,raw in jobs:
        for method in METHODS:
            ts=[t for t in trials if t['id']==meta['id'] and t['method']==method];infos=[t['pack']['info'] for t in ts]
            assert len(ts)==3 and all(t['pack']['frame_sha256']==ts[0]['pack']['frame_sha256'] and info==infos[0] for t,info in zip(ts,infos))
            info=infos[0];source=candidate if method=='neural' else common
            rows.append({'id':meta['id'],'method':method,**info,'dedicated_source_B_bytes':source,'net_B_bytes':info['frame_bytes']+source,
                         'all_runtime_C_bytes':all_source,'net_C_bytes':info['frame_bytes']+all_source,
                         **{phase+'_'+field+'_median_s':statistics.median(t[phase][field] for t in ts) for phase in ('pack','restore') for field in ('codec_wall_s','stage_wall_s','process_wall_s','write_fsync_wall_s')},
                         'pack_peak_rss_max_B':max(t['pack']['peak_rss_bytes'] for t in ts),'restore_peak_rss_max_B':max(t['restore']['peak_rss_bytes'] for t in ts)})
    points=[]
    for meta,_ in jobs:
        neural=next(r for r in rows if r['id']==meta['id'] and r['method']=='neural')
        for method in ('zlib','zstd','lzma'):
            plain=next(r for r in rows if r['id']==meta['id'] and r['method']==method);space=neural['net_B_bytes']<plain['net_B_bytes']
            points.append({'id':meta['id'],'baseline':method,'science':meta['family']!='synthetic-negative-control','space_B_pass':space,
                           'joint_pass':space and neural['pack_stage_wall_s_median_s']<=plain['pack_stage_wall_s_median_s'] and neural['restore_stage_wall_s_median_s']<=plain['restore_stage_wall_s_median_s'],
                           'neural_payload_alone_larger':neural['payload_bytes']>plain['payload_bytes']})
    science=[x for x in points if x['science']];noise=[x for x in points if not x['science']]
    metrics={'rows':rows,'points':points,'scientific_space_pass':sum(x['space_B_pass'] for x in science),'scientific_joint_pass':sum(x['joint_pass'] for x in science),
             'scientific_points':len(science),'noise_space_pass':sum(x['space_B_pass'] for x in noise),'noise_joint_pass':sum(x['joint_pass'] for x in noise),
             'science_neural_payload_larger_points':sum(x['neural_payload_alone_larger'] for x in science),'formal_pairs':len(trials),'fresh_subprocess_stages':2*len(trials),'actual_fsyncs':2*len(trials)}
    save(out/'derived-metrics.json',metrics);save(out/'source-checksums.json',checks)
    save(out/'source-resource.json',{'files':files,'total_bytes':all_source,'plain_common_frame_source_B_bytes':common,'neural_frame_plus_predictor_and_arithmetic_B_bytes':candidate,
                                   'model_is_already_in_each_frame':True,'source_B_and_full_source_C_are_alternative_allocations':True,'model_native_specific_bytes':0,'dictionary_bytes':0,
                                   'training_program_bytes':sum(Path(n).stat().st_size for n in ('scripts/train_neural_small.py','scripts/neural_inputs.py')),
                                   'training_numpy_distribution_bytes':train['numpy_installed_distribution_bytes'],'scope':'Full runtime source ledger; training dependencies/time separately allocated. Common Python/OS/FS not a complete deployment account.'})
    save(out/'validation.json',{'runtime_and_protocol_freeze':args.freeze,'pre_test_model_freeze_commit':args.model_freeze_commit,'all60_modules_and_protocol_and_training_inputs_model_identity_verified':True,
                               'all48_actual_frames_and_restored_files_match_recorded_SHA_and_original_prefix_bytes':True,'all3_round_frame_bytes_and_model_and_bits_identical':True,
                               'all96_stages_no_numpy_or_scientific_input_import':True,'actual_file_fsyncs':96,'scientific_space_pass':metrics['scientific_space_pass'],'scientific_joint_pass':metrics['scientific_joint_pass'],
                               'tests':{'run':227,'passed':226,'skipped':1,'failed':0,'log_sha256':digest(Path(args.test_log).read_bytes())},'remote_model_calls':0,'model_quality':None,'cold_cache':None,'cross_machine':None})
    names=[m['id'] for m,_ in jobs];labels=['SciPy prefix','SymPy prefix','LaTeX prefix','Noise'];fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True);x=list(range(4))
    neural=[next(r for r in rows if r['id']==name and r['method']=='neural') for name in names]
    axes[0,0].bar(x,[r['model_zlib_bytes'] for r in neural],label='model zlib6',color='#e76f51');axes[0,0].bar(x,[r['payload_bytes'] for r in neural],bottom=[r['model_zlib_bytes'] for r in neural],label='arithmetic payload',color='#2a9d8f')
    axes[0,0].bar(x,[134]*4,bottom=[r['model_zlib_bytes']+r['payload_bytes'] for r in neural],label='header',color='#577590')
    axes[0,0].plot(x,[min(r['frame_bytes'] for r in rows if r['id']==name and r['method']!='neural') for name in names],'ko-',label='best plain full frame');axes[0,0].set_ylabel('Actual self-contained frame B');axes[0,0].legend(fontsize=8)
    colors=['#e76f51','#277da1','#90be6d','#f9c74f']
    for i,method in enumerate(METHODS):
        chosen=[next(r for r in rows if r['id']==name and r['method']==method) for name in names];xx=[k+(i-1.5)*.18 for k in x]
        axes[0,1].bar(xx,[r['net_B_bytes'] for r in chosen],width=.18,label=method,color=colors[i])
        axes[1,0].bar(xx,[1000*r['pack_stage_wall_s_median_s'] for r in chosen],width=.18,label=method,color=colors[i])
        axes[1,1].bar(xx,[1000*r['restore_stage_wall_s_median_s'] for r in chosen],width=.18,label=method,color=colors[i])
    axes[0,1].set_ylabel('Full frame + dedicated source B');axes[0,1].legend(fontsize=8)
    for a,title in ((axes[1,0],'Encode phase median ms (log)'),(axes[1,1],'Restore phase median ms (log)')):a.set_yscale('log');a.set_ylabel(title)
    for a in axes.flat:a.set_xticks(x,labels,rotation=15)
    fig.suptitle('Frozen tiny neural predictor: exact bytes, weights, decoder source and CPU cost');fig.savefig(out/'neural-small-cost.png',dpi=160);plt.close(fig)
    text=f'''# v0.36.0 实验报告：E3小型神经预测与确定性整数算术编码

## 结论

本版实现可运行的因果小MLP、整数CDF/32bit算术编码与自包含实验帧。
原计划48编码恢复对、96独立阶段进程、96次实际文件fsync全部完成，逐字节恢复和SHA一致，
三轮帧/模型/bit长度相同。**科学净空间{metrics['scientific_space_pass']}/9、联合{metrics['scientific_joint_pass']}/9通过**；
噪声净空间{metrics['noise_space_pass']}/3、联合{metrics['noise_joint_pass']}/3。
科学神经位流本身在{metrics['science_neural_payload_larger_points']}/9比较中已经大于普通codec payload，
还没计算每帧{model_freeze['model_zlib6_bytes']}B权重或专用源码。因此不集成当前候选、不默认切换，
没有依据为同一概率模型追加Rust库或共享模型格式来声称空间收益。

这是第一个E3机械原型，不表示E3净收益验收完成；它也不否定所有神经方法。
模型训练loss、预测与压缩的联系不等于本项目回答能力或无限上下文；模型质量未测，远程模型请求0。

## 路线与冻结顺序

原路线要求预测未确定的信息仍能精确恢复，并将模型/解码成本计入。
[DeepZip](https://arxiv.org/abs/1811.08162)展示神经预测+算术编码；
[Language Modeling Is Compression](https://arxiv.org/html/2309.10668v2)讨论模型大小对完整编码成本的影响。
[Nacrith2026预印本](https://arxiv.org/abs/2602.19626v2)采用不同规模/硬件与CDF配置，未在本项目复现；
其论文数字不是本机结果。此处为CPU范围的微型MLP工程候选，不冒称论文架构复现或最优模型。

先提交运行库/协议`{args.freeze}`，单元227项226通过/1权限跳过；再训练一次，
将模型与训练元数据SHA于`{args.model_freeze_commit}`提交冻结，明确测试评估0，然后才执行原48对。
未用测试集早停、选epoch、扩大训练量或重复重训；训练后源码和规则未动。
所有60运行库模块、protocol/driver/trainer、模型、原完整文件/prefix及3轮帧SHA逐项核对。
旧57模块除版本字符串不变，主Archive/Memory/CAS/默认不改。

## 数据、模型与精确恢复

三个项目的第一文件前缀作训练，第二文件前8192B作测试，另固定8192B噪声。
训练95292B，科学测试24576B，噪声8192B；均来自docs/text-lanes-inputs.json固定档案。
不是完整源文件结果；同项目文件分离不等于未知领域，这六档案v0.32已见但未作神经超参搜索。
原科学代码仅作为字节读入，未执行/import；完整及prefix SHA均验证，原始数据/帧/恢复副本不发布。

context4字节，257输入×4维embedding→16维拼接→ReLU8→256输出，共3468参数。
量化Q256/signed int16，模型体6936B、8B magic共6944B；完整模型Zlib6后{model_freeze['model_zlib6_bytes']}B，
每个神经帧实际携带一份。整数层、固定exp近似表、正频率CDF总32768，模型不在线更新。
32bit算术码流携带原真实字节选择；解码只用已解码前缀和帧内权重，完全不需要NumPy或重训。
不将浮点预测结果当作原文恢复；量化后的实际帧就是评测对象。

`RKVNN001`独立实验magic，公共头134B，含长度及原文/模型/payload SHA。
普通帧用相同格式的Zlib6/Zstd3/LZMA6，模型长度0；神经带全部模型+位流，不使用免费外部权重或auto回退。
长度、padding、串联/尾数据、模型和原文校验失败必须拒绝；主Archive拒绝实验帧。
测试覆盖全256字节、空数据、Unicode/CRLF、随机和非零网络参数、skew概率边界、损坏/截断/额外数据。

## 实际大小和CPU

|输入（各8192B）|方法|头B|模型压缩B|payload B|完整帧B|专用源B|净B总计|编码phase中位ms|恢复phase中位ms|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
'''
    for r in rows:text+=f"|{labels[names.index(r['id'])]}|{r['method']}|134|{r['model_zlib_bytes']}|{r['payload_bytes']}|{r['frame_bytes']}|{r['dedicated_source_B_bytes']}|{r['net_B_bytes']}|{1000*r['pack_stage_wall_s_median_s']:.3f}|{1000*r['restore_stage_wall_s_median_s']:.3f}|\n"
    text+=f'''
![完整帧、权重、专用源及编解码CPU](neural-small-cost.png)

source B给plain分配公共neural_frame.py {common}B，神经再加predictor/算术源，总{candidate}B。
source C为整个RKV运行库60模块+HTML共{all_source}B；二者为替代方案，不相加。
权重已在帧内，不再重复添加。直接codec长度单列为plain payload，避免将公共header当节省。
神经payload单独已更大的事实说明，当前概率模型即使假设零模型存储成本也没有本次空间优势。
共享模型或原生化都不能改变同一位流的大小，因此本版不为追正结果增加新格式/库。

时间表用包含原文件读取与模型读取/首次lazy import、codec、写文件fsync和额外恢复审计的stage wall；
纯codec、I/O/审计、完整进程wall/RSS及预载模块分别保留在原始JSON。
没有排除预热调用，96个阶段都未导入NumPy或输入项目代码。父统计/绘图进程的NumPy不冒称codec依赖。
冷缓存/跨机器未测；三个输入/三个重复不能外推成跨域统计或生产吞吐结论。

## 训练和依赖成本

固定seed20261026、1epoch、batch256、Adam lr.002、float64、梯度norm clip5。
NumPy{train['numpy_version']}，线程环境设为1（未独立确认底层线程池）。
导入{train['numpy_import_wall_s']:.6f}s；训练到模型fsync {train['training_to_model_fsync_wall_s']:.6f}s；
训练阶段峰值RSS {train['peak_rss_bytes']}B；训练批次更新前加权loss {train['weighted_training_loss_nats']:.6f}nats，
量化饱和参数{train['quantized_saturations']}个。这是训练指标，不能替代测试压缩结果。
训练NumPy发行文件{train['numpy_installed_distribution_bytes']}B（每项SHA/字节在training.json），
额外依赖盘点耗时{train['dependency_inventory_wall_s']:.6f}s、之后进程峰值RSS {train['process_peak_rss_after_dependency_inventory_bytes']}B。
这些训练/盘点成本独立报告，没有把已安装训练依赖当免费；纯整数编解码不需要该发行包。
训练程序/输入本身另列源码成本，不把模型作为未经收费的世界知识。
共同Python/OS/普通codec运行时和文件系统元数据未全额分配；本报告不是完整部署账单，
float训练跨机复现未测，但相同帧整数恢复不依赖复现训练。

## 复现、交付与下一项

原始48对/96阶段日志JSON、训练与模型冻结元数据、完整源账本和验证独立提供。
训练模型与科学帧保留本地；公开重建代码/数据URL及SHA，不分发原始科学语料或私有研究。
先按NEURAL-SMALL.md训练并锁定模型，再运行scripts.run_neural_small；分析器还读取实际帧和恢复文件，
核对原prefix字节，而非仅相信worker布尔值。发布CI/实际资产/物理外部安装核验另附发行资产。

当前小候选未过净成本门槛。下一项若继续E3，优先冻结同训练资料的静态unigram+同算术coder对照，
区分当前神经条件预测是否优于廉价训练统计，以及权重成本占多少；这只能是已见前缀上的诊断，
不能称新验证或调参进步。之后再决定是否值得设计新预测规则/独立数据，不扩大对象N掩盖本次失败。
长期对话、多跳推理、模型回答质量和无限上下文目标仍未实现；模型API预算未新增。
'''
    (out/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n');print(json.dumps({k:v for k,v in metrics.items() if k not in ('rows','points')}))


if __name__=='__main__':main()
