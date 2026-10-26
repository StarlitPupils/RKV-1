"""Train-only physical original-source audit; no dev access or retrieval scoring."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.store import Store
from scripts.source_alignment import corpus_records,alignments,verify_binding
from scripts.run_memory_concurrency import save

ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/source_alignment.py','scripts/run_source_alignment.py','scripts/analyze_source_alignment.py',
         'scripts/run_memory_concurrency.py','tests/test_source_alignment.py','docs/SOURCE-ALIGNMENT.md','docs/entailment-inputs.json')


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()


def exclusive(path,raw):
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())


def ledger(root):
    return {p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file()}


def worker(args):
    begin=time.perf_counter();cpu=time.process_time();work=Path(args.work);work.mkdir(exist_ok=False)
    inputs=Path(args.inputs);manifest=json.loads((ROOT/'docs/entailment-inputs.json').read_text('utf-8'))
    raw=(inputs/'corpus.json').read_bytes();labels=(inputs/'labels-train.jsonl').read_bytes()
    for name,content in (('corpus.json',raw),('labels-train.jsonl',labels)):assert digest(content)==manifest['files'][name]['sha256']
    facts,aliases=corpus_records(raw);training=[json.loads(line) for line in labels.splitlines()]
    src=work/'source';src.mkdir();exclusive(src/'corpus.json',raw)
    store=Store.create(work/'store',compression='zlib',chunk_size=65536,io_backend='bounded')
    t=time.perf_counter();c=time.process_time();commit=store.add(src,label='train-source-alignment')
    ingest={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'commit':commit};sid=commit['snapshot_id'];before=ledger(store.root)
    records=[];counts=Counter();t=time.perf_counter();c=time.process_time()
    with store.snapshot(sid) as snapshot:
        for index,row in enumerate(training):
            for rec in alignments(row,facts,aliases):
                counts[rec['resolution']]+=1
                if rec['fact_id'] is not None:
                    rec['locator']=verify_binding(snapshot,facts,rec['fact_id'])
                    counts['original_bindings']+=1
                    counts['annotation_literal_exact' if rec['annotation_exact'] else 'UUID_bound_annotation_different']+=1
                else:rec['locator']=None
                records.append({'row_index':index,'question_id':row['id'],**rec})
        recovered=snapshot.read_range('corpus.json');assert recovered==raw
    audit={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};after=ledger(store.root);assert before==after
    exclusive(work/'ledger.json',encoded({'before':before,'after':after}))
    report={'round':args.round,'training_rows':len(training),'unique_training_ids':len({r['id'] for r in training}),
        'source_ids':len(aliases),'exact_unique_source_sentences':len(facts),'counts':dict(counts),'records':records,
        'source_SHA':digest(raw),'training_SHA':digest(labels),'source_full_recovery':True,'store_unchanged':True,
        'store_tree_sha256':digest(encoded(after)),'ingest':ingest,'physical_audit':audit,
        'files':{'store_bytes':sum(v['bytes'] for v in after.values()),'source_copy_bytes':len(raw),'ledger_bytes':(work/'ledger.json').stat().st_size,
                 'shared_input_application_read_returned_bytes':len(raw)+len(labels)},
        'worker_wall_s':time.perf_counter()-begin,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'source_input_fsyncs':1,'ledger_fsyncs':1,'internal_store_fsyncs':None,'no_dev_file_opened':True,'retrieval_scores_computed':False,
        'new_model_training_runs':0,'new_model_calls':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None}
    exclusive(Path(args.worker_report),encoded(report)+b'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('work','out','inputs','worker-report'):p.add_argument('--'+k,required=k in ('work','inputs'))
    p.add_argument('--round',type=int);args=p.parse_args()
    if args.round:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    checks=implementation_checksums();old=json.loads((ROOT/'results/v0.48.0/source-checksums.json').read_text('utf-8'))
    assert set(checks)==set(old) and all(checks[k]==v for k,v in old.items() if k!='__init__.py')
    tracked={k:digest((ROOT/k).read_bytes()) for k in TRACKED}
    save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'implementation_checksums':checks,'program_protocol_sha256':tracked,
        'workers':3,'rounds':3,'worker_timeout_s':600,'scope':'Seen training identities only, no dev open, no graph/model training or retrieval gain experiment'})
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n in (1,2,3):
        report=out/f'round-{n}.json';code=None;error=None
        with (out/f'round-{n}.log').open('wb') as log:
            begin=time.perf_counter()
            try:code=subprocess.run([sys.executable,'-m','scripts.run_source_alignment','--work',str(work/f'round-{n}'),
                '--inputs',str(Path(args.inputs).resolve()),'--round',str(n),'--worker-report',str(report)],cwd=ROOT,env=env,
                stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
            except subprocess.TimeoutExpired:error='TimeoutExpired'
            elapsed=time.perf_counter()-begin
        exclusive(out/f'round-{n}-parent.json',encoded({'round':n,'return_code':code,'error':error,'parent_full_process_wall_s':elapsed,
            'child_report_sha256':digest(report.read_bytes()) if report.exists() else None})+b'\n')
        print('round',n,'return_code',code,'parent_wall_s',elapsed,flush=True)
    assert implementation_checksums()==checks and tracked=={k:digest((ROOT/k).read_bytes()) for k in TRACKED}


if __name__=='__main__':main()
