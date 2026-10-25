"""First independent eLife正文 revision baseline; whole original XML records."""
import argparse
import json
import os
from pathlib import Path
import platform
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request

from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest,files_in
from rkv1.memory import Memory,records,STOP,_json
from rkv1.memory_projection import fingerprint
from rkv1.native import load_native_gear
from scripts.run_memory import append
from scripts.run_memory_history import inventory,query_record,clean_env
from scripts.run_units import save

ROOT=Path(__file__).resolve().parents[1]
PLANS={'rebuild':'compact-full-v2','budget-v3':'compact-budget-v3','projection-v4':'compact-projection-v4'}
CASES=('fixed','gear');SEED=20261025


def inputs(fetch=False):
    manifest=json.loads((ROOT/'docs/elife-revisions-inputs.json').read_text('utf-8'))
    for paper in manifest['papers']:
        for v in paper['versions']:
            path=ROOT/'data/elife-revisions'/v['path']
            if fetch and not path.exists():
                path.parent.mkdir(parents=True,exist_ok=True)
                with urllib.request.urlopen(v['url'],timeout=30) as response:raw=response.read((1<<20)+1)
                assert len(raw)==v['size'] and digest(raw)==v['sha256']
                with path.open('xb') as f:f.write(raw)
            raw=path.read_bytes();assert len(raw)==v['size'] and digest(raw)==v['sha256']
    return manifest


def questions(round_index):
    result=[]
    for paper in inputs()['papers']:
        previous=None
        for v in paper['versions']:
            row,=records(v['path'],(ROOT/'data/elife-revisions'/v['path']).read_bytes())
            if previous is None:text=row[1];label='title'
            else:
                text=next((p for i,p in enumerate(row[2]) if i>=len(previous[2]) or p!=previous[2][i]),row[1]);label='revision-'+str(v['version'])
            tokens=list(dict.fromkeys(t.lower() for t in re.findall(r'[A-Za-z]{4,}',text) if t.lower() not in STOP))[:8]
            assert tokens;result.append(('elife:'+paper['id']+':'+label,' '.join(tokens)));previous=row
    assert len(result)==18;random.Random(SEED+round_index).shuffle(result);return result


def schedule():
    papers=inputs()['papers'];states=[[(p['id'],1) for p in papers]]
    for version in (2,3):
        for paper in papers:
            current=dict(states[-1]);current[paper['id']]=version;states.append(list(current.items()))
    return states


def query(args):
    m=Memory(args.memory);jobs=questions(args.round);m.search(jobs[0][1],snapshot=args.snapshot,top_k=10)
    rows=[query_record(m,args.snapshot,cid,q) for cid,q in jobs]
    save(args.result,{'queries':rows,'warmup_queries':1,'peak_rss_bytes':peak_rss(),'generation_calls':0})


