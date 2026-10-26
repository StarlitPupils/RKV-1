"""Opt-in public batch API mechanical acceptance, known synthetic sources only."""
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
from rkv1.memory import Memory
from scripts.cas_traffic import CASTraffic
from scripts.path_layout_fixture import sources,identity
from scripts.run_memory_concurrency import save

ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/run_batch_api.py','scripts/analyze_batch_api.py','scripts/path_layout_fixture.py','scripts/evidence_path_fixture.py',
         'scripts/cas_traffic.py','scripts/run_memory_concurrency.py','docs/BATCH-LOOKUP.md','docs/path-layout-inputs.json','tests/test_memory_batch.py')


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')


def exclusive(path,raw):
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())


def ledger(folder):
    return {p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
            for p in sorted(folder.rglob('*')) if p.is_file()}


def original_index(epoch,layout):
    result={}
    for name,raw in sources(epoch,layout).items():
        offset=0
        for line in raw.splitlines(keepends=True):
            obj=json.loads(line);key='doc:'+str(obj['doc_id']);assert key not in result
            result[key]=(name,offset,line,obj);offset+=len(line)
    return result


def audit(memory,result,keys,sid,index):
    assert result['snapshot_id']==sid and result['scope']=='explicit-known-source-batch'
    assert [r['source_key'] for r in result['results']]==list(keys)
    count=admitted=0
    with memory.store.snapshot(sid) as snap:
        for key,group in zip(keys,result['results']):
            hits=group['hits']
            if key not in index:assert hits==[];continue
            name,offset,line,obj=index[key]
            expected={'citation_id':'D0','key':key,'title':obj['title'],'sentences':obj['abstract'],
                      'rank':None,'source_bytes_verified':True,'locator':{'snapshot_id':sid,'path':name,
                      'offset':offset,'length':len(line),'sha256':digest(line)}}
            assert hits==[expected] and snap.read_range(name,offset,len(line))==line
            count+=1;admitted+=len(line)
    assert result['admitted_source_bytes']==admitted<=result['max_source_bytes']
    return count


