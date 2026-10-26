"""Question-only heldout retrieval, one frozen train model, immutable sources."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.store import Store
from scripts.evidence_retrieval import encoded,question_identity,ranking,admit,verified_hits,gold_targets,metrics,corpus_records
from scripts.run_source_alignment import exclusive,ledger
from scripts.run_memory_concurrency import save

ROOT=Path(__file__).resolve().parents[1]
METHODS=('lexical','graph','permuted_graph')
TRACKED=('scripts/evidence_retrieval.py','scripts/run_question_test.py','scripts/analyze_question_test.py',
         'scripts/source_alignment.py','scripts/run_source_alignment.py','scripts/run_memory_concurrency.py',
         'tests/test_evidence_retrieval.py','tests/test_question_test_plan.py','docs/QUESTION-TEST.md','docs/entailment-test-inputs.json')


def load_input(folder,name):
    raw=(Path(folder)/name).read_bytes();manifest=json.loads((ROOT/'docs/entailment-test-inputs.json').read_text('utf-8'))
    assert digest(raw)==manifest['files'][name]['sha256'];return raw


def worker(args):
    begin=time.perf_counter();cpu=time.process_time();work=Path(args.work);work.mkdir(exist_ok=False)
    freeze_raw=Path(args.model_freeze).read_bytes();freeze=json.loads(freeze_raw);model_raw=Path(args.model).read_bytes()
    assert digest(model_raw)==freeze['model_sha256'];model=json.loads(model_raw)
    raw=load_input(args.inputs,'corpus.json');test_raw=load_input(args.inputs,'labels-test.jsonl')
    facts,aliases=corpus_records(raw);test=[json.loads(x) for x in test_raw.splitlines()]
    seen=json.loads((ROOT/'docs/entailment-test-inputs.json').read_bytes())
    src=work/'source';src.mkdir();exclusive(src/'corpus.json',raw)
    store=Store.create(work/'store',compression='zlib',chunk_size=65536,io_backend='bounded');t=time.perf_counter();c=time.process_time()
    commit=store.add(src,label='question-test-retrieval');ingest={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'commit':commit}
    sid=commit['snapshot_id'];before=ledger(store.root);order=list(range(len(test)));random.Random(20261027+args.round).shuffle(order)
    exclusive(work/'plan.json',encoded(order));records=[];private=[];excluded=[]
    for index in order:
        doc=test[index];qsha=question_identity(doc['question'])
        if doc['id'] in model['shared']['train_ids'] or qsha in model['shared']['train_question_sha256'] or doc['id'] in seen.get('seen_dev_question_ids',[]) or qsha in seen.get('seen_dev_question_sha256',[]):
            excluded.append({'row_index':index,'question_id':doc['id'],'question_sha256':qsha,'reason':'training_or_seen_dev_id_or_normalized_question_overlap'});continue
        # Retrieval sees only the question string and the already frozen model.
        t=time.perf_counter();c=time.process_time();ranked=ranking(model,doc['question'],args.method)
        selected,admitted=admit(model,ranked)
        with store.snapshot(sid) as snap:hits=verified_hits(snap,model,selected)
        query_cpu=time.process_time()-c;query_wall=time.perf_counter()-t
        # Gold fields enter only after the selected list and verified hits exist.
        t=time.perf_counter();c=time.process_time();gold,mapping,literal=gold_targets(doc,facts,aliases)
        proof={'row_index':index,'question_id':doc['id'],'question_sha256':qsha,'selected_ids':selected,'hits':hits,
            'admitted_record_bytes':admitted,'gold_id_groups':sorted(gold),'literal_groups':sorted(literal),
            'ID_metrics':metrics(selected,gold),'literal_metrics':metrics(selected,literal),'gold_mapping':mapping}
        score_cpu=time.process_time()-c;score_wall=time.perf_counter()-t
        records.append({**proof,'proof_sha256':digest(encoded(proof)),'query_wall_s':query_wall,'query_cpu_s':query_cpu,
            'gold_audit_wall_s':score_wall,'gold_audit_cpu_s':score_cpu,'ranked_candidates':len(ranked)})
        private.append({'row_index':index,'question':doc['question'],'selected_ids':selected})
    exclusive(work/'private-query-check.json',encoded(private));after=ledger(store.root);assert before==after
    t=time.perf_counter();c=time.process_time()
    with store.snapshot(sid) as snapshot:assert snapshot.read_range('corpus.json')==raw
    recovery={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'source_sha256':digest(raw)}
    exclusive(work/'ledger.json',encoded({'before':before,'after':after}));cost=Counter()
    for p in work.rglob('*'):
        if p.is_file():
            group=p.relative_to(work).parts[0];cost['store_bytes' if group=='store' else 'source_copy_bytes' if group=='source' else 'other_worker_files_bytes']+=p.stat().st_size
    report={'round':args.round,'method':args.method,'model_sha256':digest(model_raw),'model_freeze_sha256':digest(freeze_raw),
        'test_sha256':digest(test_raw),'source_sha256':digest(raw),'raw_test_rows':len(test),'scored_rows':len(records),'excluded':excluded,
        'records':records,'ingest':ingest,'recovery':recovery,'store_unchanged':True,'store_tree_sha256':digest(encoded(after)),
        'files':dict(cost),'loaded_full_model_bytes':len(model_raw),'source_and_dev_input_returned_bytes':len(raw)+len(test_raw),
        'worker_wall_s':time.perf_counter()-begin,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'new_model_calls':0,'source_fsyncs':1,'plan_fsyncs':1,'private_query_fsyncs':1,'ledger_fsyncs':1,'internal_store_fsyncs':None,
        'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None}
    exclusive(Path(args.worker_report),encoded(report)+b'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('work','out','inputs','model','model-freeze','worker-report'):p.add_argument('--'+k,required=k in ('work','inputs'))
    p.add_argument('--round',type=int);p.add_argument('--method',choices=METHODS);args=p.parse_args()
    if args.round:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    checks=implementation_checksums();tracked={k:digest((ROOT/k).read_bytes()) for k in TRACKED}
    old=json.loads((ROOT/'results/v0.50.0/source-checksums.json').read_text('utf-8'));assert set(old)==set(checks) and all(checks[k]==v for k,v in old.items() if k!='__init__.py')
    model_freeze=json.loads(Path(args.model_freeze).read_bytes());assert digest(Path(args.model).read_bytes())==model_freeze['model_sha256']
    save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'implementation_checksums':checks,'program_protocol_sha256':tracked,
        'workers':9,'rounds':3,'orders':['ABC','BCA','CAB'],'methods':METHODS,'worker_timeout_s':600,'model_freeze':model_freeze,
        'scope':'Question-only source-ID retrieval and literal-evidence diagnostic, no generated answer or semantic proof'})
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n,order in enumerate(('ABC','BCA','CAB'),1):
        for letter in order:
            method=METHODS[ord(letter)-65];label=f'round-{n}-{method}';report=out/(label+'.json');code=None;error=None
            with (out/(label+'.log')).open('wb') as log:
                begin=time.perf_counter()
                try:code=subprocess.run([sys.executable,'-m','scripts.run_question_test','--work',str(work/label),'--inputs',str(Path(args.inputs).resolve()),
                    '--model',str(Path(args.model).resolve()),'--model-freeze',str(Path(args.model_freeze).resolve()),'--round',str(n),'--method',method,
                    '--worker-report',str(report)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
                except subprocess.TimeoutExpired:error='TimeoutExpired'
                elapsed=time.perf_counter()-begin
            exclusive(out/(label+'-parent.json'),encoded({'round':n,'method':method,'return_code':code,'error':error,'parent_full_process_wall_s':elapsed,
                'child_report_sha256':digest(report.read_bytes()) if report.exists() else None})+b'\n')
            print(label,'return_code',code,'parent_wall_s',elapsed,flush=True)
    assert implementation_checksums()==checks and tracked=={k:digest((ROOT/k).read_bytes()) for k in TRACKED}


if __name__=='__main__':main()
