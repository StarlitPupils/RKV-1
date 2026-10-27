"""Independent actual-frame/source recovery and complete-code-cost audit."""
import argparse,json,statistics,subprocess,time
from pathlib import Path
from collections import Counter
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from scripts.index_frame import decode,HEADER,METHODS,CODECS
from scripts.postings_transform import canonical
from scripts.run_source_alignment import exclusive

def main():
    begin=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','work','out','freeze','test-log'):p.add_argument('--'+name,required=True)
    args=p.parse_args();root=Path.cwd();out=Path(args.out);work=Path(args.work);manifest=json.loads(Path(args.manifest).read_bytes());env=json.loads((out/'environment.json').read_bytes())
    checks=implementation_checksums();assert checks==env['implementation_checksums']
    for name,sha in checks.items():assert sha==digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))
    for name,sha in env['program_protocol_sha256'].items():assert sha==digest((root/name).read_bytes())==digest(subprocess.check_output(['git','show',args.freeze+':'+name]))
    log=Path(args.test_log).read_text('utf-8');assert 'Ran 310 tests' in log and 'OK (skipped=1)' in log
    source_files={name:{'bytes':(root/name).stat().st_size,'sha256':digest((root/name).read_bytes())} for name in ['rkv1/'+n for n in checks]+['rkv1/memory_demo.html']}
    runtime_bytes=sum(v['bytes'] for v in source_files.values());wrapper_bytes=(root/'scripts/index_frame.py').stat().st_size;transform_bytes=(root/'scripts/postings_transform.py').stat().st_size
    originals={}
    for dataset,entry in manifest['datasets'].items():
        raw=Path(entry['path']).read_bytes();assert digest(raw)==entry['sha256'] and len(raw)==entry['bytes'];originals[dataset]=raw
    rows=[];frame_references={};raw_report_bytes=0;artifact_bytes=0;extra_decodes=0
    for n in (1,2,3):
        for dataset,entry in manifest['datasets'].items():
            for codec in ('raw','zlib','zstd','lzma'):
                for method in ('plain','typed'):
                    label=f'round-{n}-{dataset}-{method}-{codec}';child=(out/(label+'.json')).read_bytes();parent_raw=(out/(label+'-parent.json')).read_bytes();r=json.loads(child);parent=json.loads(parent_raw);raw_report_bytes+=len(child)+len(parent_raw)
                    assert parent['return_code']==0 and parent['error'] is None and parent['child_sha256']==digest(child) and parent['parent_full_process_wall_s']>=r['worker_wall_s']>0
                    assert r['round']==n and r['dataset']==dataset and r['method']==method and r['codec']==codec and r['role']==entry['role']
                    folder=work/label;frame=(folder/'index.rkvpost').read_bytes();restored=(folder/'restored-index.json').read_bytes();source=originals[dataset]
                    assert len(frame)==r['frame_bytes'] and digest(frame)==r['frame_sha256'] and restored==source and digest(restored)==r['restored_sha256']==entry['sha256']==r['source_sha256']
                    decoded=decode(frame);extra_decodes+=1;assert decoded==restored and json.loads(decoded)==json.loads(source)
                    h=HEADER.unpack_from(frame);assert h[1]==METHODS[method] and h[2]==CODECS[codec] and h[3]==len(source) and h[4]==r['encode_stats']['payload_raw_bytes'] and h[5]==len(frame)-HEADER.size and h[6].hex()==entry['sha256']
                    actual={p.name:{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in folder.iterdir() if p.is_file()};assert actual==r['files'];artifact_bytes+=sum(x['bytes'] for x in actual.values())
                    key=(dataset,method,codec)
                    if key not in frame_references:frame_references[key]=r['frame_sha256']
                    else:assert frame_references[key]==r['frame_sha256']
                    premium=transform_bytes if method=='typed' else 0;complete=len(frame)+len(restored)+runtime_bytes+wrapper_bytes+premium
                    rows.append({**{k:r[k] for k in ('round','dataset','role','method','codec','source_bytes','frame_bytes','encode_wall_s','encode_cpu_s','decode_wall_s','decode_cpu_s','model_json_load_wall_s','model_json_load_cpu_s','decode_to_model_ready_wall_s','decode_to_model_ready_cpu_s','worker_wall_s','worker_cpu_s','observed_peak_rss_bytes','semantic_index_documents','semantic_index_tokens')},
                        'payload_raw_bytes':r['encode_stats']['payload_raw_bytes'],'typed_details':r['encode_stats']['typed_details'],
                        'allocated_active_frame_restored_and_code_bytes':complete,'allocated_typed_source_premium_bytes':premium,'actual_worker_artifact_bytes':sum(x['bytes'] for x in actual.values()),'parent_full_process_wall_s':parent['parent_full_process_wall_s']})
    assert len(rows)==72 and extra_decodes==72 and len(frame_references)==24
    def row(n,d,m,c):return next(r for r in rows if r['round']==n and r['dataset']==d and r['method']==m and r['codec']==c)
    summaries=[];ratios=[]
    for dataset,entry in manifest['datasets'].items():
        plain_best=min((row(1,dataset,'plain',codec) for codec in CODECS),key=lambda r:(r['allocated_active_frame_restored_and_code_bytes'],r['codec']))
        for codec in CODECS:
            typed=row(1,dataset,'typed',codec);plain=row(1,dataset,'plain',codec)
            summaries.append({'dataset':dataset,'role':entry['role'],'codec':codec,'typed_complete_bytes':typed['allocated_active_frame_restored_and_code_bytes'],'plain_same_codec_complete_bytes':plain['allocated_active_frame_restored_and_code_bytes'],
                'best_plain_codec':plain_best['codec'],'best_plain_complete_bytes':plain_best['allocated_active_frame_restored_and_code_bytes'],'typed_same_codec_space_wins':typed['allocated_active_frame_restored_and_code_bytes']<plain['allocated_active_frame_restored_and_code_bytes'],
                'typed_vs_best_plain_complete_space_wins':typed['allocated_active_frame_restored_and_code_bytes']<plain_best['allocated_active_frame_restored_and_code_bytes']})
        values={k:[] for k in ('decode_to_model_ready_wall_s','decode_to_model_ready_cpu_s','parent_full_process_wall_s')}
        for n in (1,2,3):
            t=row(n,dataset,'typed','zstd');b=row(n,dataset,'plain','zstd')
            for key in values:values[key].append(t[key]/b[key] if b[key]>0 else None)
        med={key:statistics.median(v) if all(x is not None for x in v) else None for key,v in values.items()}
        ratios.append({'dataset':dataset,'role':entry['role'],'typed_zstd_vs_plain_zstd_median_ratios':med,'load_time_gate':all(x is not None and x<=1 for x in med.values())})
    real=[d for d,e in manifest['datasets'].items() if e['role']=='scientific_index'];assert len(real)==2
    space_gate=all(next(s for s in summaries if s['dataset']==d and s['codec']=='zstd')['typed_vs_best_plain_complete_space_wins'] for d in real)
    time_gate=all(next(r for r in ratios if r['dataset']==d)['load_time_gate'] for d in real)
    aggregate={'rows':rows,'space_summaries':summaries,'load_ratios':ratios,'primary_typed_zstd_vs_best_plain_space_gate':space_gate,'primary_typed_zstd_vs_plain_zstd_load_gate':time_gate,'primary_index_space_load_joint':space_gate and time_gate,
        'formal_workers':72,'source_exact_restorations':72,'additional_decoder_audits':extra_decodes,'frame_determinism_cells':24,'scientific_index_cases':2,'owned_structured_control_cases':1,'shared_original_input_bytes':sum(len(raw) for raw in originals.values()),'all_actual_frame_and_restored_artifact_bytes':artifact_bytes,'raw_child_parent_report_bytes':raw_report_bytes,
        'runtime_source_bytes':runtime_bytes,'common_frame_wrapper_source_bytes':wrapper_bytes,'typed_source_premium_bytes':transform_bytes,'new_scientific_question_trials':0,'new_training_runs':0,'new_remote_model_calls':0,'freeze':args.freeze,
        'scope':'Index-frame complete-space and consumer-ready load benchmark only, not neural inference/retrieval quality/answers or transparent SDK deployment','physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None}
    exclusive(out/'derived-metrics.json',canonical(aggregate)+b'\n');exclusive(out/'source-checksums.json',canonical(checks)+b'\n');exclusive(out/'source-resource.json',canonical({'files':source_files,'total_bytes':runtime_bytes,'common_frame_wrapper_bytes':wrapper_bytes,'typed_specific_source_bytes':transform_bytes,'assessment_programs':{n:{'bytes':(root/n).stat().st_size,'sha256':sha} for n,sha in env['program_protocol_sha256'].items() if n.startswith('scripts/')}})+b'\n')
    exclusive(out/'validation.json',canonical({'formal_workers':72,'original_byte_recoveries':72,'additional_actual_frame_decoder_audits':72,'deterministic_cells':24,'unit_tests_run':310,'unit_tests_passed':309,'unit_tests_skipped':1,'runtime_module_count':len(checks),'html_files':1,'primary_space_gate':space_gate,'primary_load_gate':time_gate,'primary_joint':space_gate and time_gate,'new_scientific_question_trials':0,'new_training_runs':0,'new_remote_model_calls':0,'freeze':args.freeze,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})+b'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(15,5),layout='constrained');codecs=list(CODECS)
    for ax,dataset in zip(axes,manifest['datasets']):
        x=list(range(4));ax.bar([i-.18 for i in x],[row(1,dataset,'plain',c)['allocated_active_frame_restored_and_code_bytes']/1024 for c in codecs],width=.36,label='plain + restored + source code',color='#64748b')
        ax.bar([i+.18 for i in x],[row(1,dataset,'typed',c)['allocated_active_frame_restored_and_code_bytes']/1024 for c in codecs],width=.36,label='typed + restored + extra code',color='#2563eb');ax.set_xticks(x,codecs);ax.set_ylim(bottom=0);ax.set_title(dataset);ax.set_ylabel('Allocated active workflow KiB');ax.legend(fontsize=7)
    fig.suptitle('Original canonical-index lossless frames: 2 known indices + owned structured control');fig.savefig(out/'index-frames.png',dpi=160);plt.close(fig)
    exclusive(out/'analysis-timing.json',canonical({'wall_s':time.perf_counter()-begin,'cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'additional_actual_decode_calls':extra_decodes,'scope':'Independent actual frame/restore/source/JSON/source-fee audit and plot, separate from measured worker loads'})+b'\n')
    print(json.dumps({'space_gate':space_gate,'load_gate':time_gate,'joint':space_gate and time_gate,'restored':72}),flush=True)

if __name__=='__main__':main()
