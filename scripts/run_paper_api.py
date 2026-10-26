"""Proposed known-proof experimental API mechanism campaign, not QA evaluation."""
import argparse,json,os,subprocess,sys,time
from collections import Counter
from pathlib import Path
from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from rkv1.store import Store
from rkv1.experiments.paper_retriever import PaperRetriever
from scripts.evidence_retrieval import encoded,question_identity
from scripts.run_source_alignment import exclusive,ledger

ROOT=Path(__file__).resolve().parents[1]
METHODS=('lexical','graph','permuted_graph')

def worker(args):
    begin=time.perf_counter();cpu=time.process_time();folder=Path(args.work);folder.mkdir(exist_ok=False)
    manifest=json.loads(Path(args.manifest).read_bytes());entry=manifest['methods'][args.method]
    raw=Path(args.source).read_bytes();report_raw=Path(entry['report_path']).read_bytes();query_raw=Path(entry['queries_path']).read_bytes()
    assert digest(raw)==manifest['source_sha256'] and digest(report_raw)==entry['report_sha256'] and digest(query_raw)==entry['queries_sha256']
    old=json.loads(report_raw);queries=json.loads(query_raw);byrow={q['row_index']:q for q in queries};assert len(byrow)==298
    src=folder/'source';src.mkdir();exclusive(src/'corpus.jsonl',raw)
    store=Store.create(folder/'store',compression='zlib',chunk_size=65536,io_backend='bounded');t=time.perf_counter();c=time.process_time()
    commit=store.add(src,label='scifact-graph-transfer');ingest={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'commit':commit};sid=commit['snapshot_id']
    assert sid==old['ingest']['commit']['snapshot_id'];before=ledger(store.root)
    t=time.perf_counter();c=time.process_time();api=PaperRetriever(store.root,sid,args.model,model_sha256=manifest['model_sha256'])
    constructor={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'model_info':api.model_info()}
    records=[];bindings=0
    for rec in old['records']:
        query=byrow.pop(rec['row_index']);assert question_identity(query['question'])==rec['question_sha256']
        t=time.perf_counter();c=time.process_time();answer=api.query(query['question'],method=args.method);query_cpu=time.process_time()-c;query_wall=time.perf_counter()-t
        assert answer['selected_ids']==rec['selected_ids'] and answer['admitted_record_bytes']==rec['admitted_record_bytes']
        assert answer['snapshot_id']==sid and answer['model_sha256']==manifest['model_sha256'] and answer['source_sha256']==manifest['source_sha256']
        assert answer['selected_source_identity_verified'] is True and answer['scientific_entailment_verified'] is False and answer['generated_answer'] is None
        hits=[]
        for hit in answer['hits']:
            assert digest(hit['title'].encode('utf-8'))==hit['title_sha256'] and digest(encoded(hit['abstract']))==hit['abstract_sha256']
            hits.append({k:v for k,v in hit.items() if k not in ('title','abstract')})
        assert hits==rec['hits'];bindings+=len(hits)
        proof={'row_index':rec['row_index'],'question_id':rec['question_id'],'question_sha256':rec['question_sha256'],
            'selected_ids':answer['selected_ids'],'admitted_record_bytes':answer['admitted_record_bytes'],'hits':hits,'prior_proof_sha256':rec['proof_sha256']}
        records.append({**proof,'proof_sha256':digest(encoded(proof)),'query_wall_s':query_wall,'query_cpu_s':query_cpu})
    assert not byrow and len(records)==298 and before==ledger(store.root)
    t=time.perf_counter();c=time.process_time()
    with store.snapshot(sid) as snapshot:assert snapshot.read_range('corpus.jsonl')==raw
    recovery={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'full_source_SHA_match':True}
    files=Counter()
    for path in folder.rglob('*'):
        if path.is_file():files['store_bytes' if path.is_relative_to(store.root) else 'source_copy_bytes']+=path.stat().st_size
    exclusive(Path(args.worker_report),encoded({'method':args.method,'records':records,'bindings':bindings,'constructor':constructor,'ingest':ingest,
        'full_source_recovery':recovery,'files':dict(files),'source_bytes':len(raw),'prior_report_input_bytes':len(report_raw),'private_query_input_bytes':len(query_raw),
        'worker_wall_s':time.perf_counter()-begin,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'new_scientific_trials':0,'new_training_runs':0,'new_remote_model_calls':0,'store_unchanged':True,
        'scope':'Known SciFact proof equivalence for new API; not a new scientific quality or speed comparison',
        'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})+b'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('work','out','source','model','manifest','worker-report'):p.add_argument('--'+name)
    p.add_argument('--method',choices=METHODS);args=p.parse_args()
    if args.method:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    checks=implementation_checksums();environment={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for method in METHODS:
        report=out/(method+'.json');t=time.perf_counter();code=None;error=None
        with (out/(method+'.log')).open('xb') as log:
            try:code=subprocess.run([sys.executable,'-m','scripts.run_paper_api','--work',str(work/method),'--source',str(Path(args.source).resolve()),
                '--model',str(Path(args.model).resolve()),'--manifest',str(Path(args.manifest).resolve()),'--method',method,'--worker-report',str(report)],
                cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
            except subprocess.TimeoutExpired:error='TimeoutExpired'
        exclusive(out/(method+'-parent.json'),encoded({'return_code':code,'error':error,'parent_full_process_wall_s':time.perf_counter()-t,'child_sha256':digest(report.read_bytes()) if report.exists() else None})+b'\n')
        assert code==0 and error is None,'Preserve failures; never rerun known proof mechanism worker'
        print(method,'finished',flush=True)
    assert checks==implementation_checksums()

if __name__=='__main__':main()