def worker(args):
    began=time.perf_counter();cpu=time.process_time();folder=Path(args.work);folder.mkdir(exist_ok=False)
    src=folder/'source';src.mkdir();memory=Memory.create(folder/'memory');snapshots=[];ingests=[]
    manifest=json.loads((ROOT/'docs/path-layout-inputs.json').read_text('utf-8'))
    for epoch in range(3):
        assert identity(epoch,args.layout)==manifest['layouts'][args.layout]['epochs'][epoch]
        for name,raw in sources(epoch,args.layout).items():(src/name).write_bytes(raw)
        start=time.perf_counter();start_cpu=time.process_time();commit=memory.add(src)
        snapshots.append(commit['snapshot_id']);ingests.append({'epoch':epoch,'commit':commit,'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-start_cpu})
    before=ledger(memory.root);head=memory.current();cases=[];baseline_wall=baseline_cpu=0
    def execute(case_id,epoch,keys,budget,expected,reference,primary):
        meter=CASTraffic(memory.store);start=time.perf_counter();start_cpu=time.process_time();result=None;error=None
        with meter:
            try:result=memory.lookup_many(keys,snapshot=snapshots[epoch],max_source_bytes=budget)
            except ValueError as exc:error=str(exc)
        elapsed_cpu=time.process_time()-start_cpu;elapsed=time.perf_counter()-start
        check=time.perf_counter();check_cpu=time.process_time();bindings=0
        if expected=='accepted':
            assert error is None and result is not None
            assert [r['hits'] for r in result['results']]==reference
            bindings=audit(memory,result,keys,snapshots[epoch],original_index(epoch,args.layout))
        else:assert result is None and error=='Batch source-byte budget exceeded'
        cases.append({'case_id':case_id,'primary':primary,'epoch':epoch,'keys':keys,'budget_bytes':budget,
            'expected':expected,'result':result,'error':error,'bindings':bindings,'outcome_gate_pass':True,
            'instrumented_call_wall_s':elapsed,'instrumented_call_cpu_s':elapsed_cpu,
            'audit_wall_s':time.perf_counter()-check,'audit_cpu_s':time.process_time()-check_cpu,'traffic':meter.result()})
    for epoch,sid in enumerate(snapshots):
        for size in (1,3,32):
            keys=['doc:'+str(i) for i in range(size)];start=time.perf_counter();start_cpu=time.process_time()
            reference=[memory.lookup(k,snapshot=sid)['hits'] for k in keys]
            baseline_cpu+=time.process_time()-start_cpu;baseline_wall+=time.perf_counter()-start
            required=sum(h['locator']['length'] for g in reference for h in g)
            for budget,expected in ((required,'accepted'),(required-1,'budget-rejected')):
                execute(f'e{epoch}-n{size}-{expected}',epoch,keys,budget,expected,reference,True)
    keys=['doc:0']*3;start=time.perf_counter();start_cpu=time.process_time()
    reference=[memory.lookup(k,snapshot=snapshots[0])['hits'] for k in keys]
    baseline_cpu+=time.process_time()-start_cpu;baseline_wall+=time.perf_counter()-start
    required=sum(h['locator']['length'] for g in reference for h in g)
    for budget,expected in ((required,'accepted'),(required-1,'budget-rejected')):
        execute('duplicate-'+expected,0,keys,budget,expected,reference,False)
    execute('missing-zero-budget',0,['doc:999999'],0,'accepted',[[]],False)
    recovered=0;recover_wall=time.perf_counter();recover_cpu=time.process_time()
    for epoch,sid in enumerate(snapshots):
        with memory.store.snapshot(sid) as snap:
            expected=sources(epoch,args.layout);assert set(snap.files)==set(expected)
            for name,raw in expected.items():assert snap.read_range(name)==raw;recovered+=1
    recovery={'files':recovered,'wall_s':time.perf_counter()-recover_wall,'cpu_s':time.process_time()-recover_cpu}
    after=ledger(memory.root);assert before==after and memory.current()==head
    exclusive(folder/'full-file-ledger.json',encoded({'before':before,'after':after}))
    costs=Counter()
    for path in folder.rglob('*'):
        if path.is_file():
            group=path.relative_to(folder).parts[0];costs['memory_bytes' if group=='memory' else 'source_current_bytes' if group=='source' else 'other_worker_files_bytes']+=path.stat().st_size
    report={'round':args.round,'layout':args.layout,'ingests':ingests,'cases':cases,'outcome_counts':dict(Counter(c['expected'] for c in cases)),
        'recovery':recovery,'original_lookup_baseline_wall_s':baseline_wall,'original_lookup_baseline_cpu_s':baseline_cpu,
        'memory_tree_unchanged':True,'head_unchanged':True,'memory_tree_sha256':digest(encoded(after)),'files':dict(costs),'memory_stats':memory.stats(),
        'worker_wall_s':time.perf_counter()-began,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'source_write_fsyncs':0,'ledger_fsyncs':1,'internal_memory_fsyncs':None,'new_remote_model_calls':0,
        'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,
        'scope':'Synthetic public API mechanical acceptance with heavy traffic instrument; costs only, no speed/QA/production gain gate'}
    exclusive(Path(args.worker_report),json.dumps(report,sort_keys=True,indent=2).encode()+b'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('work','out','worker-report'):p.add_argument('--'+k,required=k=='work')
    p.add_argument('--round',type=int);p.add_argument('--layout',choices=('clustered','separated'));args=p.parse_args()
    if args.round:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    checks=implementation_checksums();tracked={k:digest((ROOT/k).read_bytes()) for k in TRACKED}
    save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'implementation_checksums':checks,'program_protocol_sha256':tracked,
        'rounds':3,'orders':[['clustered','separated'],['separated','clustered'],['clustered','separated']],'worker_timeout_s':600,
        'scope':'Synthetic opt-in API mechanical contract; no performance gain gate or scientific text','new_remote_model_calls':0})
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n,order in enumerate((('clustered','separated'),('separated','clustered'),('clustered','separated')),1):
        for layout in order:
            label=f'round-{n}-{layout}';report=out/(label+'.json');code=None;error=None
            with (out/(label+'.log')).open('wb') as log:
                began=time.perf_counter()
                try:code=subprocess.run([sys.executable,'-m','scripts.run_batch_api','--work',str(work/label),
                    '--round',str(n),'--layout',layout,'--worker-report',str(report)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
                    timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
                except subprocess.TimeoutExpired:error='TimeoutExpired'
                elapsed=time.perf_counter()-began
            exclusive(out/(label+'-parent.json'),json.dumps({'round':n,'layout':layout,'return_code':code,'error':error,
                'parent_full_process_wall_s':elapsed,'child_report_sha256':digest(report.read_bytes()) if report.exists() else None},sort_keys=True,indent=2).encode()+b'\n')
            print(label,'return_code',code,'parent_wall_s',elapsed,flush=True)
    assert checks==implementation_checksums() and tracked=={k:digest((ROOT/k).read_bytes()) for k in TRACKED}


if __name__=='__main__':main()
