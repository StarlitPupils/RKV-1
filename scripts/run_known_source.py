"""Paired explicit-source and open retrieval, with a labelled oracle diagnostic."""
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
from rkv1.qasper_audit import BUDGETS, score_selected
from scripts.run_context_selection import load, SEED, PLANS
from scripts.run_memory_history import clean_env, inventory
from scripts.run_units import save

WORKLOADS=('open-top5','known-source','oracle-if-recalled')
SCORE_FIELDS=('complete_reference_exposed','best_reference_paragraph_recall','failure_or_success_reason',
              'visible_body_utf8_bytes','serialized_context_json_bytes','visible_papers','visible_paragraphs')
TIME_FIELDS=('prepare_wall_s','prepare_cpu_s','choose_wall_s','choose_cpu_s','offline_score_wall_s')


def identity(hits):
    return [{k:h[k] for k in ('key','title','sentences','locator')} for h in hits]


def selected_identity(visible):
    # Citation numbering is local to each read, not scientific source identity.
    return digest(_json([{'key':h['key'],'locator':h['locator'],
        'sentences':[(i,digest(h['sentences'][i].encode())) for i in h['visible_sentence_ids']]} for h in visible]))


def worker(args):
    _,_,jobs=load(args.split);random.Random(SEED+args.round).shuffle(jobs)
    m=Memory(args.memory);sid=m.current();before=inventory(m.root)
    m.search(jobs[0]['question'],snapshot=sid,top_k=20);m.lookup(jobs[0]['paper_key'],snapshot=sid)
    rows=[]
    for n,c in enumerate(jobs):
        reads={};timing={};operations=['open-top5','known-source']
        rng=random.Random(SEED+args.round+int(c['question_id_sha256'][:8],16));rng.shuffle(operations)
        for op in operations:
            start=time.perf_counter();cpu=time.process_time()
            reads[op]=m.search(c['question'],snapshot=sid,top_k=20) if op=='open-top5' else m.lookup(c['paper_key'],snapshot=sid)
            timing[op]=[time.perf_counter()-start,time.process_time()-cpu]
        hits=reads['open-top5']['hits'];known=reads['known-source']['hits'];assert len(known)==1 and known[0]['key']==c['paper_key'] and known[0]['rank'] is None
        start=time.perf_counter();cpu=time.process_time();target=[h for h in hits[:5] if h['key']==c['paper_key']]
        timing['oracle-filter']=[time.perf_counter()-start,time.process_time()-cpu]
        any_target=[h for h in hits if h['key']==c['paper_key']]
        if any_target:assert identity(any_target)==identity(known)
        assert all(h['source_bytes_verified'] is True for h in hits+known)
        sources={'open-top5':hits[:5],'known-source':known,'oracle-if-recalled':target}
        scores={};times={};bindings={}
        workloads=list(WORKLOADS);rng.shuffle(workloads)
        for work in workloads:
            small=sources[work];start=time.perf_counter();cpu=time.process_time();order=lexical_order(c['question'],small)
            prep=[time.perf_counter()-start,time.process_time()-cpu]
            settings=[(p,b) for p in PLANS for b in BUDGETS];rng.shuffle(settings)
            scores[work]={};times[work]={};bindings[work]={}
            for plan,budget in settings:
                key=plan+'/'+str(budget);start=time.perf_counter();cpu=time.process_time()
                visible=exposed_hits(small,budget=budget) if plan=='source-order' else choose(small,order,budget=budget)
                cw=time.perf_counter()-start;cc=time.process_time()-cpu;start=time.perf_counter()
                score=score_selected(c,known if work=='known-source' else hits,visible,budget=budget,top_k=1 if work=='known-source' else 5)
                scores[work][key]=[score[f] for f in SCORE_FIELDS]
                times[work][key]=[*(prep if plan=='lexical' else [0,0]),cw,cc,time.perf_counter()-start]
                bindings[work][key]=selected_identity(visible)
        for p in PLANS:
            for b in BUDGETS:
                key=p+'/'+str(b)
                if target:
                    assert scores['known-source'][key]==scores['oracle-if-recalled'][key]
                    assert bindings['known-source'][key]==bindings['oracle-if-recalled'][key]
                else:assert scores['oracle-if-recalled'][key][5:]==[0,0]
        rows.append({'question_id_sha256':c['question_id_sha256'],'question_sha256':c['question_sha256'],'paper_key':c['paper_key'],
            'has_nonempty_answerable_reference':bool(c['gold_sets']),'fully_text_mapped_reference':c['fully_text_mapped_reference'],
            'keys':[h['key'] for h in hits],'ranks':[h['rank'] for h in hits],'evidence_identity_sha256':digest(_json(identity(hits))),
            'known_source_identity_sha256':digest(_json(identity(known))),'target_in_open_top5':bool(target),
            'read_timing_wall_cpu_s':timing,'scores':scores,'selection_timing':times,'selection_source_identity_sha256':bindings})
        if n%250==0:print(args.split,args.round,n+1,'/',len(jobs),flush=True)
    assert before==inventory(m.root)
    with args.result.open('x',encoding='utf-8',newline='\n') as f:
        json.dump({'split':args.split,'round':args.round,'queries':rows,'warmup_read_operations':2,'peak_rss_bytes':peak_rss(),
                   'persistent_tree_unchanged':True,'generation_calls':0},f,separators=(',',':'));f.write('\n')


