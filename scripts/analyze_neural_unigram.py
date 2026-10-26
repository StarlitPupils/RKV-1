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
from rkv1.neural_frame import HEADER,MAGIC,METHODS as ORIGINAL_METHODS,_restore
from scripts.run_neural_unigram import METHODS
FRAME_CODES={**ORIGINAL_METHODS,'unigram':4}
from scripts.neural_inputs import load
from scripts.run_memory_concurrency import save


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--work',required=True);p.add_argument('--inputs',required=True);p.add_argument('--freeze',required=True);p.add_argument('--model-freeze-commit',required=True);p.add_argument('--test-log',required=True);p.add_argument('--unigram-freeze-commit',required=True)
    args=p.parse_args();out=Path(args.out);work=Path(args.work);public=Path('results/v0.36.0')
    env=json.loads((out/'environment.json').read_text('utf-8'));model_freeze=json.loads((public/'model-freeze.json').read_text('utf-8'));train=json.loads((public/'training.json').read_text('utf-8'))
    for name in ('model-freeze.json','training.json'):assert (public/name).read_bytes()==subprocess.check_output(['git','show',args.model_freeze_commit+':results/v0.36.0/'+name])
    assert digest((public/'training.json').read_bytes())==model_freeze['training_report_sha256']
    assert env['model_freeze']==model_freeze and env['model_sha256']==model_freeze['model_sha256']==train['model_sha256']
    assert train['epochs']==1
    uf_raw=Path('results/v0.37.0/unigram-model-freeze.json').read_bytes();uf=json.loads(uf_raw)
    assert uf_raw==subprocess.check_output(['git','show',args.unigram_freeze_commit+':results/v0.37.0/unigram-model-freeze.json'])
    assert uf==env['unigram_freeze'] and uf['new_neural_training_runs']==0 and uf['training_inputs']==train['training_inputs']
    assert model_freeze['training_runs']==1 and train['test_evaluations']==0 and train['training_symbols']==95292
    checks=implementation_checksums();assert len(checks)==61 and checks==env['implementation_checksums']
    old=json.loads(Path('results/v0.36.0/source-checksums.json').read_text('utf-8'))
    for name,sha in checks.items():
        assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))==sha
        if name in old and name!='__init__.py':assert sha==old[name]
    assert set(checks)-set(old)=={'unigram_frame.py'}
    for rel,sha in env['protocol_driver_and_training_sha256'].items():assert digest(Path(rel).read_bytes())==sha==digest(subprocess.check_output(['git','show',args.freeze+':'+rel]))
    testlog=Path(args.test_log).read_text('utf-8');assert 'Ran 230 tests' in testlog and 'OK (skipped=1)' in testlog
    jobs=load(args.inputs,'test');truth={m['id']:(m,raw) for m,raw in jobs};assert env['inputs']==[m for m,_ in jobs]
    assert not ({m['id'] for m in train['training_inputs']} & set(truth))
    trials=[]
    for n in range(1,4):
        r=json.loads((out/f'round-{n}.json').read_text('utf-8'));assert r['round']==n and len(r['trials'])==20
        assert {(t['id'],t['method']) for t in r['trials']}=={(name,method) for name in truth for method in METHODS}
        for t in r['trials']:
            assert t['error'] is None,'Formal failure retained; inspect original log before producing an acceptance report'
            pack=t['pack'];restore=t['restore'];info=pack['info'];meta,raw=truth[t['id']]
            directory=work/f'round-{n}'/f"{t['order']:02d}-{t['method']}";frame=(directory/'frame.rkvnn').read_bytes()
            assert digest(frame)==pack['frame_sha256']==restore['frame_sha256'] and len(frame)==pack['frame_bytes']==restore['frame_bytes']
            assert (directory/'prefix.restored').read_bytes()==raw and restore['bytewise_and_SHA_equal'] is True
            fields=HEADER.unpack_from(frame);magic,version,method,length,model_bytes,payload_bytes,bits,raw_sha,model_sha,payload_sha=fields
            assert magic==(b'RKVUNI01' if t['method']=='unigram' else MAGIC) and version==1 and method==FRAME_CODES[t['method']] and length==len(raw)==8192 and raw_sha.hex()==meta['prefix_sha256']
            assert len(frame)==HEADER.size+model_bytes+payload_bytes==info['frame_bytes'] and info['header_bytes']==HEADER.size==134
            assert (model_bytes,payload_bytes,bits)==(info['model_zlib_bytes'],info['payload_bytes'],info['payload_bits'])
            assert digest(frame[HEADER.size+model_bytes:])==payload_sha.hex()
            if t['method'] in ('neural','unigram'):
                expected=uf if t['method']=='unigram' else model_freeze
                assert model_sha.hex()==expected['model_sha256'] and model_bytes==expected['model_zlib6_bytes'] and info['model_raw_bytes']==expected['model_bytes']
                assert digest(_restore(1,frame[HEADER.size:HEADER.size+model_bytes],expected['model_bytes']))==expected['model_sha256']
            else:assert model_bytes==0 and model_sha==bytes(32) and bits==payload_bytes*8
            for stage in (pack,restore):assert stage['fsyncs']==1 and stage['no_numpy_imported'] and stage['no_input_project_imported']
            if t['method']!='unigram':
                prior=json.loads(Path(f'results/v0.36.0/round-{n}.json').read_text('utf-8'))['trials']
                old_t=next(x for x in prior if x['id']==t['id'] and x['method']==t['method'])
                assert old_t['pack']['frame_sha256']==pack['frame_sha256']
            trials.append(t)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+name for name in checks}|{'rkv1/memory_demo.html'}
    common=files['rkv1/neural_frame.py']['bytes'];candidate=common+files['rkv1/neural_small.py']['bytes']+files['rkv1/arithmetic.py']['bytes'];all_source=sum(x['bytes'] for x in files.values());static=common+files['rkv1/unigram_frame.py']['bytes']+files['rkv1/arithmetic.py']['bytes']
    rows=[]
    for meta,raw in jobs:
        for method in METHODS:
            ts=[t for t in trials if t['id']==meta['id'] and t['method']==method];infos=[t['pack']['info'] for t in ts]
            assert len(ts)==3 and all(t['pack']['frame_sha256']==ts[0]['pack']['frame_sha256'] and info==infos[0] for t,info in zip(ts,infos))
            info=infos[0];source=candidate if method=='neural' else static if method=='unigram' else common
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
    save(out/'source-resource.json',{'files':files,'total_bytes':all_source,'plain_common_frame_source_B_bytes':common,'neural_frame_plus_predictor_and_arithmetic_B_bytes':candidate,'unigram_frame_and_arithmetic_B_bytes':static,
                                   'model_is_already_in_each_frame':True,'source_B_and_full_source_C_are_alternative_allocations':True,'model_native_specific_bytes':0,'dictionary_bytes':0,
                                   'training_program_bytes':sum(Path(n).stat().st_size for n in ('scripts/train_neural_small.py','scripts/neural_inputs.py')),
                                   'training_numpy_distribution_bytes':train['numpy_installed_distribution_bytes'],'scope':'Full runtime source ledger; training dependencies/time separately allocated. Common Python/OS/FS not a complete deployment account.'})
    save(out/'validation.json',{'runtime_and_protocol_freeze':args.freeze,'original_neural_freeze_commit':args.model_freeze_commit,'diagnostic_static_model_freeze_commit':args.unigram_freeze_commit,'all61_modules_and_protocol_and_training_inputs_model_identity_verified':True,
                               'all60_actual_frames_and_restored_files_match_recorded_SHA_and_original_prefix_bytes':True,'all3_round_frame_bytes_and_model_and_bits_identical':True,
                               'all120_stages_no_numpy_or_scientific_input_import':True,'actual_file_fsyncs':120,'scientific_space_pass':metrics['scientific_space_pass'],'scientific_joint_pass':metrics['scientific_joint_pass'],
                               'tests':{'run':230,'passed':229,'skipped':1,'failed':0,'log_sha256':digest(Path(args.test_log).read_bytes())},'remote_model_calls':0,'model_quality':None,'cold_cache':None,'cross_machine':None})
    static_points=[];diagnostic=[]
    for meta,_ in jobs:
        nn=next(r for r in rows if r['id']==meta['id'] and r['method']=='neural');u=next(r for r in rows if r['id']==meta['id'] and r['method']=='unigram')
        diagnostic.append({'id':meta['id'],'science':meta['family']!='synthetic-negative-control','nn_payload_bytes':nn['payload_bytes'],'unigram_payload_bytes':u['payload_bytes'],
                           'nn_payload_smaller':nn['payload_bytes']<u['payload_bytes'],'nn_net_B_bytes':nn['net_B_bytes'],'unigram_net_B_bytes':u['net_B_bytes'],
                           'nn_net_B_smaller':nn['net_B_bytes']<u['net_B_bytes']})
        for method in ('zlib','zstd','lzma'):
            b=next(r for r in rows if r['id']==meta['id'] and r['method']==method);space=u['net_B_bytes']<b['net_B_bytes']
            static_points.append({'id':meta['id'],'baseline':method,'science':meta['family']!='synthetic-negative-control','space_pass':space,
                                  'joint_pass':space and u['pack_stage_wall_s_median_s']<=b['pack_stage_wall_s_median_s'] and u['restore_stage_wall_s_median_s']<=b['restore_stage_wall_s_median_s']})
    metrics.update({'unigram_points':static_points,'neural_vs_unigram':diagnostic,'all48_original_v036_frame_SHA_reproduced':True,
                    'unigram_scientific_space_pass':sum(r['space_pass'] for r in static_points if r['science']),
                    'unigram_scientific_joint_pass':sum(r['joint_pass'] for r in static_points if r['science'])})
    save(out/'derived-metrics.json',metrics)
    source_meta=json.loads((out/'source-resource.json').read_text('utf-8'))
    source_meta['historical_neural_training_program_bytes']=source_meta.pop('training_program_bytes')
    source_meta['historical_neural_training_numpy_distribution_bytes']=source_meta.pop('training_numpy_distribution_bytes')
    source_meta['new_unigram_build_program_bytes']=Path('scripts/build_unigram.py').stat().st_size
    source_meta['new_neural_training_runs']=0;source_meta['new_static_model_builds']=1
    save(out/'source-resource.json',source_meta)
    names=[m['id'] for m,_ in jobs];labels=['SciPy prefix','SymPy prefix','LaTeX prefix','Noise'];x=list(range(4));fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    colors=['#e76f51','#8e7dbe','#277da1','#90be6d','#f9c74f']
    for i,method in enumerate(METHODS):
        chosen=[next(r for r in rows if r['id']==name and r['method']==method) for name in names];xx=[k+(i-2)*.16 for k in x]
        for a,key in ((axes[0,0],'payload_bytes'),(axes[0,1],'net_B_bytes')):a.bar(xx,[r[key] for r in chosen],width=.16,label=method,color=colors[i])
        for a,phase in ((axes[1,0],'pack'),(axes[1,1],'restore')):a.bar(xx,[1000*r[phase+'_stage_wall_s_median_s'] for r in chosen],width=.16,label=method,color=colors[i])
    axes[0,0].set_ylabel('Arithmetic / ordinary codec payload B');axes[0,1].set_ylabel('Actual full frame + dedicated source B')
    handles,legend_labels=axes[0,1].get_legend_handles_labels();fig.legend(handles,legend_labels,loc='outside lower center',ncol=5,fontsize=9)
    for a,phase in ((axes[1,0],'Encode'),(axes[1,1],'Restore')):a.set_yscale('log');a.set_ylabel(phase+' phase median ms (log)')
    for a in axes.flat:a.set_xticks(x,labels,rotation=15)
    fig.suptitle('Fixed same-training unigram diagnostic: no neural retraining or unseen validation')
    fig.savefig(out/'neural-unigram-diagnostic.png',dpi=160);plt.close(fig)
    nn_payload_wins=sum(r['nn_payload_smaller'] for r in diagnostic if r['science']);nn_full_wins=sum(r['nn_net_B_smaller'] for r in diagnostic if r['science'])
    text=f"""# v0.37.0 实验报告：同训练资料的unigram廉价统计诊断

## 结论与范围

原计划60编码恢复对/120新进程阶段/120文件fsync均精确恢复，三轮帧一致。
48个原v0.36条件的帧SHA逐项复现；神经模型未重训，静态模型只在相同95292B训练资料构建一次。
科学3对象中，神经payload比unigram小 **{nn_payload_wins}/3**，神经完整B成本较小 **{nn_full_wins}/3**。
unigram对三种普通codec的科学净空间 **{metrics['unigram_scientific_space_pass']}/9**、联合 **{metrics['unigram_scientific_joint_pass']}/9**；
神经仍为净空间{metrics['scientific_space_pass']}/9、联合{metrics['scientific_joint_pass']}/9。
不能把胜过昂贵神经模型当成胜过普通codec，也不能把这次已见前缀诊断称作独立新验证。

## 冻结设计

v0.36首个神经原型实现精确恢复但9/9位流已比普通codec大，本版补上缺失的低成本训练统计对照。
先冻结协议/新模块{args.freeze}，再提交静态模型{args.unigram_freeze_commit}，之后才评估。
原60个runtime模块除版本字符串字节不变，包括原神经帧/MLP/算术coder；只新增unigram_frame.py。
新帧magic RKVUNI01独立，旧神经帧和主Archive拒绝，未改主格式或默认。
神经模型仍{model_freeze['model_sha256']}，新神经训练0次；原浮点训练/NumPy代价保留v0.36记录。

静态控制对同3个训练前缀数256字节频数，每字节保底1，余量32512按count比例floor并按字节升序补齐，
总32768，与神经CDF相同保底/精度/舍入。测试时不更新，使用同一个32bit整数算术码器。
模型520B，Zlib6后{uf['model_zlib6_bytes']}B；神经原模型6944B、压缩4878B。
两模型每帧都完整收费，不使用未实现的模型共享。新静态构建到fsync {uf['build_through_model_fsync_wall_s']:.6f}s、峰值RSS {uf['peak_rss_bytes']}B。
无NumPy参与新统计构建或任何编解码阶段；共同解释器/OS/普通codec依赖未全额分配。

测试原样为三个科学8192B前缀+同8192B噪声，文件/精确范围/SHA与v0.36相同，不是未知项目或完整源文件。
不调context/epoch/位宽，不重训或搜索规则来改善这些前缀；三个重复不是三个新科学样本。
各阶段180s上限，无重跑；记录codec/输入/模型读取、lazy import状态、同步写入、审计、完整进程时间和RSS。

## 模型能力和费用分解

|对象|神经payload B|unigram payload B|NN payload较小|神经完整B|unigram完整B|NN完整B较小|
|---|---:|---:|---|---:|---:|---|
"""
    for r in diagnostic:text+=f"|{labels[names.index(r['id'])]}|{r['nn_payload_bytes']}|{r['unigram_payload_bytes']}|{r['nn_payload_smaller']}|{r['nn_net_B_bytes']}|{r['unigram_net_B_bytes']}|{r['nn_net_B_smaller']}|\n"
    text+="""
|对象|方法|头B|模型ZlibB|payload B|完整帧B|净B总计|编码中位ms|恢复中位ms|
|---|---|---:|---:|---:|---:|---:|---:|---:|
"""
    for r in rows:text+=f"|{labels[names.index(r['id'])]}|{r['method']}|134|{r['model_zlib_bytes']}|{r['payload_bytes']}|{r['frame_bytes']}|{r['net_B_bytes']}|{1000*r['pack_stage_wall_s_median_s']:.3f}|{1000*r['restore_stage_wall_s_median_s']:.3f}|\n"
    text+=f"""
![payload、完整成本和CPU分离](neural-unigram-diagnostic.png)

source B：plain公共neural_frame.py {common}B，NN公共+算术+预测器 {candidate}B，unigram公共+算术+静态模块 {static}B。
source C为全部61模块+HTML {all_source}B，替代分配不相加，权重已在帧内不再双计。
新静态统计比神经少4675B压缩模型费用；实际payload方向与完整成本方向应分开判断。
即使NN在某些payload上更小，也不代表此单对象规模足以抵消模型/解码器/CPU开销。
对普通codec是否有收益以各9点独立门槛为准，不从只胜NN推出生产净收益。
不同版本调度/阶段预载状态允许不同，帧SHA复现不等于时间严格复现；本版CPU为同一固定计划的观测中位。

## 独立核验与复现

分析核对实际60帧/恢复文件及原prefix、两个实际嵌入模型SHA、三轮bit/模型账本，
原48条件和v0.36帧SHA相同；源码/协议/训练输入/模型锁定记录都与先前Git提交匹配。
完整230单元项229通过/1权限跳过；新增正频率/总数、空训练拒绝、all256/Unicode/CRLF恢复、
损坏/尾数据/模型表拒绝及新旧magic隔离。实际老v0.36发行reader拒绝在发布后外部smoke单独验证。
原始JSON保留60对每阶段时间/RSS/I/O/模型、所有输入SHA；unigram-model-freeze.json记录预评估构建。
模型、科学prefix/帧/恢复副本及私有研究留本地，公开重建代码/URL/SHA，不输出原始科学语料或密钥。
0新模型API调用。冷缓存/跨机器未测，有限诊断非形式证明或长期/生产稳定性验证。

## 后续边界

保留当前神经候选和unigram控制的完整结果，不修改本次模型或重复同一gold直至正结果。
若二者均未胜普通codec，不能靠“廉价统计比NN好”升级默认；需要新假设及另冻独立数据，
并计全部模型、程序与运行时费用才值得继续集成。字节精确不推出模型智能，
E3净收益、长期对话、多跳/回答质量和无限上下文目标仍未验收。
"""
    noise_id=next(m['id'] for m,_ in jobs if m['family']=='synthetic-negative-control')
    noise_nn=next(r for r in rows if r['id']==noise_id and r['method']=='neural');noise_u=next(r for r in rows if r['id']==noise_id and r['method']=='unigram')
    text+=f'''

## 噪声与源码分配的反向案例

噪声中，NN位流{noise_nn['payload_bytes']}B、静态{noise_u['payload_bytes']}B；但NN完整帧{noise_nn['frame_bytes']}B，
仍大于静态完整帧{noise_u['frame_bytes']}B。source B下NN总计{noise_nn['net_B_bytes']}B、静态{noise_u['net_B_bytes']}B，
NN小{noise_u['net_B_bytes']-noise_nn['net_B_bytes']}B，因为静态模块包含独立帧解析和模型构建，专用源码较大。
source C将整个相同运行库分给两者时，大小顺序又与帧本身相同。
这是分配方案敏感性，不能称NN能压缩随机噪声或胜过普通codec；两模型在噪声上的普通codec联合门槛均未过。
该反向案例和所有原行保留，不能为使结论简单而删掉。新静态构建脚本{Path('scripts/build_unigram.py').stat().st_size}B，
构建资料/源、CPU/RSS单列；原NN训练及NumPy成本仍见v0.36，不当作本版重训或向静态模型收取。
'''
    (out/'SUMMARY.md').write_text(text,encoding='utf-8',newline='\n')
    print(json.dumps({'pairs':len(trials),'nn_payload_wins_science':nn_payload_wins,'nn_full_B_wins_science':nn_full_wins,'unigram_net_space_pass':metrics['unigram_scientific_space_pass'],'unigram_joint_pass':metrics['unigram_scientific_joint_pass']}))


if __name__=='__main__':main()
