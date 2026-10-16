"""Frozen v0.17/v0.18 query comparison on byte-identical retained v3 stores.

No model calls, cross-query caches, mutation, native scanner or new data claims.
"""
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
PLANS=('v017','scoped-eager','scoped-deferred')
STAGES=(0,1,3,9,10)
PROBES=(('probe-note','RKV17NOTE01Q9'),('probe-insert-1','RKV17EDITQ9'),('probe-insert-2','RKV17SECONDINSERTQ9'))
SEED=20261021


def save(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(path):
    rows={p.relative_to(path).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(path.rglob('*')) if p.is_file()}
    return {'files':len(rows),'logical_bytes':sum(r['bytes'] for r in rows.values()),
            'sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()}


def questions(round_index):
    from rkv1.datasets import SCIFACT
    base=ROOT/'data/scifact'
    for name in ('corpus.jsonl','claims_dev.jsonl'):assert sha(base/name)==SCIFACT[name]
    claims=[json.loads(line) for line in (base/'claims_dev.jsonl').read_bytes().splitlines()]
    claims=sorted((c for c in claims if c['evidence']),key=lambda c:c['id'])
    assert len(claims)==188
    result=[(str(c['id']),c['claim']) for c in claims]+list(PROBES)
    random.Random(SEED+round_index).shuffle(result)
    return result


def worker(args):
    from rkv1.benchmark import peak_rss
    from rkv1.controlled import implementation_checksums
    from rkv1.memory import Memory
    import rkv1
    assert rkv1.__version__==('0.17.0' if args.plan=='v017' else '0.18.0')
    if args.plan=='scoped-eager':
        from rkv1 import memory_index
        original=memory_index.view
        @contextmanager
        def eager(memory,value,*,writable=False,query=None,deferred=False):
            with original(memory,value,writable=writable,query=query,deferred=False) as db:
                yield (db,({},set())) if deferred else db
        memory_index.view=eager
    selected=questions(args.round);memory=Memory(args.memory)
    # One explicit, uncounted warmup; each worker is a fresh process.
    memory.search(selected[0][1],snapshot=args.snapshot,top_k=10)
    records=[];started=time.perf_counter();cpu=time.process_time()
    for cid,question in selected:
        before=time.perf_counter();before_cpu=time.process_time()
        found=memory.search(question,snapshot=args.snapshot,top_k=10)
        wall=time.perf_counter()-before;used=time.process_time()-before_cpu
        hits=found['hits']
        identity=[{k:h[k] for k in ('key','title','sentences','locator')} for h in hits]
        records.append({'claim_id':cid,'question_sha256':hashlib.sha256(question.encode()).hexdigest(),
                        'keys':[h['key'] for h in hits],'ranks':[h['rank'] for h in hits],
                        'evidence_identity_sha256':hashlib.sha256(json.dumps(identity,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
                        'wall_s':wall,'cpu_s':used,'reported_internal_wall_s':found['wall_s'],
                        'all_original_records_verified':all(h['source_bytes_verified'] for h in hits)})
    result={'plan':args.plan,'representation':args.representation,'round':args.round,'stage':args.stage,
            'snapshot_id':args.snapshot,'queries':records,'warmup_queries':1,
            'batch_wall_s':time.perf_counter()-started,'batch_cpu_s':time.process_time()-cpu,
            'peak_rss_bytes':peak_rss(),'generation_calls':0,'cross_query_cache':False,
            'native_module_loaded':'rkv1.native' in sys.modules,'implementation_checksums':implementation_checksums()}
    save(args.result,result)


def main(args):
    from rkv1.controlled import implementation_checksums
    from rkv1.memory import Memory
    from scripts.run_memory import append
    candidate=implementation_checksums();questions(0)
    reference=args.reference.resolve();expected=json.loads((ROOT/'results/v0.17.0/source-checksums.json').read_text('utf-8'))
    assert {p.relative_to(reference/'rkv1').as_posix():sha(p) for p in sorted((reference/'rkv1').rglob('*.py'))}==expected
    args.out.mkdir();args.work.mkdir()
    save(args.out/'source-checksums.json',candidate);save(args.out/'reference-checksums.json',expected)
    resource={}
    for plan,base in [('v017',reference),('v018',ROOT)]:
        files={name:{'bytes':(base/name).stat().st_size,'sha256':sha(base/name)} for name in ('rkv1/memory.py','rkv1/memory_index.py')}
        resource[plan]={'files':files,'total_bytes':sum(v['bytes'] for v in files.values())}
    save(args.out/'source-resource.json',{'implementations':resource,'allocation':'Two complete query source modules once; common Store/core/Python/SQLite/OS excluded; no query native library'})
    fixtures={}
    fixture_root=args.fixtures.resolve()
    for representation,case in [('fixed','fixed-v3'),('gear','gear-rust-v3')]:
        trial=json.loads((fixture_root/('0-'+case+'.json')).read_text('utf-8'))
        path=fixture_root/('0-'+case)/'memory'
        fixtures[representation]={'root':str(path),'inventory_before':tree(path),'stages':[
            {'index':s['index'],'stage':s['stage'],'snapshot_id':s['build']['snapshot_id'],'source_truth':s['source_truth']}
            for s in trial['stages']]}
    save(args.out/'fixture-provenance.json',fixtures)
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,
         'logical_cpus':os.cpu_count(),'rounds':3,'measured_stages':list(STAGES),'plans':list(PLANS),'seed':SEED,
         'scope':'Same host, warm filesystem cache, fresh query process per plan/representation/stage/round; peak RSS includes interpreter/input loading',
         'generation_calls':0,'cold_cache':None,'cross_machine':None,'new_scientific_claims':0})
    trials=[]
    for round_index in range(3):
        order=[(r,n,p) for r in fixtures for n in STAGES for p in PLANS]
        random.Random(SEED+round_index).shuffle(order)
        for representation,stage,plan in order:
            entry=fixtures[representation];sid=entry['stages'][stage]['snapshot_id']
            path=args.work/f'{round_index}-{representation}-{stage}-{plan}.json'
            env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
            env['PYTHONPATH']=os.pathsep.join([str(reference if plan=='v017' else ROOT),str(ROOT)])
            start=time.perf_counter()
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker','--memory',entry['root'],
                            '--snapshot',sid,'--stage',str(stage),'--plan',plan,'--representation',representation,
                            '--round',str(round_index),'--result',str(path.resolve())],cwd=args.work,env=env,check=True)
            process_wall=time.perf_counter()-start
            result=json.loads(path.read_text('utf-8'));result['process_wall_including_startup_s']=process_wall
            assert result['implementation_checksums']==(expected if plan=='v017' else candidate)
            assert not result['native_module_loaded']
            trials.append(result);append(args.out/'trials.jsonl',result)
            print(round_index,representation,stage,plan,round(result['batch_wall_s'],3),flush=True)
    historical=0
    for representation,entry in fixtures.items():
        path=Path(entry['root']);assert tree(path)==entry['inventory_before']
        memory=Memory(path)
        for stage in entry['stages']:
            with memory.store.snapshot(stage['snapshot_id']) as snap:
                assert set(snap.files)==set(stage['source_truth'])
                for name,truth in stage['source_truth'].items():
                    raw=snap.read_range(name);assert len(raw)==truth['bytes'] and hashlib.sha256(raw).hexdigest()==truth['sha256']
            historical+=1
    assert implementation_checksums()==candidate
    save(args.out/'trials.json',{'trials':trials,'historical_snapshots_fully_reopened':historical,
         'all_persistent_fixture_files_unchanged':True,'generation_calls':0})


if __name__=='__main__':
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--out',type=Path);p.add_argument('--work',type=Path)
    p.add_argument('--reference',type=Path);p.add_argument('--fixtures',type=Path)
    p.add_argument('--memory',type=Path);p.add_argument('--snapshot');p.add_argument('--stage',type=int)
    p.add_argument('--plan',choices=PLANS);p.add_argument('--representation',choices=('fixed','gear'));p.add_argument('--round',type=int);p.add_argument('--result',type=Path)
    args=p.parse_args()
    if args.worker:worker(args)
    else:main(args)
