"""Real QASPER releases and a separately labelled 100-update stress control."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import sqlite3
import subprocess
import sys
import time

from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import files_in,digest
from rkv1.memory import Memory,records,_json
from rkv1.memory_index import differences,LOCATORS
from rkv1.native import load_native_gear
from rkv1.version_data import VERSIONS
from scripts.run_memory import append
from scripts.run_units import save

ROOT=Path(__file__).resolve().parents[1]
PROFILES={'rebuild':'compact-full-v2','incremental':'compact-base-v3'}
LONG_QUERY_STAGES=(0,1,40,41,42,43,79,80,100)
SEED=20261022
LONG_QUESTIONS=[(f'control-{i}',q) for i,q in enumerate(('calibration silver','rare variants','token0000','token0017',
    'token0511','token0512','token1024','token2047','RKV19SHIFTQ9','RKV19NOTEQ9','RKV19FRAGMENTQ9','RKV19TAILQ9'))]


def clean_env():return {k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}


def real_inputs():
    result=[]
    for version,expected in VERSIONS.items():
        path=ROOT/'data/qasper-versions'/('v'+version)/f'qasper-dev-v{version}.json'
        raw=path.read_bytes();assert digest(raw)==expected['dev']
        result.append({'version':version,'filename':path.name,'path':str(path),'bytes':len(raw),'sha256':digest(raw)})
    return result


def questions(campaign,round_index):
    if campaign=='qasper':
        first=real_inputs()[0];docs=json.loads(Path(first['path']).read_bytes());selected=[];seen=set()
        for key,doc in sorted(docs.items()):
            eligible=[qa['question'] for qa in doc['qas'] if isinstance(qa.get('question'),str) and qa['question'].strip() and qa['question'] not in seen]
            if eligible:
                question=eligible[0];seen.add(question);selected.append(('qasper:'+key,question))
            if len(selected)==64:break
        assert len(selected)==64
    else:selected=LONG_QUESTIONS[:]
    random.Random(SEED+round_index).shuffle(selected)
    return selected


class Stress:
    def __init__(self):
        rng=random.Random(SEED)
        self.original=[{'doc_id':i,'title':f'Calibration silver record {i:04d}',
            'abstract':[f'rare variants token{i:04d} '+''.join(rng.choices('abcdefghijklmnopqrstuvwxyz ',k=160))]} for i in range(2048)]
        self.docs=copy.deepcopy(self.original);self.base43=None

    def advance(self,n):
        if n in (41,):self.docs=copy.deepcopy(self.original)
        elif n==42:
            for doc in self.docs[:508]:doc['title']='X'+doc['title'][1:]
        elif n==43:
            self.docs[508]['title']='X'+self.docs[508]['title'][1:];self.base43=copy.deepcopy(self.docs)
        elif n==79:self.docs=copy.deepcopy(self.base43)
        elif n==80:
            for i in range(260):self.docs[2*i]['abstract'][0]+=' RKV19FRAGMENTQ9'
        elif n:
            original=(self.original if n<41 else self.base43 if n<80 else None)
            self.docs[0]['abstract'][0]=(original[0]['abstract'][0] if original else self.original[0]['abstract'][0]+' RKV19FRAGMENTQ9')+' RKV19SHIFTQ9 '+str(n)
            self.docs[-1]['abstract'][0]=self.original[-1]['abstract'][0]+' RKV19TAILQ9 '+str(n)

    def write(self,source,n):
        self.advance(n)
        if n in (10,20,30,40):(source/f'note-{n//10}.txt').write_bytes(f'RKV19NOTEQ9 calibration note {n//10}\r\n'.encode())
        (source/'control.jsonl').write_bytes(b''.join(_json(doc)+b'\r\n' for doc in self.docs))


def inventory(root):
    entries={name:{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p,name in files_in(root)}
    return {'files':len(entries),'bytes':sum(e['bytes'] for e in entries.values()),
            'sha256':digest(_json(entries))}


def query_record(m,sid,cid,question):
    start=time.perf_counter();cpu=time.process_time();found=m.search(question,snapshot=sid,top_k=10)
    wall=time.perf_counter()-start;cpu=time.process_time()-cpu;hits=found['hits']
    identity=[{k:h[k] for k in ('key','title','sentences','locator')} for h in hits]
    return {'query_id':cid,'question_sha256':digest(question.encode()),'keys':[h['key'] for h in hits],
            'ranks':[h['rank'] for h in hits],'evidence_identity_sha256':digest(_json(identity)),
            'all_original_records_verified':all(h['source_bytes_verified'] for h in hits),'wall_s':wall,'cpu_s':cpu,
            'source_paper_hit5':cid in [h['key'] for h in hits[:5]] if cid.startswith('qasper:') else None}


def query(args):
    m=Memory(args.memory);jobs=questions(args.campaign,args.round);m.search(jobs[0][1],snapshot=args.snapshot,top_k=10)
    rows=[query_record(m,args.snapshot,cid,q) for cid,q in jobs]
    save(args.result,{'queries':rows,'warmup_queries':1,'peak_rss_bytes':peak_rss(),'generation_calls':0})


def candidate_changes(m,source):
    if not (m.root/'HEAD.json').exists():return None
    value=m._manifest(m.current());base=value['base_snapshot_id']
    db=sqlite3.connect((m.root/'indexes'/(base+'.sqlite')).as_uri()+'?mode=ro',uri=True)
    try:prior={r[0]:list(r) for r in db.execute('SELECT '+LOCATORS+' FROM locators')}
    finally:db.close()
    current={}
    for path,name in files_in(source):
        for key,title,body,offset,raw,kind in records(name,path.read_bytes()):
            current[key]=([key,name,offset,len(raw),digest(raw),kind],title,body)
    removed,upserted,moves=differences(prior,current)
    return {'prior_base_records':len(prior),'nonposition_changes':len(removed)+len(upserted),'relocation_ranges':len(moves),
            'nonposition_limit':max(1,len(prior)//4),'relocation_limit':256,'base_snapshot_id':base}


def worker(args):
    args.work.mkdir();source=args.work/'source';source.mkdir();stress=Stress() if args.campaign=='stress' else None
    releases=real_inputs() if args.campaign=='qasper' else None
    m=Memory.create(args.work/'memory',index_profile=PROFILES[args.profile],chunker='gear-v1')
    stages=[];history=[];first=None;jobs=questions(args.campaign,0)
    for n in range(3 if releases else 101):
        if releases:
            if n:(source/releases[n-1]['filename']).unlink()
            shutil.copyfile(releases[n]['path'],source/releases[n]['filename'])
        else:stress.write(source,n)
        truth={name:{'bytes':path.stat().st_size,'sha256':digest(path.read_bytes())} for path,name in files_in(source)}
        diagnostic=candidate_changes(m,source)  # excluded from commit timing; same work in both profiles
        before=time.perf_counter();cpu=time.process_time()
        built=m.add(source,label=f'v019-{args.campaign}-{n:03d}',chunker_backend='rust',native_library=args.native_library)
        wall=time.perf_counter()-before;cpu=time.process_time()-cpu;sid=built['snapshot_id']
        if first is None:first=sid
        history.append((sid,truth))
        with m.store.snapshot(sid) as snap:
            for name,pathmeta in truth.items():assert snap.read_range(name)==(source/name).read_bytes()
        state=inventory(m.root);stats=m.stats();result=None;process_wall=None
        if releases or n in LONG_QUERY_STAGES:
            target=args.work/(str(n)+'-queries.json');before=time.perf_counter()
            subprocess.run([sys.executable,'-m','scripts.run_memory_history','--query','--campaign',args.campaign,'--round',str(args.round),
                            '--memory',str(m.root),'--snapshot',sid,'--result',str(target)],env=clean_env(),check=True)
            process_wall=time.perf_counter()-before;result=json.loads(target.read_text('utf-8'))
        old=[query_record(m,first,cid,q) for cid,q in jobs[:4]]
        future_probe_absent=None
        if args.campaign=='stress':
            future_probe_absent=not m.search('RKV19SHIFTQ9',snapshot=first)['hits'];assert future_probe_absent
        assert inventory(m.root)==state
        value=m._manifest(sid);checkpoint=value['base_snapshot_id']==sid
        if args.campaign=='stress' and args.profile=='incremental':
            assert checkpoint==(n in (0,43,80)),(n,diagnostic,built)
            if n==42:assert diagnostic['nonposition_changes']==diagnostic['nonposition_limit']==512
            if n==43:assert diagnostic['nonposition_changes']==513
            if n==80:assert diagnostic['relocation_ranges']==260 and diagnostic['nonposition_changes']<=diagnostic['nonposition_limit']
        stages.append({'index':n,'build':built,'build_wall_s':wall,'build_cpu_s':cpu,'pre_commit_candidate':diagnostic,
            'checkpoint':checkpoint,'storage':stats,'tree':state,'source_truth':truth,'full_source_bytewise_verified':True,
            'query':result,'query_process_wall_including_startup_s':process_wall,'old_snapshot_queries':old,
            'original_future_probe_absent':future_probe_absent})
        print(args.campaign,args.profile,args.round,n,stats['logical_file_bytes'],'base' if checkpoint else 'overlay',flush=True)
    for sid,truth in history:
        with m.store.snapshot(sid) as snap:
            assert set(snap.files)==set(truth)
            for name,expected in truth.items():
                raw=snap.read_range(name);assert len(raw)==expected['bytes'] and digest(raw)==expected['sha256']
    save(args.result,{'campaign':args.campaign,'profile':args.profile,'round':args.round,'stages':stages,
        'all_historical_snapshots_fully_reopened':True,'generation_calls':0,'build_process_peak_rss_bytes':peak_rss(),
        'final_CAS_tree':inventory(m.root/'cas')})


def main(args):
    inputs=real_inputs();checks=implementation_checksums();args.out.mkdir();args.work.mkdir()
    library=args.native_library.resolve();load_native_gear(str(library));metadata=library.with_name('native.json')
    save(args.out/'source-checksums.json',checks)
    files={name:{'bytes':Path(name).stat().st_size,'sha256':digest(Path(name).read_bytes())} for name in
           ('rkv1/memory.py','rkv1/memory_index.py','rkv1/memory_qasper.py','rkv1/chunking.py')}
    save(args.out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
         'scope':'Four complete source modules once in each condition; common Store/core/Python/SQLite/OS excluded'})
    native={'bytes':library.stat().st_size,'sha256':digest(library.read_bytes()),'metadata_bytes':metadata.stat().st_size,
            'metadata_sha256':digest(metadata.read_bytes()),'metadata':json.loads(metadata.read_text('utf-8'))}
    save(args.out/'native-resource.json',native)
    changes=[];previous=None
    for item in inputs:
        current={key:(digest(raw),digest(_json([title,body]))) for key,title,body,offset,raw,kind in records(item['filename'],Path(item['path']).read_bytes())}
        changes.append({'version':item['version'],'records':len(current),'raw_members_changed':None if previous is None else sum(previous[k][0]!=v[0] for k,v in current.items()),
                        'projected_paper_text_changed':None if previous is None else sum(previous[k][1]!=v[1] for k,v in current.items())})
        previous=current
    save(args.out/'dataset-provenance.json',{'official_QASPER_dev_releases':inputs,'changes':changes,'questions':64,
         'question_rule':'Sorted v0.1 paper IDs, first unseen question per paper; first 64; no question/answer annotations in FTS',
         'stress_control':'Synthetic 2048 JSONL records and four notes, 100 updates; not real scientific samples'})
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,
         'logical_cpus':os.cpu_count(),'seed':SEED,'rounds':3,'generation_calls':0,'cold_cache':None,'cross_machine':None,
         'scope':'One Windows host, warm cache; fresh query processes at predefined stages; all history retained'})
    trials=[]
    for n in range(3):
        order=[(campaign,profile) for campaign in ('qasper','stress') for profile in PROFILES]
        random.Random(SEED+n).shuffle(order)
        for campaign,profile in order:
            work=args.work/f'{n}-{campaign}-{profile}';result=args.work/f'{n}-{campaign}-{profile}.json'
            subprocess.run([sys.executable,'-m','scripts.run_memory_history','--worker','--campaign',campaign,'--profile',profile,
                            '--round',str(n),'--work',str(work),'--result',str(result),'--native-library',str(library)],env=clean_env(),check=True)
            trial=json.loads(result.read_text('utf-8'));trials.append(trial);append(args.out/'trials.jsonl',trial)
    assert implementation_checksums()==checks and digest(library.read_bytes())==native['sha256'] and digest(metadata.read_bytes())==native['metadata_sha256']
    save(args.out/'trials.json',{'trials':trials,'rounds':3,'generation_calls':0})


if __name__=='__main__':
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--work',type=Path);p.add_argument('--native-library',type=Path)
    p.add_argument('--query',action='store_true');p.add_argument('--worker',action='store_true');p.add_argument('--campaign',choices=('qasper','stress'))
    p.add_argument('--profile',choices=PROFILES);p.add_argument('--round',type=int);p.add_argument('--memory',type=Path);p.add_argument('--snapshot');p.add_argument('--result',type=Path)
    args=p.parse_args()
    if args.query:query(args)
    elif args.worker:worker(args)
    else:main(args)
