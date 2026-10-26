"""Independent whole-record scientific claim-source transfer audit."""
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import statistics
import subprocess
import time
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.store import Store
from scripts.evidence_retrieval import encoded,ranking,admit,question_identity
from scripts.run_source_alignment import ledger
from scripts.run_memory_concurrency import save


def main():
    begin=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser()
    for key in ('work','out','inputs','model','model-freeze','freeze','test-log'):p.add_argument('--'+key,required=True)
    args=p.parse_args();work=Path(args.work);out=Path(args.out);inputs=Path(args.inputs)
    manifest=json.loads(Path('docs/scifact-graph-inputs.json').read_bytes());raw=(inputs/'corpus.jsonl').read_bytes();dev_raw=(inputs/'claims_dev.jsonl').read_bytes()
    assert digest(raw)==manifest['files']['corpus.jsonl']['sha256'] and digest(dev_raw)==manifest['files']['claims_dev.jsonl']['sha256']
    corpus={};offset=0
    for line in raw.splitlines(keepends=True):
        obj=json.loads(line);key='doc:'+str(obj['doc_id']);assert key not in corpus
        corpus[key]={'object':obj,'offset':offset,'raw':line};offset+=len(line)
    dev=[json.loads(x) for x in dev_raw.splitlines()];assert len(dev)==300 and len(corpus)==5183
    model_raw=Path(args.model).read_bytes();model=json.loads(model_raw);model_freeze=json.loads(Path(args.model_freeze).read_bytes());assert digest(model_raw)==model_freeze['model_sha256'] and model_freeze['code_protocol_freeze']==args.freeze
    assert model_freeze['known_project_data'] and model_freeze['dev_not_scored_with_this_candidate_before_model_freeze']
    assert model_freeze['training_summary']['source_sha256']==digest(raw)
    assert model_freeze['training_summary']['training_label_sha256']==manifest['files']['claims_train.jsonl']['sha256']
    env=json.loads((out/'environment.json').read_bytes());checks=implementation_checksums();assert checks==env['implementation_checksums']
    for k,sha in checks.items():assert sha==digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+k]))
    for k,sha in env['program_protocol_sha256'].items():assert sha==digest(Path(k).read_bytes())==digest(subprocess.check_output(['git','show',args.freeze+':'+k]))
    log=Path(args.test_log).read_text('utf-8');assert 'Ran 273 tests' in log and 'OK (skipped=1)' in log
    assert model['shared']['parameters']=={'k1':1.2,'b':.75,'max_facts':12,'source_budget':4096,'seeds':6,'neighbors':6}
    assert model['shared']['source_kind']=='scifact-whole-original-record-v1' and model['shared']['N']==5183
    degrees=lambda g:sorted((len(x),sum(x.values())) for x in g.values());assert degrees(model['graph'])==degrees(model['permuted_graph'])
    rows=[];reference={};tree_ref=None;bindings=0;raw_bytes=0;gold_ref=None
    for n in (1,2,3):
        for method in ('lexical','graph','permuted_graph'):
            label=f'round-{n}-{method}';folder=work/label;child=(out/(label+'.json')).read_bytes();pr=(out/(label+'-parent.json')).read_bytes();raw_bytes+=len(child)+len(pr)
            data=json.loads(child);parent=json.loads(pr);assert parent['return_code']==0 and parent['error'] is None and parent['child_report_sha256']==digest(child)
            assert parent['parent_full_process_wall_s']>=data['worker_wall_s']>0 and data['model_sha256']==digest(model_raw) and data['dev_sha256']==digest(dev_raw) and data['source_sha256']==digest(raw)
            assert data['model_freeze_sha256']==digest(Path(args.model_freeze).read_bytes())
            order=list(range(len(dev)));random.Random(20261027+n).shuffle(order);assert (folder/'plan.json').read_bytes()==encoded(order)
            excluded=[{'row_index':i,'question_id':dev[i]['id'],'question_sha256':question_identity(dev[i]['claim']),'reason':'training_id_or_normalized_question_overlap'} for i in order
                if str(dev[i]['id']) in model['shared']['train_ids'] or question_identity(dev[i]['claim']) in model['shared']['train_question_sha256']]
            assert data['excluded']==excluded;indices=[i for i in order if i not in {x['row_index'] for x in excluded}]
            assert [r['row_index'] for r in data['records']]==indices and data['retrieved_rows']==len(indices)
            store=Store(folder/'store',io_backend='bounded');sid=data['ingest']['commit']['snapshot_id'];counts=Counter();identities={};goldmap={};admitted_list=[]
            with store.snapshot(sid) as snapshot:
                for rec in data['records']:
                    doc=dev[rec['row_index']];assert rec['question_id']==doc['id'] and rec['question_sha256']==question_identity(doc['claim'])
                    proof={k:v for k,v in rec.items() if k not in ('proof_sha256','query_wall_s','query_cpu_s','gold_audit_wall_s','gold_audit_cpu_s','ranked_candidates')}
                    assert digest(encoded(proof))==rec['proof_sha256'];identities[rec['row_index']]=rec['proof_sha256']
                    ranked=ranking(model,doc['claim'],method);selected,used=admit(model,ranked);assert selected==rec['selected_ids'] and used==rec['admitted_record_bytes']<=4096
                    assert len(selected)<=12 and len(selected)==len(set(selected)) and [h['paper_id'] for h in rec['hits']]==selected;admitted_list.append(len(selected))
                    for hit in rec['hits']:
                        key=hit['paper_id'];r=corpus[key];loc=hit['locator'];assert loc=={'snapshot_id':sid,'path':'corpus.jsonl','offset':r['offset'],'length':len(r['raw']),'sha256':digest(r['raw'])}
                        assert snapshot.read_range('corpus.jsonl',loc['offset'],loc['length'])==r['raw']
                        assert hit['title_sha256']==digest(r['object']['title'].encode()) and hit['abstract_sha256']==digest(encoded(r['object']['abstract']));bindings+=1
                    gold={'doc:'+str(k) for k in doc['evidence']};assert gold==set(rec['gold_paper_ids']);goldmap[rec['row_index']]=sorted(gold)
                    if not gold:assert rec['paper_metrics'] is None and rec['annotation_status']=='no-gold-evidence-annotation';counts['unannotated']+=1;continue
                    for key,sets in doc['evidence'].items():
                        assert sets and 'doc:'+str(key) in corpus
                        for ev in sets:assert ev['sentences'] and all(type(i) is int and 0<=i<len(corpus['doc:'+str(key)]['object']['abstract']) for i in ev['sentences'])
                    recovered=len(set(selected)&gold);m=rec['paper_metrics'];assert m=={'gold_groups':len(gold),'recovered_groups':recovered,'leaf_recall':recovered/len(gold),'complete_coverage':recovered==len(gold)}
                    counts['annotated']+=1;counts['complete']+=m['complete_coverage'];counts['gold_paper_groups']+=len(gold);counts['recovered_groups']+=recovered;counts['macro_sum']+=m['leaf_recall']
                assert snapshot.read_range('corpus.jsonl')==raw
            assert data['annotated_scored_rows']==counts['annotated'] and data['unannotated_rows']==counts['unannotated']
            if method not in reference:reference[method]=identities
            else:assert reference[method]==identities
            if gold_ref is None:gold_ref=goldmap
            else:assert gold_ref==goldmap
            tree=ledger(store.root);saved=json.loads((folder/'ledger.json').read_bytes());assert tree==saved['before']==saved['after'] and digest(encoded(tree))==data['store_tree_sha256']
            if tree_ref is None:tree_ref=tree
            else:assert tree_ref==tree
            actual=Counter()
            for path in folder.rglob('*'):
                if path.is_file():
                    group=path.relative_to(folder).parts[0];actual['store_bytes' if group=='store' else 'source_copy_bytes' if group=='source' else 'other_worker_files_bytes']+=path.stat().st_size
            assert dict(actual)==data['files']
            rows.append({'round':n,'method':method,'retrieved_rows':len(indices),'annotated_rows':counts['annotated'],'unannotated_rows':counts['unannotated'],'excluded_rows':len(excluded),
                'complete_paper_questions':counts['complete'],'complete_paper_rate':counts['complete']/counts['annotated'],'macro_paper_recall':counts['macro_sum']/counts['annotated'],
                'micro_paper_recall':counts['recovered_groups']/counts['gold_paper_groups'],'recovered_paper_groups':counts['recovered_groups'],'gold_paper_groups':counts['gold_paper_groups'],
                'selected_papers_min':min(admitted_list),'selected_papers_max':max(admitted_list),'selected_papers_mean':sum(admitted_list)/len(admitted_list),
                **{k:sum(r[k] for r in data['records']) for k in ('query_wall_s','query_cpu_s','gold_audit_wall_s','gold_audit_cpu_s','admitted_record_bytes')},
                **{k:data[k] for k in ('worker_wall_s','worker_cpu_s','observed_peak_rss_bytes','files','ingest','recovery','loaded_full_model_bytes')},'parent_full_process_wall_s':parent['parent_full_process_wall_s']})
    def row(n,m):return next(x for x in rows if x['round']==n and x['method']==m)
    gates=[];ratios=[];pairs=[]
    for n in (1,2,3):
        g=row(n,'graph');a=row(n,'lexical');c=row(n,'permuted_graph')
        gates.append(g['macro_paper_recall']>max(a['macro_paper_recall'],c['macro_paper_recall']) and g['complete_paper_questions']>=max(a['complete_paper_questions'],c['complete_paper_questions']))
        ratios.append({'round':n,**{k:g[k]/a[k] if a[k]>0 else None for k in ('query_wall_s','query_cpu_s','parent_full_process_wall_s')}})
        rr={m:{r['row_index']:r for r in json.loads((out/f'round-{n}-{m}.json').read_bytes())['records'] if r['paper_metrics'] is not None} for m in ('lexical','graph','permuted_graph')}
        for other in ('lexical','permuted_graph'):
            counter=Counter()
            for i,r in rr['graph'].items():
                x=r['paper_metrics']['leaf_recall'];y=rr[other][i]['paper_metrics']['leaf_recall'];counter['win' if x>y else 'loss' if x<y else 'tie']+=1
            pairs.append({'round':n,'graph_vs':other,**dict(counter)})
    med={k:statistics.median(r[k] for r in ratios) if all(r[k] is not None for r in ratios) else None for k in ('query_wall_s','query_cpu_s','parent_full_process_wall_s')};qgate=all(gates);tgate=all(v is not None and v<=1 for v in med.values())
    save(out/'derived-metrics.json',{'rows':rows,'graph_quality_gate':qgate,'graph_time_gate':tgate,'graph_joint_gate':qgate and tgate,'median_graph_lexical_time_ratios':med,
        'time_ratios':ratios,'per_question_pairs':pairs,'verified_original_paper_bindings':bindings,'raw_report_json_bytes':raw_bytes,'driver_log_bytes':sum(p.stat().st_size for p in out.glob('*.log')),
        'model_freeze':model_freeze,'known_project_data_transfer_not_unseen':True,'verdict_classification_evaluated':False})
    save(out/'source-checksums.json',checks);files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+k for k in checks}|{'rkv1/memory_demo.html'}
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),'assessment_programs':{k:{'bytes':Path(k).stat().st_size,'sha256':digest(Path(k).read_bytes())} for k in env['program_protocol_sha256'] if k.startswith('scripts/')},'new_training_runs':1,'new_model_bytes':len(model_raw),'private_model_not_published':True})
    save(out/'validation.json',{'raw_dev_claims':300,'retrieved_per_worker':rows[0]['retrieved_rows'],'annotated_scored_per_worker':rows[0]['annotated_rows'],'unannotated_per_worker':rows[0]['unannotated_rows'],'excluded_train_overlap':rows[0]['excluded_rows'],
        'workers':9,'parent_timing_records':9,'source_full_recoveries':9,'original_paper_bindings':bindings,'proof_determinism_methods':3,'all_mechanical_gates_pass':True,
        'graph_quality_gate':qgate,'graph_time_gate':tgate,'graph_joint_gate':qgate and tgate,'new_training_runs':1,'new_remote_model_calls':0,'unit_tests_run':273,'unit_tests_passed':272,'unit_tests_skipped':1,
        'runtime_module_count':len(checks),'html_files':1,'freeze':args.freeze,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained');names=('lexical','graph','permuted_graph');colors=('#64748b','#2563eb','#f59e0b')
    for ax,key,title in ((axes[0],'macro_paper_recall','Annotated claim macro paper recall'),(axes[1],'complete_paper_rate','All gold papers retrieved')):
        ax.bar(names,[row(1,m)[key] for m in names],color=colors);ax.set_title(title);ax.set_ylabel('Fraction / annotated claims');ax.set_ylim(0,1)
    axes[2].bar(names,[statistics.median(row(n,m)['query_wall_s'] for n in (1,2,3)) for m in names],color=colors);axes[2].set_title('All claim retrieval + original verification');axes[2].set_ylabel('Median seconds / full retrieved split')
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('RKV-1 v0.53: known SciFact transfer, claim-only / fixed12 whole records / 4096 original bytes')
    fig.savefig(out/'scifact-graph.png',dpi=160);plt.close(fig)
    save(out/'analysis-timing.json',{'analysis_wall_s':time.perf_counter()-begin,'analysis_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'scope':'Independent raw-paper binding, gold/ranking/tree audit and plot; not new evaluation trial/training'})
    print(json.dumps({'quality_gate':qgate,'time_gate':tgate,'joint':qgate and tgate,'bindings':bindings,'annotated':rows[0]['annotated_rows'],'retrieved':rows[0]['retrieved_rows']}))


if __name__=='__main__':main()
