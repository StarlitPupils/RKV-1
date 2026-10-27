"""Independent integer-cross-product Jaccard and all-claim gain audit."""
import argparse,json,statistics,subprocess,time
from pathlib import Path
from fractions import Fraction
from collections import Counter
from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from scripts.evidence_retrieval import tokens,question_identity,encoded
from scripts.run_source_alignment import exclusive

def main():
    start=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser(description=__doc__)
    for n in ('manifest','out','freeze','test-log'):p.add_argument('--'+n,required=True)
    args=p.parse_args();root=Path.cwd();out=Path(args.out);manifest=json.loads(Path(args.manifest).read_bytes());env=json.loads((out/'environment.json').read_bytes());checks=implementation_checksums();assert env['implementation_checksums']==checks
    for n,sha in checks.items():assert sha==digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+n]))
    for n,sha in env['program_protocol_sha256'].items():assert sha==digest((root/n).read_bytes())==digest(subprocess.check_output(['git','show',args.freeze+':'+n]))
    test=Path(args.test_log).read_text('utf-8');assert 'Ran 335 tests' in test and 'OK (skipped=1)' in test
    inputs={}
    for n,e in manifest['files'].items():
        raw=Path(e['path']).read_bytes();assert len(raw)==e['bytes'] and digest(raw)==e['sha256'];inputs[n]=raw
    training=[json.loads(x) for x in inputs['train'].splitlines()];dev=[json.loads(x) for x in inputs['dev'].splitlines()];train_sets={question_identity(r['claim']):set(tokens(r['claim'])) for r in training};assert len(training)==809 and len(train_sets)==807 and len(dev)==300
    child=(out/'worker.json').read_bytes();parent_bytes=(out/'parent.json').read_bytes();r=json.loads(child);parent=json.loads(parent_bytes);assert parent['return_code']==0 and parent['error'] is None and parent['child_sha256']==digest(child) and parent['parent_full_process_wall_s']>=r['worker_wall_s']>0
    methods=('lexical','expansion','permuted_expansion');records={m:{x['row_index']:x for x in json.loads(inputs[m])['records']} for m in methods};indices=sorted(records['lexical']);assert len(indices)==298 and [x['row_index'] for x in r['records']]==indices
    for m in methods:
        for round in (2,3):
            raw=inputs[f'{m}_round{round}'];later={x['row_index']:x for x in json.loads(raw)['records']};assert set(later)==set(indices)
            assert all(later[i]['proof_sha256']==records[m][i]['proof_sha256'] for i in indices)
    directions=[];annotated=[];cohorts={'near':[],'nonnear':[]};best_counts=Counter();exact_counts=Counter()
    for item in r['records']:
        i=item['row_index'];doc=dev[i];query=set(tokens(doc['claim']));best_num=0;best_den=1;best=set()
        for identity,other in train_sets.items():
            num=len(query.intersection(other));den=len(query.union(other)) or 1
            cross=num*best_den-best_num*den
            if cross>0:best_num=num;best_den=den;best={identity}
            elif cross==0 and num>0:best.add(identity)
        exact=question_identity(doc['claim']) in train_sets;near=5*best_num>=4*best_den
        assert not exact and item['is_exact_normalized_question']==exact and item['question_sha256']==question_identity(doc['claim']) and item['question_id']==doc['id'] and item['query_token_types']==len(query)
        assert Fraction(item['max_jaccard_numerator'],item['max_jaccard_denominator'])==Fraction(best_num,best_den) and item['near_at_least_four_fifths']==near and item['best_train_question_sha256']==sorted(best)
        for m in methods:assert item['prior_proof_sha256'][m]==records[m][i]['proof_sha256'] and item['method_metrics'][m]==records[m][i]['paper_metrics']
        best_counts['near' if near else 'nonnear']+=1;exact_counts[str(exact)]+=1;gold=records['lexical'][i]['gold_paper_ids'];assert all(records[m][i]['gold_paper_ids']==gold for m in methods)
        if not gold:assert all(item['method_metrics'][m] is None for m in methods);continue
        recalls={m:Fraction(len(set(records[m][i]['selected_ids'])&set(gold)),len(gold)) for m in methods}
        for m in methods:
            metric=records[m][i]['paper_metrics'];assert metric['gold_groups']==len(gold) and metric['recovered_groups']==recalls[m]*len(gold) and metric['leaf_recall']==float(recalls[m]) and metric['complete_coverage']==(recalls[m]==1)
        b=recalls['lexical'];c=recalls['expansion'];delta=c-b;direction='win' if delta>0 else 'loss' if delta<0 else 'tie'
        directions.append({'identity':i,'near':near,'direction':direction,'delta_numerator':delta.numerator,'delta_denominator':delta.denominator,'base_complete':b==1,'candidate_complete':c==1});entry={'row_index':i,'near':near,'recalls':recalls,'delta':delta};annotated.append(entry);cohorts['near' if near else 'nonnear'].append(entry)
    assert directions==r['annotated_directions'] and len(directions)==188 and r['unannotated_rows']==110 and r['annotated_rows']==188 and r['retrieved_rows']==298
    summaries=[]
    for group,items in cohorts.items():
        for m in methods:
            total=sum((x['recalls'][m] for x in items),Fraction(0));summaries.append({'cohort':group,'method':m,'annotated_claims':len(items),'macro_paper_recall':float(total/len(items)) if items else None,'recall_sum_numerator':total.numerator,'recall_sum_denominator':total.denominator,'complete_claims':sum(x['recalls'][m]==1 for x in items)})
    positive=sum((x['delta'] for x in annotated if x['delta']>0),Fraction(0));near_positive=sum((x['delta'] for x in cohorts['near'] if x['delta']>0),Fraction(0));negative=sum((x['delta'] for x in annotated if x['delta']<0),Fraction(0));net=sum((x['delta'] for x in annotated),Fraction(0));assert positive+negative==net
    fraction=near_positive/positive if positive else None;H1=fraction is not None and fraction>=Fraction(1,2);nonnear=cohorts['nonnear'];H2=bool(nonnear) and sum((x['delta'] for x in nonnear),Fraction(0))>0 and sum(x['recalls']['expansion']==1 for x in nonnear)>=sum(x['recalls']['lexical']==1 for x in nonnear)
    def frac(value):return {'numerator':value.numerator,'denominator':value.denominator} if value is not None else None
    derived={'cohort_summaries':summaries,'all_retrieved_near_counts':dict(best_counts),'all_annotated_near_counts':{k:len(v) for k,v in cohorts.items()},'direction_counts':{k:dict(Counter(x['direction'] for x in directions if x['near']==(k=='near'))) for k in cohorts},'positive_recall_sum':frac(positive),'near_positive_recall_sum':frac(near_positive),'negative_recall_sum':frac(negative),'net_recall_sum':frac(net),'near_fraction_of_positive_recall_sum':frac(fraction),'H1_at_least_half_positive_gain_near':H1,'H2_nonnear_quality_gain':H2,'formal_diagnostic_workers':1,'retrieved_records':298,'annotated_records':188,'unannotated_null_records':110,'new_query_calls':0,'new_training_runs':0,'new_scientific_trials':0,'source_range_bindings':0,'new_remote_model_calls':0,'prior_report_proofs_checked':9*298,'raw_child_parent_report_bytes':len(child)+len(parent_bytes),'shared_existing_input_bytes':sum(len(v) for v in inputs.values()),'worker_wall_s':r['worker_wall_s'],'worker_cpu_s':r['worker_cpu_s'],'parent_full_process_wall_s':parent['parent_full_process_wall_s'],'observed_peak_rss_bytes':r['observed_peak_rss_bytes'],'freeze':args.freeze,'semantic_overlap_or_leakage_absence_proved':False,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None}
    exclusive(out/'derived-metrics.json',encoded(derived)+b'\n');exclusive(out/'source-checksums.json',encoded(checks)+b'\n');files={n:{'bytes':(root/n).stat().st_size,'sha256':digest((root/n).read_bytes())} for n in ['rkv1/'+x for x in checks]+['rkv1/memory_demo.html']};programs={n:{'bytes':(root/n).stat().st_size,'sha256':sha} for n,sha in env['program_protocol_sha256'].items()};exclusive(out/'source-resource.json',encoded({'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),'assessment_programs':{n:v for n,v in programs.items() if n.startswith('scripts/')},'all_program_protocol_test_input_files':programs})+b'\n')
    exclusive(out/'validation.json',encoded({'formal_diagnostic_workers':1,'retrieved_records':298,'annotated_records':188,'unannotated_null_records':110,'independent_integer_Jaccard_audits':298,'prior_report_proofs_checked':2682,'new_query_calls':0,'new_training_runs':0,'source_range_bindings':0,'new_scientific_trials':0,'new_remote_model_calls':0,'unit_tests_run':335,'unit_tests_passed':334,'unit_tests_skipped':1,'runtime_module_count':len(checks),'html_files':1,'freeze':args.freeze,'H1':H1,'H2':H2})+b'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained');groups=('near','nonnear');x=(0,1)
    for off,m,color in ((-.24,'lexical','#64748b'),(0,'expansion','#2563eb'),(.24,'permuted_expansion','#f59e0b')):
        axes[0].bar([i+off for i in x],[next(s['macro_paper_recall'] for s in summaries if s['cohort']==g and s['method']==m) or 0 for g in groups],width=.23,label=m,color=color)
    axes[0].set_ylim(0,1);axes[0].set_ylabel('Annotated macro source recall');axes[0].legend(fontsize=7)
    for off,direction,color in ((-.24,'win','#0d9488'),(0,'loss','#dc2626'),(.24,'tie','#94a3b8')):axes[1].bar([i+off for i in x],[derived['direction_counts'][g].get(direction,0) for g in groups],width=.23,label=direction,color=color)
    axes[1].set_ylim(bottom=0);axes[1].set_ylabel('Annotated claim count, candidate vs baseline');axes[1].legend(fontsize=8)
    axes[2].hist([float(Fraction(v['max_jaccard_numerator'],v['max_jaccard_denominator'])) for v in r['records']],bins=[i/10 for i in range(11)],color='#2563eb',edgecolor='white');axes[2].axvline(.8,color='#dc2626',linestyle='--',label='Frozen4/5 threshold');axes[2].set_xlim(0,1);axes[2].set_ylim(bottom=0);axes[2].set_xlabel('Maximum training token-set Jaccard');axes[2].set_ylabel('All298 retrieved claims');axes[2].legend(fontsize=8)
    for ax in axes[:2]:ax.set_xticks(x,[g+' (n='+str(len(cohorts[g]))+')' for g in groups])
    fig.suptitle('Known SciFact split overlap diagnostic: literal token sets, not semantic leakage assurance');fig.savefig(out/'query-similarity.png',dpi=160);plt.close(fig)
    exclusive(out/'analysis-timing.json',encoded({'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'independent_Jaccard_audits':298,'scope':'Independent token-set/oldproof/delta/denominator/source-fee audit and plot; no new retrieval or raw-corpus source validation'})+b'\n');print(json.dumps({'H1':H1,'H2':H2,'near':derived['all_annotated_near_counts'],'workers':1}),flush=True)

if __name__=='__main__':main()
