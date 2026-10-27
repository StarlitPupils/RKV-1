"""Known SciFact exploratory sentence-max ranking, still whole-paper admission."""
import argparse,json,os,random,subprocess,sys,time
from collections import Counter
from pathlib import Path
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.store import Store
from scripts.scifact_graph import paper_records,evidence_ids,verified_hits,ranking,admit,metrics,encoded,question_identity
from scripts.sentence_index import build_index,parent_ranking,verified_parent_hits
from scripts.run_source_alignment import exclusive,ledger

ROOT=Path(__file__).resolve().parents[1]
METHODS=('paper_lexical','paper_graph','sentence_max')
TRACKED=('scripts/run_sentence_parent.py','scripts/analyze_sentence_parent.py','scripts/audit_sentence_catalog.py','scripts/sentence_index.py','scripts/source_string_spans.py','scripts/evidence_retrieval.py','scripts/scifact_graph.py','scripts/source_alignment.py','scripts/run_source_alignment.py','tests/test_audit_sentence_catalog.py','tests/test_source_string_spans.py','tests/test_sentence_index.py','tests/test_sentence_parent.py','docs/SENTENCE-PARENT.md','docs/sentence-parent-inputs.json')

def checked(path,sha):
    raw=Path(path).read_bytes()
    if digest(raw)!=sha:raise ValueError('Frozen input SHA differs')
    return raw

def source_input(args,name):
    manifest=json.loads(Path(args.manifest).read_bytes());return checked(Path(args.inputs)/name,manifest['files'][name]['sha256'])

def build(args):
    begin=time.perf_counter();cpu=time.process_time();folder=Path(args.work);folder.mkdir(exist_ok=False)
    manifest=json.loads(Path(args.manifest).read_bytes());model_raw=checked(args.model,manifest['paper_model_sha256']);paper_model=json.loads(model_raw)
    raw=source_input(args,'corpus.jsonl');index,parts=build_index(raw,paper_model);index_raw=encoded(index);exclusive(folder/'sentence-index.json',index_raw)
    exclusive(folder/'construction.json',encoded({'source_sha256':digest(raw),'paper_model_sha256':digest(model_raw),'sentence_index_sha256':digest(index_raw),
        'sentence_index_bytes':len(index_raw),'parts':parts,'worker_wall_s':time.perf_counter()-begin,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'source_bytes':len(raw),'original_model_bytes':len(model_raw),'new_unlabelled_source_index_builds':1,'new_training_runs':0,'dev_queries_or_gold_read':False})+b'\n')