def main(args):
    args.out.mkdir();args.work.mkdir();checks=implementation_checksums();save(args.out/'source-checksums.json',checks)
    paths=[*sorted(Path('rkv1').rglob('*.py')),Path('rkv1/memory_demo.html')]
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in paths}
    old=subprocess.check_output(['git','show','v0.28.0:rkv1/memory.py'])
    save(args.out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
        'lookup_memory_module_delta_bytes':Path('rkv1/memory.py').stat().st_size-len(old),'native_specific_bytes':0,'model_bytes':0})
    inputs={};builds={}
    for split in ('dev','train'):
        path,raw,jobs=load(split)
        inputs[split]={'filename':path.name,'bytes':len(raw),'sha256':digest(raw),'papers':len({c['paper_key'] for c in jobs}),
            'question_instances':len(jobs),'unique_question_strings':len({c['question_sha256'] for c in jobs}),
            'answerability':dict(Counter(c['answerability'] for c in jobs)),
            'nonempty_answerable_reference_questions':sum(bool(c['gold_sets']) for c in jobs),
            'fully_text_mapped_reference_questions':sum(c['fully_text_mapped_reference'] for c in jobs)}
        source=args.work/(split+'-source');source.mkdir();shutil.copyfile(path,source/path.name)
        m=Memory.create(args.work/(split+'-memory'));start=time.perf_counter();cpu=time.process_time()
        built=m.add(source,label='v026-qasper-coverage' if split=='dev' else 'v027-qasper-train')
        wall=time.perf_counter()-start;cpu=time.process_time()-cpu
        with m.store.snapshot(built['snapshot_id']) as snap:assert snap.read_range(path.name)==raw
        builds[split]={'build':built,'wall_s':wall,'cpu_s':cpu,'storage':m.stats(),'tree':inventory(m.root),'full_original_source_bytewise_verified':True}
    save(args.out/'dataset-provenance.json',inputs);save(args.out/'build.json',builds)
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,
        'logical_cpus':os.cpu_count(),'seed':SEED,'rounds':3,'generation_calls':0,'cold_cache':None,'cross_machine':None,'new_model_answer_quality':None,
        'score_fields':SCORE_FIELDS,'selection_timing_fields':TIME_FIELDS,'workloads':WORKLOADS})
    for r in range(3):
        splits=['dev','train'];random.Random(SEED+r).shuffle(splits)
        for split in splits:
            result=args.out/f'{split}-round{r}.json';start=time.perf_counter()
            subprocess.run([sys.executable,'-m','scripts.run_known_source','--worker','--split',split,'--round',str(r),
                '--memory',str(args.work/(split+'-memory')),'--result',str(result)],env=clean_env(),check=True)
            t=json.loads(result.read_text('utf-8'));t['process_wall_including_startup_s']=time.perf_counter()-start
            with result.open('w',encoding='utf-8',newline='\n') as f:json.dump(t,f,separators=(',',':'));f.write('\n')
    for split in ('dev','train'):
        m=Memory(args.work/(split+'-memory'));assert builds[split]['tree']==inventory(m.root)
        path,raw,_=load(split)
        with m.store.snapshot(m.current()) as snap:assert snap.read_range(path.name)==raw
    save(args.out/'postconditions.json',{'all_persistent_trees_unchanged':True,'all_full_original_files_bytewise_restored':True,
         'checksums_unchanged':checks==implementation_checksums(),'remote_model_calls':0})
    assert checks==implementation_checksums();print('Known/open workload campaign complete',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--work',type=Path);p.add_argument('--worker',action='store_true')
    p.add_argument('--split',choices=('dev','train'));p.add_argument('--round',type=int);p.add_argument('--memory',type=Path);p.add_argument('--result',type=Path)
    a=p.parse_args()
    if a.worker:worker(a)
    else:main(a)
