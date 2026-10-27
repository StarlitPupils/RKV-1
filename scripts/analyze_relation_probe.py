"""Independent feature/logit, explicit-label, original-source and cost audit."""
import argparse,json,math,random,statistics,subprocess,time
from collections import Counter
from pathlib import Path
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from rkv1.benchmark import peak_rss
from rkv1.store import Store
from scripts.evidence_retrieval import encoded,question_identity,admit
from scripts.audit_supervised_expansion import reference_ranking
from scripts.audit_relation_probe import reference_predict,reference_features
from scripts.run_source_alignment import exclusive,ledger
METHODS=('majority','pair','claim_only','permuted_pair')

def independent_metrics(gold,predictions):
    labels=('CONTRADICT','SUPPORT');matrix=[[0,0],[0,0]];total=[0,0];ambiguous=0;selected_ambiguous=0
    for key,value in gold.items():
        if value is None:ambiguous+=1;selected_ambiguous+=key in predictions;continue
        label=labels.index(value);total[label]+=1
        if key in predictions:matrix[label][labels.index(predictions[key])]+=1
    retrieved=[sum(row) for row in matrix];correct=[matrix[0][0],matrix[1][1]];covered=sum(retrieved);n=sum(total);nc=sum(correct)
    return {'all_selected_pairs':len(predictions),'all_explicit_labeled_gold_pairs':n,'retrieved_explicit_gold_pairs':covered,'missing_explicit_gold_pairs':n-covered,'ambiguous_gold_pairs':ambiguous,'selected_ambiguous_gold_pairs':selected_ambiguous,'selected_without_gold_annotation':sum(key not in gold for key in predictions),'class_total_gold':dict(zip(labels,total)),'class_retrieved_gold':dict(zip(labels,retrieved)),'class_correct':dict(zip(labels,correct)),'confusion_on_retrieved_gold':{label:dict(zip(labels,matrix[i])) for i,label in enumerate(labels)},'correct_retrieved_gold':nc,'conditional_accuracy_on_retrieved_labeled_gold':nc/covered if covered else None,'all_labeled_gold_correct_coverage':nc/n if n else None,'balanced_accuracy_on_retrieved_labeled_gold':(correct[0]/retrieved[0]+correct[1]/retrieved[1])/2 if retrieved[0] and retrieved[1] else None,'unannotated_are_not_NEI_or_negative':True}

def gold_labels(doc,corpus):
    gold={}
    for identifier,items in doc['evidence'].items():
        key='doc:'+str(identifier);assert key in corpus and items;labels=set()
        for item in items:
            assert item['label'] in ('CONTRADICT','SUPPORT') and item['sentences'] and all(type(i) is int and 0<=i<len(corpus[key]['object']['abstract']) for i in item['sentences']);labels.add(item['label'])
        gold[key]=next(iter(labels)) if len(labels)==1 else None
    return gold

