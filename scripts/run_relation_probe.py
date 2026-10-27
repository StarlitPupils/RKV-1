"""Fixed CPU lexical relation probe on actual source-verified retrieved papers."""
import argparse,json,os,platform,random,subprocess,sys,time
from pathlib import Path
from collections import Counter
from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from rkv1.store import Store
from scripts.evidence_retrieval import encoded,question_identity,ranking,admit,metrics
from scripts.scifact_graph import paper_records,evidence_ids
from scripts.relation_probe import labeled_pairs,fit,majority,RelationProbe,LABELS
from scripts.audit_relation_probe import relation_metrics
from scripts.run_source_alignment import exclusive,ledger
ROOT=Path(__file__).resolve().parents[1]
METHODS=('majority','pair','claim_only','permuted_pair')
TRACKED=('scripts/relation_probe.py','scripts/audit_relation_probe.py','scripts/audit_supervised_expansion.py','scripts/run_relation_probe.py','scripts/analyze_relation_probe.py','scripts/evidence_retrieval.py','scripts/scifact_graph.py','scripts/run_source_alignment.py','scripts/run_memory_concurrency.py','tests/test_relation_probe.py','tests/test_audit_relation_probe.py','tests/test_relation_probe_worker.py','docs/RELATION-PROBE.md','docs/relation-probe-inputs.json','docs/scifact-graph-inputs.json')

def original(folder,name):
    raw=(Path(folder)/name).read_bytes();e=json.loads((ROOT/'docs/scifact-graph-inputs.json').read_bytes())['files'][name]
    if digest(raw)!=e['sha256'] or ('bytes' in e and len(raw)!=e['bytes']):raise ValueError('Original scientific input SHA/size differs')
    return raw

