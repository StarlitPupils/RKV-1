"""Fixed factorial cache assessment; proofs, resource work and unmetered timing."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from rkv1.store import OBJECT
from scripts.run_memory_concurrency import save


def main():
    p=argparse.ArgumentParser()
    for name in ('out','work','freeze','test-log'):p.add_argument('--'+name,required=True)
    args=p.parse_args();out=Path(args.out);work=Path(args.work)
    env=json.loads((out/'environment.json').read_text('utf-8'));checks=implementation_checksums()
    assert checks==env['implementation_checksums']
    for name,sha in checks.items():assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))==sha
    for rel,sha in env['program_protocol_sha256'].items():assert digest(Path(rel).read_bytes())==sha==digest(subprocess.check_output(['git','show',args.freeze+':'+rel]))
    assert Path(__file__).read_bytes()==subprocess.check_output(['git','show',args.freeze+':scripts/analyze_cached_paths.py'])
    log=Path(args.test_log).read_text('utf-8');assert 'Ran 246 tests' in log and 'OK (skipped=1)' in log
    rows=[];count=bindings=0;raw_json_bytes=0
    for n in (1,2,3):
        old=json.loads(Path(f'results/v0.40.0/round-{n}.json').read_text('utf-8'))
        gold={c['question']['case_id']:c['proof'] for c in old['questions']+old['controls']};reference_tree=None
        for cache_mode,meter_mode in (('off','off'),('on','off'),('off','on'),('on','on')):
            label=f'round-{n}-c{cache_mode}-m{meter_mode}'
            raw=(out/(label+'.json')).read_bytes();mr=(out/(label+'-meter.json')).read_bytes();pr=(out/(label+'-parent.json')).read_bytes()
            raw_json_bytes+=len(raw)+len(mr)+len(pr);data=json.loads(raw);meter=json.loads(mr);parent=json.loads(pr)
            assert parent['return_code']==0 and parent['error'] is None and parent['child_report_sha256']==digest(raw) and parent['meter_report_sha256']==digest(mr)
            assert parent['parent_full_process_wall_s']>=data['worker_wall_s']>0
            assert meter['cache']==cache_mode and meter['condition']==meter_mode and len(meter['traces'])==100
            assert data['old_files_unchanged'] and data['head_unchanged'] and data['added_files_only_derived']
            assert data['question_sha256']==old['question_sha256'] and [x['source_sha256'] for x in data['ingests']]==[x['source_sha256'] for x in old['ingests']]
            assert len(data['questions'])==96 and len(data['controls'])==4 and all(x['rejected'] for x in data['negative_audits']) and len(data['negative_audits'])==2
            totals={};cache_totals={};peak=graph=0;cases=data['questions']+data['controls']
            for index,(case,m) in enumerate(zip(cases,meter['traces'])):
                q=case['question'];proof=case['proof'];assert case['gate_pass'] and proof==gold[q['case_id']]
                assert m['index']==index and m['root_key']==q['root_key'] and m['snapshot_id']==q['snapshot_id']
                encoded=json.dumps(proof,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
                assert m['proof_sha256']==digest(encoded);count+=1;bindings+=case['audit']['bindings']
                c=m['cache'];t=m['traffic']
                if cache_mode=='off':assert c is None
                else:
                    assert c['requests']==c['hits']+c['misses'] and c['peak_payload_bytes']<=65536 and c['retained_payload_bytes_after_scope']==0
                    assert c['oversize']==0;peak=max(peak,c['peak_payload_bytes']);graph=max(graph,c['peak_retained_graph_bytes'])
                    for k in ('requests','hits','misses','evictions','oversize'):cache_totals[k]=cache_totals.get(k,0)+c[k]
                if meter_mode=='off':assert t is None
                else:
                    assert t['object_opens']==t['decode_attempts']==t['decode_successes'] and t['read_calls']==2*t['object_opens']
                    assert t['application_CAS_file_bytes']==t['payload_input_bytes']+OBJECT.size*t['object_opens']
                    assert t['CAS_decoded_output_bytes']==t['raw_codec_output_bytes']+t['compressed_decode_output_bytes']
                    if c is not None:assert t['decode_successes']==c['misses']
                    for k,v in t.items():
                        if type(v) is int:totals[k]=totals.get(k,0)+v
            ledger_raw=(work/label/'full-file-ledger.json').read_bytes();ledger=json.loads(ledger_raw)
            assert digest(ledger_raw)==data['file_accounting']['full_ledger_sha256']
            tree={x.relative_to(work/label/'memory').as_posix():{'bytes':x.stat().st_size,'sha256':digest(x.read_bytes())} for x in (work/label/'memory').rglob('*') if x.is_file()}
            assert tree==ledger['after_queries'] and all(tree.get(k)==v for k,v in ledger['before_queries'].items())
            if reference_tree is None:reference_tree=tree
            else:assert tree==reference_tree
            rows.append({'round':n,'cache':cache_mode,'meter':meter_mode,'traffic':totals if meter_mode=='on' else None,
                'cache_totals':cache_totals if cache_mode=='on' else None,'peak_retained_payload_bytes':peak if cache_mode=='on' else None,
                'peak_retained_graph_bytes':graph if cache_mode=='on' else None,
                'trace_wall_s':sum(x['trace_wall_s'] for x in cases),'trace_cpu_s':sum(x['trace_cpu_s'] for x in cases),
                'parent_full_process_wall_s':parent['parent_full_process_wall_s'],'worker_wall_s':data['worker_wall_s'],
                'observed_peak_rss_bytes':data['peak_rss_bytes'],'memory_bytes':sum(v['bytes'] for v in tree.values()),
                'admitted_record_bytes':sum(x['proof']['admitted_record_bytes'] for x in cases)})
    assert (count,bindings)==(1200,3420)
    def row(n,c,m):return next(x for x in rows if (x['round'],x['cache'],x['meter'])==(n,c,m))
    time_pairs=[];work_pairs=[]
    for n in (1,2,3):
        a=row(n,'off','off');b=row(n,'on','off');c=row(n,'off','on');d=row(n,'on','on')
        time_pairs.append({'round':n,**{k:b[k]/a[k] if a[k]>0 else None for k in ('trace_wall_s','trace_cpu_s','parent_full_process_wall_s')}})
        work_pairs.append({'round':n,**{k:d['traffic'][k]/c['traffic'][k] for k in ('application_CAS_file_bytes','CAS_decoded_output_bytes')}})
    med={k:statistics.median(x[k] for x in time_pairs) if all(x[k] is not None for x in time_pairs) else None for k in ('trace_wall_s','trace_cpu_s','parent_full_process_wall_s')}
    work_gate=all(x[k]<1 for x in work_pairs for k in ('application_CAS_file_bytes','CAS_decoded_output_bytes'))
    time_gate=all(v is not None and v<=1 for v in med.values())
    save(out/'derived-metrics.json',{'rows':rows,'unmetered_time_pairs':time_pairs,'metered_work_pairs':work_pairs,'median_unmetered_time_ratios':med,'work_reduction_gate':work_gate,'time_joint_gate':time_gate,'raw_report_json_bytes':raw_json_bytes})
    save(out/'source-checksums.json',checks)
    files={x.as_posix():{'bytes':x.stat().st_size,'sha256':digest(x.read_bytes())} for x in sorted(Path('rkv1').rglob('*')) if x.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+k for k in checks}|{'rkv1/memory_demo.html'}
    programs=('scripts/query_block_cache.py','scripts/run_cached_paths.py','scripts/analyze_cached_paths.py','scripts/cas_traffic.py','scripts/run_evidence_paths.py','scripts/evidence_path_fixture.py')
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),'assessment_programs':{s:{'bytes':Path(s).stat().st_size,'sha256':digest(Path(s).read_bytes())} for s in programs},'new_training_runs':0,'new_model_bytes':0,'native_specific_bytes':0})
    save(out/'validation.json',{'main_questions':1152,'controls':48,'negative_audits':24,'all_mechanical_gates_pass':True,'all_1200_proofs_match_v040':True,'accepted_bindings':3420,'four_condition_tree_identity_rounds':3,'parent_timing_records':12,'meter_ON_conservation_cases':600,'meter_OFF_null_cases':600,'cache_ON_budget_and_clear_cases':600,'work_reduction_gate':work_gate,'unmetered_time_joint_gate':time_gate,'unit_tests_run':246,'unit_tests_passed':245,'unit_tests_skipped':1,'runtime_module_count':len(checks),'html_files':1,'freeze':args.freeze,'new_remote_model_calls':0,'physical_SSD_bytes':None,'cold_cache':None,'cross_machine':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,5.5),layout='constrained')
    for mode,delta,color in (('off',-.18,'#64748b'),('on',.18,'#2563eb')):
        axes[0].bar([n+delta for n in (1,2,3)],[row(n,mode,'on')['traffic']['CAS_decoded_output_bytes']/(1<<20) for n in (1,2,3)],.34,label='Cache '+mode,color=color)
        axes[1].bar([n+delta for n in (1,2,3)],[row(n,mode,'off')['trace_wall_s'] for n in (1,2,3)],.34,label='Cache '+mode,color=color)
        axes[2].bar([n+delta for n in (1,2,3)],[row(n,mode,'off')['observed_peak_rss_bytes']/(1<<20) for n in (1,2,3)],.34,label='Cache '+mode,color=color)
    for ax in axes:
        ax.set_xticks((1,2,3));ax.set_xlabel('Paired round');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.legend(loc='upper center',bbox_to_anchor=(.5,-.16),ncol=2,frameon=False,fontsize=8)
    axes[0].set_title('Decoded CAS work, meter ON');axes[0].set_ylabel('MiB / 100 traces')
    axes[1].set_title('Trace time, meter OFF');axes[1].set_ylabel('Seconds / 100 traces')
    axes[2].set_title('Observed worker peak RSS, meter OFF');axes[2].set_ylabel('MiB (observed interval)')
    fig.suptitle('RKV-1 v0.42: fixed 64KiB trace-local cache, favorable known same-block fixture')
    fig.savefig(out/'cached-paths.png',dpi=160);plt.close(fig)
    print(json.dumps({'work_gate':work_gate,'unmetered_time_gate':time_gate,'median_time_ratios':med,'work_pairs':work_pairs}))


if __name__=='__main__':main()
