"""Frozen replay-budget policy ablation; no model calls or cross-query cache."""
import argparse
import copy
import json
import os
from pathlib import Path
import platform
import random
import sqlite3
import subprocess
import sys
import time

from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest,files_in
from rkv1.memory import Memory,_json
from rkv1.memory_budget import DEFAULT_BUDGET
from rkv1.native import load_native_gear
from scripts.run_memory import append
from scripts.run_memory_history import Stress,LONG_QUERY_STAGES,LONG_QUESTIONS,inventory,query_record
from scripts.run_units import save

SEED=20261024
CASES=('regression-gear','regression-fixed','large-record','cas-amplification')
PLANS=('rebuild','legacy','count-only','bounded')
SMALL_QUESTIONS=[('target-'+str(i),q) for i,q in enumerate(('calibration','marker','token0000','token0001','token0002','token0003',
    'token0017','token0031','token0063','xalibration','absentword','token0050'))]
COUNT_ONLY={**DEFAULT_BUDGET,'max_record_bytes':64<<20,'max_cas_bytes':1<<30}


def clean_env():return {k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}


def questions(case,round_index):
    values=LONG_QUESTIONS[:] if case.startswith('regression') else SMALL_QUESTIONS[:]
    random.Random(SEED+round_index).shuffle(values);return values


def storage_mode(case):
    return ('fixed',65536,'python') if case=='regression-fixed' else ('fixed',1<<20,'python') if case=='cas-amplification' else ('gear-v1',65536,'rust')


class Target:
    def __init__(self,case):
        if case=='large-record':
            self.original=[{'doc_id':i,'title':f'Calibration record {i:04d}',
                'abstract':[(f'marker token{i:04d} '+'calibration evidence '*6000)[:96<<10]]} for i in range(64)]
        else:
            rng=random.Random(SEED)
            self.original=[{'doc_id':i,'title':f'Calibration record {i:04d}',
                'abstract':[f'marker token{i:04d} '+''.join(rng.choices('abcdefghijklmnopqrstuvwxyz ',k=320))]} for i in range(4096)]
        self.docs=copy.deepcopy(self.original)

    def write(self,source,n):
        if n==4:self.docs=copy.deepcopy(self.original)
        elif n:self.docs[n]['title']='X'+self.docs[n]['title'][1:]
        (source/'control.jsonl').write_bytes(b''.join(_json(d)+b'\r\n' for d in self.docs))


def query(args):
    memory=Memory(args.memory);jobs=questions(args.case,args.round)
    memory.search(jobs[0][1],snapshot=args.snapshot,top_k=10)
    found=[query_record(memory,args.snapshot,cid,q) for cid,q in jobs]
    save(args.result,{'queries':found,'warmup_queries':1,'peak_rss_bytes':peak_rss(),'generation_calls':0})


