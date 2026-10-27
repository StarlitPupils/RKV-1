"""Independent profiler observer cost, call conservation and actual input audit."""
import argparse,json,math,statistics,subprocess,time
from pathlib import Path
from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from scripts.index_frame import decode
from scripts.postings_transform import canonical
from scripts.run_source_alignment import exclusive

def main():
    start=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser(description=__doc__)
    for n in ('manifest','out','freeze','test-log'):p.add_argument('--'+n,required=True)
    args=p.parse_args();root=Path.cwd();out=Path(args.out);manifest=json.loads(Path(args.manifest).read_bytes());env=json.loads((out/'environment.json').read_bytes());checks=implementation_checksums();assert checks==env['implementation_checksums']
    for name,sha in checks.items():assert sha==digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))
    for name,sha in env['program_protocol_sha256'].items():assert sha==digest((root/name).read_bytes())==digest(subprocess.check_output(['git','show',args.freeze+':'+name]))
    test=Path(args.test_log).read_text('utf-8');assert 'Ran 314 tests' in test and 'OK (skipped=1)' in test
    sources={n:Path(e['path']).read_bytes() for n,e in manifest['datasets'].items()};frames={n:Path(e['frame_path']).read_bytes() for n,e in manifest['datasets'].items()}
    rows=[];raw_bytes=0;extra_decodes=0
    for n in (1,2,3):
        for dataset,e in manifest['datasets'].items():
            assert digest(sources[dataset])==e['sha256'] and len(sources[dataset])==e['bytes'] and digest(frames[dataset])==e['frame_sha256'] and len(frames[dataset])==e['frame_bytes']
            obj=json.loads(sources[dataset]);tokens=len(obj['shared']['postings']);pairs=sum(len(x) for x in obj['shared']['postings'].values())
            for mode in ('off','on'):
                label=f'round-{n}-{dataset}-{mode}';child=(out/(label+'.json')).read_bytes();parent_bytes=(out/(label+'-parent.json')).read_bytes();r=json.loads(child);parent=json.loads(parent_bytes);raw_bytes+=len(child)+len(parent_bytes)
                assert r['round']==n and r['dataset']==dataset and r['role']==e['role'] and r['profiler']==mode and r['tokens']==tokens and r['posting_pairs']==pairs and r['documents']==len(obj['shared']['doc_lengths'])
                assert parent['return_code']==0 and parent['error'] is None and parent['child_sha256']==digest(child) and parent['parent_full_process_wall_s']>=r['worker_wall_s']>=r['model_ready_wall_s']>0
                assert r['source_sha256']==r['restored_sha256']==e['sha256'] and r['frame_sha256']==e['frame_sha256'] and r['exact_original_and_model']
                assert decode(frames[dataset])==sources[dataset];extra_decodes+=1
                varint_fraction=None;inverse_fraction=None;expected=4+2*tokens+2*pairs
                if mode=='off':assert r['functions'] is None and r['profiler_total_self_s'] is None
                else:
                    functions=r['functions'];assert all(x['calls']>=x['primitive_calls']>=0 and x['instrumented_self_s']>=0 and x['instrumented_cumulative_s']>=0 for x in functions)
                    assert math.isclose(sum(x['instrumented_self_s'] for x in functions),r['profiler_total_self_s'],rel_tol=1e-10,abs_tol=1e-12) and r['profiler_total_self_s']>0
                    def exact(function):
                        found=[x for x in functions if x['file']=='scripts/postings_transform.py' and x['function']==function];assert len(found)==1;return found[0]
                    v=exact('read_uvar');i=exact('inverse');assert v['calls']==v['primitive_calls']==expected and i['calls']==i['primitive_calls']==1
                    varint_fraction=v['instrumented_self_s']/r['profiler_total_self_s'];inverse_fraction=i['instrumented_self_s']/r['profiler_total_self_s']
                rows.append({**{k:r[k] for k in ('round','dataset','role','profiler','source_bytes','frame_bytes','model_ready_wall_s','model_ready_cpu_s','worker_wall_s','worker_cpu_s','observed_peak_rss_bytes','tokens','posting_pairs','profiler_total_self_s')},'parent_full_process_wall_s':parent['parent_full_process_wall_s'],'expected_varint_calls':expected,'instrumented_varint_self_fraction':varint_fraction,'instrumented_inverse_self_fraction':inverse_fraction})
    summaries=[]
    for dataset,e in manifest['datasets'].items():
        def row(n,m):return next(r for r in rows if r['round']==n and r['dataset']==dataset and r['profiler']==m)
        ratios={k:[row(n,'on')[k]/row(n,'off')[k] if row(n,'off')[k]>0 else None for n in (1,2,3)] for k in ('model_ready_wall_s','model_ready_cpu_s','parent_full_process_wall_s')}
        med={k:statistics.median(v) if all(x is not None for x in v) else None for k,v in ratios.items()}
        hot=[row(n,'on')['instrumented_varint_self_fraction']+row(n,'on')['instrumented_inverse_self_fraction'] for n in (1,2,3)]
        summaries.append({'dataset':dataset,'role':e['role'],'observer_ON_OFF_paired_ratios':ratios,'observer_ON_OFF_median_ratios':med,'H1_observer_within_10_percent':all(x is not None and x<=1.10 for x in med.values()),'instrumented_inverse_plus_varint_self_fractions':hot,'H2_instrumented_inverse_varint_at_least_half_every_round':all(x>=.5 for x in hot)})
    real=[s for s in summaries if s['role']=='scientific_index'];assert len(real)==2 and len(rows)==18
    files={n:{'bytes':(root/n).stat().st_size,'sha256':digest((root/n).read_bytes())} for n in ['rkv1/'+x for x in checks]+['rkv1/memory_demo.html']};runtime=sum(x['bytes'] for x in files.values());assessment={n:{'bytes':(root/n).stat().st_size,'sha256':sha} for n,sha in env['program_protocol_sha256'].items()}
    derived={'rows':rows,'summaries':summaries,'H1_observer_within_10_percent_both_indices':all(s['H1_observer_within_10_percent'] for s in real),'H2_instrumented_inverse_varint_at_least_half_both_indices_every_round':all(s['H2_instrumented_inverse_varint_at_least_half_every_round'] for s in real),'formal_workers':18,'formal_byte_and_model_recoveries':18,'additional_actual_frame_decode_audits':extra_decodes,'profiled_workers':9,'unprofiled_workers':9,'raw_child_parent_bytes':raw_bytes,'shared_original_input_bytes':sum(len(x) for x in sources.values()),'shared_stored_frame_bytes':sum(len(x) for x in frames.values()),'new_frame_encoding_calls':0,'runtime_source_bytes':runtime,'freeze':args.freeze,'new_scientific_question_trials':0,'new_training_runs':0,'new_remote_model_calls':0,'performance_improvement_proved':False,'instrumented_fractions_are_unprofiled_CPU_fractions':False,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None}
    exclusive(out/'derived-metrics.json',canonical(derived)+b'\n');exclusive(out/'source-checksums.json',canonical(checks)+b'\n');exclusive(out/'source-resource.json',canonical({'files':files,'total_bytes':runtime,'assessment_programs':{n:v for n,v in assessment.items() if n.startswith('scripts/')},'assessment_program_protocol_test_input_files':assessment,'assessment_files_bytes':sum(x['bytes'] for x in assessment.values())})+b'\n')
    exclusive(out/'validation.json',canonical({'formal_workers':18,'formal_restorations':18,'additional_decoder_audits':18,'ON_exact_varint_counts_and_self_time_conservation':9,'OFF_counter_null_records':9,'unit_tests_run':314,'unit_tests_passed':313,'unit_tests_skipped':1,'runtime_module_count':len(checks),'html_files':1,'freeze':args.freeze,'H1':derived['H1_observer_within_10_percent_both_indices'],'H2':derived['H2_instrumented_inverse_varint_at_least_half_both_indices_every_round'],'new_scientific_question_trials':0,'new_training_runs':0,'new_remote_model_calls':0})+b'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained');names=[s['dataset'] for s in summaries];x=list(range(len(names)));colors=['#2563eb','#64748b','#0d9488']
    for offset,(key,label),color in zip((-.24,0,.24),(('model_ready_wall_s','ready wall'),('model_ready_cpu_s','ready CPU'),('parent_full_process_wall_s','parent wall')),colors):
        axes[0].bar([i+offset for i in x],[s['observer_ON_OFF_median_ratios'][key] or 0 for s in summaries],width=.23,label=label,color=color)
    axes[0].axhline(1.10,color='#dc2626',linestyle='--',label='H1 limit 1.10');axes[0].set_xticks(x,names);axes[0].set_ylabel('Profiler ON/OFF median paired ratio');axes[0].set_ylim(bottom=0);axes[0].legend(fontsize=8);axes[0].set_title('Observer cost, not algorithm speedup')
    var=[statistics.median(r['instrumented_varint_self_fraction'] for r in rows if r['dataset']==d and r['profiler']=='on') for d in names];inv=[statistics.median(r['instrumented_inverse_self_fraction'] for r in rows if r['dataset']==d and r['profiler']=='on') for d in names]
    axes[1].bar(x,var,label='read_uvar instrumented self',color=colors[0]);axes[1].bar(x,inv,bottom=var,label='inverse instrumented self',color=colors[1]);axes[1].bar(x,[1-a-b for a,b in zip(var,inv)],bottom=[a+b for a,b in zip(var,inv)],label='remaining instrumented self',color='#cbd5e1');axes[1].axhline(.5,color='#dc2626',linestyle='--');axes[1].set_xticks(x,names);axes[1].set_ylim(0,1);axes[1].set_ylabel('Median fraction of instrumented self-time');axes[1].set_title('Call-heavy Python can be profiler-biased');axes[1].legend(fontsize=8)
    fig.suptitle('Unchanged typed/LZMA frames: paired profiler diagnostic, 18 fresh workers');fig.savefig(out/'index-profile.png',dpi=160);plt.close(fig)
    exclusive(out/'analysis-timing.json',canonical({'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'additional_actual_frame_decodes':extra_decodes,'scope':'Independent 18 child/parent/profile/source/frame audits and standard figure; excluded from timed loads'})+b'\n');print(json.dumps({'H1':derived['H1_observer_within_10_percent_both_indices'],'H2':derived['H2_instrumented_inverse_varint_at_least_half_both_indices_every_round'],'workers':18}),flush=True)

if __name__=='__main__':main()
