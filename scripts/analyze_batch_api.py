"""Independent mechanical contract audit; instrumented costs are not speed gains."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import time
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.memory import Memory
from rkv1.store import OBJECT
from scripts.run_batch_api import audit,encoded,ledger,original_index
from scripts.path_layout_fixture import sources
from scripts.run_memory_concurrency import save


def main():
    began=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser()
    for k in ('work','out','freeze','test-log'):p.add_argument('--'+k,required=True)
    args=p.parse_args();out=Path(args.out);work=Path(args.work)
    env=json.loads((out/'environment.json').read_text('utf-8'));checks=implementation_checksums();assert checks==env['implementation_checksums']
    for k,sha in checks.items():assert sha==digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+k]))
    for k,sha in env['program_protocol_sha256'].items():assert sha==digest(Path(k).read_bytes())==digest(subprocess.check_output(['git','show',args.freeze+':'+k]))
    test=Path(args.test_log).read_text('utf-8');assert 'Ran 259 tests' in test and 'OK (skipped=1)' in test
    rows=[];outcomes=Counter();bindings=recovered=raw_json=0;budget_reads=[];trees={}
    for n in (1,2,3):
        for layout in ('clustered','separated'):
            label=f'round-{n}-{layout}';folder=work/label;raw=(out/(label+'.json')).read_bytes();pr=(out/(label+'-parent.json')).read_bytes()
            raw_json+=len(raw)+len(pr);data=json.loads(raw);parent=json.loads(pr)
            assert (data['round'],data['layout'])==(n,layout) and parent['return_code']==0 and parent['error'] is None
            assert parent['child_report_sha256']==digest(raw) and parent['parent_full_process_wall_s']>=data['worker_wall_s']>0
            cases=data['cases'];assert len(cases)==21 and sum(c['primary'] for c in cases)==18
            assert len(data['ingests'])==3;memory=Memory(folder/'memory');totals=Counter()
            expected_ids={f'e{e}-n{s}-{status}' for e in range(3) for s in (1,3,32) for status in ('accepted','budget-rejected')}
            expected_ids|={'duplicate-accepted','duplicate-budget-rejected','missing-zero-budget'}
            assert {c['case_id'] for c in cases}==expected_ids
            for c in cases:
                assert c['outcome_gate_pass'];outcomes[c['expected']]+=1
                if c['primary']:
                    assert c['epoch'] in (0,1,2) and len(c['keys']) in (1,3,32)
                    assert c['keys']==['doc:'+str(i) for i in range(len(c['keys']))]
                    assert c['case_id']==f"e{c['epoch']}-n{len(c['keys'])}-{c['expected']}"
                elif c['case_id']=='missing-zero-budget':assert c['epoch']==0 and c['keys']==['doc:999999'] and c['expected']=='accepted' and c['budget_bytes']==0
                else:assert c['epoch']==0 and c['keys']==['doc:0']*3 and c['case_id']=='duplicate-'+c['expected']

                epoch=c['epoch'];sid=data['ingests'][epoch]['commit']['snapshot_id'];index=original_index(epoch,layout)
                required=sum(len(index[k][2]) for k in c['keys'] if k in index)
                if c['expected']=='accepted':
                    assert c['error'] is None and c['result']['max_keys']==32 and c['result']['max_source_bytes']==c['budget_bytes']==required
                    count=audit(memory,c['result'],c['keys'],sid,index);assert count==c['bindings'];bindings+=count
                else:
                    assert c['result'] is None and c['error']=='Batch source-byte budget exceeded' and c['bindings']==0
                    assert c['budget_bytes']==required-1
                    budget_reads.append({'round':n,'layout':layout,'case_id':c['case_id'],'application_CAS_file_bytes':c['traffic']['application_CAS_file_bytes'],
                        'CAS_decoded_output_bytes':c['traffic']['CAS_decoded_output_bytes']})
                t=c['traffic'];assert t['object_opens']==t['decode_successes']==t['decode_attempts'] and t['read_calls']==2*t['object_opens']
                assert t['application_CAS_file_bytes']==t['payload_input_bytes']+OBJECT.size*t['object_opens']
                assert t['CAS_decoded_output_bytes']==t['compressed_decode_output_bytes']+t['raw_codec_output_bytes']
                for k,v in t.items():
                    if type(v) is int:totals[k]+=v
            for epoch,ingest in enumerate(data['ingests']):
                with memory.store.snapshot(ingest['commit']['snapshot_id']) as snap:
                    expected=sources(epoch,layout);assert set(snap.files)==set(expected)
                    for name,raw_source in expected.items():assert snap.read_range(name)==raw_source;recovered+=1
            tree=ledger(memory.root);saved=json.loads((folder/'full-file-ledger.json').read_text('utf-8'))
            assert tree==saved['before']==saved['after'] and data['memory_tree_unchanged'] and data['head_unchanged']
            assert digest(encoded(tree))==data['memory_tree_sha256'] and memory.current()==data['ingests'][-1]['commit']['snapshot_id']
            if layout in trees:assert tree==trees[layout]
            else:trees[layout]=tree
            actual=Counter()
            for path in folder.rglob('*'):
                if path.is_file():
                    group=path.relative_to(folder).parts[0];actual['memory_bytes' if group=='memory' else 'source_current_bytes' if group=='source' else 'other_worker_files_bytes']+=path.stat().st_size
            assert dict(actual)==data['files']
            rows.append({'round':n,'layout':layout,'accepted':11,'budget_rejected':10,'bindings':111,'traffic':dict(totals),
                'instrumented_call_wall_s':sum(c['instrumented_call_wall_s'] for c in cases),
                'instrumented_call_cpu_s':sum(c['instrumented_call_cpu_s'] for c in cases),
                'audit_wall_s':sum(c['audit_wall_s'] for c in cases),'audit_cpu_s':sum(c['audit_cpu_s'] for c in cases),
                'ingest_wall_s':sum(i['wall_s'] for i in data['ingests']),'ingest_cpu_s':sum(i['cpu_s'] for i in data['ingests']),
                **{k:data[k] for k in ('worker_wall_s','worker_cpu_s','observed_peak_rss_bytes','files','recovery','original_lookup_baseline_wall_s','original_lookup_baseline_cpu_s')},
                'parent_full_process_wall_s':parent['parent_full_process_wall_s']})
    assert dict(outcomes)=={'accepted':66,'budget-rejected':60} and bindings==666 and recovered==36
    save(out/'derived-metrics.json',{'rows':rows,'budget_rejection_CAS_work':budget_reads,'nonzero_CAS_read_budget_rejections':sum(r['application_CAS_file_bytes']>0 for r in budget_reads),
        'raw_report_json_bytes':raw_json,'driver_log_bytes':sum(p.stat().st_size for p in out.glob('*.log')),'performance_gain_gate':None})
    save(out/'source-checksums.json',checks)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+k for k in checks}|{'rkv1/memory_demo.html'}
    programs=[k for k in env['program_protocol_sha256'] if k.startswith('scripts/')]
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
        'assessment_programs':{k:{'bytes':Path(k).stat().st_size,'sha256':digest(Path(k).read_bytes())} for k in programs},
        'new_training_runs':0,'new_model_bytes':0,'dictionary_bytes':0})
    save(out/'validation.json',{'primary_cases':108,'primary_accepted':54,'primary_expected_budget_rejected':54,'controls':18,
        'control_duplicate_accepted':6,'control_duplicate_budget_rejected':6,'control_missing_accepted_empty':6,
        'all_cases':126,'accepted':66,'expected_budget_rejected':60,'accepted_bindings':666,'full_source_files_recovered':36,
        'traffic_conservation_cases':126,'parent_timing_records':6,'all_mechanical_gates_pass':True,'performance_gain_gate':None,
        'unit_tests_run':259,'unit_tests_passed':258,'unit_tests_skipped':1,'runtime_module_count':len(checks),'html_files':1,
        'freeze':args.freeze,'new_remote_model_calls':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained')
    for layout,dx,color in (('clustered',-.18,'#64748b'),('separated',.18,'#2563eb')):
        rr=[r for r in rows if r['layout']==layout]
        for ax,key,div in ((axes[0],'instrumented_call_wall_s',1),(axes[1],'parent_full_process_wall_s',1),(axes[2],'observed_peak_rss_bytes',1<<20)):
            ax.bar([r['round']+dx for r in rr],[r[key]/div for r in rr],.34,label=layout,color=color)
    for ax,title,unit in zip(axes,('Instrumented API call cost','Complete worker cost','Observed worker peak RSS'),('Seconds / 21 cases','Seconds / worker','MiB, observed interval')):
        ax.set_title(title);ax.set_ylabel(unit);ax.set_xticks((1,2,3));ax.set_xlabel('Round');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        ax.legend(loc='upper center',bbox_to_anchor=(.5,-.17),ncol=2,frameon=False,fontsize=8)
    fig.suptitle('RKV-1 v0.47: public batch API mechanical acceptance; cost observations, no speed-gain comparison')
    fig.savefig(out/'batch-api.png',dpi=160);plt.close(fig)
    save(out/'analysis-timing.json',{'analysis_wall_s':time.perf_counter()-began,'analysis_cpu_s':time.process_time()-cpu,
        'observed_peak_rss_bytes':peak_rss(),'scope':'Separate synthetic source/proof/tree/counter audit and plot; excludes initial interpreter startup and writing this record'})
    print(json.dumps({'outcomes':dict(outcomes),'bindings':bindings,'recovered_files':recovered,'performance_gain_gate':None}))


if __name__=='__main__':main()