def worker(args):
    begin=time.perf_counter();cpu=time.process_time();folder=Path(args.work);folder.mkdir(exist_ok=False)
    manifest=json.loads(Path(args.manifest).read_bytes());freeze_raw=Path(args.index_freeze).read_bytes();freeze=json.loads(freeze_raw)
    assert freeze['paper_model_sha256']==manifest['paper_model_sha256'] and freeze['source_sha256']==manifest['files']['corpus.jsonl']['sha256']
    t=time.perf_counter();c=time.process_time();model_raw=checked(args.model,manifest['paper_model_sha256']);paper_model=json.loads(model_raw);loaded_index_bytes=0;index=None
    if args.method=='sentence_max':
        index_raw=checked(args.index,freeze['sentence_index_sha256']);loaded_index_bytes=len(index_raw);index=json.loads(index_raw)
    load={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'paper_model_bytes':len(model_raw),'sentence_index_loaded_bytes':loaded_index_bytes}
    raw=source_input(args,'corpus.jsonl');dev_raw=source_input(args,'claims_dev.jsonl');papers=paper_records(raw);dev=[json.loads(row) for row in dev_raw.splitlines()]
    src=folder/'source';src.mkdir();exclusive(src/'corpus.jsonl',raw);store=Store.create(folder/'store',compression='zlib',chunk_size=65536,io_backend='bounded')
    t=time.perf_counter();c=time.process_time();commit=store.add(src,label='scifact-graph-transfer');ingest={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'commit':commit};sid=commit['snapshot_id']
    assert sid==manifest['expected_source_snapshot_id'];before=ledger(store.root);order=list(range(len(dev)));random.Random(20261027+args.round).shuffle(order);exclusive(folder/'plan.json',encoded(order))
    records=[];excluded=[];private=[]
    for row in order:
        claim=dev[row];qsha=question_identity(claim['claim'])
        if str(claim['id']) in paper_model['shared']['train_ids'] or qsha in paper_model['shared']['train_question_sha256']:
            excluded.append({'row_index':row,'question_id':claim['id'],'question_sha256':qsha,'reason':'training_id_or_normalized_question_overlap'});continue
        t=time.perf_counter();c=time.process_time()
        if args.method=='sentence_max':ranked,best=parent_ranking(index,claim['claim'])
        else:ranked=ranking(paper_model,claim['claim'],'lexical' if args.method=='paper_lexical' else 'graph')
        selected,admitted=admit(paper_model,ranked)
        with store.snapshot(sid) as snapshot:
            if args.method=='sentence_max':hits,hints=verified_parent_hits(snapshot,paper_model,index,selected,best)
            else:hits=verified_hits(snapshot,paper_model,selected);hints=[]
        query_cpu=time.process_time()-c;query_wall=time.perf_counter()-t
        t=time.perf_counter();c=time.process_time();gold=evidence_ids(claim,papers);hint_metric=None
        if args.method=='sentence_max':
            selected_gold=[h for h in hints if h['paper_id'] in gold];correct=0
            for hint in selected_gold:
                sets=claim['evidence'][hint['paper_id'].removeprefix('doc:')]
                correct+=hint['sentence_index'] in {i for entry in sets for i in entry['sentences']}
            hint_metric={'selected_gold_papers':len(selected_gold),'best_hint_in_any_annotated_rationale':correct,'rate':correct/len(selected_gold) if selected_gold else None}
        proof={'row_index':row,'question_id':claim['id'],'question_sha256':qsha,'selected_ids':selected,'hits':hits,'best_sentence_hints':hints,
            'admitted_record_bytes':admitted,'gold_paper_ids':sorted(gold),'paper_metrics':metrics(selected,gold) if gold else None,'hint_metrics':hint_metric,
            'annotation_status':'evidence-annotated' if gold else 'no-gold-evidence-annotation'}
        score_cpu=time.process_time()-c;score_wall=time.perf_counter()-t
        records.append({**proof,'proof_sha256':digest(encoded(proof)),'query_cpu_s':query_cpu,'query_wall_s':query_wall,'gold_audit_cpu_s':score_cpu,'gold_audit_wall_s':score_wall,'ranked_parent_candidates':len(ranked)})
        private.append({'row_index':row,'question':claim['claim'],'selected_ids':selected})
    exclusive(folder/'private-query-check.json',encoded(private));after=ledger(store.root);assert before==after
    t=time.perf_counter();c=time.process_time()
    with store.snapshot(sid) as snapshot:assert snapshot.read_range('corpus.jsonl')==raw
    recovery={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'source_SHA_match':True};exclusive(folder/'ledger.json',encoded({'before':before,'after':after}));files=Counter()
    for p in folder.rglob('*'):
        if p.is_file():files['store_bytes' if p.is_relative_to(store.root) else 'source_copy_bytes' if p.is_relative_to(src) else 'other_worker_files_bytes']+=p.stat().st_size
    exclusive(Path(args.worker_report),encoded({'round':args.round,'method':args.method,'records':records,'excluded':excluded,'raw_dev_rows':len(dev),'retrieved_rows':len(records),
        'annotated_rows':sum(r['paper_metrics'] is not None for r in records),'unannotated_rows':sum(r['paper_metrics'] is None for r in records),
        'source_sha256':digest(raw),'dev_sha256':digest(dev_raw),'paper_model_sha256':digest(model_raw),'sentence_index_sha256':freeze['sentence_index_sha256'],'index_freeze_sha256':digest(freeze_raw),
        'model_load':load,'ingest':ingest,'full_source_recovery':recovery,'files':dict(files),'store_unchanged':True,'store_tree_sha256':digest(encoded(after)),
        'worker_wall_s':time.perf_counter()-begin,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'new_remote_model_calls':0,'new_training_runs':0,
        'source_plus_dev_input_returned_bytes':len(raw)+len(dev_raw),'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})+b'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','model','index','index-freeze','manifest','work','out','worker-report'):p.add_argument('--'+name)
    p.add_argument('--build-index',action='store_true');p.add_argument('--round',type=int,choices=(1,2,3));p.add_argument('--method',choices=METHODS);args=p.parse_args()
    if args.build_index:build(args);return
    if args.round:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False);checks=implementation_checksums();programs={n:digest((ROOT/n).read_bytes()) for n in TRACKED}
    exclusive(out/'environment.json',encoded({'python':sys.version,'workers':9,'orders':['ABC','BCA','CAB'],'methods':METHODS,'implementation_checksums':checks,'program_protocol_sha256':programs,'worker_timeout_s':600,'scope':'Known SciFact exploratory ranking trial, whole original paper admission, not unseen data or answers'})+b'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n,order in enumerate(('ABC','BCA','CAB'),1):
        for letter in order:
            method=METHODS[ord(letter)-65];name=f'round-{n}-{method}';report=out/(name+'.json');t=time.perf_counter();code=None;error=None
            with (out/(name+'.log')).open('xb') as log:
                try:code=subprocess.run([sys.executable,'-m','scripts.run_sentence_parent','--inputs',str(Path(args.inputs).resolve()),'--model',str(Path(args.model).resolve()),'--index',str(Path(args.index).resolve()),'--index-freeze',str(Path(args.index_freeze).resolve()),'--manifest',str(Path(args.manifest).resolve()),'--work',str(work/name),'--round',str(n),'--method',method,'--worker-report',str(report)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
                except subprocess.TimeoutExpired:error='TimeoutExpired'
            exclusive(out/(name+'-parent.json'),encoded({'return_code':code,'error':error,'parent_full_process_wall_s':time.perf_counter()-t,'child_sha256':digest(report.read_bytes()) if report.exists() else None})+b'\n')
            print(name,code,flush=True)
    assert checks==implementation_checksums() and programs=={n:digest((ROOT/n).read_bytes()) for n in TRACKED}

if __name__=='__main__':main()
