"""Whole-paper retrieval versus gold paragraph exposure on all fixed dev tasks."""
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
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.memory import Memory, _json
from rkv1.qasper_audit import BUDGETS, cases, score
from rkv1.version_data import VERSIONS, fetch_versions
from scripts.run_memory_history import clean_env, inventory, questions as old_questions
from scripts.run_units import save

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'data/qasper-versions/v0.3/qasper-dev-v0.3.json'
SEED=20261025


def load():
    raw=INPUT.read_bytes();assert len(raw)==11398686 and digest(raw)==VERSIONS['0.3']['dev']
    jobs=cases(raw);assert len(jobs)==1005 and len({c['paper_key'] for c in jobs})==281
    return raw,jobs


def worker(args):
    _,jobs=load();random.Random(SEED+args.round).shuffle(jobs)
    m=Memory(args.memory);sid=m.current();before=inventory(m.root)
    m.search(jobs[0]['question'],snapshot=sid,top_k=20)
    rows=[]
    for i,c in enumerate(jobs):
        start=time.perf_counter();cpu=time.process_time()
        found=m.search(c['question'],snapshot=sid,top_k=20)
        wall=time.perf_counter()-start;cpu=time.process_time()-cpu;hits=found['hits']
        assert all(h['source_bytes_verified'] for h in hits)
        identity=[{k:h[k] for k in ('key','title','sentences','locator')} for h in hits]
        start=time.perf_counter();scores={str(b):score(c,hits,budget=b) for b in BUDGETS};scoring=time.perf_counter()-start
        rows.append({'question_id_sha256':c['question_id_sha256'],'question_sha256':c['question_sha256'],'paper_key':c['paper_key'],
            'answerability':c['answerability'],'has_nonempty_answerable_reference':bool(c['gold_sets']),
            'fully_text_mapped_reference':c['fully_text_mapped_reference'],'annotation_count':c['annotation_count'],
            'unmapped_evidence_strings':c['unmapped_evidence_strings'],'keys':[h['key'] for h in hits],'ranks':[h['rank'] for h in hits],
            'evidence_identity_sha256':digest(_json(identity)),'all_original_records_verified':True,
            'search_wall_s':wall,'search_cpu_s':cpu,'scoring_wall_s':scoring,'scores':scores})
        if i%100==0:print('qasper coverage',args.round,i+1,'/1005',flush=True)
    assert inventory(m.root)==before
    save(args.result,{'round':args.round,'queries':rows,'warmups':1,'peak_rss_bytes':peak_rss(),'persistent_tree_unchanged':True,'generation_calls':0})


def main(args):
    if args.fetch:fetch_versions(ROOT/'data/qasper-versions')
    raw,jobs=load();args.out.mkdir();args.work.mkdir();checks=implementation_checksums()
    source=args.work/'source';source.mkdir();shutil.copyfile(INPUT,source/INPUT.name)
    m=Memory.create(args.work/'memory')
    start=time.perf_counter();cpu=time.process_time();built=m.add(source,label='v026-qasper-coverage')
    wall=time.perf_counter()-start;cpu=time.process_time()-cpu
    assert built['indexed_records']==281
    with m.store.snapshot(built['snapshot_id']) as snap:assert snap.read_range(INPUT.name)==raw
    before=inventory(m.root)
    save(args.out/'source-checksums.json',checks)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in [*sorted(Path('rkv1').rglob('*.py')),Path('rkv1/memory_demo.html')]}
    save(args.out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),'native_specific_bytes':0,'model_bytes':0,
        'scope':'All RKV Python and HTML once; shared runtime, pyc, installation and filesystem overhead not allocated'})
    save(args.out/'build.json',{'build':built,'wall_s':wall,'cpu_s':cpu,'storage':m.stats(),'tree':before,'full_original_source_bytewise_verified':True})
    previous={digest(q.encode()) for _,q in old_questions('qasper',0)}
    unique={c['question_sha256'] for c in jobs}
    save(args.out/'dataset-provenance.json',{'input_path':INPUT.name,'bytes':len(raw),'sha256':digest(raw),'version':'0.3','license':'CC BY 4.0',
        'archive_url':'https://qasper-dataset.s3-us-west-2.amazonaws.com/qasper-train-dev-v0.3.tgz','archive_sha256':VERSIONS['0.3']['archive'],
        'paper_instances':281,'new_independent_papers':0,'question_id_instances':1005,'unique_question_strings':len(unique),
        'previous_64_unique_question_strings':len(previous),'overlap_question_strings':len(unique & previous),'new_question_strings_vs_previous_64':len(unique-previous),
        'answerability':dict(Counter(c['answerability'] for c in jobs)),
        'nonempty_answerable_reference_questions':sum(bool(c['gold_sets']) for c in jobs),
        'at_least_one_fully_text_mapped_reference_questions':sum(c['fully_text_mapped_reference'] for c in jobs),
        'unmapped_evidence_strings_including_repeated_annotations':sum(c['unmapped_evidence_strings'] for c in jobs),
        'annotations_are_scoring_labels_only_not_FTS':True,'not_official_QASPER_answer_or_evidence_F1':True})
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,
        'logical_cpus':os.cpu_count(),'rounds':3,'seed':SEED,'generation_calls':0,'new_model_answer_quality':None,'cold_cache':None,'cross_machine':None})
    trials=[]
    for r in range(3):
        path=args.work/f'queries-{r}.json';start=time.perf_counter()
        subprocess.run([sys.executable,'-m','scripts.run_qasper_coverage','--worker','--memory',str(m.root),'--round',str(r),'--result',str(path)],check=True,env=clean_env())
        trial=json.loads(path.read_text('utf-8'));trial['process_wall_including_startup_s']=time.perf_counter()-start;trials.append(trial)
    assert before==inventory(m.root) and checks==implementation_checksums()
    with m.store.snapshot(built['snapshot_id']) as snap:assert snap.read_range(INPUT.name)==raw
    save(args.out/'trials.json',{'trials':trials,'formal_queries':3015,'warmups_excluded':3,'full_original_source_verified_at_start_and_end':True})
    print('QASPER all-dev offline coverage complete',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--work',type=Path);p.add_argument('--fetch',action='store_true')
    p.add_argument('--worker',action='store_true');p.add_argument('--memory',type=Path);p.add_argument('--round',type=int);p.add_argument('--result',type=Path)
    a=p.parse_args()
    if a.worker:worker(a)
    else:main(a)