def worker(args):
    args.work.mkdir();source=args.work/'source';source.mkdir()
    chunker,size,backend=storage_mode(args.case)
    profile='compact-full-v2' if args.plan=='rebuild' else 'compact-base-v3' if args.plan=='legacy' else 'compact-budget-v3'
    limits=COUNT_ONLY if args.plan=='count-only' else None
    m=Memory.create(args.work/'memory',index_profile=profile,chunker=chunker,chunk_size=size,replay_budget=limits)
    regression=args.case.startswith('regression');control=Stress() if regression else Target(args.case)
    reference=None
    if args.case=='regression-gear' and args.plan in ('legacy','rebuild'):
        data=json.loads(Path('results/v0.19.0/trials.json').read_text('utf-8'))
        old='incremental' if args.plan=='legacy' else 'rebuild'
        reference=next(t for t in data['trials'] if t['campaign']=='stress' and t['round']==0 and t['profile']==old)
    stages=[];history=[];first=None
    for n in range(101 if regression else 5):
        control.write(source,n)
        truth={name:{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p,name in files_in(source)}
        start=time.perf_counter();cpu=time.process_time()
        label=f'v019-stress-{n:03d}' if regression else f'v020-{args.case}-{n:03d}'
        built=m.add(source,label=label,chunker_backend=backend,native_library=args.native_library if backend=='rust' else None)
        wall=time.perf_counter()-start;cpu=time.process_time()-cpu;sid=built['snapshot_id']
        if first is None:first=sid
        history.append((sid,truth))
        with m.store.snapshot(sid) as snap:
            assert set(snap.files)==set(truth)
            for name in truth:assert snap.read_range(name)==(source/name).read_bytes()
        before=inventory(m.root);stats=m.stats();result=None;process_wall=None
        if not regression or n in LONG_QUERY_STAGES:
            path=args.work/f'{n}-queries.json';start=time.perf_counter()
            subprocess.run([sys.executable,'-m','scripts.run_replay_budget','--query','--case',args.case,'--round',str(args.round),
                '--memory',str(m.root),'--snapshot',sid,'--result',str(path)],env=clean_env(),check=True)
            process_wall=time.perf_counter()-start;result=json.loads(path.read_text('utf-8'))
        old=[query_record(m,first,cid,q) for cid,q in questions(args.case,0)[:4]]
        absent=not m.search('RKV19SHIFTQ9' if regression else 'xalibration',snapshot=first)['hits'];assert absent
        assert inventory(m.root)==before
        value=m._manifest(sid);checkpoint=value['base_snapshot_id']==sid
        if reference is not None:
            expected=reference['stages'][n]
            assert truth==expected['source_truth'] and sid==expected['build']['snapshot_id']
            assert before==expected['tree'],(n,before,expected['tree'])
        if args.plan in ('bounded','count-only'):
            if regression and n==42:assert checkpoint and built['checkpoint_reason']=='budget-changes'
            if not regression and n in (1,2):
                if n==1:assert not checkpoint
                elif args.plan=='bounded':
                    assert checkpoint and built['checkpoint_reason']==('budget-record-bytes' if args.case=='large-record' else 'budget-cas-bytes')
                else:assert not checkpoint
        stages.append({'index':n,'build':built,'build_wall_s':wall,'build_cpu_s':cpu,'checkpoint':checkpoint,
            'source_truth':truth,'full_current_source_bytewise_verified':True,'storage':stats,'tree':before,'query':result,
            'query_process_wall_including_startup_s':process_wall,'old_snapshot_queries':old,'original_future_probe_absent':absent})
        print(args.case,args.plan,args.round,n,stats['logical_file_bytes'],built.get('checkpoint_reason'),flush=True)
    for sid,truth in history:
        with m.store.snapshot(sid) as snap:
            assert set(snap.files)==set(truth)
            for name,meta in truth.items():
                raw=snap.read_range(name);assert len(raw)==meta['bytes'] and digest(raw)==meta['sha256']
    save(args.result,{'case':args.case,'plan':args.plan,'round':args.round,'storage_mode':{'chunker':chunker,'chunk_size':size,'backend':backend},
        'stages':stages,'all_historical_snapshots_full_source_verified':True,'legacy_persistent_bytes_match_v019':reference is not None,
        'final_CAS_tree':inventory(m.root/'cas'),'build_process_peak_rss_bytes':peak_rss(),'generation_calls':0})


def main(args):
    checks=implementation_checksums();args.out.mkdir();args.work.mkdir()
    library=args.native_library.resolve();load_native_gear(str(library));meta=library.with_name('native.json')
    native={'bytes':library.stat().st_size,'sha256':digest(library.read_bytes()),'metadata_bytes':meta.stat().st_size,
            'metadata_sha256':digest(meta.read_bytes()),'metadata':json.loads(meta.read_text('utf-8'))}
    paths=sorted(Path('rkv1').rglob('*.py'))+[Path('rkv1/memory_demo.html')]
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in paths}
    save(args.out/'source-checksums.json',checks);save(args.out/'native-resource.json',native)
    save(args.out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
         'scope':'All RKV Python source modules and packaged HTML once in every condition; Gear cases additionally charge entire measured DLL/metadata; fixed cases no native dependency; Python/SQLite/OS, pyc and installation metadata excluded'})
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,'rounds':3,
        'logical_cpus':os.cpu_count(),'seed':SEED,'default_limits':DEFAULT_BUDGET,'count_only_limits':COUNT_ONLY,'generation_calls':0,
        'scope':'Same-source writer-policy comparison, not whole-version performance; synthetic controls only; local warm cache',
        'cold_cache':None,'cross_machine':None,'new_model_quality':None})
    trials=[]
    for n in range(3):
        order=[(case,plan) for case in CASES for plan in PLANS];random.Random(SEED+n).shuffle(order)
        for case,plan in order:
            work=args.work/f'{n}-{case}-{plan}';path=args.work/f'{n}-{case}-{plan}.json'
            subprocess.run([sys.executable,'-m','scripts.run_replay_budget','--worker','--case',case,'--plan',plan,'--round',str(n),
                '--work',str(work),'--result',str(path),'--native-library',str(library)],env=clean_env(),check=True)
            trial=json.loads(path.read_text('utf-8'));trials.append(trial);append(args.out/'trials.jsonl',trial)
    assert checks==implementation_checksums() and digest(library.read_bytes())==native['sha256'] and digest(meta.read_bytes())==native['metadata_sha256']
    save(args.out/'trials.json',{'trials':trials,'rounds':3,'generation_calls':0})


if __name__=='__main__':
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--work',type=Path);p.add_argument('--native-library',type=Path)
    p.add_argument('--worker',action='store_true');p.add_argument('--query',action='store_true');p.add_argument('--case',choices=CASES);p.add_argument('--plan',choices=PLANS)
    p.add_argument('--round',type=int);p.add_argument('--memory',type=Path);p.add_argument('--snapshot');p.add_argument('--result',type=Path)
    a=p.parse_args()
    if a.query:query(a)
    elif a.worker:worker(a)
    else:main(a)
