"""Read-only v0.21/v0.22 query comparison on exact retained v3/v4 stores."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import sqlite3
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
PLANS=('v021','lazy-copy','lazy-direct','budget-v3')
CASES=('official-gear','official-fixed','synthetic-fixed')
SEED=20261024


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(args):
    import rkv1
    from rkv1.benchmark import peak_rss
    from rkv1.controlled import implementation_checksums
    from rkv1.core import digest,files_in
    from rkv1.memory import Memory,_json
    assert rkv1.__version__==('0.21.0' if args.plan=='v021' else '0.22.0')
    if args.plan=='lazy-copy':
        from rkv1 import memory_projection
        original=memory_projection.view
        @contextmanager
        def forced_copy(memory,value,**kwargs):
            with original(memory,value,copy_base=bool(value['deltas']),**kwargs) as result:yield result
        memory_projection.view=forced_copy
    def inventory(path):
        items={name:{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p,name in files_in(path)}
        return {'files':len(items),'bytes':sum(v['bytes'] for v in items.values()),'sha256':digest(_json(items))}
    def record(m,sid,cid,question):
        before=time.perf_counter();cpu=time.process_time();found=m.search(question,snapshot=sid,top_k=10)
        wall=time.perf_counter()-before;cpu=time.process_time()-cpu;hits=found['hits']
        identity=[{k:h[k] for k in ('key','title','sentences','locator')} for h in hits]
        return {'query_id':cid,'question_sha256':digest(question.encode()),'keys':[h['key'] for h in hits],'ranks':[h['rank'] for h in hits],
                'evidence_identity_sha256':digest(_json(identity)),'all_original_records_verified':all(h['source_bytes_verified'] for h in hits),
                'wall_s':wall,'cpu_s':cpu,'source_paper_hit5':cid in [h['key'] for h in hits[:5]] if cid.startswith('qasper:') else None}
    jobs=json.loads(args.jobs.read_text('utf-8'));m=Memory(args.memory);before=inventory(m.root)
    m.search(jobs['formal'][0][1],snapshot=args.snapshot,top_k=10)
    start=time.perf_counter();cpu=time.process_time()
    rows=[record(m,args.snapshot,cid,q) for cid,q in jobs['formal']]
    batch_wall=time.perf_counter()-start;batch_cpu=time.process_time()-cpu
    old=[record(m,args.first,cid,q) for cid,q in jobs['history']]
    absent=None if args.case.startswith('official') else not m.search('TRUEBODYQ21 TRUETITLEQ21 ADDEDPAPERQ21',snapshot=args.first)['hits']
    if absent is not None:assert absent
    after=inventory(m.root);assert before==after
    save(args.result,{'case':args.case,'plan':args.plan,'round':args.round,'stage':args.stage,'snapshot_id':args.snapshot,
         'queries':rows,'historical_queries':old,'warmup_queries':1,'original_future_probe_absent':absent,
         'batch_wall_s':batch_wall,'batch_cpu_s':batch_cpu,'peak_rss_bytes':peak_rss(),'tree_before':before,'tree_after':after,
         'generation_calls':0,'cross_query_cache':False,'native_module_loaded':'rkv1.native' in sys.modules,'implementation_checksums':implementation_checksums()})


def main(args):
    from rkv1.controlled import implementation_checksums
    from rkv1.memory import Memory
    from scripts.run_memory_history import inventory
    from scripts.run_memory_projection import questions
    from scripts.run_memory import append
    candidate=implementation_checksums();reference=args.reference.resolve();old=json.loads((ROOT/'results/v0.21.0/source-checksums.json').read_text('utf-8'))
    assert {p.relative_to(reference/'rkv1').as_posix():sha(p) for p in sorted((reference/'rkv1').rglob('*.py'))}==old
    args.out.mkdir();args.work.mkdir();save(args.out/'source-checksums.json',candidate);save(args.out/'reference-checksums.json',old)
    resource={}
    for label,base in (('v021',reference),('v022',ROOT)):
        paths=sorted((base/'rkv1').rglob('*.py'))+[base/'rkv1/memory_demo.html']
        files={p.relative_to(base).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths}
        resource[label]={'files':files,'total_bytes':sum(v['bytes'] for v in files.values())}
    save(args.out/'source-resource.json',{'implementations':resource,'scope':'All RKV Python and HTML once for each actual reader; lazy plans/v3 share current allocation, Gear retains entire fixture-generation DLL/metadata once; no native query work; common runtime/pyc/install/filesystem metadata excluded'})
    native=json.loads((ROOT/'results/v0.21.0/native-resource.json').read_text('utf-8'))
    assert sha(args.native_library)==native['sha256'] and sha(args.native_library.with_name('native.json'))==native['metadata_sha256']
    save(args.out/'native-resource.json',native)
    prior=json.loads((ROOT/'results/v0.21.0/trials.json').read_text('utf-8'))['trials'];fixtures={}
    for case in CASES:
        fixtures[case]={}
        for kind in ('projection-v4','budget-v3'):
            t=next(t for t in prior if t['case']==case and t['plan']==kind and t['round']==0)
            path=args.fixtures.resolve()/f'0-{case}-{kind}'/'memory';tree=inventory(path)
            assert tree==t['stages'][-1]['tree']
            fixtures[case][kind]={'root':str(path),'tree':tree,'logical_file_bytes':t['stages'][-1]['storage']['logical_file_bytes'],
                'stages':[{'index':s['index'],'snapshot_id':s['build']['snapshot_id'],'source_truth':s['source_truth']} for s in t['stages']]}
    save(args.out/'fixture-provenance.json',fixtures)
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,'logical_cpus':os.cpu_count(),
         'rounds':3,'plans':list(PLANS),'seed':SEED,'generation_calls':0,'new_scientific_questions':0,'cold_cache':None,'cross_machine':None,
         'scope':'Same retained v0.21 roots, no commits; fresh query worker per case/stage/plan/round; one warmup; identical small prepared question jobs in all readers; warm cache on one host'})
    for case in CASES:
        for r in range(3):save(args.work/f'{case}-{r}-jobs.json',{'formal':questions(case,r),'history':questions(case,0)[:4]})
    trials=[]
    for r in range(3):
        order=[(c,s['index'],p) for c in CASES for s in fixtures[c]['projection-v4']['stages'] for p in PLANS];random.Random(SEED+r).shuffle(order)
        for case,n,plan in order:
            fixture=fixtures[case]['budget-v3' if plan=='budget-v3' else 'projection-v4'];stage=fixture['stages'][n]
            target=args.work/f'{r}-{case}-{n}-{plan}.json';env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
            env['PYTHONPATH']=os.pathsep.join([str(reference if plan=='v021' else ROOT),str(ROOT)])
            before=time.perf_counter()
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker','--memory',fixture['root'],'--snapshot',stage['snapshot_id'],
                '--first',fixture['stages'][0]['snapshot_id'],'--stage',str(n),'--plan',plan,'--case',case,'--round',str(r),
                '--jobs',str((args.work/f'{case}-{r}-jobs.json').resolve()),'--result',str(target.resolve())],cwd=args.work,env=env,check=True)
            process_wall=time.perf_counter()-before;result=json.loads(target.read_text('utf-8'));result['process_wall_including_startup_s']=process_wall
            assert result['implementation_checksums']==(old if plan=='v021' else candidate)
            assert result['tree_before']==result['tree_after']==fixture['tree'] and not result['native_module_loaded']
            trials.append(result);append(args.out/'trials.jsonl',result)
            print(r,case,n,plan,round(result['batch_wall_s'],3),flush=True)
    reopened=0
    for variants in fixtures.values():
        for fixture in variants.values():
            m=Memory(fixture['root']);assert inventory(m.root)==fixture['tree']
            for stage in fixture['stages']:
                with m.store.snapshot(stage['snapshot_id']) as snap:
                    assert set(snap.files)==set(stage['source_truth'])
                    for name,expected in stage['source_truth'].items():
                        raw=snap.read_range(name);assert len(raw)==expected['bytes'] and hashlib.sha256(raw).hexdigest()==expected['sha256']
                reopened+=1
    assert candidate==implementation_checksums() and sha(args.native_library)==native['sha256']
    save(args.out/'trials.json',{'trials':trials,'historical_snapshot_instances_fully_reopened':reopened,'all_persistent_fixture_files_unchanged':True,'generation_calls':0})


if __name__=='__main__':
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--out',type=Path);p.add_argument('--work',type=Path)
    p.add_argument('--reference',type=Path);p.add_argument('--fixtures',type=Path);p.add_argument('--native-library',type=Path)
    p.add_argument('--memory',type=Path);p.add_argument('--snapshot');p.add_argument('--first');p.add_argument('--stage',type=int)
    p.add_argument('--plan',choices=PLANS);p.add_argument('--case',choices=CASES);p.add_argument('--round',type=int);p.add_argument('--jobs',type=Path);p.add_argument('--result',type=Path)
    a=p.parse_args()
    if a.worker:worker(a)
    else:main(a)
