"""Independent partition and dynamic-program bound audit, not a new score trial."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import time
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from scripts.evidence_retrieval import encoded,ranking,admit
from scripts.run_retrieval_gap import load_verified,CONDITIONS
from scripts.run_memory_concurrency import save
from scripts.retrieval_gap import CATEGORIES


def audit_bound(loc,targets,value,candidates=None):
    available=set(targets)&set(loc)
    if candidates is not None:available&=set(candidates)
    costs=[10**30]*13;costs[0]=0
    for key in available:
        length=loc[key]['length']
        for n in range(12,0,-1):costs[n]=min(costs[n],costs[n-1]+length)
    best=max(n for n in range(13) if costs[n]<=4096)
    selected=value['known_gold_selected_ids'];assert len(selected)==len(set(selected))==best and set(selected)<=available
    assert sum(loc[k]['length'] for k in selected)==value['selected_bytes']<=4096
    assert value['recovered_groups']==best and value['gold_groups']==len(targets) and value['complete_possible']==(best==len(targets))
    assert value['recall_ceiling']==best/len(targets)


def main():
    begin=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser()
    for k in ('work','out','model','freeze','test-log'):p.add_argument('--'+k,required=True)
    args=p.parse_args();out=Path(args.out);manifest=json.loads(Path('docs/retrieval-gap-inputs.json').read_bytes())
    model_raw=load_verified(Path(args.model),manifest['model_sha256']);model=json.loads(model_raw);loc=model['shared']['locators']
    env=json.loads((out/'environment.json').read_bytes());checks=implementation_checksums();assert checks==env['implementation_checksums']
    for k,v in checks.items():assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+k]))==v
    for k,v in env['program_protocol_sha256'].items():assert digest(Path(k).read_bytes())==v==digest(subprocess.check_output(['git','show',args.freeze+':'+k]))
    log=Path(args.test_log).read_text('utf-8');assert 'Ran 270 tests' in log and 'OK (skipped=1)' in log
    rows=[];records_checked=groups_checked=0;raw_bytes=0
    for split,method in CONDITIONS:
        label=split+'-'+method;raw=(out/(label+'.json')).read_bytes();pr=(out/(label+'-parent.json')).read_bytes();raw_bytes+=len(raw)+len(pr)
        data=json.loads(raw);parent=json.loads(pr);assert parent['return_code']==0 and parent['error'] is None
        assert parent['child_report_sha256']==digest(raw) and parent['parent_full_process_wall_s']>=data['worker_wall_s']>0
        frozen=next(x for x in manifest['reports'] if (x['split'],x['method'])==(split,method))
        old_raw=load_verified(Path(frozen['report_path']),frozen['report_sha256']);query_raw=load_verified(Path(frozen['private_query_path']),frozen['private_query_sha256'])
        old=json.loads(old_raw);queries={r['row_index']:r['question'] for r in json.loads(query_raw)}
        assert data['archived_report_sha256']==digest(old_raw) and data['private_query_sha256']==digest(query_raw) and data['model_sha256']==digest(model_raw)
        assert len(data['records'])==len(old['records']);totals=Counter();oracle_sums=Counter()
        for diagnostic,rec in zip(data['records'],old['records']):
            assert diagnostic['row_index']==rec['row_index'] and diagnostic['question_id']==rec['question_id'] and diagnostic['archived_proof_sha256']==rec['proof_sha256']
            ranked=ranking(model,queries[rec['row_index']],method);selected,used=admit(model,ranked);assert selected==rec['selected_ids'] and used==rec['admitted_record_bytes']
            gold=set(rec['gold_id_groups']);prefix=set(list(dict.fromkeys(ranked))[:12]);expected={}
            for key in gold:
                if key in selected:category='recovered'
                elif key not in loc:category='unresolved_source'
                elif key not in ranked:category='no_candidate'
                elif key not in prefix:category='below_count_prefix'
                else:category='byte_budget_excluded'
                expected[key]=category
            counts=Counter({k:0 for k in CATEGORIES});counts.update(expected.values())
            assert diagnostic['partition']['categories_by_group']==expected and diagnostic['partition']['counts']==dict(counts)
            assert sum(counts.values())==len(gold)==rec['ID_metrics']['gold_groups'] and counts['recovered']==rec['ID_metrics']['recovered_groups']
            assert diagnostic['archived_ID_metrics']==rec['ID_metrics'] and diagnostic['archived_literal_metrics']==rec['literal_metrics']
            audit_bound(loc,gold,diagnostic['source_ID_oracle'])
            audit_bound(loc,gold,diagnostic['candidate_ID_oracle'],ranked)
            audit_bound(loc,set(rec['literal_groups']),diagnostic['literal_oracle'])
            for name in ('source_ID_oracle','candidate_ID_oracle','literal_oracle'):
                oracle_sums[name+'_recall_sum']+=diagnostic[name]['recall_ceiling'];oracle_sums[name+'_complete']+=diagnostic[name]['complete_possible']
            totals.update(counts);records_checked+=1;groups_checked+=len(gold)
        assert dict(totals)==data['counts'];n=len(data['records'])
        rows.append({'split':split,'method':method,'question_records':n,'counts':dict(totals),
            'archived_macro_ID_recall':sum(r['ID_metrics']['leaf_recall'] for r in old['records'])/n,
            'archived_complete_ID_questions':sum(r['ID_metrics']['complete_coverage'] for r in old['records']),
            **{name+'_macro_ceiling':oracle_sums[name+'_recall_sum']/n for name in ('source_ID_oracle','candidate_ID_oracle','literal_oracle')},
            **{name+'_complete_possible':oracle_sums[name+'_complete'] for name in ('source_ID_oracle','candidate_ID_oracle','literal_oracle')},
            'worker_wall_s':data['worker_wall_s'],'worker_cpu_s':data['worker_cpu_s'],'parent_full_process_wall_s':parent['parent_full_process_wall_s'],
            'observed_peak_rss_bytes':data['observed_peak_rss_bytes'],'loaded_bytes':data['loaded_bytes'],'replay_and_diagnostic':data['replay_and_diagnostic']})
    assert records_checked==1578 and groups_checked==6204
    ratios={r['split']:r['counts']['byte_budget_excluded']/(sum(r['counts'].values())-r['counts']['recovered']) for r in rows if r['method']=='graph'}
    dominant=all(v>=.5 for v in ratios.values())
    save(out/'derived-metrics.json',{'rows':rows,'records_checked':records_checked,'source_ID_groups_partitioned':groups_checked,
        'graph_missing_groups_first12_byte_exclusion_fraction':ratios,'first12_byte_exclusion_majority_hypothesis':dominant,
        'raw_report_json_bytes':raw_bytes,'driver_log_bytes':sum(p.stat().st_size for p in out.glob('*.log')),
        'new_scientific_trials':0,'new_training_runs':0,'oracle_is_not_deployable':True})
    save(out/'source-checksums.json',checks)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+k for k in checks}|{'rkv1/memory_demo.html'}
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),'assessment_programs':{
        k:{'bytes':Path(k).stat().st_size,'sha256':digest(Path(k).read_bytes())} for k in env['program_protocol_sha256'] if k.startswith('scripts/')},
        'new_training_runs':0,'new_model_bytes':0,'reused_model_bytes':len(model_raw)})
    save(out/'validation.json',{'diagnostic_workers':6,'parent_timing_records':6,'question_records_checked':1578,'source_ID_groups_partitioned':6204,
        'partition_and_DP_oracle_audit_pass':True,'first12_byte_exclusion_majority_hypothesis':dominant,'new_scientific_evaluation_trials':0,'new_model_training_runs':0,
        'new_original_source_range_bindings':0,'unit_tests_run':270,'unit_tests_passed':269,'unit_tests_skipped':1,'runtime_module_count':len(checks),'html_files':1,
        'freeze':args.freeze,'new_remote_model_calls':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(14,5.5),layout='constrained');colors=('#10b981','#dc2626','#f59e0b','#2563eb','#9333ea')
    for ax,split in zip(axes,('dev','test')):
        rr=[r for r in rows if r['split']==split];bottom=[0]*3
        for category,color in zip(CATEGORIES,colors):
            vals=[r['counts'][category] for r in rr];ax.bar([r['method'] for r in rr],vals,bottom=bottom,label=category,color=color);bottom=[a+b for a,b in zip(bottom,vals)]
        ax.set_title(split+': fixed source-ID group positions');ax.set_ylabel('Gold groups, archived split');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.margins(y=.1)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=3,frameon=False,fontsize=9)
    fig.suptitle('RKV-1 v0.52: known-report failure ledger, no new retrieval trial; gold-aware bounds diagnostic only')
    fig.savefig(out/'retrieval-gap.png',dpi=160);plt.close(fig)
    save(out/'analysis-timing.json',{'analysis_wall_s':time.perf_counter()-begin,'analysis_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'scope':'Independent partition replay and dynamic-program oracle proof plus plot; not online inference/retrieval time'})
    print(json.dumps({'first12_byte_exclusion_majority':dominant,'fractions':ratios,'question_records':records_checked,'gold_groups':groups_checked}))


if __name__=='__main__':main()