def main():
    start=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser(description=__doc__)
    for n in ('inputs','model','model-freeze','training','work','out','freeze','test-log'):p.add_argument('--'+n,required=True)
    args=p.parse_args();root=Path.cwd();out=Path(args.out);work=Path(args.work);training=Path(args.training);input_dir=Path(args.inputs);manifest=json.loads((root/'docs/scifact-graph-inputs.json').read_bytes());source_raw=(input_dir/'corpus.jsonl').read_bytes();train_raw=(input_dir/'claims_train.jsonl').read_bytes();dev_raw=(input_dir/'claims_dev.jsonl').read_bytes()
    for name,raw in (('corpus.jsonl',source_raw),('claims_train.jsonl',train_raw),('claims_dev.jsonl',dev_raw)):assert digest(raw)==manifest['files'][name]['sha256'] and len(raw)==manifest['files'][name]['bytes']
    corpus={};offset=0
    for line in source_raw.splitlines(keepends=True):
        obj=json.loads(line);key='doc:'+str(obj['doc_id']);assert key not in corpus;corpus[key]={'object':obj,'raw':line,'offset':offset,'projection':'\n'.join([obj['title'],*obj['abstract']])};offset+=len(line)
    train_rows=[json.loads(x) for x in train_raw.splitlines()];dev=[json.loads(x) for x in dev_raw.splitlines()];assert len(train_rows)==809 and len(dev)==300 and len(corpus)==5183
    freeze_raw=Path(args.model_freeze).read_bytes();freeze=json.loads(freeze_raw);base_raw=Path(args.model).read_bytes();base=json.loads(base_raw);assert digest(base_raw)==freeze['source_retrieval_model_sha256'] and base['shared']['source_sha256']==digest(source_raw)
    env=json.loads((out/'environment.json').read_bytes());checks=implementation_checksums();assert checks==env['implementation_checksums']
    for n,sha in checks.items():assert sha==digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+n]))
    for n,sha in env['program_protocol_sha256'].items():assert sha==digest((root/n).read_bytes())==digest(subprocess.check_output(['git','show',args.freeze+':'+n]))
    test=Path(args.test_log).read_text('utf-8');assert 'Ran 349 tests' in test and 'OK (skipped=1)' in test
    summary=json.loads((training/'training.json').read_bytes());assert summary['training_campaigns']==1 and summary['individual_fits']==3 and summary['source_sha256']==digest(source_raw) and summary['train_sha256']==digest(train_raw) and freeze['code_protocol_freeze']==args.freeze
    groups={};physical=0;unannotated=0
    for row in train_rows:
        unannotated+=not row['evidence']
        for key,label in gold_labels(row,corpus).items():
            k=(question_identity(row['claim']),key);g=groups.setdefault(k,{'claim':row['claim'],'document':corpus[key]['projection'],'labels':set(),'ids':set()});g['labels'].add(label);g['ids'].add(str(row['id']));physical+=1
    examples=[];identities=[];counts=Counter({'ambiguous_unique_pairs':0,'unique_SUPPORT':0,'unique_CONTRADICT':0})
    for (qsha,key),g in sorted(groups.items()):
        labels=g['labels']
        if None in labels or len(labels)!=1:counts['ambiguous_unique_pairs']+=1;continue
        label=next(iter(labels));target=1 if label=='SUPPORT' else 0;counts['unique_'+label]+=1;examples.append({'claim':g['claim'],'document':g['document'],'target':target});identities.append({'question_sha256':qsha,'paper_id':key,'target':target,'original_claim_ids':sorted(g['ids'])})
    expected_counts={'input_rows':len(train_rows),'unannotated_rows':unannotated,'physical_annotated_claim_paper_rows':physical,'unique_unambiguous_pairs':len(examples),'all_unique_pair_groups':len(groups),**dict(counts)}
    assert summary['explicit_training_label_counts']==expected_counts and (training/'training-example-identities.json').read_bytes()==encoded(identities)+b'\n' and summary['training_example_identities_sha256']==digest((training/'training-example-identities.json').read_bytes())
    models={};terminal_objective_audits=0
    for method in METHODS:
        entry=freeze['models'][method];raw=Path(entry['path']).read_bytes();assert digest(raw)==entry['sha256'] and len(raw)==entry['bytes'] and entry==summary['models'][method];model=json.loads(raw);assert model['method']==method and model['scientific_entailment_verified'] is False and model['training_pairs']==len(examples);assert model['training_class_counts']=={'CONTRADICT':sum(e['target']==0 for e in examples),'SUPPORT':sum(e['target']==1 for e in examples)}
        if method!='majority':
            labels=[e['target'] for e in examples]
            if method=='permuted_pair':random.Random(20261027).shuffle(labels)
            weights=model['weights'];assert len(weights)==389 and all(type(w) in (int,float) and math.isfinite(w) for w in weights);loss=0.
            for e,y in zip(examples,labels):
                x=reference_features(e['claim'],e['document'],method=='claim_only');z=sum(x[i]*weights[i] for i in range(389));loss+=max(z,0)+math.log1p(math.exp(-abs(z)))-y*z
            objective=loss/len(examples)+.005*sum(w*w for w in weights[:-1]);assert math.isclose(objective,entry['fit_details']['training_objective_trace'][-1]['training_objective'],rel_tol=1e-11,abs_tol=1e-12);terminal_objective_audits+=1
            if method=='claim_only':assert all(weights[i]==0 for i in range(128,384)) and all(weights[i]==0 for i in (385,386,387))
        models[method]=model
    control_available=summary['models']['permuted_pair']['fit_details']['permuted_label_positions_changed']>0
    old={r['row_index']:r['proof_sha256'] for r in json.loads((root/'results/v0.53.0/round-1-lexical.json').read_bytes())['records']};rows=[];proof_reference={};tree_reference=None;source_bindings=0;pred_audits=0;raw_bytes=0;gold_reference=None
    for n in (1,2,3):
        for method in METHODS:
            label=f'round-{n}-{method}';folder=work/label;child=(out/(label+'.json')).read_bytes();parent_raw=(out/(label+'-parent.json')).read_bytes();r=json.loads(child);parent=json.loads(parent_raw);raw_bytes+=len(child)+len(parent_raw);assert parent['return_code']==0 and parent['error'] is None and parent['child_sha256']==digest(child) and parent['parent_full_process_wall_s']>=r['worker_wall_s']>0
            assert r['source_retrieval_model_sha256']==digest(base_raw) and r['relation_model_sha256']==freeze['models'][method]['sha256'] and r['model_freeze_sha256']==digest(freeze_raw) and r['source_sha256']==digest(source_raw) and r['dev_sha256']==digest(dev_raw)
            order=list(range(len(dev)));random.Random(20261027+n).shuffle(order);assert (folder/'plan.json').read_bytes()==encoded(order);excluded=[{'row_index':i,'question_id':dev[i]['id'],'question_sha256':question_identity(dev[i]['claim']),'reason':'training_id_or_normalized_question_overlap'} for i in order if str(dev[i]['id']) in base['shared']['train_ids'] or question_identity(dev[i]['claim']) in base['shared']['train_question_sha256']];assert r['excluded']==excluded;indices=[i for i in order if i not in {e['row_index'] for e in excluded}];assert [rec['retrieval']['row_index'] for rec in r['records']]==indices and len(indices)==r['retrieved_rows']==298 and r['annotated_rows']==188 and r['unannotated_rows']==110
            store=Store(folder/'store',io_backend='bounded');sid=r['ingest']['commit']['snapshot_id'];all_gold={};all_predictions={};identities={}
            with store.snapshot(sid) as snapshot:
                for rec in r['records']:
                    retrieval=rec['retrieval'];i=retrieval['row_index'];doc=dev[i];assert retrieval['question_id']==doc['id'] and retrieval['question_sha256']==question_identity(doc['claim']);ranked=reference_ranking(base,None,doc['claim'],'lexical');selected,used=admit(base,ranked);assert selected==retrieval['selected_ids'] and used==retrieval['admitted_record_bytes']<=4096 and len(selected)<=12 and rec['ranked_candidates']==len(ranked)
                    assert digest(encoded(retrieval))==rec['retrieval_proof_sha256']==old[i] and [h['paper_id'] for h in retrieval['hits']]==selected and [v['paper_id'] for v in rec['predictions']]==selected
                    for hit,prediction in zip(retrieval['hits'],rec['predictions']):
                        key=hit['paper_id'];original=corpus[key];loc=hit['locator'];assert loc=={'snapshot_id':sid,'path':'corpus.jsonl','offset':original['offset'],'length':len(original['raw']),'sha256':digest(original['raw'])};assert snapshot.read_range('corpus.jsonl',loc['offset'],loc['length'])==original['raw'];source_bindings+=1
                        obj=original['object'];assert hit['title_sha256']==digest(obj['title'].encode()) and hit['abstract_sha256']==digest(encoded(obj['abstract'])) and prediction['source_sha256']==loc['sha256'] and prediction['model_input_document_sha256']==digest(original['projection'].encode())
                        expected=reference_predict(models[method],doc['claim'],original['projection']);assert prediction['predicted_relation']==expected['predicted_relation'] and abs(prediction['support_score_uncalibrated']-expected['support_score_uncalibrated'])<=1e-12 and prediction['scientific_entailment_verified'] is False and prediction['generated_answer'] is None;pred_audits+=1;all_predictions[str(i)+'|'+key]=prediction['predicted_relation']
                    gold=gold_labels(doc,corpus);assert rec['gold_relation_labels']==gold
                    for key,value in gold.items():all_gold[str(i)+'|'+key]=value
                    proof={k:rec[k] for k in ('retrieval','retrieval_proof_sha256','predictions','gold_relation_labels')};assert digest(encoded(proof))==rec['proof_sha256'];identities[i]=rec['proof_sha256'];assert 0<=rec['classification_wall_s']<=rec['query_wall_s'] and 0<=rec['classification_cpu_s']<=rec['query_cpu_s']+1e-9
                assert snapshot.read_range('corpus.jsonl')==source_raw
            expected_metrics=independent_metrics(all_gold,all_predictions);assert expected_metrics==r['relation_metrics']
            if gold_reference is None:gold_reference=all_gold
            else:assert gold_reference==all_gold
            if method not in proof_reference:proof_reference[method]=identities
            else:assert proof_reference[method]==identities
            tree=ledger(store.root);saved=json.loads((folder/'ledger.json').read_bytes());assert tree==saved['before']==saved['after'] and digest(encoded(tree))==r['store_tree_sha256']
            if tree_reference is None:tree_reference=tree
            else:assert tree_reference==tree
            actual=Counter()
            for path in folder.rglob('*'):
                if path.is_file():actual['store_bytes' if path.relative_to(folder).parts[0]=='store' else 'source_copy_bytes' if path.relative_to(folder).parts[0]=='source' else 'other_worker_files_bytes']+=path.stat().st_size
            assert dict(actual)==r['files'];entry=freeze['models'][method];assert r['model_load']['bytes']==entry['bytes'] and r['loaded_model_bytes']==len(base_raw)+entry['bytes']
            row={'round':n,'method':method,'relation_metrics':expected_metrics,**{k:sum(rec[k] for rec in r['records']) for k in ('query_wall_s','query_cpu_s','classification_wall_s','classification_cpu_s','gold_audit_wall_s','gold_audit_cpu_s')},**{k:r[k] for k in ('model_load','loaded_model_bytes','worker_wall_s','worker_cpu_s','observed_peak_rss_bytes','files','ingest','recovery')},'parent_full_process_wall_s':parent['parent_full_process_wall_s'],'relation_model_bytes':entry['bytes']};pairs=expected_metrics['all_selected_pairs'];row['classification_wall_s_per_1000_pairs']=row['classification_wall_s']*1000/pairs if pairs else None;row['classification_cpu_s_per_1000_pairs']=row['classification_cpu_s']*1000/pairs if pairs else None;rows.append(row)
    def row(n,m):return next(r for r in rows if r['round']==n and r['method']==m)
    quality=[];resource_gates=[]
    for n in (1,2,3):
        candidate=row(n,'pair');metric=candidate['relation_metrics'];controls=[row(n,m)['relation_metrics'] for m in METHODS if m!='pair'];quality.append(control_available and metric['balanced_accuracy_on_retrieved_labeled_gold'] is not None and all(c['balanced_accuracy_on_retrieved_labeled_gold'] is not None and metric['balanced_accuracy_on_retrieved_labeled_gold']>c['balanced_accuracy_on_retrieved_labeled_gold'] and metric['correct_retrieved_gold']>=c['correct_retrieved_gold'] for c in controls));resource_gates.append(candidate['relation_model_bytes']<=1<<20 and all(candidate[k] is not None and candidate[k]<=2. for k in ('classification_wall_s_per_1000_pairs','classification_cpu_s_per_1000_pairs')))
    H1=all(quality);H2=all(resource_gates);files={n:{'bytes':(root/n).stat().st_size,'sha256':digest((root/n).read_bytes())} for n in ['rkv1/'+k for k in checks]+['rkv1/memory_demo.html']};programs={n:{'bytes':(root/n).stat().st_size,'sha256':sha} for n,sha in env['program_protocol_sha256'].items()};training_files={p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in training.rglob('*') if p.is_file()}
    derived={'rows':rows,'H1_pair_relation_quality_over_three_controls':H1,'H2_fixed_local_CPU_and_model_feasibility':H2,'relation_quality_and_local_feasibility_joint':H1 and H2,'formal_workers':12,'actual_training_campaigns':1,'individual_trained_fits':3,'majority_count_models':1,'shuffle_label_control_available':control_available,'source_retrieval_proofs_all_equal_original_v053':True,'source_bindings':source_bindings,'independent_prediction_audits':pred_audits,'independent_terminal_objective_audits':terminal_objective_audits,'full_original_source_recoveries':12,'raw_child_parent_JSON_bytes':raw_bytes,'driver_log_bytes':sum(p.stat().st_size for p in out.glob('*.log')),'source_retrieval_model_bytes':len(base_raw),'retained_training_files':training_files,'retained_training_directory_bytes':sum(e['bytes'] for e in training_files.values()),'training_summary':summary,'freeze':args.freeze,'new_remote_model_calls':0,'scientific_entailment_verified':False,'generated_answers':0,'semantic_generalization_or_production_benefit_proved':False,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None}
    exclusive(out/'derived-metrics.json',encoded(derived)+b'\n');exclusive(out/'source-checksums.json',encoded(checks)+b'\n');exclusive(out/'source-resource.json',encoded({'files':files,'total_bytes':sum(e['bytes'] for e in files.values()),'assessment_programs':{n:e for n,e in programs.items() if n.startswith('scripts/')},'all_protocol_test_input_program_files':programs,'relation_specific_runtime_source_bytes':(root/'scripts/relation_probe.py').stat().st_size,'entire_role_model_bytes':{m:freeze['models'][m]['bytes'] for m in METHODS},'retained_training_files_bytes':sum(e['bytes'] for e in training_files.values())})+b'\n')
    exclusive(out/'validation.json',encoded({'formal_workers':12,'training_campaigns':1,'individual_fits':3,'source_bindings':source_bindings,'independent_prediction_audits':pred_audits,'full_source_recoveries':12,'source_proofs_old_v053_equal':True,'relation_proof_determinism_methods':4,'annotated_per_worker':188,'unannotated_unknown_per_worker':110,'retrieved_per_worker':298,'unit_tests_run':349,'unit_tests_passed':348,'unit_tests_skipped':1,'runtime_module_count':len(checks),'html_files':1,'freeze':args.freeze,'H1':H1,'H2':H2,'joint':H1 and H2,'new_remote_model_calls':0,'scientific_entailment_verified':False})+b'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(15,4.8),layout='constrained');colors=('#64748b','#2563eb','#f59e0b','#0d9488')
    for ax,key,title in ((axes[0],'balanced_accuracy_on_retrieved_labeled_gold','Balanced relation accuracy / retrieved labeled gold'),(axes[1],'all_labeled_gold_correct_coverage','Correct relation / all labeled gold including missing')):
        ax.bar(METHODS,[row(1,m)['relation_metrics'][key] or 0 for m in METHODS],color=colors);ax.set_ylim(0,1);ax.set_title(title,fontsize=10);ax.set_ylabel('Fraction, explicit SUPPORT/CONTRADICT only')
    axes[2].bar(METHODS,[statistics.median(row(n,m)['classification_wall_s_per_1000_pairs'] for n in (1,2,3)) for m in METHODS],color=colors);axes[2].axhline(2,color='#dc2626',linestyle='--',label='Frozen local classification budget2s');axes[2].set_ylim(bottom=0);axes[2].set_ylabel('Classification wall seconds /1000actual selected pairs');axes[2].set_title('Source/read/retrieval and parent costs separately reported',fontsize=10);axes[2].legend(fontsize=7)
    for ax in axes:ax.tick_params(axis='x',labelrotation=12,labelsize=8)
    fig.suptitle('Known SciFact CPU lexical relation probe: actual retrieved papers, no oracle rationale or answer');fig.savefig(out/'relation-probe.png',dpi=160);plt.close(fig)
    exclusive(out/'analysis-timing.json',encoded({'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'independent_terminal_training_objective_evaluations':3,'source_rebindings':source_bindings,'independent_predictions':pred_audits,'scope':'Independent frozen-model feature/logit/gold/source/file audit and standard plot, not retraining or new formal dev trials'})+b'\n');print(json.dumps({'H1':H1,'H2':H2,'joint':H1 and H2,'bindings':source_bindings,'prediction_audits':pred_audits}),flush=True)

if __name__=='__main__':main()
