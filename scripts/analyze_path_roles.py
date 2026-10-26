"""Audit exclusive original CAS event work, compare frozen v043, no speed test."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import time
from rkv1.benchmark import peak_rss
from rkv1.core import digest,valid_hash
from rkv1.controlled import implementation_checksums
from rkv1.memory import Memory
from rkv1.store import OBJECT
from scripts.evidence_path_fixture import audit
from scripts.path_layout_fixture import sources
from scripts.path_roles import ROLES
from scripts.run_memory_concurrency import save


def main():
    began=time.perf_counter();cpu=time.process_time()
    p=argparse.ArgumentParser()
    for key in ('work','out','freeze','test-log'):p.add_argument('--'+key,required=True)
    args=p.parse_args();out=Path(args.out);work=Path(args.work)
    env=json.loads((out/'environment.json').read_text('utf-8'));checks=implementation_checksums()
    assert checks==env['implementation_checksums']
    for name,sha in checks.items():assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))==sha
    for name,sha in env['program_protocol_sha256'].items():assert digest(Path(name).read_bytes())==sha==digest(subprocess.check_output(['git','show',args.freeze+':'+name]))
    assert Path(__file__).read_bytes()==subprocess.check_output(['git','show',args.freeze+':scripts/analyze_path_roles.py'])
    log=Path(args.test_log).read_text('utf-8');assert 'Ran 250 tests' in log and 'OK (skipped=1)' in log
    rows=[];proofs=bindings=files_recovered=events_count=raw_bytes=0;status=Counter()
    for n in (1,2,3):
        for layout in ('clustered','separated'):
            label=f'round-{n}-{layout}';folder=work/label
            raw=(out/(label+'.json')).read_bytes();rr=(out/(label+'-roles.json')).read_bytes();pr=(out/(label+'-parent.json')).read_bytes()
            raw_bytes+=len(raw)+len(rr)+len(pr);data=json.loads(raw);roles=json.loads(rr);parent=json.loads(pr)
            prior_name=f'round-{n}-{layout}-coff-mon'
            old=json.loads(Path(f'results/v0.43.0/{prior_name}.json').read_text('utf-8'))
            old_meter=json.loads(Path(f'results/v0.43.0/{prior_name}-meter.json').read_text('utf-8'))
            assert (data['round'],data['layout'])==(n,layout)==(roles['round'],roles['layout'])
            assert parent['return_code']==0 and parent['error'] is None
            assert parent['child_report_sha256']==digest(raw) and parent['role_report_sha256']==digest(rr)
            assert parent['parent_full_process_wall_s']>=data['worker_wall_s']>0
            assert data['old_files_unchanged'] and data['head_unchanged'] and data['added_files_only_derived']
            assert data['question_sha256']==old['question_sha256']
            assert data['ingestion_finished_elapsed_s']<data['questions_fsynced_elapsed_s']<=data['first_query_started_elapsed_s']
            assert len(data['questions'])==96 and len(data['controls'])==4
            assert len(data['negative_audits'])==2 and all(x['rejected'] for x in data['negative_audits'])
            cases=data['questions']+data['controls'];old_cases=old['questions']+old['controls']
            assert len(roles['traces'])==len(old_meter['traces'])==100
            memory=Memory(folder/'memory');totals=Counter();by_role={role:Counter() for role in ROLES};role_calls=Counter()
            block_calls=unique_requests=0
            for index,(case,prior,sc,prior_sc) in enumerate(zip(cases,old_cases,roles['traces'],old_meter['traces'])):
                q=case['question'];proof=case['proof']
                assert case['gate_pass'] and q==prior['question'] and proof==prior['proof']
                assert audit(memory,proof,snapshot=q['snapshot_id'],root_key=q['root_key'])==case['audit']
                bindings+=case['audit']['bindings'];proofs+=1
                if index<96:status[proof['status']]+=1
                assert sc['index']==index and sc['root_key']==q['root_key'] and sc['snapshot_id']==q['snapshot_id']
                assert sc['proof_sha256']==digest(json.dumps(proof,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
                rec=sc['roles'];t=rec['traffic'];assert t==prior_sc['traffic']
                assert rec['methods_restored'] and not rec['active'] and rec['final_role']=='other_trace'
                assert t['object_opens']==t['decode_attempts']==t['decode_successes'] and t['read_calls']==2*t['object_opens']
                assert t['application_CAS_file_bytes']==t['payload_input_bytes']+OBJECT.size*t['object_opens']
                assert t['CAS_decoded_output_bytes']==t['raw_codec_output_bytes']+t['compressed_decode_output_bytes']
                assert t['physical_SSD_bytes'] is None and t['all_system_file_bytes'] is None
                summed=Counter({k:0 for k,v in t.items() if type(v) is int});unique=set()
                for j,event in enumerate(rec['events']):
                    assert event['index']==j and event['role'] in ROLES and event['error'] is None
                    assert valid_hash(event['block_id']) and type(event['expected_size']) is int
                    assert event['returned_bytes']==event['expected_size']>0
                    assert event['traffic']['decode_successes']==event['traffic']['decode_attempts']==event['traffic']['object_opens']==1
                    assert event['traffic']['CAS_decoded_output_bytes']==event['returned_bytes']
                    assert all(type(v) is int and v>=0 for v in event['traffic'].values())
                    summed.update(event['traffic']);by_role[event['role']].update(event['traffic']);role_calls[event['role']]+=1
                    unique.add((event['block_id'],event['expected_size']));events_count+=1;block_calls+=1
                assert dict(summed)=={k:v for k,v in t.items() if type(v) is int}
                assert len(rec['events'])==t['decode_successes'];unique_requests+=len(unique);totals.update(summed)
            for ingest,prior_ingest in zip(data['ingests'],old['ingests']):
                assert ingest['snapshot_id']==prior_ingest['snapshot_id'] and ingest['source_files']==prior_ingest['source_files']
                snap=memory.store.snapshot(ingest['snapshot_id']);files=sources(ingest['epoch'],layout)
                assert set(snap.files)==set(files)
                for name,source in files.items():assert snap.read_range(name)==source;files_recovered+=1
            ledger_raw=(folder/'full-file-ledger.json').read_bytes();ledger=json.loads(ledger_raw)
            assert digest(ledger_raw)==data['file_accounting']['full_ledger_sha256']==old['file_accounting']['full_ledger_sha256']
            tree={p.relative_to(folder/'memory').as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in (folder/'memory').rglob('*') if p.is_file()}
            assert tree==ledger['after_queries'] and all(tree.get(k)==v for k,v in ledger['before_queries'].items())
            costs={'memory_bytes':sum(v['bytes'] for v in tree.values()),'source_current_bytes':0,'other_worker_files_bytes':0}
            for path in folder.rglob('*'):
                if path.is_file():
                    first=path.relative_to(folder).parts[0]
                    if first=='source':costs['source_current_bytes']+=path.stat().st_size
                    elif first!='memory':costs['other_worker_files_bytes']+=path.stat().st_size
            rows.append({'round':n,'layout':layout,'traffic':dict(totals),
                'roles':{role:{'block_calls':role_calls[role],'traffic':{key:by_role[role][key] for key in totals}} for role in ROLES},
                'block_calls':block_calls,'sum_trace_unique_block_requests':unique_requests,'repeated_calls_within_trace':block_calls-unique_requests,
                **{k:sum(c[k] for c in cases) for k in ('trace_wall_s','trace_cpu_s','independent_audit_wall_s','independent_audit_cpu_s','derived_write_wall_s','derived_write_cpu_s')},
                'parent_full_process_wall_s':parent['parent_full_process_wall_s'],'worker_wall_s':data['worker_wall_s'],
                'worker_cpu_s':data['worker_cpu_s'],'observed_peak_rss_bytes':data['peak_rss_bytes'],**costs,
                'derived_added_bytes':data['file_accounting']['derived_added_bytes']})
    assert (proofs,bindings,files_recovered,events_count)==(600,1710,156,12795)
    assert status=={'complete':558,'missing':12,'cycle':6}
    hypotheses=[]
    for n in (1,2,3):
        a,b=(next(r for r in rows if (r['round'],r['layout'])==(n,layout)) for layout in ('clustered','separated'))
        extra=b['traffic']['CAS_decoded_output_bytes']-a['traffic']['CAS_decoded_output_bytes']
        attributed=sum(b['roles'][role]['traffic']['CAS_decoded_output_bytes']-a['roles'][role]['traffic']['CAS_decoded_output_bytes'] for role in ('manifest_validation','index_view'))
        fraction=attributed/extra if extra>0 else None
        hypotheses.append({'round':n,'extra_decoded_bytes':extra,'extra_manifest_and_view_decoded_bytes':attributed,
            'attributed_fraction':fraction,'gate_pass':fraction is not None and fraction>=.80})
    gate=all(h['gate_pass'] for h in hypotheses)
    save(out/'derived-metrics.json',{'rows':rows,'hypothesis_rounds':hypotheses,'role_attribution_gate':gate,
        'raw_report_json_bytes':raw_bytes,'driver_log_bytes':sum(p.stat().st_size for p in out.glob('*.log')),
        'scope':'Role diagnostic timings are costs, not optimization performance comparisons'})
    save(out/'source-checksums.json',checks)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+key for key in checks}|{'rkv1/memory_demo.html'}
    programs=('scripts/path_roles.py','scripts/run_path_roles.py','scripts/analyze_path_roles.py','scripts/run_layout_paths.py',
              'scripts/path_layout_fixture.py','scripts/evidence_path_fixture.py','scripts/query_block_cache.py','scripts/cas_traffic.py','scripts/run_memory_concurrency.py')
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
        'assessment_programs':{s:{'bytes':Path(s).stat().st_size,'sha256':digest(Path(s).read_bytes())} for s in programs},
        'new_training_runs':0,'new_model_bytes':0,'native_specific_bytes':0})
    save(out/'validation.json',{'main_questions':576,'main_status':dict(status),'controls':24,'negative_audits':12,'proofs':proofs,
        'accepted_bindings':bindings,'historical_source_files_recovered':files_recovered,'role_events':events_count,
        'all_mechanical_gates_pass':True,'all_proofs_trees_and_traffic_match_v043':True,'role_conservation_and_restoration_cases':600,
        'role_attribution_gate':gate,'parent_timing_records':6,'unit_tests_run':250,'unit_tests_passed':249,'unit_tests_skipped':1,
        'runtime_module_count':len(checks),'html_files':1,'freeze':args.freeze,'new_remote_model_calls':0,
        'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
    names=('clustered','separated');colors=('#f59e0b','#8b5cf6','#2563eb','#94a3b8')
    # All deterministic work counts are identical in the three repeats; show every round in JSON.
    chosen=[next(r for r in rows if r['round']==1 and r['layout']==layout) for layout in names]
    for ax,key,scale,unit in ((axes[0],'CAS_decoded_output_bytes',1<<20,'MiB / 100 traces'),(axes[1],'application_CAS_file_bytes',1<<20,'MiB / 100 traces')):
        bottoms=[0.,0.]
        for role,color in zip(ROLES,colors):
            values=[r['roles'][role]['traffic'][key]/scale for r in chosen]
            ax.bar(names,values,bottom=bottoms,label=role,color=color);bottoms=[a+b for a,b in zip(bottoms,values)]
        ax.set_ylabel(unit);ax.set_title('Decoded output' if key.startswith('CAS_') else 'Application CAS read returns')
        ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='outside lower center',ncol=2,frameon=False)
    fig.suptitle('RKV-1 v0.44: original CAS work by exclusive call-entry role, cache OFF\nRound 1 shown; three full paired rounds preserved; no timing-benefit claim')
    fig.savefig(out/'path-roles.png',dpi=160);plt.close(fig)
    save(out/'analysis-timing.json',{'analysis_wall_s':time.perf_counter()-began,'analysis_cpu_s':time.process_time()-cpu,
        'observed_peak_rss_bytes':peak_rss(),'scope':'Separate full audit and plotting, excludes interpreter startup and this record writing; diagnostic cost'})
    print(json.dumps({'role_attribution_gate':gate,'hypothesis_rounds':hypotheses,'role_events':events_count}))


if __name__=='__main__':main()
