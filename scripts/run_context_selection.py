"""Paired source-order/lexical contexts over the same exact retrieved evidence."""
import argparse
from collections import Counter
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
from rkv1.context_selection import choose, lexical_order
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.memory import Memory, _json
from rkv1.memory_model import exposed_hits
from rkv1.qasper_audit import BUDGETS, cases, score_selected
from rkv1.version_data import VERSIONS
from scripts.run_memory_history import clean_env, inventory
from scripts.run_units import save

ROOT=Path(__file__).resolve().parents[1];SEED=20261025;PLANS=('source-order','lexical')


def load(split):
    path=ROOT/f'data/qasper-versions/v0.3/qasper-{split}-v0.3.json';raw=path.read_bytes()
    assert digest(raw)==VERSIONS['0.3'][split]
    jobs=cases(raw);assert len(jobs)==(1005 if split=='dev' else 2593)
    assert len({c['paper_key'] for c in jobs})==(281 if split=='dev' else 888)
    return path,raw,jobs


def worker(args):
    _,_,jobs=load(args.split);random.Random(SEED+args.round).shuffle(jobs)
    m=Memory(args.memory);sid=m.current();before=inventory(m.root);m.search(jobs[0]['question'],snapshot=sid,top_k=20)
    rows=[]
    for n,c in enumerate(jobs):
        start=time.perf_counter();cpu=time.process_time();found=m.search(c['question'],snapshot=sid,top_k=20)
        sw=time.perf_counter()-start;sc=time.process_time()-cpu;hits=found['hits'];small=hits[:5]
        assert all(h['source_bytes_verified'] for h in hits)
        start=time.perf_counter();cpu=time.process_time();order=lexical_order(c['question'],small)
        pw=time.perf_counter()-start;pc=time.process_time()-cpu
        settings=[(p,b) for p in PLANS for b in BUDGETS]
        random.Random(SEED+args.round+int(c['question_id_sha256'][:8],16)).shuffle(settings)
        scores={p:{} for p in PLANS};times={p:{} for p in PLANS};bindings={p:{} for p in PLANS}
        for plan,budget in settings:
            start=time.perf_counter();cpu=time.process_time()
            visible=exposed_hits(small,budget=budget) if plan=='source-order' else choose(small,order,budget=budget)
            cw=time.perf_counter()-start;cc=time.process_time()-cpu
            start=time.perf_counter();score=score_selected(c,hits,visible,budget=budget);audit=time.perf_counter()-start
            scores[plan][str(budget)]=score
            times[plan][str(budget)]={'prepare_wall_s':pw if plan=='lexical' else 0,'prepare_cpu_s':pc if plan=='lexical' else 0,
                'choose_wall_s':cw,'choose_cpu_s':cc,'offline_score_wall_s':audit}
            identity=[{'key':h['key'],'citation_id':h['citation_id'],'locator':h['locator'],'sentences':[(i,digest(h['sentences'][i].encode())) for i in h['visible_sentence_ids']]} for h in visible]
            bindings[plan][str(budget)]=digest(_json(identity))
        full_identity=[{k:h[k] for k in ('key','title','sentences','locator')} for h in hits]
        rows.append({'question_id_sha256':c['question_id_sha256'],'question_sha256':c['question_sha256'],'paper_key':c['paper_key'],
            'answerability':c['answerability'],'has_nonempty_answerable_reference':bool(c['gold_sets']),'fully_text_mapped_reference':c['fully_text_mapped_reference'],
            'annotation_count':c['annotation_count'],'unmapped_evidence_strings':c['unmapped_evidence_strings'],
            'keys':[h['key'] for h in hits],'ranks':[h['rank'] for h in hits],'evidence_identity_sha256':digest(_json(full_identity)),
            'all_original_records_verified':True,'search_wall_s':sw,'search_cpu_s':sc,'scores':scores,'selection_timing':times,'selection_identity_sha256':bindings})
        if n%200==0:print(args.split,args.round,n+1,'/',len(jobs),flush=True)
    assert before==inventory(m.root)
    # Compact raw records avoid duplicating hundreds of thousands of pretty-print lines.
    with args.result.open('x',encoding='utf-8',newline='\n') as f:
        json.dump({'split':args.split,'round':args.round,'queries':rows,'warmups':1,'peak_rss_bytes':peak_rss(),'persistent_tree_unchanged':True,'generation_calls':0},f,separators=(',',':'));f.write('\n')


