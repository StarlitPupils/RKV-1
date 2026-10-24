"""Pinned QASPER releases and clearly synthetic projection/locator controls."""
import argparse
import copy
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
from rkv1.core import digest,files_in
from rkv1.memory import Memory,_json,records
from rkv1.memory_projection import fingerprint,MAX_REBINDINGS
from rkv1.memory_budget import DEFAULT_BUDGET
from rkv1.native import load_native_gear
from scripts.run_memory import append
from scripts.run_memory_history import real_inputs,questions as release_questions,query_record,inventory,clean_env
from scripts.run_units import save

CASES=('official-gear','official-fixed','synthetic-fixed')
PLANS={'rebuild':'compact-full-v2','budget-v3':'compact-budget-v3','projection-v4':'compact-projection-v4'}
SEED=20261024
CONTROL_QUESTIONS=['calibration silver','rare variants','token000','token001','token032','token033','token099','token159',
                   'token999','TRUEBODYQ21','TRUETITLEQ21','ADDEDPAPERQ21','ANNOTATIONONLYQ21','PRIVATEANSWERQ21','unfindablewordq21','neutrino']


def questions(case,n):
    if case.startswith('official'):return release_questions('qasper',n)
    result=[('synthetic-'+str(i),q) for i,q in enumerate(CONTROL_QUESTIONS)]
    random.Random(SEED+n).shuffle(result);return result


class Control:
    """New text edits here are generated controls, never called real revisions."""
    def __init__(self):
        self.original={str(i):{'title':f'Calibration silver paper {i:03d}',
            'abstract':f'Neutrino token{i:03d} café 雪.',
            'full_text':[{'section_name':'Introduction','paragraphs':['Rare variants confirm beacon. '+('calibration '*32)]}],
            'qas':[{'question':'ANNOTATIONONLYQ21','answer':'PRIVATEANSWERQ21'}]} for i in range(160)}
        self.docs=copy.deepcopy(self.original)

    def write(self,source,n):
        if n==1:
            for d in self.docs.values():d['qas'].append({'question':'ANNOTATIONONLYQ21 '+('changed '*8)})
        if n==2:self.docs=dict(reversed(list(self.docs.items())))
        if n==3:self.docs['0']['full_text'][0]['paragraphs'][0]+=' TRUEBODYQ21'
        if n==4:
            del self.docs['1'];self.docs['new']=copy.deepcopy(self.original['0'])
            self.docs['new']['title']='ADDEDPAPERQ21';self.docs['new']['abstract']='token999'
        if n==5:
            for i in [0,*range(2,34)]:self.docs[str(i)]['title']+=' TRUETITLEQ21'
        if n==6:self.docs=copy.deepcopy(self.original)
        if n==8:self.docs['0']['qas'].append({'question':'ANNOTATIONONLYQ21 latest'})
        name='control-v1.json' if n==0 else 'control-v2.json' if n<6 else 'control-restored.json'
        for p in source.iterdir():
            if p.name!=name:p.unlink()
        # Stages 6/7 have identical bytes but different labels.
        raw=(json.dumps(self.docs,ensure_ascii=n<2,indent=2 if n<2 else 1)+'\r\n').encode()
        (source/name).write_bytes(raw)


def query(args):
    m=Memory(args.memory);jobs=questions(args.case,args.round);m.search(jobs[0][1],snapshot=args.snapshot,top_k=10)
    rows=[query_record(m,args.snapshot,cid,q) for cid,q in jobs]
    save(args.result,{'queries':rows,'warmup_queries':1,'peak_rss_bytes':peak_rss(),'generation_calls':0})


