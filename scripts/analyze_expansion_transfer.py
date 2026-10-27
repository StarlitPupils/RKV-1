"""Independent heldout source/group/byte audit and fixed quality/cost gates."""
import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
import random
import re
import statistics
import subprocess
import time
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.store import Store
from scripts.run_source_alignment import ledger
from scripts.run_memory_concurrency import save
from scripts.evidence_retrieval import encoded,admit,question_identity
from scripts.audit_supervised_expansion import validate,reference_ranking


def independent_gold(doc,corpus):
    bytext=defaultdict(list)
    for key,text in corpus.items():bytext[text].append(key)
    aliases={k:min(group) for group in bytext.values() for k in group};groups=set();literal=set();counts=Counter()
    leaves=sorted(set(re.findall(r'\bsent\d+\b',doc['proof'])));assert leaves
    for leaf in leaves:
        text=doc['meta']['triples'][leaf];uid=doc['meta']['worldtree_provenance'][leaf]['uuid'];sha=digest(text.encode())
        if uid in corpus:
            key=aliases[uid];counts['provided_UUID']+=1
            if text!=corpus[key]:counts['annotated_text_differs']+=1
        elif text in bytext:key=min(bytext[text]);counts['exact_decoded_text']+=1
        else:key=None;counts['unresolved']+=1
        groups.add(key if key is not None else 'unresolved:'+sha)
        literal.add(key if key is not None and text==corpus[key] else 'nonliteral:'+sha)
    return groups,literal,dict(counts)


def check_metrics(selected,gold,value):
    hits=len(set(selected)&gold)
    assert value=={'gold_groups':len(gold),'recovered_groups':hits,'leaf_recall':hits/len(gold),'complete_coverage':hits==len(gold)}


def text_free(value):
    if isinstance(value,dict):
        assert not set(value)&{'question','answer','hypothesis','context','text','title','abstract','sentences','proof','original_text','postings'}
        for v in value.values():text_free(v)
    elif isinstance(value,list):
        for v in value:text_free(v)


