"""Single-trace view factorial audit, including baseline identities and complete costs."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import statistics
import subprocess
import time
from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from rkv1.memory import Memory
from rkv1.store import OBJECT
from scripts.evidence_path_fixture import audit
from scripts.path_layout_fixture import sources,identity
from scripts.run_memory_concurrency import save


def semantic(proof):
    value=copy.deepcopy(proof)
    del value['snapshot_id']
    for hop in value['evidence']:
        for field in ('snapshot_id','path','offset'):del hop['locator'][field]
    return value


def main():
    began=time.perf_counter();began_cpu=time.process_time()
    p=argparse.ArgumentParser()
    for key in ('work','out','freeze','test-log'):p.add_argument('--'+key,required=True)
    args=p.parse_args();out=Path(args.out);work=Path(args.work)
    env=json.loads((out/'environment.json').read_text('utf-8'));checks=implementation_checksums()
    assert checks==env['implementation_checksums']
    for name,sha in checks.items():assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))==sha
    for name,sha in env['program_protocol_sha256'].items():
        assert digest(Path(name).read_bytes())==sha==digest(subprocess.check_output(['git','show',args.freeze+':'+name]))
    assert Path(__file__).read_bytes()==subprocess.check_output(['git','show',args.freeze+':scripts/analyze_view_paths.py'])
    test=Path(args.test_log).read_text('utf-8');assert 'Ran 253 tests' in test and 'OK (skipped=1)' in test
    rows=[];proofs=bindings=negative=recovered_files=raw_json_bytes=0;main_status=Counter()
    for n in (1,2,3):
        old=json.loads(Path(f'results/v0.40.0/round-{n}.json').read_text('utf-8'))
        old_cases=old['questions']+old['controls'];gold={c['question']['case_id']:c['proof'] for c in old_cases}
        for layout in ('clustered','separated'):
            reference_proofs=None;reference_tree=None;reference_questions=None
            for view,meter_mode in (('off','off'),('on','off'),('off','on'),('on','on')):
                label=f'round-{n}-{layout}-v{view}-m{meter_mode}';folder=work/label
                raw=(out/(label+'.json')).read_bytes();mr=(out/(label+'-meter.json')).read_bytes();pr=(out/(label+'-parent.json')).read_bytes()
                raw_json_bytes+=len(raw)+len(mr)+len(pr);data=json.loads(raw);sidecar=json.loads(mr);parent=json.loads(pr)
                assert (data['round'],data['layout'])==(n,layout)
                assert (sidecar['round'],sidecar['layout'],sidecar['view'],sidecar['meter'])==(n,layout,view,meter_mode)
                assert parent['return_code']==0 and parent['error'] is None
                assert parent['child_report_sha256']==digest(raw) and parent['meter_report_sha256']==digest(mr)
                assert parent['parent_full_process_wall_s']>=data['worker_wall_s']>0
                assert data['old_files_unchanged'] and data['head_unchanged'] and data['added_files_only_derived']
                assert data['ingestion_finished_elapsed_s']<data['questions_fsynced_elapsed_s']<=data['first_query_started_elapsed_s']
                assert len(data['questions'])==96 and len(data['controls'])==4 and len(data['negative_audits'])==2
                assert all(x['rejected'] for x in data['negative_audits']);negative+=2
                cases=data['questions']+data['controls'];assert len(sidecar['traces'])==100
                case_proofs={x['question']['case_id']:x['proof'] for x in cases}
                if reference_proofs is None:reference_proofs=case_proofs;reference_questions=data['question_sha256']
                else:assert case_proofs==reference_proofs and data['question_sha256']==reference_questions
                assert [c['question']['case_id'] for c in cases]==[c['question']['case_id'] for c in old_cases]
                memory=Memory(folder/'memory');totals=Counter();view_totals=Counter();peak=graph=0
                for index,(case,sc) in enumerate(zip(cases,sidecar['traces'])):
                    q=case['question'];proof=case['proof'];assert case['gate_pass']
                    if layout=='clustered':assert proof==gold[q['case_id']]
                    assert semantic(proof)==semantic(gold[q['case_id']])
                    verified=audit(memory,proof,snapshot=q['snapshot_id'],root_key=q['root_key'])
                    assert verified==case['audit'];bindings+=verified['bindings'];proofs+=1
                    if index<96:main_status[proof['status']]+=1
                    assert sc['index']==index and sc['root_key']==q['root_key'] and sc['snapshot_id']==q['snapshot_id']
                    encoded=json.dumps(proof,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
                    assert digest(encoded)==sc['proof_sha256']
                    c=sc['view'];t=sc['traffic']
                    if view=='off':assert c is None
                    else:
                        assert c['lookup_calls']==proof['lookup_calls'] and c['view_builds']==1
                        assert c['lookup_restored'] and c['resources_cleared'] and c['view_closed'] and not c['active']
                        assert c['view_storage'] in ('in-memory-replay-copy','read-only-base-connection')
                        assert c['peak_sqlite_logical_page_bytes']>0 and c['peak_metadata_graph_bytes']>0
                        peak=max(peak,c['peak_sqlite_logical_page_bytes']);graph=max(graph,c['peak_metadata_graph_bytes'])
                        for k in ('lookup_calls','view_builds'):view_totals[k]+=c[k]
                        key='view_storage:'+c['view_storage'];view_totals[key]+=1
                        for key in ('peak_snapshots','peak_deltas'):view_totals[key]=max(view_totals[key],c[key])
                    if meter_mode=='off':assert t is None
                    else:
                        if view=='off':
                            prior=json.loads(Path(f'results/v0.43.0/round-{n}-{layout}-coff-mon-meter.json').read_text('utf-8'))
                            assert t==prior['traces'][index]['traffic']
                        assert t['object_opens']==t['decode_attempts']==t['decode_successes'] and t['read_calls']==2*t['object_opens']
                        assert t['application_CAS_file_bytes']==t['payload_input_bytes']+OBJECT.size*t['object_opens']
                        assert t['CAS_decoded_output_bytes']==t['raw_codec_output_bytes']+t['compressed_decode_output_bytes']
                        assert t['physical_SSD_bytes'] is None and t['all_system_file_bytes'] is None
                        for key,value in t.items():
                            if type(value) is int:totals[key]+=value
                for epoch,ingest in enumerate(data['ingests']):
                    expected=identity(epoch,layout);assert ingest['source_files']==expected['files']
                    assert ingest['source_sha256']==expected['original_corpus_sha256']
                    snap=memory.store.snapshot(ingest['snapshot_id']);expected_raw=sources(epoch,layout)
                    assert set(snap.files)==set(expected_raw)
                    block_ids=set()
                    for name,source in expected_raw.items():
                        assert snap.read_range(name)==source;recovered_files+=1
                        if layout=='separated':
                            assert len(snap.files[name]['chunks'])==1
                            block_ids.add(snap.files[name]['chunks'][0]['id'])
                    if layout=='separated':assert len(block_ids)==3
                ledger_raw=(folder/'full-file-ledger.json').read_bytes();ledger=json.loads(ledger_raw)
                assert digest(ledger_raw)==data['file_accounting']['full_ledger_sha256']
                baseline=json.loads(Path(f'results/v0.43.0/round-{n}-{layout}-coff-mon.json').read_text('utf-8'))
                assert data['question_sha256']==baseline['question_sha256'] and digest(ledger_raw)==baseline['file_accounting']['full_ledger_sha256']
                assert [c['proof'] for c in cases]==[c['proof'] for c in baseline['questions']+baseline['controls']]
                tree={x.relative_to(folder/'memory').as_posix():{'bytes':x.stat().st_size,'sha256':digest(x.read_bytes())}
                      for x in (folder/'memory').rglob('*') if x.is_file()}
                assert tree==ledger['after_queries'] and all(tree.get(k)==v for k,v in ledger['before_queries'].items())
                if reference_tree is None:reference_tree=tree
                else:assert tree==reference_tree
                costs={'source_current_bytes':0,'other_worker_files_bytes':0,'memory_bytes':sum(v['bytes'] for v in tree.values())}
                for path in folder.rglob('*'):
                    if path.is_file():
                        rel=path.relative_to(folder).parts
                        if rel[0]=='source':costs['source_current_bytes']+=path.stat().st_size
                        elif rel[0]!='memory':costs['other_worker_files_bytes']+=path.stat().st_size
                assert costs['memory_bytes']==data['file_accounting']['final_memory_bytes']
                rows.append({'round':n,'layout':layout,'view':view,'meter':meter_mode,
                    'traffic':dict(totals) if meter_mode=='on' else None,'view_totals':dict(view_totals) if view=='on' else None,
                    'peak_sqlite_logical_page_bytes':peak if view=='on' else None,'peak_metadata_graph_bytes':graph if view=='on' else None,
                    **{k:sum(c[k] for c in cases) for k in ('trace_wall_s','trace_cpu_s','independent_audit_wall_s','independent_audit_cpu_s','derived_write_wall_s','derived_write_cpu_s')},
                    'parent_full_process_wall_s':parent['parent_full_process_wall_s'],'worker_wall_s':data['worker_wall_s'],
                    'worker_cpu_s':data['worker_cpu_s'],'ingest_wall_s':sum(i['wall_s'] for i in data['ingests']),
                    'ingest_cpu_s':sum(i['cpu_s'] for i in data['ingests']),
                    'observed_peak_rss_bytes':data['peak_rss_bytes'],'admitted_record_bytes':sum(c['proof']['admitted_record_bytes'] for c in cases),
                    'derived_added_bytes':data['file_accounting']['derived_added_bytes'],**costs})
    assert (proofs,bindings,negative,recovered_files)==(2400,6840,48,624)
    assert main_status=={'complete':2232,'missing':48,'cycle':24}
    def row(n,l,c,m):return next(r for r in rows if (r['round'],r['layout'],r['view'],r['meter'])==(n,l,c,m))
    gates={};time_pairs=[];work_pairs=[]
    for layout in ('clustered','separated'):
        for n in (1,2,3):
            a=row(n,layout,'off','off');b=row(n,layout,'on','off');c=row(n,layout,'off','on');d=row(n,layout,'on','on')
            time_pairs.append({'round':n,'layout':layout,**{k:b[k]/a[k] if a[k]>0 else None for k in ('trace_wall_s','trace_cpu_s','parent_full_process_wall_s')}})
            work_pairs.append({'round':n,'layout':layout,**{k:d['traffic'][k]/c['traffic'][k] for k in ('application_CAS_file_bytes','CAS_decoded_output_bytes')}})
        med={k:statistics.median(p[k] for p in time_pairs if p['layout']==layout)
             if all(p[k] is not None for p in time_pairs if p['layout']==layout) else None
             for k in ('trace_wall_s','trace_cpu_s','parent_full_process_wall_s')}
        gates[layout]={'expected_work_gate':all((p[k]<1 if layout=='separated' else p[k]==1) for p in work_pairs if p['layout']==layout for k in ('application_CAS_file_bytes','CAS_decoded_output_bytes')),'work_rule':'strict_reduction' if layout=='separated' else 'exact_equality',
                       'median_unmetered_time_ratios':med,'time_joint_gate':all(v is not None and v<=1 for v in med.values())}
    save(out/'derived-metrics.json',{'rows':rows,'unmetered_time_pairs':time_pairs,'metered_work_pairs':work_pairs,
        'gates_by_layout':gates,'separated_reduction_and_clustered_control_gate':all(g['expected_work_gate'] for g in gates.values()),'raw_report_json_bytes':raw_json_bytes,
        'driver_log_bytes':sum(p.stat().st_size for p in out.glob('*.log'))})
    save(out/'source-checksums.json',checks)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+key for key in checks}|{'rkv1/memory_demo.html'}
    programs=('scripts/query_view.py','scripts/run_view_paths.py','scripts/analyze_view_paths.py','scripts/run_layout_paths.py','scripts/query_block_cache.py','scripts/cas_traffic.py','scripts/path_layout_fixture.py','scripts/evidence_path_fixture.py','scripts/run_memory_concurrency.py')
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
        'assessment_programs':{s:{'bytes':Path(s).stat().st_size,'sha256':digest(Path(s).read_bytes())} for s in programs},
        'new_training_runs':0,'new_model_bytes':0,'native_specific_bytes':0})
    save(out/'validation.json',{'main_questions':2304,'main_status':dict(main_status),'controls':96,'negative_audits':negative,
        'proofs':proofs,'accepted_bindings':bindings,'all_mechanical_gates_pass':True,'all_clustered_proofs_match_v040':True,
        'cross_layout_semantics_and_record_sha_match':True,'four_condition_tree_identity_groups':6,'historical_source_files_recovered':recovered_files,
        'parent_timing_records':24,'meter_ON_conservation_cases':1200,'meter_OFF_null_cases':1200,'view_ON_scope_and_cleanup_cases':1200,
        'gates_by_layout':gates,'unit_tests_run':253,'unit_tests_passed':252,'unit_tests_skipped':1,'runtime_module_count':len(checks),'html_files':1,
        'freeze':args.freeze,'new_remote_model_calls':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(14,9),layout='constrained')
    for y,layout in enumerate(('clustered','separated')):
        for view,delta,color in (('off',-.18,'#64748b'),('on',.18,'#2563eb')):
            axes[y,0].bar([n+delta for n in (1,2,3)],[row(n,layout,view,'on')['traffic']['CAS_decoded_output_bytes']/(1<<20) for n in (1,2,3)],.34,label='View reuse '+view,color=color)
            axes[y,1].bar([n+delta for n in (1,2,3)],[row(n,layout,view,'off')['trace_wall_s'] for n in (1,2,3)],.34,label='View reuse '+view,color=color)
            axes[y,2].bar([n+delta for n in (1,2,3)],[row(n,layout,view,'off')['observed_peak_rss_bytes']/(1<<20) for n in (1,2,3)],.34,label='View reuse '+view,color=color)
        for ax,title,unit in zip(axes[y],('CAS decoded work, meter ON','Trace wall, meter OFF','Observed worker peak RSS, meter OFF'),('MiB / 100 traces','Seconds / 100 traces','MiB, observed interval')):
            ax.set_title(layout+': '+title);ax.set_ylabel(unit);ax.set_xticks((1,2,3));ax.set_xlabel('Paired round')
            ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.legend(loc='upper center',bbox_to_anchor=(.5,-.16),ncol=2,frameon=False,fontsize=8)
    fig.suptitle('RKV-1 v0.45: fixed-SID preverified SQLite view, two known layouts, no block cache')
    fig.savefig(out/'view-paths.png',dpi=160);plt.close(fig)
    save(out/'analysis-timing.json',{'analysis_wall_s':time.perf_counter()-began,'analysis_cpu_s':time.process_time()-began_cpu,
        'observed_peak_rss_bytes':peak_rss(),'scope':'Separate diagnostic full-file/source/proof audit and plot, excludes initial interpreter startup and writing this timing record; not query performance'})
    print(json.dumps({'gates':gates,'proofs':proofs,'bindings':bindings,'historical_files':recovered_files}))


if __name__=='__main__':main()