def worker(args):
    args.work.mkdir();source=args.work/'source';source.mkdir();official=args.case.startswith('official')
    native=args.case=='official-gear';inputs=real_inputs() if official else None;control=None if official else Control()
    m=Memory.create(args.work/'memory',index_profile=PLANS[args.plan],chunker='gear-v1' if native else 'fixed')
    reference=None
    if native and args.plan=='rebuild':
        old=json.loads(Path('results/v0.19.0/trials.json').read_text('utf-8'))
        reference=next(t for t in old['trials'] if t['campaign']=='qasper' and t['profile']=='rebuild' and t['round']==0)
    stages=[];history=[];first=None
    for n in range(3 if official else 9):
        if official:
            if n:(source/inputs[n-1]['filename']).unlink()
            shutil.copyfile(inputs[n]['path'],source/inputs[n]['filename'])
        else:control.write(source,n)
        truth={name:{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p,name in files_in(source)}
        start=time.perf_counter();cpu=time.process_time()
        built=m.add(source,label=f'v019-qasper-{n:03d}' if official else f'v021-synthetic-{n:03d}',
                    chunker_backend='rust' if native else 'python',native_library=args.native_library if native else None)
        wall=time.perf_counter()-start;cpu=time.process_time()-cpu;sid=built['snapshot_id']
        if first is None:first=sid
        history.append((sid,truth))
        with m.store.snapshot(sid) as snap:
            assert set(snap.files)==set(truth)
            for name in truth:assert snap.read_range(name)==(source/name).read_bytes()
        before=inventory(m.root);stats=m.stats();target=args.work/f'{n}-queries.json';start=time.perf_counter()
        subprocess.run([sys.executable,'-m','scripts.run_memory_projection','--query','--case',args.case,'--round',str(args.round),
                        '--memory',str(m.root),'--snapshot',sid,'--result',str(target)],env=clean_env(),check=True)
        process_wall=time.perf_counter()-start;found=json.loads(target.read_text('utf-8'))
        old=[query_record(m,first,cid,q) for cid,q in questions(args.case,0)[:4]]
        absent=None if official else not m.search('TRUEBODYQ21 TRUETITLEQ21 ADDEDPAPERQ21',snapshot=first)['hits']
        if not official:assert absent
        assert inventory(m.root)==before
        value=m._manifest(sid);checkpoint=value['base_snapshot_id']==sid
        if reference is not None:
            expected=reference['stages'][n]
            assert truth==expected['source_truth'] and sid==expected['build']['snapshot_id'] and before==expected['tree']
        if official:
            if args.plan=='projection-v4':
                assert checkpoint==(n==0)
                if n:assert built['overlay_rebindings']==281 and built['overlay_upserts']==0 and built['replay_budget']['cas_bytes']==0
            else:assert checkpoint
        elif args.plan=='projection-v4':
            assert checkpoint==(n in (0,5,6))
            if n in (1,2):assert built['overlay_rebindings']==160 and built['overlay_upserts']==0 and built['replay_budget']['cas_bytes']==0
            if n==5:assert built['checkpoint_reason']=='budget-changes'
        stages.append({'index':n,'build':built,'build_wall_s':wall,'build_cpu_s':cpu,'checkpoint':checkpoint,'storage':stats,'tree':before,
                       'source_truth':truth,'full_current_source_bytewise_verified':True,'query':found,'query_process_wall_including_startup_s':process_wall,
                       'old_snapshot_queries':old,'original_future_probe_absent':absent})
        print(args.case,args.plan,args.round,n,stats['logical_file_bytes'],built.get('checkpoint_reason'),built.get('overlay_rebindings'),flush=True)
    for sid,truth in history:
        with m.store.snapshot(sid) as snap:
            assert set(snap.files)==set(truth)
            for name,meta in truth.items():
                raw=snap.read_range(name);assert len(raw)==meta['bytes'] and digest(raw)==meta['sha256']
    save(args.result,{'case':args.case,'plan':args.plan,'round':args.round,'stages':stages,'all_historical_snapshots_full_source_verified':True,
                     'legacy_rebuild_bytes_match_v019':reference is not None,'final_CAS_tree':inventory(m.root/'cas'),
                     'build_process_peak_rss_bytes':peak_rss(),'generation_calls':0})


def main(args):
    inputs=real_inputs();checks=implementation_checksums();args.out.mkdir();args.work.mkdir()
    library=args.native_library.resolve();load_native_gear(str(library));meta=library.with_name('native.json')
    native={'bytes':library.stat().st_size,'sha256':digest(library.read_bytes()),'metadata_bytes':meta.stat().st_size,
            'metadata_sha256':digest(meta.read_bytes()),'metadata':json.loads(meta.read_text('utf-8'))}
    paths=sorted(Path('rkv1').rglob('*.py'))+[Path('rkv1/memory_demo.html')]
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in paths}
    save(args.out/'source-checksums.json',checks);save(args.out/'native-resource.json',native)
    save(args.out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
         'scope':'All RKV Python/HTML once, including v4 code in all conditions; only Gear case adds entire exact measured DLL/metadata; common runtime/pyc/installation/filesystem metadata excluded'})
    changes=[];previous=None
    for item in inputs:
        current={key:(digest(raw),fingerprint(title,body)) for key,title,body,offset,raw,kind in records(item['filename'],Path(item['path']).read_bytes())}
        changes.append({'version':item['version'],'records':len(current),'raw_members_changed':None if previous is None else sum(previous[k][0]!=v[0] for k,v in current.items()),
                        'projected_paper_text_changed':None if previous is None else sum(previous[k][1]!=v[1] for k,v in current.items())})
        previous=current
    save(args.out/'dataset-provenance.json',{'official_QASPER_dev_releases':inputs,'changes':changes,'official_questions':64,
         'question_rule':'Same v0.19 64 questions: v0.1 sorted paper IDs, first unseen question each; not new scientific questions',
         'synthetic_control':'160 generated papers, 9 states: annotations/rename/reorder/true text/add-delete/33 text updates/revert/label alias/one annotation; not actual paper revisions'})
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,'rounds':3,
         'logical_cpus':os.cpu_count(),'seed':SEED,'default_limits':DEFAULT_BUDGET,'max_rebindings':MAX_REBINDINGS,'generation_calls':0,
         'scope':'Same-source strategies; existing real dataset releases plus directed synthetic controls; one warm-cache host',
         'cold_cache':None,'cross_machine':None,'new_model_quality':None})
    trials=[]
    for n in range(3):
        order=[(case,plan) for case in CASES for plan in PLANS];random.Random(SEED+n).shuffle(order)
        for case,plan in order:
            work=args.work/f'{n}-{case}-{plan}';target=args.work/f'{n}-{case}-{plan}.json'
            subprocess.run([sys.executable,'-m','scripts.run_memory_projection','--worker','--case',case,'--plan',plan,'--round',str(n),
                            '--work',str(work),'--result',str(target),'--native-library',str(library)],env=clean_env(),check=True)
            trial=json.loads(target.read_text('utf-8'));trials.append(trial);append(args.out/'trials.jsonl',trial)
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
