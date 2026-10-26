"""Independent source/hit/tree audit and frozen science-bundle cost gates."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import subprocess
import time
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.memory import Memory
from rkv1.store import OBJECT
from scripts.run_memory_concurrency import save
from scripts.api_bundles import SOURCE_SHA,SOURCE_BYTES,catalog,bundles,audit,canonical,public_proof,assert_text_free,ledger


def main():
    began=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser()
    for key in ('work','out','corpus','freeze','test-log'):p.add_argument('--'+key,required=True)
    args=p.parse_args();out=Path(args.out);work=Path(args.work);raw=Path(args.corpus).read_bytes()
    assert len(raw)==SOURCE_BYTES and digest(raw)==SOURCE_SHA;index=catalog(raw)
    env=json.loads((out/'environment.json').read_text('utf-8'));checks=implementation_checksums()
    assert checks==env['implementation_checksums']
    for k,sha in checks.items():assert sha==digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+k]))
    for k,sha in env['program_protocol_sha256'].items():
        assert sha==digest(Path(k).read_bytes())==digest(subprocess.check_output(['git','show',args.freeze+':'+k]))
    test=Path(args.test_log).read_text('utf-8');assert 'Ran 260 tests' in test and 'OK (skipped=1)' in test
    rows=[];bound=bundle_count=restored=raw_report_bytes=0
    for n in (1,2,3):
        for batch_size in (1,3,32):
            reference=None;tree_reference=None
            for api,meter in (('off','off'),('on','off'),('off','on'),('on','on')):
                label=f'round-{n}-{batch_size}-a{api}-m{meter}';folder=work/label
                raw_report=(out/(label+'.json')).read_bytes();parent_raw=(out/(label+'-parent.json')).read_bytes()
                raw_report_bytes+=len(raw_report)+len(parent_raw);data=json.loads(raw_report);parent=json.loads(parent_raw)
                assert_text_free(data);assert parent['return_code']==0 and parent['error'] is None
                assert parent['child_report_sha256']==digest(raw_report) and parent['parent_full_process_wall_s']>=data['worker_wall_s']>0
                assert (data['round'],data['batch_size'],data['api'],data['meter'])==(n,batch_size,api,meter)
                private_raw=(folder/'private-hits.json').read_bytes();assert digest(private_raw)==data['private_hits_sha256']
                private=json.loads(private_raw);plan=bundles(index,batch_size,n)
                assert len(data['cases'])==len(private)==len(plan)==32 and data['plan_sha256']==digest(canonical(plan))
                assert (folder/'plan.json').read_bytes()==canonical(plan)
                totals=Counter();identities={}
                sid=data['ingest']['commit']['snapshot_id']
                for q,case,pvt in zip(plan,data['cases'],private):
                    proof=pvt['proof'];assert q['case_id']==case['case_id']==pvt['case_id'] and proof['keys']==q['keys']
                    assert audit(index,proof,sid)==case['bindings']==batch_size;bound+=batch_size;bundle_count+=1
                    assert all(case[k]==v for k,v in public_proof(proof).items())
                    identities[case['case_id']]=case['proof_sha256']
                    assert case['selected_record_bytes']==sum(index[k]['length'] for k in q['keys'])
                    t=case['traffic'];meta=case['batch_result']
                    if meter=='off':assert t is None
                    else:
                        assert t['read_calls']==2*t['object_opens'] and t['object_opens']==t['decode_successes']==t['decode_attempts']
                        assert t['application_CAS_file_bytes']==t['payload_input_bytes']+OBJECT.size*t['object_opens']
                        assert t['CAS_decoded_output_bytes']==t['compressed_decode_output_bytes']+t['raw_codec_output_bytes']
                        for k,value in t.items():
                            if type(value) is int:totals[k]+=value
                    if api=='off':assert meta is None
                    else:
                        assert meta['admitted_source_bytes']==case['selected_record_bytes']
                        assert meta['max_keys']==32 and meta['max_source_bytes']==1<<20 and meta['wall_s']>0
                if reference is None:reference=identities
                else:assert reference==identities
                m=Memory(folder/'memory');tree=ledger(m.root);saved=json.loads((folder/'full-file-ledger.json').read_text('utf-8'))
                assert tree==saved['before']==saved['after'] and data['memory_tree_unchanged'] and digest(canonical(tree))==data['memory_tree_sha256']
                assert sum(v['bytes'] for v in tree.values())==data['files']['memory_bytes']
                if tree_reference is None:tree_reference=tree
                else:assert tree==tree_reference
                assert m.current()==sid and m.store.snapshot(sid).read_range('corpus.jsonl')==raw;restored+=1
                assert data['recovery']['bytes']==SOURCE_BYTES and data['recovery']['sha256']==SOURCE_SHA
                assert data['files']['source_bytes']==SOURCE_BYTES
                actual=Counter()
                for path in folder.rglob('*'):
                    if path.is_file():
                        group=path.relative_to(folder).parts[0]
                        actual['memory_bytes' if group=='memory' else 'source_bytes' if group=='source' else 'other_worker_files_bytes']+=path.stat().st_size
                assert dict(actual)==data['files']
                rows.append({'round':n,'batch_size':batch_size,'api':api,'meter':meter,'traffic':dict(totals) if meter=='on' else None,
                    'batch_request_count':32 if api=='on' else None,
                    **{k:sum(c[k] for c in data['cases']) for k in ('query_wall_s','query_cpu_s','audit_wall_s','audit_cpu_s','selected_record_bytes')},
                    'parent_full_process_wall_s':parent['parent_full_process_wall_s'],
                    **{k:data[k] for k in ('worker_wall_s','worker_cpu_s','observed_peak_rss_bytes','files')},
                    'ingest_wall_s':data['ingest']['wall_s'],'ingest_cpu_s':data['ingest']['cpu_s'],
                    'recovery_wall_s':data['recovery']['wall_s'],'recovery_cpu_s':data['recovery']['cpu_s']})
    assert (bundle_count,bound,restored)==(1152,13824,36)
    def row(n,w,v,m):return next(r for r in rows if (r['round'],r['batch_size'],r['api'],r['meter'])==(n,w,v,m))
    gates={};pairs=[];work_pairs=[]
    for w in (1,3,32):
        for n in (1,2,3):
            a=row(n,w,'off','off');b=row(n,w,'on','off');c=row(n,w,'off','on');d=row(n,w,'on','on')
            pairs.append({'round':n,'batch_size':w,**{k:b[k]/a[k] if a[k]>0 else None for k in ('query_wall_s','query_cpu_s','parent_full_process_wall_s')}})
            work_pairs.append({'round':n,'batch_size':w,'all_traffic_equal':c['traffic']==d['traffic'],
                **{k:d['traffic'][k]/c['traffic'][k] for k in ('application_CAS_file_bytes','CAS_decoded_output_bytes')}})
        med={k:statistics.median(p[k] for p in pairs if p['batch_size']==w) if all(p[k] is not None for p in pairs if p['batch_size']==w) else None
             for k in ('query_wall_s','query_cpu_s','parent_full_process_wall_s')}
        gates[w]={'expected_exact_CAS_equality':all(p['all_traffic_equal'] for p in work_pairs if p['batch_size']==w),
                  'median_unmetered_time_ratios':med,'time_joint_gate':all(v is not None and v<=1 for v in med.values())}
    save(out/'derived-metrics.json',{'rows':rows,'unmetered_time_pairs':pairs,'metered_work_pairs':work_pairs,'gates_by_batch_size':gates,
        'raw_report_json_bytes':raw_report_bytes,'driver_log_bytes':sum(p.stat().st_size for p in out.glob('*.log'))})
    save(out/'source-checksums.json',checks)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+k for k in checks}|{'rkv1/memory_demo.html'}
    programs=[k for k in env['program_protocol_sha256'] if k.startswith('scripts/')]
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
        'assessment_programs':{k:{'bytes':Path(k).stat().st_size,'sha256':digest(Path(k).read_bytes())} for k in programs},
        'new_training_runs':0,'new_model_bytes':0,'dictionary_bytes':0})
    save(out/'validation.json',{'bundles':1152,'accepted_bindings':13824,'full_corpus_recoveries':36,'four_condition_identity_groups':9,
        'all_mechanical_gates_pass':True,'text_free_new_public_JSON':True,'parent_timing_records':36,'meter_ON_cases':576,'meter_OFF_null_cases':576,
        'batch_API_ON_contract_cases':576,'unit_tests_run':260,'unit_tests_passed':259,'unit_tests_skipped':1,
        'runtime_module_count':len(checks),'html_files':1,'freeze':args.freeze,'gates_by_batch_size':gates,'new_remote_model_calls':0,
        'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,3,figsize=(14,12),layout='constrained')
    for y,w in enumerate((1,3,32)):
        for v,dx,color in (('off',-.18,'#64748b'),('on',.18,'#2563eb')):
            for ax,key,unit,m in ((axes[y,0],'query_wall_s','Seconds / 32 bundles','off'),(axes[y,1],'parent_full_process_wall_s','Seconds / complete worker','off'),(axes[y,2],'observed_peak_rss_bytes','MiB, observed interval','off')):
                ax.bar([n+dx for n in (1,2,3)],[row(n,w,v,m)[key]/((1<<20) if key=='observed_peak_rss_bytes' else 1) for n in (1,2,3)],.34,label='Public batch API '+v,color=color)
                ax.set_ylabel(unit)
        for ax,title in zip(axes[y],('Query wall, meter OFF','Parent full wall, meter OFF','Observed worker peak RSS')):
            ax.set_title('Batch '+str(w)+': '+title);ax.set_xlabel('Paired round');ax.set_xticks((1,2,3));ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
            ax.legend(loc='upper center',bbox_to_anchor=(.5,-.16),ncol=2,frameon=False,fontsize=8)
    fig.suptitle('RKV-1 v0.48: existing SciFact, fixed1/3/32 keys, original lookups versus public batch API')
    fig.savefig(out/'api-bundles.png',dpi=160);plt.close(fig)
    save(out/'analysis-timing.json',{'analysis_wall_s':time.perf_counter()-began,'analysis_cpu_s':time.process_time()-cpu,
        'observed_peak_rss_bytes':peak_rss(),'scope':'Separate diagnostic byte/hit/tree audit and plot; excludes initial interpreter startup and writing this record'})
    for path in out.glob('*.json'):assert_text_free(json.loads(path.read_text('utf-8')))
    print(json.dumps({'gates':gates,'bundles':bundle_count,'bindings':bound,'corpus_recoveries':restored}))


if __name__=='__main__':main()
