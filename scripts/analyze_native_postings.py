"""Independent same-frame/native identity, full source/binary fee and time audit."""
import argparse,json,statistics,subprocess,time
from pathlib import Path
from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from scripts.index_frame import decode
from scripts.native_postings import decode_native
from scripts.postings_transform import canonical
from scripts.run_source_alignment import exclusive

def main():
    start=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser(description=__doc__)
    for n in ('manifest','binary-manifest','out','freeze','binary-freeze','test-log'):p.add_argument('--'+n,required=True)
    args=p.parse_args();root=Path.cwd();out=Path(args.out);manifest=json.loads(Path(args.manifest).read_bytes());binary_raw=Path(args.binary_manifest).read_bytes();binary=json.loads(binary_raw);env=json.loads((out/'environment.json').read_bytes());checks=implementation_checksums();assert checks==env['implementation_checksums'] and digest(binary_raw)==env['binary_manifest_sha256']
    assert binary_raw==subprocess.check_output(['git','show',args.binary_freeze+':docs/native-postings-binary.json'])
    for name,sha in checks.items():assert sha==digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))
    for name,sha in env['program_protocol_sha256'].items():assert sha==digest((root/name).read_bytes())==digest(subprocess.check_output(['git','show',args.freeze+':'+name]))
    for name in ('scripts/index_frame.py','scripts/postings_transform.py'):assert (root/name).read_bytes()==subprocess.check_output(['git','show','v0.58.0:'+name])
    test=Path(args.test_log).read_text('utf-8');assert 'Ran 320 tests' in test and 'OK (skipped=1)' in test
    library=Path(binary['path']);metadata=Path(binary['metadata_path']);assert digest(library.read_bytes())==binary['sha256'] and library.stat().st_size==binary['bytes'] and digest(metadata.read_bytes())==binary['metadata_sha256'];meta=json.loads(metadata.read_bytes());assert meta['sha256']==binary['sha256'] and meta['bytes']==binary['bytes'] and meta['source_commit']==args.freeze and meta['abi']==1
    files={n:{'bytes':(root/n).stat().st_size,'sha256':digest((root/n).read_bytes())} for n in ['rkv1/'+x for x in checks]+['rkv1/memory_demo.html']};runtime=sum(x['bytes'] for x in files.values());wrapper=(root/'scripts/index_frame.py').stat().st_size;typed=(root/'scripts/postings_transform.py').stat().st_size;native_names=('scripts/native_postings.py','rust/postings/Cargo.toml','rust/postings/src/lib.rs');native_source=sum((root/n).stat().st_size for n in native_names);native_premium=native_source+library.stat().st_size+metadata.stat().st_size
    rows=[];raw_bytes=0;py_decodes=0;native_decodes=0;sources={}
    for dataset,e in manifest['datasets'].items():
        sources[dataset]=Path(e['path']).read_bytes();assert digest(sources[dataset])==e['sha256'] and len(sources[dataset])==e['bytes']
    for n in (1,2,3):
        for dataset,e in manifest['datasets'].items():
            source=sources[dataset];obj=json.loads(source);posts=obj['shared']['postings'];maximum=max((len(v) for v in posts.values()),default=0)
            for mode in ('plain','typed','native'):
                label=f'round-{n}-{dataset}-{mode}';child=(out/(label+'.json')).read_bytes();parent_bytes=(out/(label+'-parent.json')).read_bytes();r=json.loads(child);parent=json.loads(parent_bytes);raw_bytes+=len(child)+len(parent_bytes);fr=e['frames']['plain' if mode=='plain' else 'typed'];frame=Path(fr['path']).read_bytes();restored=Path(fr['existing_restored_path']).read_bytes()
                assert r['round']==n and r['dataset']==dataset and r['role']==e['role'] and r['mode']==mode and r['tokens']==len(posts) and r['posting_pairs']==sum(len(v) for v in posts.values()) and r['documents']==len(obj['shared']['doc_lengths'])
                assert parent['return_code']==0 and parent['error'] is None and parent['child_sha256']==digest(child) and parent['parent_full_process_wall_s']>=r['worker_wall_s']>=r['model_ready_wall_s']>0
                assert len(frame)==fr['bytes']==r['frame_bytes'] and digest(frame)==fr['sha256']==r['frame_sha256'] and restored==source and r['existing_restored_on_disk_bytes']==len(source)
                assert r['source_sha256']==r['restored_sha256']==e['sha256'] and r['exact_original_and_model']
                assert decode(frame)==source;py_decodes+=1
                if mode=='native':
                    assert decode_native(frame,library,binary['sha256'])==source;native_decodes+=1;assert r['native_binary_sha256']==binary['sha256'] and r['native_max_owned_u64_buffer_payload_bytes']==16*maximum and r['native_buffer_transient_payload_upper_bound_bytes']==32*maximum
                else:assert r['native_binary_sha256'] is None and r['native_max_owned_u64_buffer_payload_bytes'] is None and r['native_buffer_transient_payload_upper_bound_bytes'] is None
                premium=(typed if mode!='plain' else 0)+(native_premium if mode=='native' else 0);complete=len(frame)+len(restored)+runtime+wrapper+premium
                rows.append({**{k:r[k] for k in ('round','dataset','role','mode','source_bytes','frame_bytes','model_ready_wall_s','model_ready_cpu_s','worker_wall_s','worker_cpu_s','observed_peak_rss_bytes','tokens','posting_pairs','native_max_owned_u64_buffer_payload_bytes','native_buffer_transient_payload_upper_bound_bytes')},'parent_full_process_wall_s':parent['parent_full_process_wall_s'],'allocated_active_frame_restored_and_code_bytes':complete,'allocated_specific_source_binary_metadata_premium_bytes':premium})
    summaries=[]
    for dataset,e in manifest['datasets'].items():
        def row(n,m):return next(r for r in rows if r['round']==n and r['dataset']==dataset and r['mode']==m)
        comparisons={}
        for base in ('typed','plain'):
            ratios={k:[row(n,'native')[k]/row(n,base)[k] if row(n,base)[k]>0 else None for n in (1,2,3)] for k in ('model_ready_wall_s','model_ready_cpu_s','parent_full_process_wall_s')};med={k:statistics.median(v) if all(x is not None for x in v) else None for k,v in ratios.items()};comparisons[base]={'native_over_baseline_paired_ratios':ratios,'median_ratios':med,'time_gate':all(x is not None and x<=1 for x in med.values())}
        space=row(1,'native')['allocated_active_frame_restored_and_code_bytes']<row(1,'plain')['allocated_active_frame_restored_and_code_bytes']
        summaries.append({'dataset':dataset,'role':e['role'],'comparisons':comparisons,'native_vs_plain_complete_space_gate':space,'native_vs_plain_complete_bytes_difference':row(1,'native')['allocated_active_frame_restored_and_code_bytes']-row(1,'plain')['allocated_active_frame_restored_and_code_bytes'],'native_vs_plain_space_load_joint':space and comparisons['plain']['time_gate']})
    real=[s for s in summaries if s['role']=='scientific_index'];assert len(real)==2 and len(rows)==27 and py_decodes==27 and native_decodes==9
    assessment={n:{'bytes':(root/n).stat().st_size,'sha256':sha} for n,sha in env['program_protocol_sha256'].items()}
    d={'rows':rows,'summaries':summaries,'H1_native_vs_Python_typed_time_gate':all(s['comparisons']['typed']['time_gate'] for s in real),'H2_native_vs_plain_complete_space_load_joint':all(s['native_vs_plain_space_load_joint'] for s in real),'native_vs_plain_complete_space_gate':all(s['native_vs_plain_complete_space_gate'] for s in real),'native_vs_plain_time_gate':all(s['comparisons']['plain']['time_gate'] for s in real),'formal_workers':27,'formal_original_byte_model_restorations':27,'independent_original_Python_decode_audits':27,'independent_actual_native_decode_audits':9,'raw_child_parent_bytes':raw_bytes,'shared_original_input_bytes':sum(len(x) for x in sources.values()),'shared_frame_and_existing_restored_files_bytes':sum(f['bytes']+e['bytes'] for e in manifest['datasets'].values() for f in e['frames'].values()),'runtime_source_bytes':runtime,'common_frame_wrapper_source_bytes':wrapper,'typed_source_bytes':typed,'native_specific_source_bytes':native_source,'entire_measured_native_binary_bytes':library.stat().st_size,'entire_measured_native_metadata_bytes':metadata.stat().st_size,'entire_native_source_binary_metadata_premium_bytes':native_premium,'measured_native_binary_sha256':binary['sha256'],'freeze':args.freeze,'binary_freeze':args.binary_freeze,'new_frame_encoding_calls':0,'new_scientific_question_trials':0,'new_training_runs':0,'new_remote_model_calls':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,'CI_compile_CPU_s':None,'real_question_or_answer_improvement_proved':False}
    exclusive(out/'derived-metrics.json',canonical(d)+b'\n');exclusive(out/'source-checksums.json',canonical(checks)+b'\n');exclusive(out/'source-resource.json',canonical({'files':files,'total_bytes':runtime,'common_frame_wrapper_bytes':wrapper,'typed_transform_bytes':typed,'native_specific_files':{n:assessment[n] for n in native_names},'native_library':{'bytes':library.stat().st_size,'sha256':binary['sha256']},'native_metadata':{'bytes':metadata.stat().st_size,'sha256':binary['metadata_sha256']},'assessment_programs':{n:v for n,v in assessment.items() if n.startswith('scripts/')},'assessment_all_files':assessment})+b'\n')
    exclusive(out/'validation.json',canonical({'formal_workers':27,'formal_byte_model_restorations':27,'independent_Python_actual_decode_audits':27,'independent_native_actual_decode_audits':9,'unit_tests_run':320,'unit_tests_passed':319,'unit_tests_skipped':1,'native_CI_Rust_tests':4,'native_CI_Python_tests':6,'runtime_module_count':len(checks),'html_files':1,'freeze':args.freeze,'binary_freeze':args.binary_freeze,'H1':d['H1_native_vs_Python_typed_time_gate'],'H2':d['H2_native_vs_plain_complete_space_load_joint'],'new_scientific_question_trials':0,'new_training_runs':0,'new_remote_model_calls':0})+b'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(15,5),layout='constrained');names=[s['dataset'] for s in summaries];x=list(range(3));colors=['#64748b','#2563eb','#0d9488']
    for offset,mode,color in zip((-.24,0,.24),('plain','typed','native'),colors):
        axes[0].bar([i+offset for i in x],[next(r['allocated_active_frame_restored_and_code_bytes'] for r in rows if r['dataset']==ds and r['mode']==mode)/1024 for ds in names],width=.23,label=mode,color=color)
        axes[1].bar([i+offset for i in x],[statistics.median(r['model_ready_wall_s'] for r in rows if r['dataset']==ds and r['mode']==mode) for ds in names],width=.23,label=mode,color=color)
    axes[0].set_ylabel('Active frame + restored + whole code/binary KiB');axes[0].set_title('Entire native DLL + source + metadata charged');axes[1].set_ylabel('Median model-ready wall seconds');axes[1].set_title('Includes native import/hash/load/FFI')
    for off,base,color in ((-.18,'typed','#2563eb'),(.18,'plain','#64748b')):axes[2].bar([i+off for i in x],[s['comparisons'][base]['median_ratios']['model_ready_wall_s'] or 0 for s in summaries],width=.35,label='native / '+base,color=color)
    axes[2].axhline(1,color='#dc2626',linestyle='--');axes[2].set_ylabel('Median paired model-ready wall ratio');axes[2].set_title('Kernel gain and full baseline kept separate')
    for ax in axes:ax.set_xticks(x,names,rotation=10);ax.set_ylim(bottom=0);ax.legend(fontsize=8)
    fig.suptitle('Same existing LZMA frames, 27 fresh workers; no profiler, no new questions');fig.savefig(out/'native-postings.png',dpi=160);plt.close(fig)
    exclusive(out/'analysis-timing.json',canonical({'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'additional_Python_decodes':27,'additional_native_decodes':9,'scope':'Independent real frame/source/restored/native identity/source-fee audits and plot, separate from formal loads'})+b'\n');print(json.dumps({'H1':d['H1_native_vs_Python_typed_time_gate'],'H2':d['H2_native_vs_plain_complete_space_load_joint'],'workers':27}),flush=True)

if __name__=='__main__':main()
