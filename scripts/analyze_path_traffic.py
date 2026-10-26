"""Audit parent identities, paired proofs, tree equality and CAS conservation."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import time

from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from rkv1.store import OBJECT
from scripts.run_memory_concurrency import save


def proof_sha(proof):
    return digest(json.dumps(proof,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','work','freeze','test-log'):p.add_argument('--'+name,required=True)
    args=p.parse_args();out=Path(args.out);work=Path(args.work);start=time.perf_counter();cpu=time.process_time()
    env=json.loads((out/'environment.json').read_text('utf-8'));checks=implementation_checksums()
    assert checks==env['implementation_checksums']
    for name,sha in checks.items():assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))==sha
    for rel,sha in env['program_protocol_sha256'].items():
        assert digest(Path(rel).read_bytes())==sha==digest(subprocess.check_output(['git','show',args.freeze+':'+rel]))
    assert Path(__file__).read_bytes()==subprocess.check_output(['git','show',args.freeze+':scripts/analyze_path_traffic.py'])
    log=Path(args.test_log).read_text('utf-8');assert 'Ran 243 tests' in log and 'OK (skipped=1)' in log
    rows=[];paired=[];totals={};proofs={};trees={};main_gates=controls=negatives=bindings=0
    for n in range(1,4):
        previous=json.loads(Path(f'results/v0.40.0/round-{n}.json').read_text('utf-8'))
        old={c['question']['case_id']:c['proof'] for c in previous['questions']+previous['controls']}
        for condition in ('off','on'):
            label=f'round-{n}-{condition}'
            raw=(out/(label+'.json')).read_bytes();meter_raw=(out/(label+'-meter.json')).read_bytes()
            parent=json.loads((out/(label+'-parent.json')).read_text('utf-8'));data=json.loads(raw);meter=json.loads(meter_raw)
            assert parent['return_code']==0 and parent['error'] is None
            assert parent['child_report_sha256']==digest(raw) and parent['meter_report_sha256']==digest(meter_raw)
            assert parent['parent_full_process_wall_s']>=data['worker_wall_s']>0
            assert data['round']==n and meter['round']==n and meter['condition']==condition
            assert len(data['questions'])==96 and len(data['controls'])==4 and len(meter['traces'])==100
            assert data['old_files_unchanged'] and data['head_unchanged'] and data['added_files_only_derived']
            assert data['question_sha256']==previous['question_sha256']
            assert [i['source_sha256'] for i in data['ingests']]==[i['source_sha256'] for i in previous['ingests']]
            assert data['ingestion_finished_elapsed_s']<=data['questions_fsynced_elapsed_s']<=data['first_query_started_elapsed_s']
            assert data['remote_model_calls']==0 and data['no_numpy_imported']
            cases=data['questions']+data['controls'];this_proofs={};traffic={}
            for index,(case,measure) in enumerate(zip(cases,meter['traces'])):
                q=case['question'];proof=case['proof'];key=q['case_id']
                assert case['gate_pass'] and proof==old[key]
                assert measure['index']==index and measure['root_key']==q['root_key'] and measure['snapshot_id']==q['snapshot_id']
                assert measure['proof_sha256']==proof_sha(proof)
                this_proofs[key]=measure['proof_sha256'];bindings+=case['audit']['bindings']
                stats=measure['traffic']
                if condition=='off':assert stats is None
                else:
                    assert stats['physical_SSD_bytes'] is None and stats['all_system_file_bytes'] is None
                    assert stats['object_opens']==stats['decode_attempts']==stats['decode_successes']
                    assert stats['read_calls']==2*stats['object_opens']
                    assert stats['application_CAS_file_bytes']==stats['payload_input_bytes']+OBJECT.size*stats['object_opens']
                    assert stats['CAS_decoded_output_bytes']==stats['raw_codec_output_bytes']+stats['compressed_decode_output_bytes']
                    for field,value in stats.items():
                        if type(value) is int:traffic[field]=traffic.get(field,0)+value
            main_gates+=len(data['questions']);controls+=len(data['controls'])
            assert len(data['negative_audits'])==2 and all(c['rejected'] for c in data['negative_audits']);negatives+=2
            ledger_raw=(work/label/'full-file-ledger.json').read_bytes();ledger=json.loads(ledger_raw)
            assert digest(ledger_raw)==data['file_accounting']['full_ledger_sha256']
            actual={x.relative_to(work/label/'memory').as_posix():{'bytes':x.stat().st_size,'sha256':digest(x.read_bytes())}
                    for x in (work/label/'memory').rglob('*') if x.is_file()}
            assert actual==ledger['after_queries']
            assert all(actual.get(k)==v for k,v in ledger['before_queries'].items())
            trees[n,condition]=actual;proofs[n,condition]=this_proofs
            admitted=sum(c['proof']['admitted_record_bytes'] for c in cases)
            verified=sum(c['proof']['verified_record_bytes'] for c in cases)
            row={'round':n,'condition':condition,'admitted_record_bytes':admitted,'verified_record_bytes':verified,
                 'traffic':traffic if condition=='on' else None,'parent_full_process_wall_s':parent['parent_full_process_wall_s'],
                 'worker_wall_s':data['worker_wall_s'],'outside_worker_interval_wall_s':parent['parent_full_process_wall_s']-data['worker_wall_s'],
                 'trace_wall_s':sum(c['trace_wall_s'] for c in cases),'trace_cpu_s':sum(c['trace_cpu_s'] for c in cases),
                 'worker_cpu_s':data['worker_cpu_s'],'observed_worker_peak_rss_bytes':data['peak_rss_bytes'],
                 'final_memory_bytes':sum(v['bytes'] for v in actual.values()),
                 'derived_added_bytes':data['file_accounting']['derived_added_bytes'],
                 'physical_SSD_bytes':None,'all_system_file_bytes':None}
            if condition=='on':
                row['CAS_read_over_admitted']=traffic['application_CAS_file_bytes']/admitted
                row['CAS_decoded_over_admitted']=traffic['CAS_decoded_output_bytes']/admitted
                for key,value in traffic.items():totals[key]=totals.get(key,0)+value
            rows.append(row)
        assert proofs[n,'off']==proofs[n,'on'] and trees[n,'off']==trees[n,'on']
        off=next(r for r in rows if r['round']==n and r['condition']=='off')
        on=next(r for r in rows if r['round']==n and r['condition']=='on')
        paired.append({'round':n,'trace_wall_ON_over_OFF':on['trace_wall_s']/off['trace_wall_s'],
                       'trace_CPU_ON_over_OFF':on['trace_cpu_s']/off['trace_cpu_s'] if off['trace_cpu_s'] else None,
                       'parent_wall_ON_over_OFF':on['parent_full_process_wall_s']/off['parent_full_process_wall_s']})
    assert (main_gates,controls,negatives,bindings)==(576,24,12,1710)
    summary={'rounds':rows,'pairs':paired,'ON_300_trace_totals':totals,
        'median_paired_ratios':{key:statistics.median(x[key] for x in paired if x[key] is not None)
                               for key in ('trace_wall_ON_over_OFF','trace_CPU_ON_over_OFF','parent_wall_ON_over_OFF')},
        'analysis_wall_s':time.perf_counter()-start,'analysis_cpu_s':time.process_time()-cpu}
    save(out/'derived-metrics.json',summary);save(out/'source-checksums.json',checks)
    files={x.as_posix():{'bytes':x.stat().st_size,'sha256':digest(x.read_bytes())} for x in sorted(Path('rkv1').rglob('*')) if x.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+key for key in checks}|{'rkv1/memory_demo.html'}
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
         'assessment_programs':{name:{'bytes':Path(name).stat().st_size,'sha256':digest(Path(name).read_bytes())}
             for name in ('scripts/cas_traffic.py','scripts/run_path_traffic.py','scripts/analyze_path_traffic.py')},
         'new_training_runs':0,'new_model_bytes':0,'native_performance_specific_bytes':0,
         'scope':'Runtime source, memory files and assessment sidecars separate; no physical IO or complete TCO claim'})
    save(out/'validation.json',{'main_questions':576,'all_main_gates_pass':True,'controls':24,'negative_audits_rejected':12,
         'accepted_original_record_bindings':1710,'paired_full_tree_identity_cases':3,'all_600_proofs_match_v040':True,
         'ON_trace_conservation_cases':300,'OFF_trace_counters_null':300,'parent_complete_timing_identity_records':6,
         'measurement_protocol_gates_pass':True,'unit_tests_run':243,'unit_tests_passed':242,'unit_tests_skipped':1,
         'runtime_module_count':len(checks),'html_files':1,'runtime_protocol_freeze':args.freeze,
         'test_log_sha256':digest(Path(args.test_log).read_bytes()),'new_remote_model_calls':0,
         'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,5.8),layout='constrained')
    onrows=[r for r in rows if r['condition']=='on']
    bars=[sum(r['admitted_record_bytes'] for r in onrows),sum(r['verified_record_bytes'] for r in onrows),
          totals['application_CAS_file_bytes'],totals['CAS_decoded_output_bytes']]
    axes[0].bar(range(4),bars,color=['#16a34a','#64748b','#d97706','#2563eb'])
    axes[0].set_xticks(range(4),['Admitted','Verified','CAS read','Decoded'],rotation=18)
    axes[0].set_yscale('log');axes[0].set_ylabel('Bytes (log), 300 ON traces');axes[0].set_title('Application work, not physical SSD IO')
    for i,b in enumerate(bars):axes[0].text(i,b*1.12,f'{b:,}',ha='center',fontsize=7)
    axes[0].set_ylim(min(bars)*.65,max(bars)*2)
    for condition,delta,color in (('off',-.18,'#64748b'),('on',.18,'#d97706')):
        selected=[next(r for r in rows if r['round']==n and r['condition']==condition) for n in (1,2,3)]
        axes[1].bar([n+delta for n in (1,2,3)],[r['trace_wall_s'] for r in selected],.34,label=condition.upper(),color=color)
    axes[1].set_xticks((1,2,3));axes[1].set_xlabel('Paired round');axes[1].set_ylabel('100 traces wall seconds');axes[1].set_title('Observer overhead and timing noise')
    axes[1].legend(loc='upper center',bbox_to_anchor=(.5,-.14),ncol=2,frameon=False)
    axes[2].bar(range(6),[r['worker_wall_s'] for r in rows],label='Measured inside worker',color='#2563eb')
    axes[2].bar(range(6),[r['outside_worker_interval_wall_s'] for r in rows],bottom=[r['worker_wall_s'] for r in rows],label='Outside worker interval',color='#64748b')
    axes[2].set_xticks(range(6),[f"{r['round']} {r['condition']}" for r in rows],rotation=30)
    axes[2].set_ylabel('Complete child process wall seconds');axes[2].set_title('Parent interval includes startup and tail')
    axes[2].legend(loc='upper center',bbox_to_anchor=(.5,-.2),frameon=False,fontsize=8)
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('RKV-1 v0.41: known synthetic fixture; six fresh workers / scope OFF and ON')
    fig.savefig(out/'path-traffic.png',dpi=160);plt.close(fig)
    print(json.dumps({'ON_totals':totals,'median_ratios':summary['median_paired_ratios']}))


if __name__=='__main__':main()