def worker(args):
    args.work.mkdir();source=args.work/'source';source.mkdir();manifest=inputs()
    versions={(p['id'],v['version']):v for p in manifest['papers'] for v in p['versions']}
    m=Memory.create(args.work/'memory',index_profile=PLANS[args.plan],chunker='gear-v1' if args.case=='gear' else 'fixed')
    stages=[];history=[];first=None
    for n,state in enumerate(schedule()):
        wanted={versions[id,v]['path'] for id,v in state}
        for p in source.iterdir():
            if p.name not in wanted:p.unlink()
        for name in wanted:
            if not (source/name).exists():shutil.copyfile(ROOT/'data/elife-revisions'/name,source/name)
        truth={name:{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p,name in files_in(source)}
        start=time.perf_counter();cpu=time.process_time()
        built=m.add(source,label=f'v023-elife-{n:02d}',chunker_backend='rust' if args.case=='gear' else 'python',native_library=args.native_library if args.case=='gear' else None)
        wall=time.perf_counter()-start;cpu=time.process_time()-cpu;sid=built['snapshot_id'];first=first or sid;history.append((sid,truth))
        with m.store.snapshot(sid) as snap:
            for name in truth:assert snap.read_range(name)==(source/name).read_bytes()
        before=inventory(m.root);stats=m.stats();path=args.work/f'{n}-queries.json';start=time.perf_counter()
        subprocess.run([sys.executable,'-m','scripts.run_paper_revisions','--query','--memory',str(m.root),'--snapshot',sid,'--round',str(args.round),'--result',str(path)],env=clean_env(),check=True)
        process_wall=time.perf_counter()-start;found=json.loads(path.read_text('utf-8'))
        old=[query_record(m,first,cid,q) for cid,q in questions(0)[:4]]
        assert not m.search('RKV23NEVERAPPEARQ9',snapshot=first)['hits'];assert inventory(m.root)==before
        value=m._manifest(sid);checkpoint=value['base_snapshot_id']==sid
        assert checkpoint  # all actual changed whole-file pairs exceed 256 KiB
        if n and args.plan!='rebuild':assert built['checkpoint_reason']=='budget-record-bytes'
        stages.append({'index':n,'build':built,'build_wall_s':wall,'build_cpu_s':cpu,'checkpoint':checkpoint,'storage':stats,'tree':before,
                       'source_truth':truth,'full_current_source_bytewise_verified':True,'query':found,'query_process_wall_including_startup_s':process_wall,
                       'old_snapshot_queries':old,'negative_control_absent':True})
        print(args.case,args.plan,args.round,n,stats['logical_file_bytes'],built['checkpoint_reason'],flush=True)
    for sid,truth in history:
        with m.store.snapshot(sid) as snap:
            assert set(snap.files)==set(truth)
            for name,v in truth.items():
                raw=snap.read_range(name);assert len(raw)==v['bytes'] and digest(raw)==v['sha256']
    save(args.result,{'case':args.case,'plan':args.plan,'round':args.round,'stages':stages,'all_historical_snapshots_full_source_verified':True,
                     'final_CAS_tree':inventory(m.root/'cas'),'build_process_peak_rss_bytes':peak_rss(),'generation_calls':0})


def main(args):
    manifest=inputs(args.fetch);checks=implementation_checksums();args.out.mkdir();args.work.mkdir()
    library=args.native_library.resolve();load_native_gear(str(library));meta=library.with_name('native.json')
    native={'bytes':library.stat().st_size,'sha256':digest(library.read_bytes()),'metadata_bytes':meta.stat().st_size,'metadata_sha256':digest(meta.read_bytes()),'metadata':json.loads(meta.read_text('utf-8'))}
    save(args.out/'source-checksums.json',checks);save(args.out/'native-resource.json',native)
    paths=sorted(Path('rkv1').rglob('*.py'))+[Path('rkv1/memory_demo.html')]
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in paths}
    save(args.out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),'scope':'All RKV Python/HTML once in every condition; Gear adds entire exact native library/metadata; common runtime/pyc/install/filesystem metadata excluded'})
    changes=[]
    for paper in manifest['papers']:
        prior=None
        for v in paper['versions']:
            row,=records(v['path'],(ROOT/'data/elife-revisions'/v['path']).read_bytes());sha=fingerprint(row[1],row[2])
            changes.append({'paper_id':paper['id'],'version':v['version'],'original_bytes':v['size'],'paragraphs':len(row[2]),'projection_sha256':sha,
                'projection_changed':None if prior is None else prior[0]!=sha,'old_plus_new_record_bytes':None if prior is None else prior[1]+v['size']})
            prior=sha,v['size']
    save(args.out/'dataset-provenance.json',{'inputs':manifest,'changes':changes,'states':schedule(),'query_count':18,
        'query_rule':'Six initial-title + twelve first-changed-paragraph queries: first eight unique ASCII alphabetic length>=4 non-stop tokens; generated retrieval diagnostics, not human QA labels'})
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,'rounds':3,'logical_cpus':os.cpu_count(),'seed':SEED,
        'generation_calls':0,'new_scientific_QA_questions':0,'new_independent_papers':6,'real_revision_transitions':12,'cold_cache':None,'cross_machine':None,
        'scope':'Six eLife reviewed preprints with actual body projection changes, staggered version updates; whole XML record granularity; one warm-cache host'})
    trials=[]
    for r in range(3):
        order=[(c,p) for c in CASES for p in PLANS];random.Random(SEED+r).shuffle(order)
        for case,plan in order:
            work=args.work/f'{r}-{case}-{plan}';path=args.work/f'{r}-{case}-{plan}.json'
            subprocess.run([sys.executable,'-m','scripts.run_paper_revisions','--worker','--case',case,'--plan',plan,'--round',str(r),'--work',str(work),'--result',str(path),'--native-library',str(library)],env=clean_env(),check=True)
            trial=json.loads(path.read_text('utf-8'));trials.append(trial);append(args.out/'trials.jsonl',trial)
    assert checks==implementation_checksums() and digest(library.read_bytes())==native['sha256']
    save(args.out/'trials.json',{'trials':trials,'rounds':3,'generation_calls':0})


if __name__=='__main__':
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--work',type=Path);p.add_argument('--native-library',type=Path);p.add_argument('--fetch',action='store_true')
    p.add_argument('--worker',action='store_true');p.add_argument('--query',action='store_true');p.add_argument('--case',choices=CASES);p.add_argument('--plan',choices=PLANS)
    p.add_argument('--round',type=int);p.add_argument('--memory',type=Path);p.add_argument('--snapshot');p.add_argument('--result',type=Path)
    a=p.parse_args()
    if a.query:query(a)
    elif a.worker:worker(a)
    else:main(a)
