"""Known-report failure partition and gold-aware bounds; no new retrieval trials."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from scripts.evidence_retrieval import encoded,ranking,admit
from scripts.retrieval_gap import partition,oracle
from scripts.run_source_alignment import exclusive
from scripts.run_memory_concurrency import save

ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/retrieval_gap.py','scripts/run_retrieval_gap.py','scripts/analyze_retrieval_gap.py','scripts/evidence_retrieval.py',
         'scripts/source_alignment.py','scripts/run_source_alignment.py','scripts/run_memory_concurrency.py',
         'docs/RETRIEVAL-GAP.md','docs/retrieval-gap-inputs.json','tests/test_retrieval_gap.py')
CONDITIONS=tuple((split,method) for split in ('dev','test') for method in ('lexical','graph','permuted_graph'))


def load_verified(path,sha):
    raw=Path(path).read_bytes()
    if digest(raw)!=sha:raise ValueError('Frozen diagnostic input identity differs')
    return raw


def worker(args):
    begin=time.perf_counter();cpu=time.process_time();work=Path(args.work);work.mkdir(exist_ok=False)
    manifest_raw=(ROOT/'docs/retrieval-gap-inputs.json').read_bytes();manifest=json.loads(manifest_raw)
    frozen=next(x for x in manifest['reports'] if (x['split'],x['method'])==(args.split,args.method))
    report_raw=load_verified(ROOT/frozen['report_path'],frozen['report_sha256']);old=json.loads(report_raw)
    queries_raw=load_verified(ROOT/frozen['private_query_path'],frozen['private_query_sha256']);queries={x['row_index']:x['question'] for x in json.loads(queries_raw)}
    model_raw=load_verified(Path(args.model),manifest['model_sha256']);model=json.loads(model_raw)
    assert old['model_sha256']==manifest['model_sha256'];loc=model['shared']['locators'];records=[];counts=Counter()
    t=time.perf_counter();c=time.process_time()
    for rec in old['records']:
        ranked=ranking(model,queries[rec['row_index']],args.method);selected,used=admit(model,ranked)
        assert selected==rec['selected_ids'] and used==rec['admitted_record_bytes']
        for hit in rec['hits']:
            key=hit['fact_id'];assert {k:hit['locator'][k] for k in ('offset','length','sha256')}==loc[key]
        gold=set(rec['gold_id_groups']);part=partition(loc,ranked,selected,gold);counts.update(part['counts'])
        assert part['counts']['recovered']==rec['ID_metrics']['recovered_groups']
        records.append({'row_index':rec['row_index'],'question_id':rec['question_id'],'archived_proof_sha256':rec['proof_sha256'],
            'partition':part,'source_ID_oracle':oracle(loc,gold),'candidate_ID_oracle':oracle(loc,gold,candidates=ranked),
            'literal_oracle':oracle(loc,set(rec['literal_groups'])),'archived_ID_metrics':rec['ID_metrics'],'archived_literal_metrics':rec['literal_metrics']})
    replay={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};data={'split':args.split,'method':args.method,
        'archived_report_sha256':digest(report_raw),'private_query_sha256':digest(queries_raw),'model_sha256':digest(model_raw),
        'records':records,'counts':dict(counts),'replay_and_diagnostic':replay,
        'loaded_bytes':{'model':len(model_raw),'archived_report':len(report_raw),'private_queries':len(queries_raw),'manifest':len(manifest_raw)},
        'worker_wall_s':time.perf_counter()-begin,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'new_model_training_runs':0,'new_scientific_evaluation_trials':0,'new_original_source_range_bindings':0,
        'new_remote_model_calls':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,
        'scope':'Pure frozen-ranking replay plus gold-aware diagnostic; oracle knows gold, never an implementable retrieval score'}
    exclusive(Path(args.worker_report),encoded(data)+b'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('work','out','model','worker-report'):p.add_argument('--'+k,required=k in ('work','model'))
    p.add_argument('--split',choices=('dev','test'));p.add_argument('--method',choices=('lexical','graph','permuted_graph'));args=p.parse_args()
    if args.split:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    checks=implementation_checksums();old=json.loads((ROOT/'results/v0.51.0/source-checksums.json').read_bytes());assert set(old)==set(checks) and all(checks[k]==v for k,v in old.items() if k!='__init__.py')
    tracked={k:digest((ROOT/k).read_bytes()) for k in TRACKED}
    save(out/'environment.json',{'implementation_checksums':checks,'program_protocol_sha256':tracked,'conditions':CONDITIONS,
        'workers':6,'worker_timeout_s':600,'new_scientific_trials':0,'new_training_runs':0,'scope':'Known original reports, model unchanged; diagnostic only'})
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for split,method in CONDITIONS:
        label=split+'-'+method;report=out/(label+'.json');code=None;error=None
        with (out/(label+'.log')).open('wb') as log:
            begin=time.perf_counter()
            try:code=subprocess.run([sys.executable,'-m','scripts.run_retrieval_gap','--work',str(work/label),'--model',str(Path(args.model).resolve()),
                '--split',split,'--method',method,'--worker-report',str(report)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
                timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
            except subprocess.TimeoutExpired:error='TimeoutExpired'
            elapsed=time.perf_counter()-begin
        exclusive(out/(label+'-parent.json'),encoded({'split':split,'method':method,'return_code':code,'error':error,'parent_full_process_wall_s':elapsed,
            'child_report_sha256':digest(report.read_bytes()) if report.exists() else None})+b'\n')
        print(label,'return_code',code,'parent_wall_s',elapsed,flush=True)
    assert implementation_checksums()==checks and tracked=={k:digest((ROOT/k).read_bytes()) for k in TRACKED}


if __name__=='__main__':main()
