"""Audit fixed online campaign and all source/state/CPU allocations."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess

from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from rkv1.online_frame import HEADER,MAGIC,METHODS
from rkv1.online_counts import RULE_SHA,RULE_BYTES
from scripts.online_inputs import load
from scripts.run_memory_concurrency import save


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('out','work','inputs','freeze','input-freeze','test-log'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();out=Path(args.out);work=Path(args.work)
    env=json.loads((out/'environment.json').read_text('utf-8'))
    checks=implementation_checksums();assert checks==env['implementation_checksums']
    for name,value in checks.items():assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))==value
    for name,value in env['driver_protocol_sha256'].items():
        assert digest(Path(name).read_bytes())==value==digest(subprocess.check_output(['git','show',args.freeze+':'+name]))
    input_raw=Path('docs/online-counts-inputs.json').read_bytes()
    assert input_raw==subprocess.check_output(['git','show',args.input_freeze+':docs/online-counts-inputs.json'])
    jobs=load(args.inputs);truth={m['id']:(m,raw) for m,raw in jobs}
    assert env['inputs']['inputs']==[m for m,_ in jobs]
    testlog=Path(args.test_log).read_text('utf-8')
    assert 'Ran 237 tests' in testlog and 'OK (skipped=1)' in testlog
    trials=[];identities={}
    for n in range(1,4):
        record=json.loads((out/f'round-{n}.json').read_text('utf-8'))
        assert len(record['trials'])==25
        assert {(t['id'],t['method']) for t in record['trials']}=={(i,m) for i in truth for m in METHODS}
        for t in record['trials']:
            assert t['error'] is None,'Formal failure retained; do not report success or overwrite'
            directory=work/f'round-{n}'/f"{t['order']:02d}-{t['method']}"
            frame=(directory/'frame.rkvonline').read_bytes();meta,raw=truth[t['id']]
            assert digest(frame)==t['pack']['frame_sha256']==t['restore']['frame_sha256']
            assert (directory/'slice.restored').read_bytes()==raw and t['restore']['bytewise_and_SHA_equal']
            magic,version,code,length,model_n,pn,bits,rs,rules,ps=HEADER.unpack_from(frame)
            assert magic==MAGIC and version==1 and code==METHODS[t['method']] and model_n==0
            assert length==8192==len(raw) and rs.hex()==meta['sha256'] and digest(frame[HEADER.size:])==ps.hex()
            assert len(frame)==134+pn==t['pack']['info']['frame_bytes'] and bits==t['pack']['info']['payload_bits']
            assert rules==(RULE_SHA if code<2 else bytes(32))
            assert (bits+7)//8==pn
            if code<2:
                assert t['pack']['info']['state']['logical_state_bytes']==(516 if code==0 else 132612)
                assert t['pack']['info']['embedded_model_bytes']==0
            key=(t['id'],t['method'])
            if key in identities:assert identities[key]==digest(frame)
            identities[key]=digest(frame)
            for phase in ('pack','restore'):
                s=t[phase];assert s['fsyncs']==1 and s['no_numpy_imported'] and s['no_input_project_imported']
            trials.append(t)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
           for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+k for k in checks}|{'rkv1/memory_demo.html'}
    common=sum(files['rkv1/'+k]['bytes'] for k in ('online_frame.py','neural_frame.py','codecs.py'))
    extra=sum(files['rkv1/'+k]['bytes'] for k in ('online_counts.py','arithmetic.py'))
    total=sum(x['bytes'] for x in files.values())
    rows=[]
    for meta,_ in jobs:
        for method in METHODS:
            selected=[t for t in trials if t['id']==meta['id'] and t['method']==method]
            info=selected[0]['pack']['info'];source=common+(extra if METHODS[method]<2 else 0)
            row={'id':meta['id'],'scientific':meta['scientific'],'method':method,'frame_bytes':info['frame_bytes'],
                 'payload_bytes':info['payload_bytes'],'source_B_bytes':source,'net_B_bytes':source+info['frame_bytes'],
                 'net_C_bytes':total+info['frame_bytes'],'logical_state_bytes':info.get('state',{}).get('logical_state_bytes',0),
                 'owned_state_containers_bytes':info.get('state',{}).get('owned_state_containers_bytes',0),
                 'peak_process_rss_bytes':max(t[p]['peak_rss_bytes'] for t in selected for p in ('pack','restore'))}
            for metric in ('codec_wall_s','codec_cpu_s','process_wall_s'):
                row[metric+'_pair_median']=statistics.median(t['pack'][metric]+t['restore'][metric] for t in selected)
            rows.append(row)
    comparisons=[]
    for row in rows:
        if row['method'] not in ('order0','order1'):continue
        for baseline in ('zlib','zstd','lzma'):
            other=next(r for r in rows if r['id']==row['id'] and r['method']==baseline)
            space=row['net_B_bytes']<=other['net_B_bytes']
            timings=all(row[k+'_pair_median']<=other[k+'_pair_median'] for k in ('codec_wall_s','codec_cpu_s','process_wall_s'))
            comparisons.append({'id':row['id'],'scientific':row['scientific'],'method':row['method'],'baseline':baseline,
                                'payload_win':row['payload_bytes']<=other['payload_bytes'],'frame_win':row['frame_bytes']<=other['frame_bytes'],
                                'net_B_win':space,'net_C_win':row['net_C_bytes']<=other['net_C_bytes'],'time_all_three_win':timings,
                                'joint_win':space and timings})
    save(out/'derived-metrics.json',{'rows':rows,'comparisons':comparisons})
    save(out/'source-checksums.json',checks)
    save(out/'source-resource.json',{'files':files,'total_bytes':total,'plain_common_B_bytes':common,
         'online_extra_B_bytes':extra,'rule_configuration_bytes':len(RULE_BYTES),'rule_configuration_sha256':RULE_SHA.hex(),
         'rule_configuration_charged_in_source_not_added_twice':True,'external_model_bytes':0,'dictionary_bytes':0,
         'new_training_runs':0,'B_and_C_alternative_allocations':True,'native_specific_bytes':0,
         'diagnostic_programs':{k:{'bytes':Path(k).stat().st_size,'sha256':digest(Path(k).read_bytes())}
            for k in ('scripts/run_online_counts.py','scripts/online_inputs.py','scripts/analyze_online_counts.py')},
         'scope':'No complete OS/Python/third-party deployment TCO claim; logical state and RSS separately reported'})
    save(out/'validation.json',{'pairs':75,'fresh_codec_stage_processes':150,'file_fsyncs':150,'all_byte_exact':True,
         'deterministic_frame_conditions':25,'unit_tests_run':237,'unit_tests_passed':236,'unit_tests_skipped':1,
         'test_log_sha256':digest(Path(args.test_log).read_bytes()),'runtime_module_count':len(checks),'html_files':1,
         'runtime_protocol_freeze':args.freeze,'input_freeze':args.input_freeze,'no_numpy_in_codec_workers':True,
         'no_input_project_execution':True,'remote_model_calls':0,'cold_cache':None,'cross_machine':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(15,5),layout='constrained')
    colors=['#2563eb','#d97706','#16a34a','#9333ea','#64748b']
    for index,method in enumerate(METHODS):
        selected=[next(r for r in rows if r['id']==meta['id'] and r['method']==method) for meta,_ in jobs]
        x=[n+(index-2)*.15 for n in range(5)]
        axes[0].bar(x,[r['net_B_bytes'] for r in selected],.14,color=colors[index],label=method)
        axes[1].bar(x,[r['process_wall_s_pair_median'] for r in selected],.14,color=colors[index])
        axes[2].bar(x,[r['peak_process_rss_bytes']/(1<<20) for r in selected],.14,color=colors[index])
    for ax in axes:
        ax.set_xticks(range(5),['SciPy','SymPy','LaTeX','Noise','Cycle']);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    axes[0].set_title('Frame + allocated source B');axes[0].set_ylabel('Bytes')
    axes[1].set_title('Fresh pack + restore process time');axes[1].set_ylabel('Median seconds (log)');axes[1].set_yscale('log')
    axes[2].set_title('Whole-process peak RSS');axes[2].set_ylabel('MiB (max of six stages)')
    fig.legend(*axes[0].get_legend_handles_labels(),loc='outside lower center',ncol=5,frameon=False)
    fig.suptitle('RKV-1 v0.39: fixed new suffix ranges; 75 byte-exact pairs / 150 fresh codec stages')
    fig.savefig(out/'online-counts-cost.png',dpi=160);plt.close(fig)
    print(json.dumps({method:{key:sum(c[key] for c in comparisons if c['scientific'] and c['method']==method)
                              for key in ('payload_win','net_B_win','joint_win')}
                      for method in ('order0','order1')}))


if __name__=='__main__':main()