def main():
    begin=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser()
    for key in ('work','out','inputs','model','source-base','sidecar','model-freeze','freeze','test-log'):p.add_argument('--'+key,required=True)
    args=p.parse_args();work=Path(args.work);out=Path(args.out);inputs=Path(args.inputs)
    raw=(inputs/'corpus.json').read_bytes();corpus=json.loads(raw);test_raw=(inputs/'labels-test.jsonl').read_bytes();test=[json.loads(x) for x in test_raw.splitlines()]
    seen=json.loads(Path('docs/entailment-test-inputs.json').read_bytes())
    model_raw=Path(args.model).read_bytes();model=json.loads(model_raw);model_freeze=json.loads(Path(args.model_freeze).read_bytes());assert digest(model_raw)==model_freeze['model_sha256']
    transfer_plan=json.loads(Path('docs/expansion-transfer-inputs.json').read_bytes());source_seen=set(transfer_plan['source_training_question_sha256']);source_base_raw=Path(args.source_base).read_bytes();side_raw=Path(args.sidecar).read_bytes();assert digest(source_base_raw)==model_freeze['source_model_sha256'] and digest(side_raw)==model_freeze['sidecar_sha256'];source_base=json.loads(source_base_raw);sidecar=json.loads(side_raw);association_audit=validate(source_base,sidecar)
    env=json.loads((out/'environment.json').read_text('utf-8'));checks=implementation_checksums();assert checks==env['implementation_checksums']
    for k,sha in checks.items():assert sha==digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+k]))
    for k,sha in env['program_protocol_sha256'].items():assert sha==digest(Path(k).read_bytes())==digest(subprocess.check_output(['git','show',args.freeze+':'+k]))
    log=Path(args.test_log).read_text('utf-8');assert 'Ran 340 tests' in log and 'OK (skipped=1)' in log
    assert model_freeze['code_protocol_freeze']==args.freeze and model_freeze['new_training_runs']==0
    assert digest(model_raw)=='2f82ee4b28c943038e7a37ddcbd8871443f7a441ddd45a1af599decc8bade183'
    assert model['shared']['parameters']=={'k1':1.2,'b':.75,'max_facts':12,'source_budget':4096,'seeds':6,'neighbors':6}
    old_lexical={r['row_index']:r['proof_sha256'] for r in json.loads(Path('results/v0.51.0/round-1-lexical.json').read_bytes())['records']}
    rows=[];mechanical=0;reference={};tree_reference=None;raw_json=0;gold_mapping=None;question_gold=None
    for n in (1,2,3):
        for method in ('lexical','expansion','permuted_expansion'):
            label=f'round-{n}-{method}';folder=work/label;child=(out/(label+'.json')).read_bytes();pr=(out/(label+'-parent.json')).read_bytes();raw_json+=len(child)+len(pr)
            data=json.loads(child);parent=json.loads(pr);text_free(data)
            assert parent['return_code']==0 and parent['error'] is None and parent['child_report_sha256']==digest(child)
            assert parent['parent_full_process_wall_s']>=data['worker_wall_s']>0 and data['model_sha256']==digest(model_raw)
            assert data['model_freeze_sha256']==digest(Path(args.model_freeze).read_bytes()) and data['test_sha256']==digest(test_raw) and data['source_sha256']==digest(raw)
            assert data['loaded_sidecar_sha256']==(None if method=='lexical' else digest(side_raw)) and data['loaded_source_base_sha256']==(None if method=='lexical' else digest(source_base_raw)) and data['loaded_full_model_bytes']==len(model_raw)+(0 if method=='lexical' else len(side_raw)+len(source_base_raw))
            order=list(range(len(test)));random.Random(20261027+n).shuffle(order);assert (folder/'plan.json').read_bytes()==encoded(order)
            expected_excluded=[{'row_index':i,'question_id':test[i]['id'],'question_sha256':question_identity(test[i]['question']),'reason':'target_training_or_seen_dev_or_source_training_normalized_overlap'}
                for i in order if test[i]['id'] in model['shared']['train_ids'] or question_identity(test[i]['question']) in model['shared']['train_question_sha256'] or test[i]['id'] in seen['seen_dev_question_ids'] or question_identity(test[i]['question']) in seen['seen_dev_question_sha256'] or question_identity(test[i]['question']) in source_seen]
            assert data['excluded']==expected_excluded and data['raw_test_rows']==len(test)==340
            indices=[i for i in order if i not in {x['row_index'] for x in expected_excluded}]
            assert [r['row_index'] for r in data['records']]==indices and data['scored_rows']==len(indices)>0
            store=Store(folder/'store',io_backend='bounded');sid=data['ingest']['commit']['snapshot_id'];mapping=Counter();literal_total=Counter();id_total=Counter();identities={};gold_identity={}
            with store.snapshot(sid) as snapshot:
                for rec in data['records']:
                    doc=test[rec['row_index']];selected=rec['selected_ids'];assert rec['question_id']==doc['id'] and rec['question_sha256']==question_identity(doc['question'])
                    proof={k:v for k,v in rec.items() if k not in ('proof_sha256','query_wall_s','query_cpu_s','gold_audit_wall_s','gold_audit_cpu_s','ranked_candidates')}
                    assert digest(encoded(proof))==rec['proof_sha256'];identities[rec['row_index']]=rec['proof_sha256']
                    ranked=reference_ranking(model,sidecar,doc['question'],method);admitted,used=admit(model,ranked)
                    assert selected==admitted and rec['admitted_record_bytes']==used<=4096 and len(selected)<=12 and len(selected)==len(set(selected))
                    assert rec['ranked_candidates']==len(ranked) and [h['fact_id'] for h in rec['hits']]==selected
                    for hit in rec['hits']:
                        key=hit['fact_id'];loc=hit['locator'];assert loc['snapshot_id']==sid and loc['path']=='corpus.json'
                        member=raw[loc['offset']:loc['offset']+loc['length']]
                        assert digest(member)==loc['sha256'] and snapshot.read_range('corpus.json',loc['offset'],loc['length'])==member
                        assert json.loads(b'{'+member+b'}')=={key:corpus[key]} and hit['decoded_text_sha256']==digest(corpus[key].encode());mechanical+=1
                    gold,literal,mm=independent_gold(doc,corpus);mapping.update(mm)
                    assert rec['gold_id_groups']==sorted(gold) and rec['literal_groups']==sorted(literal) and rec['gold_mapping']==mm
                    check_metrics(selected,gold,rec['ID_metrics']);check_metrics(selected,literal,rec['literal_metrics'])
                    gold_identity[rec['row_index']]=(sorted(gold),sorted(literal))
                    for key,metrics in (('ID',rec['ID_metrics']),('literal',rec['literal_metrics'])):
                        total=id_total if key=='ID' else literal_total
                        total['complete']+=metrics['complete_coverage'];total['recovered_groups']+=metrics['recovered_groups'];total['gold_groups']+=metrics['gold_groups'];total['macro_recall_sum']+=metrics['leaf_recall']
                assert snapshot.read_range('corpus.json')==raw
            if method=='lexical':assert all(old_lexical.get(i)==sha for i,sha in identities.items())
            if method not in reference:reference[method]=identities
            else:assert reference[method]==identities
            if question_gold is None:question_gold=gold_identity;gold_mapping=dict(mapping)
            else:assert question_gold==gold_identity and gold_mapping==dict(mapping)
            tree=ledger(store.root);saved=json.loads((folder/'ledger.json').read_bytes());assert tree==saved['before']==saved['after'] and digest(encoded(tree))==data['store_tree_sha256']
            if tree_reference is None:tree_reference=tree
            else:assert tree_reference==tree
            actual=Counter()
            for path in folder.rglob('*'):
                if path.is_file():
                    group=path.relative_to(folder).parts[0];actual['store_bytes' if group=='store' else 'source_copy_bytes' if group=='source' else 'other_worker_files_bytes']+=path.stat().st_size
            assert dict(actual)==data['files']
            quality={name:{'complete_questions':total['complete'],'complete_rate':total['complete']/len(indices),
                'macro_leaf_recall':total['macro_recall_sum']/len(indices),'micro_leaf_recall':total['recovered_groups']/total['gold_groups'],
                'recovered_groups':total['recovered_groups'],'gold_groups':total['gold_groups']} for name,total in (('ID',id_total),('literal',literal_total))}
            rows.append({'round':n,'method':method,'scored_rows':len(indices),'excluded_rows':len(expected_excluded),'quality':quality,
                **{key:sum(r[key] for r in data['records']) for key in ('query_wall_s','query_cpu_s','gold_audit_wall_s','gold_audit_cpu_s','admitted_record_bytes')},
                **{key:data[key] for key in ('worker_wall_s','worker_cpu_s','observed_peak_rss_bytes','files','ingest','recovery','loaded_full_model_bytes')},
                'parent_full_process_wall_s':parent['parent_full_process_wall_s']})
    def row(n,m):return next(x for x in rows if x['round']==n and x['method']==m)
    gains=[];literal_gains=[];pair_results=[];time_ratios=[]
    for n in (1,2,3):
        g=row(n,'expansion');a=row(n,'lexical');c=row(n,'permuted_expansion')
        gains.append(g['quality']['ID']['macro_leaf_recall']>a['quality']['ID']['macro_leaf_recall'] and g['quality']['ID']['macro_leaf_recall']>c['quality']['ID']['macro_leaf_recall'] and g['quality']['ID']['complete_questions']>=max(a['quality']['ID']['complete_questions'],c['quality']['ID']['complete_questions']))
        literal_gains.append(g['quality']['literal']['macro_leaf_recall']>max(a['quality']['literal']['macro_leaf_recall'],c['quality']['literal']['macro_leaf_recall']) and g['quality']['literal']['complete_questions']>=max(a['quality']['literal']['complete_questions'],c['quality']['literal']['complete_questions']))
        time_ratios.append({'round':n,**{k:g[k]/a[k] if a[k]>0 else None for k in ('query_wall_s','query_cpu_s','parent_full_process_wall_s')}})
        # Per-question win/loss uses independent source-group metric, duplicates remain physical rows.
        reports={m:json.loads((out/f'round-{n}-{m}.json').read_bytes()) for m in ('lexical','expansion','permuted_expansion')}
        maps={m:{r['row_index']:r for r in reports[m]['records']} for m in reports}
        for other in ('lexical','permuted_expansion'):
            delta=Counter()
            for i,r in maps['expansion'].items():
                a=r['ID_metrics']['leaf_recall'];b=maps[other][i]['ID_metrics']['leaf_recall'];delta['win' if a>b else 'loss' if a<b else 'tie']+=1
            pair_results.append({'round':n,'transfer_vs':other,**dict(delta)})
    med={k:statistics.median(x[k] for x in time_ratios) if all(x[k] is not None for x in time_ratios) else None for k in ('query_wall_s','query_cpu_s','parent_full_process_wall_s')}
    time_gate=all(v is not None and v<=1 for v in med.values());quality_gate=all(gains) and association_audit['control_available'];literal_gate=all(literal_gains) and association_audit['control_available']
    save(out/'derived-metrics.json',{'rows':rows,'transfer_ID_quality_gate':quality_gate,'transfer_literal_quality_gate':literal_gate,'source_association_audit':association_audit,'transfer_time_gate':time_gate,'transfer_ID_literal_time_joint':quality_gate and literal_gate and time_gate,
        'transfer_vs_lexical_median_time_ratios':med,'time_ratios':time_ratios,'per_question_pairs':pair_results,'gold_mapping_per_worker':gold_mapping,
        'original_v051_lexical_proofs_equal_for_all_retained_rows':True,'new_training_runs':0,'retained_source_base_bytes':len(source_base_raw),'retained_target_base_bytes':len(model_raw),'retained_sidecar_bytes':len(side_raw),'raw_report_json_bytes':raw_json,'driver_log_bytes':sum(p.stat().st_size for p in out.glob('*.log')),'verified_selected_original_bindings':mechanical,
        'model_cost':{'new_training_runs':0,'source_base_bytes':len(source_base_raw),'target_base_bytes':len(model_raw),'sidecar_bytes':len(side_raw),'historical_training_ledgers':['results/v0.53.0/measurement-context.json','results/v0.61.0/measurement-context.json']},'distinct_scored_question_ids':len({test[i]['id'] for i in question_gold}),
        'literal_evidence_is_diagnostic_not_NLI':True,'retrieval_uses_question_only':True})
    save(out/'source-checksums.json',checks)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+k for k in checks}|{'rkv1/memory_demo.html'}
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
        'assessment_programs':{k:{'bytes':Path(k).stat().st_size,'sha256':digest(Path(k).read_bytes())} for k in env['program_protocol_sha256'] if k.startswith('scripts/')},
        'new_model_bytes':0,'reused_model_bytes':len(model_raw)+len(source_base_raw)+len(side_raw),'baseline_loaded_target_bytes':len(model_raw),'candidate_additional_source_and_sidecar_bytes':len(source_base_raw)+len(side_raw),'new_training_runs':0,'model_private_not_published':True})
    save(out/'validation.json',{'raw_test_rows':340,'scored_rows_per_worker':rows[0]['scored_rows'],'excluded_overlap_rows':rows[0]['excluded_rows'],
        'workers':9,'parent_timing_records':9,'selected_original_bindings':mechanical,'source_full_recoveries':9,'proof_determinism_methods':3,
        'all_mechanical_gates_pass':True,'transfer_ID_quality_gate':quality_gate,'transfer_literal_quality_gate':literal_gate,'source_association_audit':association_audit,'transfer_time_gate':time_gate,'transfer_ID_literal_time_joint':quality_gate and literal_gate and time_gate,
        'unit_tests_run':340,'unit_tests_passed':339,'unit_tests_skipped':1,'runtime_module_count':len(checks),'html_files':1,'freeze':args.freeze,
        'model_sha256':digest(model_raw),'new_training_runs':0,'new_remote_model_calls':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,4,figsize=(17,4.8),layout='constrained');names=('lexical','expansion','permuted_expansion');colors=('#64748b','#2563eb','#f59e0b')
    for ax,metric,field,title in ((axes[0],'ID','macro_leaf_recall','Source-ID macro recall'),(axes[1],'literal','macro_leaf_recall','Literal-source macro recall'),(axes[2],'ID','complete_rate','All source-ID groups covered')):
        ax.bar(names,[row(1,m)['quality'][metric][field] for m in names],color=colors);ax.set_title(title);ax.set_ylabel('Fraction, fixed retained rows');ax.set_ylim(0,1)
    axes[3].bar(names,[statistics.median(row(n,m)['query_wall_s'] for n in (1,2,3)) for m in names],color=colors);axes[3].set_title('Retrieval + original verification');axes[3].set_ylabel('Median seconds / retained split');axes[3].set_ylim(bottom=0)
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.tick_params(axis='x',labelrotation=12,labelsize=8)
    fig.suptitle('Known EntailmentBank target: unchanged SciFact associations / no retraining / fixed12facts and4096B')
    fig.savefig(out/'expansion-transfer.png',dpi=160);plt.close(fig)
    save(out/'analysis-timing.json',{'analysis_wall_s':time.perf_counter()-begin,'analysis_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'scope':'Separate pure ranking replay, independent gold/source binding/full file audit and plot; not a new evaluation trial or model retrain'})
    for p in out.glob('*.json'):text_free(json.loads(p.read_bytes()))
    print(json.dumps({'quality_gate':quality_gate,'time_gate':time_gate,'joint':quality_gate and literal_gate and time_gate,'bindings':mechanical,'scored':rows[0]['scored_rows']}))


if __name__=='__main__':main()