def train(args):
    start=time.perf_counter();cpu=time.process_time();folder=Path(args.work);folder.mkdir(exist_ok=False);raw=original(args.inputs,'corpus.jsonl');labels=original(args.inputs,'claims_train.jsonl');papers=paper_records(raw);rows=[json.loads(x) for x in labels.splitlines()];examples,counts=labeled_pairs(rows,papers);summaries={}
    identities=[{k:e[k] for k in ('question_sha256','paper_id','target','original_claim_ids')} for e in examples];exclusive(folder/'training-example-identities.json',encoded(identities)+b'\n')
    for method in METHODS:
        t=time.perf_counter();c=time.process_time()
        if method=='majority':model=majority(examples);cost={'individual_fit':0,'epochs':0}
        else:model,cost=fit(examples,method)
        elapsed=time.perf_counter()-t;used=time.process_time()-c;model_raw=encoded(model);path=folder/(method+'.json');exclusive(path,model_raw+b'\n')
        summaries[method]={'path':path.as_posix(),'sha256':digest(path.read_bytes()),'bytes':path.stat().st_size,'fit_wall_s':elapsed,'fit_cpu_s':used,'observed_peak_rss_bytes':peak_rss(),'fit_details':cost,'training_class_counts':model['training_class_counts'],'scientific_entailment_verified':False}
    report={'training_campaigns':1,'individual_fits':3,'majority_count_models':1,'models':summaries,'explicit_training_label_counts':counts,'training_example_identities_sha256':digest((folder/'training-example-identities.json').read_bytes()),'training_example_identities_bytes':(folder/'training-example-identities.json').stat().st_size,'source_sha256':digest(raw),'train_sha256':digest(labels),'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'new_dev_predictions':0,'new_remote_model_calls':0}
    exclusive(folder/'training.json',encoded(report)+b'\n');print('Trainingcampaign complete, individualfits3; freeze all4modelSHA before dev',flush=True)

def labels_for_claim(doc,papers):
    # Only invoked after every actual retrieved-paper prediction has been made.
    evidence_ids(doc,papers);gold={}
    for identifier,items in doc['evidence'].items():
        labels={x['label'] for x in items}
        if not labels or not labels<=set(LABELS):raise ValueError('Unsupported relation annotation')
        gold['doc:'+str(identifier)]=next(iter(labels)) if len(labels)==1 else None
    return gold

def worker(args):
    start=time.perf_counter();cpu=time.process_time();folder=Path(args.work);folder.mkdir(exist_ok=False);freeze_raw=Path(args.model_freeze).read_bytes();freeze=json.loads(freeze_raw);base_raw=Path(args.model).read_bytes();assert digest(base_raw)==freeze['source_retrieval_model_sha256'];base=json.loads(base_raw)
    load_t=time.perf_counter();load_c=time.process_time();entry=freeze['models'][args.method];model_raw=Path(entry['path']).read_bytes();probe=RelationProbe(model_raw,sha256=entry['sha256']);assert len(model_raw)==entry['bytes'];model_load={'wall_s':time.perf_counter()-load_t,'cpu_s':time.process_time()-load_c,'bytes':len(model_raw)}
    raw=original(args.inputs,'corpus.jsonl');dev_raw=original(args.inputs,'claims_dev.jsonl');papers=paper_records(raw);dev=[json.loads(x) for x in dev_raw.splitlines()];source=folder/'source';source.mkdir();exclusive(source/'corpus.jsonl',raw);store=Store.create(folder/'store',compression='zlib',chunk_size=65536,io_backend='bounded');t=time.perf_counter();c=time.process_time();commit=store.add(source,label='scifact-graph-transfer');ingest={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'commit':commit};sid=commit['snapshot_id'];before=ledger(store.root);order=list(range(len(dev)));random.Random(20261027+args.round).shuffle(order);exclusive(folder/'plan.json',encoded(order));records=[];excluded=[];all_gold={};all_predictions={};private=[]
    for i in order:
        doc=dev[i];qsha=question_identity(doc['claim'])
        if str(doc['id']) in base['shared']['train_ids'] or qsha in base['shared']['train_question_sha256']:
            excluded.append({'row_index':i,'question_id':doc['id'],'question_sha256':qsha,'reason':'training_id_or_normalized_question_overlap'});continue
        begin=time.perf_counter();begin_cpu=time.process_time();ranked=ranking(base,doc['claim'],'lexical');selected,used=admit(base,ranked);hits=[];predictions=[];class_wall=0.;class_cpu=0.
        with store.snapshot(sid) as snapshot:
            for key in selected:
                loc=base['shared']['locators'][key];member=snapshot.read_range('corpus.jsonl',loc['offset'],loc['length'])
                if digest(member)!=loc['sha256']:raise ValueError('Selected original paper SHA differs')
                obj=json.loads(member)
                if 'doc:'+str(obj['doc_id'])!=key:raise ValueError('Selected original paper identity differs')
                projection='\n'.join([obj['title'],*obj['abstract']]);hits.append({'paper_id':key,'locator':{'snapshot_id':sid,'path':'corpus.jsonl',**loc},'abstract_sha256':digest(encoded(obj['abstract'])),'title_sha256':digest(obj['title'].encode())})
                t=time.perf_counter();c=time.process_time();prediction=probe.predict(doc['claim'],projection);class_cpu+=time.process_time()-c;class_wall+=time.perf_counter()-t;predictions.append({'paper_id':key,'source_sha256':loc['sha256'],'model_input_document_sha256':digest(projection.encode()),**prediction})
        query_wall=time.perf_counter()-begin;query_cpu=time.process_time()-begin_cpu
        # Neither claim relation labels nor gold sentence positions were used by ranking/predict.
        t=time.perf_counter();c=time.process_time();gold_source=evidence_ids(doc,papers);gold_labels=labels_for_claim(doc,papers);retrieval={'row_index':i,'question_id':doc['id'],'question_sha256':qsha,'selected_ids':selected,'hits':hits,'admitted_record_bytes':used,'gold_paper_ids':sorted(gold_source),'paper_metrics':metrics(selected,gold_source) if gold_source else None,'annotation_status':'evidence-annotated' if gold_source else 'no-gold-evidence-annotation'}
        proof={'retrieval':retrieval,'retrieval_proof_sha256':digest(encoded(retrieval)),'predictions':predictions,'gold_relation_labels':gold_labels};records.append({**proof,'proof_sha256':digest(encoded(proof)),'query_wall_s':query_wall,'query_cpu_s':query_cpu,'classification_wall_s':class_wall,'classification_cpu_s':class_cpu,'gold_audit_wall_s':time.perf_counter()-t,'gold_audit_cpu_s':time.process_time()-c,'ranked_candidates':len(ranked)})
        for key,value in gold_labels.items():all_gold[str(i)+'|'+key]=value
        for prediction in predictions:all_predictions[str(i)+'|'+prediction['paper_id']]=prediction['predicted_relation']
        private.append({'row_index':i,'question':doc['claim'],'selected_ids':selected})
    exclusive(folder/'private-query-check.json',encoded(private)+b'\n');after=ledger(store.root);assert before==after;t=time.perf_counter();c=time.process_time()
    with store.snapshot(sid) as snapshot:assert snapshot.read_range('corpus.jsonl')==raw
    recovery={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'source_sha256':digest(raw)};exclusive(folder/'ledger.json',encoded({'before':before,'after':after}));cost=Counter()
    for p in folder.rglob('*'):
        if p.is_file():cost['store_bytes' if p.relative_to(folder).parts[0]=='store' else 'source_copy_bytes' if p.relative_to(folder).parts[0]=='source' else 'other_worker_files_bytes']+=p.stat().st_size
    report={'round':args.round,'method':args.method,'source_retrieval_model_sha256':digest(base_raw),'relation_model_sha256':digest(model_raw),'model_freeze_sha256':digest(freeze_raw),'model_load':model_load,'dev_sha256':digest(dev_raw),'source_sha256':digest(raw),'raw_dev_rows':len(dev),'retrieved_rows':len(records),'annotated_rows':sum(bool(r['gold_relation_labels']) for r in records),'unannotated_rows':sum(not r['gold_relation_labels'] for r in records),'excluded':excluded,'records':records,'relation_metrics':relation_metrics(all_gold,all_predictions),'ingest':ingest,'recovery':recovery,'store_unchanged':True,'store_tree_sha256':digest(encoded(after)),'files':dict(cost),'loaded_model_bytes':len(base_raw)+len(model_raw),'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'new_remote_model_calls':0,'scientific_entailment_verified':False,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None};exclusive(Path(args.worker_report),encoded(report)+b'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('inputs','model','model-freeze','work','out','worker-report'):p.add_argument('--'+n)
    p.add_argument('--train',action='store_true');p.add_argument('--round',type=int,choices=(1,2,3));p.add_argument('--method',choices=METHODS);args=p.parse_args()
    if args.train:train(args);return
    if args.round:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False);checks=implementation_checksums();programs={n:digest((ROOT/n).read_bytes()) for n in TRACKED};freeze=json.loads(Path(args.model_freeze).read_bytes());exclusive(out/'environment.json',encoded({'python':sys.version,'platform':platform.platform(),'implementation_checksums':checks,'program_protocol_sha256':programs,'workers':12,'methods':METHODS,'orders':['ABCD','BADC','CDAB'],'model_freeze':freeze,'scope':'Known SciFact actual lexical-retrieved-paper weak relation classification. Not oracle document/rationale input, semantic verification or answers.'})+b'\n');env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n,order in enumerate(('ABCD','BADC','CDAB'),1):
        for letter in order:
            method=METHODS[ord(letter)-65];label=f'round-{n}-{method}';report=out/(label+'.json');code=None;error=None;t=time.perf_counter()
            with (out/(label+'.log')).open('xb') as log:
                try:code=subprocess.run([sys.executable,'-m','scripts.run_relation_probe','--inputs',str(Path(args.inputs).resolve()),'--model',str(Path(args.model).resolve()),'--model-freeze',str(Path(args.model_freeze).resolve()),'--work',str(work/label),'--round',str(n),'--method',method,'--worker-report',str(report)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
                except subprocess.TimeoutExpired:error='TimeoutExpired'
            exclusive(out/(label+'-parent.json'),encoded({'return_code':code,'error':error,'parent_full_process_wall_s':time.perf_counter()-t,'child_sha256':digest(report.read_bytes()) if report.exists() else None})+b'\n');print(label,code,flush=True)
    assert checks==implementation_checksums() and programs=={n:digest((ROOT/n).read_bytes()) for n in TRACKED}

if __name__=='__main__':main()
