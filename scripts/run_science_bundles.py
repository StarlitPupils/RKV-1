"""Frozen fixed-SID three-key lookup bundles, existing SciFact, CPU/offline."""
import argparse
from collections import Counter
from contextlib import nullcontext
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
from rkv1.memory import Memory
from scripts.cas_traffic import CASTraffic
from scripts.query_view import QueryView
from scripts.run_memory_concurrency import save
from scripts.science_bundles import SOURCE_SHA,SOURCE_BYTES,catalog,bundles,audit,canonical,public_proof,assert_text_free,exclusive,ledger

ROOT=Path(__file__).resolve().parents[1]
CONDITIONS=tuple((w,v,m) for w in ('spread','repeated') for v,m in (('off','off'),('on','off'),('off','on'),('on','on')))
ORDERS=('ABCDEFGH','BADCFEHG','GHCDEFAB')
TRACKED=('scripts/science_bundles.py','scripts/run_science_bundles.py','scripts/analyze_science_bundles.py',
         'scripts/query_view.py','scripts/cas_traffic.py','scripts/run_memory_concurrency.py',
         'docs/SCIENCE-BUNDLES.md','tests/test_science_bundles.py')


def worker(args):
    began=time.perf_counter();cpu=time.process_time();folder=Path(args.work);folder.mkdir(exist_ok=False)
    raw=Path(args.corpus).read_bytes();assert len(raw)==SOURCE_BYTES and digest(raw)==SOURCE_SHA
    index=catalog(raw);assert len(index)==5183
    source=folder/'source';source.mkdir();exclusive(source/'corpus.jsonl',raw)
    memory=Memory.create(folder/'memory');start=time.perf_counter();start_cpu=time.process_time()
    commit=memory.add(source);ingest={'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-start_cpu,'commit':commit}
    sid=commit['snapshot_id'];before=ledger(memory.root);head=memory.current()
    plan=bundles(index,args.workload,args.round);plan_raw=canonical(plan);exclusive(folder/'plan.json',plan_raw)
    rows=[];private=[]
    for question in plan:
        view=QueryView(memory,sid) if args.view=='on' else None
        meter=CASTraffic(memory.store) if args.meter=='on' else None
        start=time.perf_counter();start_cpu=time.process_time()
        with meter if meter is not None else nullcontext():
            with view if view is not None else nullcontext():
                hits=[memory.lookup(key,snapshot=sid)['hits'] for key in question['keys']]
        query_cpu=time.process_time()-start_cpu;query_wall=time.perf_counter()-start
        proof={'snapshot_id':sid,'keys':question['keys'],'hits':hits}
        check=time.perf_counter();check_cpu=time.process_time();bindings=audit(index,proof,sid)
        audit_cpu=time.process_time()-check_cpu;audit_wall=time.perf_counter()-check
        private.append({'case_id':question['case_id'],'proof':proof})
        rows.append({'case_id':question['case_id'],**public_proof(proof),'bindings':bindings,
            'selected_record_bytes':sum(g[0]['locator']['length'] for g in hits),
            'query_wall_s':query_wall,'query_cpu_s':query_cpu,'audit_wall_s':audit_wall,'audit_cpu_s':audit_cpu,
            'traffic':meter.result() if meter else None,'view':view.result() if view else None})
    exclusive(folder/'private-hits.json',canonical(private));after=ledger(memory.root)
    assert before==after and head==memory.current()==sid
    check=time.perf_counter();check_cpu=time.process_time()
    restored=memory.store.snapshot(sid).read_range('corpus.jsonl');assert restored==raw
    recovery={'wall_s':time.perf_counter()-check,'cpu_s':time.process_time()-check_cpu,'bytes':len(restored),'sha256':digest(restored)}
    exclusive(folder/'full-file-ledger.json',canonical({'before':before,'after':after}))
    costs=Counter()
    for path in folder.rglob('*'):
        if path.is_file():
            group=path.relative_to(folder).parts[0]
            costs['memory_bytes' if group=='memory' else 'source_bytes' if group=='source' else 'other_worker_files_bytes']+=path.stat().st_size
    report={'round':args.round,'workload':args.workload,'view':args.view,'meter':args.meter,'cases':rows,
        'source_sha256':digest(raw),'source_bytes':len(raw),'source_records':len(index),'plan_sha256':digest(plan_raw),
        'ingest':ingest,'recovery':recovery,'files':dict(costs),'memory_stats':memory.stats(),
        'memory_tree_unchanged':True,'memory_tree_sha256':digest(canonical(after)),
        'private_hits_sha256':digest((folder/'private-hits.json').read_bytes()),
        'worker_wall_s':time.perf_counter()-began,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'input_fsyncs':1,'plan_fsyncs':1,'private_proof_fsyncs':1,'ledger_fsyncs':1,'internal_memory_fsyncs':None,
        'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,'remote_model_calls':0}
    assert_text_free(report);exclusive(Path(args.worker_report),json.dumps(report,sort_keys=True,indent=2).encode()+b'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('work','out','corpus','worker-report'):p.add_argument('--'+key,required=key in ('work','corpus'))
    p.add_argument('--round',type=int);p.add_argument('--workload',choices=('spread','repeated'))
    p.add_argument('--view',choices=('off','on'));p.add_argument('--meter',choices=('off','on'));args=p.parse_args()
    if args.round:worker(args);return
    raw=Path(args.corpus).read_bytes();assert digest(raw)==SOURCE_SHA and len(raw)==SOURCE_BYTES
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    checks=implementation_checksums();old=json.loads((ROOT/'results/v0.45.0/source-checksums.json').read_text('utf-8'))
    assert set(old)==set(checks) and all(sha==checks[k] for k,sha in old.items() if k!='__init__.py')
    assert (ROOT/'scripts/query_view.py').read_bytes()==subprocess.check_output(['git','show','v0.45.0:scripts/query_view.py'])
    tracked={name:digest((ROOT/name).read_bytes()) for name in TRACKED}
    save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'implementation_checksums':checks,
        'program_protocol_sha256':tracked,'conditions':CONDITIONS,'orders':ORDERS,'worker_timeout_s':600,
        'source_sha256':SOURCE_SHA,'source_bytes':SOURCE_BYTES,'source_records':5183,'rounds':3,'workers':24,
        'scope':'Existing scientific corpus; three explicit known keys, no semantic retrieval/multihop/answers/model calls',
        'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,'remote_model_calls':0})
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n,order in enumerate(ORDERS,1):
        for letter in order:
            workload,view,meter=CONDITIONS[ord(letter)-ord('A')];label=f'round-{n}-{workload}-v{view}-m{meter}';report=out/(label+'.json')
            command=[sys.executable,'-m','scripts.run_science_bundles','--work',str(work/label),'--corpus',str(Path(args.corpus).resolve()),
                '--round',str(n),'--workload',workload,'--view',view,'--meter',meter,'--worker-report',str(report)]
            code=None;error=None
            with (out/(label+'.log')).open('wb') as log:
                began=time.perf_counter()
                try:code=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
                except subprocess.TimeoutExpired:error='TimeoutExpired'
                elapsed=time.perf_counter()-began
            exclusive(out/(label+'-parent.json'),json.dumps({'round':n,'workload':workload,'view':view,'meter':meter,
                'return_code':code,'error':error,'parent_full_process_wall_s':elapsed,
                'child_report_sha256':digest(report.read_bytes()) if report.exists() else None},sort_keys=True,indent=2).encode()+b'\n')
            print(label,'return_code',code,'parent_wall_s',elapsed,flush=True)
    assert checks==implementation_checksums() and tracked=={name:digest((ROOT/name).read_bytes()) for name in TRACKED}


if __name__=='__main__':main()
