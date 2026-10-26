"""Audit frozen path records and full historical sources; no model calls."""
import argparse
import collections
import json
from pathlib import Path
import statistics
import subprocess
import time

from rkv1.core import digest
from rkv1.memory import Memory
from rkv1.controlled import implementation_checksums
from scripts.evidence_path_fixture import corpus,gold
from scripts.run_memory_concurrency import save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','work','freeze','input-freeze','test-log'):p.add_argument('--'+name,required=True)
    args=p.parse_args();out=Path(args.out);work=Path(args.work)
    env=json.loads((out/'environment.json').read_text('utf-8'));checks=implementation_checksums()
    assert checks==env['implementation_checksums']
    for name,sha in checks.items():assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+name]))==sha
    for rel,sha in env['driver_protocol_sha256'].items():
        assert digest(Path(rel).read_bytes())==sha==digest(subprocess.check_output(['git','show',args.freeze+':'+rel]))
    assert Path(__file__).read_bytes()==subprocess.check_output(['git','show',args.freeze+':scripts/analyze_evidence_paths.py'])
    raw_manifest=Path('docs/evidence-path-inputs.json').read_bytes()
    assert raw_manifest==subprocess.check_output(['git','show',args.input_freeze+':docs/evidence-path-inputs.json'])
    manifest=json.loads(raw_manifest);assert manifest==env['fixture_manifest']
    log=Path(args.test_log).read_text('utf-8');assert 'Ran 240 tests' in log and 'OK (skipped=1)' in log
    rows=[];total_bindings=0;expected_counts=collections.Counter();physical=[]
    source_start=time.perf_counter();source_cpu=time.process_time()
    for n in range(1,4):
        data=json.loads((out/f'round-{n}.json').read_text('utf-8'))
        assert data['round']==n and len(data['questions'])==96 and len(data['controls'])==4
        assert len(data['ingests'])==13 and data['old_files_unchanged'] and data['head_unchanged'] and data['added_files_only_derived']
        assert data['no_numpy_imported'] and data['remote_model_calls']==0
        assert data['ingestion_finished_elapsed_s']<=data['questions_fsynced_elapsed_s']<=data['first_query_started_elapsed_s']
        question_raw=(work/f'round-{n}/questions.json').read_bytes()
        assert digest(question_raw)==data['question_sha256']
        assert json.loads(question_raw)==[case['question'] for case in data['questions']]
        assert {(c['question']['chain'],c['question']['epoch']) for c in data['questions']}=={(c,e) for c in range(32) for e in (0,6,12)}
        memory=Memory(work/f'round-{n}/memory')
        for epoch,item in enumerate(data['ingests']):
            with memory.store.snapshot(item['snapshot_id']) as snap:
                raw=snap.read_range('records.jsonl')
                assert raw==corpus(epoch) and digest(raw)==manifest['epochs'][epoch]['sha256']==item['source_sha256']
        all_cases=data['questions']+data['controls']
        for case in data['questions']:
            q=case['question'];status,value,keys=gold(q['chain'],q['epoch'])
            assert case['gate_pass'] and case['expected_status']==status and case['expected_value']==value
            assert case['proof']['status']==status and case['proof']['value']==value
            assert [h['key'] for h in case['proof']['evidence']]==keys==case['expected_keys']
            expected_counts[status]+=1
        for case in data['controls']:
            assert case['gate_pass'] and case['proof']['status']==case['expected_status'] and case['proof']['value'] is None
        for case in all_cases:
            proof=case['proof'];q=case['question'];audit=case['audit']
            assert proof['snapshot_id']==q['snapshot_id'] and proof['root_key']==q['root_key']
            assert all(h['locator']['snapshot_id']==q['snapshot_id'] for h in proof['evidence'])
            assert len(proof['evidence'])==audit['bindings'] and proof['admitted_record_bytes']==audit['requested_record_bytes']
            assert proof['physical_read_or_decompressed_bytes'] is None
            total_bindings+=audit['bindings']
        assert len(data['negative_audits'])==2 and all(x['rejected'] for x in data['negative_audits'])
        ledger_raw=(work/f'round-{n}/full-file-ledger.json').read_bytes()
        assert digest(ledger_raw)==data['file_accounting']['full_ledger_sha256']
        ledger=json.loads(ledger_raw);actual={x.relative_to(memory.root).as_posix():{'bytes':x.stat().st_size,'sha256':digest(x.read_bytes())}
                                           for x in memory.root.rglob('*') if x.is_file()}
        assert actual==ledger['after_queries']
        assert all(actual.get(k)==v for k,v in ledger['before_queries'].items())
        total=sum(x['bytes'] for x in actual.values());account=data['file_accounting']
        assert total==account['final_memory_bytes']==account['before_query_bytes']+account['derived_added_bytes']
        extra=total-account['memory_stats']['logical_file_bytes']
        physical.append(extra)
        rows.append({'round':n,'question_sha256':data['question_sha256'],'complete':sum(c['proof']['status']=='complete' for c in data['questions']),
            'expected_missing_or_cycle':sum(c['proof']['status']!='complete' for c in data['questions']),
            'bindings':sum(c['audit']['bindings'] for c in all_cases),'lookup_calls':sum(c['proof']['lookup_calls'] for c in all_cases),
            'verified_record_bytes':sum(c['proof']['verified_record_bytes'] for c in all_cases),
            'admitted_record_bytes':sum(c['proof']['admitted_record_bytes'] for c in all_cases),
            'independent_audit_requested_record_bytes':sum(c['audit']['requested_record_bytes'] for c in all_cases),
            'final_memory_bytes':total,'before_query_bytes':account['before_query_bytes'],
            'derived_added_bytes':account['derived_added_bytes'],'memory_stats_unclassified_bytes':extra,
            'ingest_wall_s':sum(x['wall_s'] for x in data['ingests']),'ingest_cpu_s':sum(x['cpu_s'] for x in data['ingests']),
            **{metric:sum(c[metric] for c in all_cases) for metric in ('trace_wall_s','trace_cpu_s','independent_audit_wall_s',
               'independent_audit_cpu_s','derived_write_wall_s','derived_write_cpu_s')},
            'worker_wall_s':data['worker_wall_s'],'worker_cpu_s':data['worker_cpu_s'],
            'peak_rss_bytes':data['peak_rss_bytes'],'physical_read_or_decompressed_bytes':None})
    assert dict(expected_counts)=={'complete':279,'missing':6,'cycle':3}
    assert total_bindings==855
    source_audit={'wall_s':time.perf_counter()-source_start,'cpu_s':time.process_time()-source_cpu,
                  'full_historical_sources_recovered_and_equal':39,'scope':'Postcampaign analysis overhead, not query throughput'}
    save(out/'derived-metrics.json',{'rounds':rows,'postcampaign_audit':source_audit})
    files={x.as_posix():{'bytes':x.stat().st_size,'sha256':digest(x.read_bytes())} for x in sorted(Path('rkv1').rglob('*')) if x.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+k for k in checks}|{'rkv1/memory_demo.html'}
    save(out/'source-checksums.json',checks)
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(x['bytes'] for x in files.values()),
        'evidence_path_source_bytes':files['rkv1/evidence_path.py']['bytes'],'path_source_already_in_full_runtime':True,
        'evaluation_programs':{str(x):{'bytes':x.stat().st_size,'sha256':digest(x.read_bytes())} for x in
            map(Path,('scripts/evidence_path_fixture.py','scripts/run_evidence_paths.py','scripts/prepare_evidence_paths.py','scripts/analyze_evidence_paths.py'))},
        'external_model_bytes':0,'dictionary_bytes':0,'new_training_runs':0,'native_specific_bytes':0,
        'scope':'Runtime source, evaluation programs and memory files separately allocated; no complete platform TCO claim'})
    save(out/'validation.json',{'main_questions':288,'complete_with_expected_value':279,'expected_missing':6,'expected_cycle':3,
         'all_288_main_gates_pass':True,'controls':12,'all_controls_expected_failure':True,'negative_audits_rejected':6,
         'accepted_original_record_bindings':855,'full_historical_source_checks':39,'full_trees_and_existing_files_verified':True,
         'all_question_freeze_timelines_valid':True,'unit_tests_run':240,'unit_tests_passed':239,'unit_tests_skipped':1,
         'test_log_sha256':digest(Path(args.test_log).read_bytes()),'runtime_protocol_freeze':args.freeze,'input_freeze':args.input_freeze,
         'runtime_module_count':len(checks),'html_files':1,'new_remote_model_calls':0,'physical_read_or_decompressed_bytes':None,
         'cold_cache':None,'cross_machine':None,'model_reasoning_quality':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained')
    x=[r['round'] for r in rows]
    axes[0].bar(x,[r['complete'] for r in rows],label='Complete (93 expected)',color='#2563eb')
    axes[0].bar(x,[r['expected_missing_or_cycle'] for r in rows],bottom=[r['complete'] for r in rows],label='Missing/cycle (3 expected)',color='#d97706')
    axes[0].set_ylabel('Main queries (96 per round)');axes[0].set_title('Correct statuses, not model answers')
    axes[1].bar(x,[r['before_query_bytes']/1024 for r in rows],label='Stored sources/index/history',color='#64748b')
    axes[1].bar(x,[r['derived_added_bytes']/1024 for r in rows],bottom=[r['before_query_bytes']/1024 for r in rows],label='Derived path records',color='#16a34a')
    axes[1].set_ylabel('KiB, full memory file tree');axes[1].set_title('All persistent memory files charged')
    for field,label,color in (('ingest_wall_s','13 ingests','#64748b'),('trace_wall_s','100 traces','#2563eb'),
                             ('independent_audit_wall_s','100 original-record audits','#d97706'),('derived_write_wall_s','100 derived writes','#16a34a')):
        index=['ingest_wall_s','trace_wall_s','independent_audit_wall_s','derived_write_wall_s'].index(field)
        axes[2].bar([n+(index-1.5)*.18 for n in x],[r[field] for r in rows],.17,label=label,color=color)
    axes[2].set_ylabel('Seconds (log)');axes[2].set_yscale('log');axes[2].set_title('Wall time by separately charged stage')
    for ax in axes:
        ax.set_xticks(x,[f'Round {n}' for n in x]);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        ax.legend(loc='upper left',fontsize=7)
    axes[0].set_ylim(0,120)
    axes[1].set_ylim(0,max(r['final_memory_bytes']/1024 for r in rows)*1.25)
    fig.suptitle('RKV-1 v0.40: synthetic known-root / specified-SID explicit evidence paths')
    fig.savefig(out/'evidence-paths.png',dpi=160);plt.close(fig)
    print(json.dumps({'main_gates':288,'controls':12,'negative_audits':6,'bindings':855,'storage_stats_extra':physical}))


if __name__=='__main__':main()