def main(args):
    args.out.mkdir();args.work.mkdir();checks=implementation_checksums()
    save(args.out/'source-checksums.json',checks)
    paths=[*sorted(Path('rkv1').rglob('*.py')),Path('rkv1/memory_demo.html')]
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in paths}
    save(args.out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
        'selector_module_bytes':Path('rkv1/context_selection.py').stat().st_size,'native_specific_bytes':0,'model_bytes':0})
    inputs={};jobs_by_split={};builds={}
    for split in ('dev','train'):
        path,raw,jobs=load(split);jobs_by_split[split]=jobs
        inputs[split]={'path':path.name,'bytes':len(raw),'sha256':digest(raw),'papers':len({c['paper_key'] for c in jobs}),'question_instances':len(jobs),
            'unique_question_strings':len({c['question_sha256'] for c in jobs}),'answerability':dict(Counter(c['answerability'] for c in jobs)),
            'nonempty_answerable_reference_questions':sum(bool(c['gold_sets']) for c in jobs),
            'fully_text_mapped_reference_questions':sum(c['fully_text_mapped_reference'] for c in jobs)}
        source=args.work/(split+'-source');source.mkdir();shutil.copyfile(path,source/path.name)
        m=Memory.create(args.work/(split+'-memory'));start=time.perf_counter();cpu=time.process_time()
        built=m.add(source,label='v026-qasper-coverage' if split=='dev' else 'v027-qasper-train')
        wall=time.perf_counter()-start;cpu=time.process_time()-cpu
        with m.store.snapshot(built['snapshot_id']) as snap:assert snap.read_range(path.name)==raw
        builds[split]={'build':built,'wall_s':wall,'cpu_s':cpu,'storage':m.stats(),'tree':inventory(m.root),'full_original_source_bytewise_verified':True}
    inputs['cross_split']={'paper_id_overlap':len({c['paper_key'] for c in jobs_by_split['dev']} & {c['paper_key'] for c in jobs_by_split['train']}),
        'question_string_overlap':len({c['question_sha256'] for c in jobs_by_split['dev']} & {c['question_sha256'] for c in jobs_by_split['train']}),
        'train_is_new_task_evaluation_not_new_scientific_source':True,'no_training_or_annotation_tuning':True}
    save(args.out/'dataset-provenance.json',inputs);save(args.out/'build.json',builds)
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,'logical_cpus':os.cpu_count(),
        'seed':SEED,'rounds':3,'generation_calls':0,'cold_cache':None,'cross_machine':None,'new_model_answer_quality':None})
    trials={split:[] for split in ('dev','train')}
    for r in range(3):
        order=['dev','train'];random.Random(SEED+r).shuffle(order)
        for split in order:
            result=args.work/f'{split}-{r}.json';start=time.perf_counter()
            subprocess.run([sys.executable,'-m','scripts.run_context_selection','--worker','--split',split,'--round',str(r),'--memory',str(args.work/(split+'-memory')),'--result',str(result)],env=clean_env(),check=True)
            t=json.loads(result.read_text('utf-8'));t['process_wall_including_startup_s']=time.perf_counter()-start;trials[split].append(t)
    for split in ('dev','train'):
        m=Memory(args.work/(split+'-memory'));assert builds[split]['tree']==inventory(m.root)
        path,raw,_=load(split)
        with m.store.snapshot(m.current()) as snap:assert snap.read_range(path.name)==raw
        with (args.out/(split+'-trials.json')).open('x',encoding='utf-8',newline='\n') as f:
            json.dump({'trials':trials[split],'full_original_source_verified_at_start_and_end':True},f,separators=(',',':'));f.write('\n')
    assert checks==implementation_checksums()
    print('Paired dev/train context selection complete',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--work',type=Path);p.add_argument('--worker',action='store_true')
    p.add_argument('--split',choices=('dev','train'));p.add_argument('--round',type=int);p.add_argument('--memory',type=Path);p.add_argument('--result',type=Path)
    a=p.parse_args()
    if a.worker:worker(a)
    else:main(a)
