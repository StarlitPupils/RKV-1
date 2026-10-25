"""Frozen whole-paper versus best-unit BM25, including SciFact task transfer."""
import argparse
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
from rkv1.datasets import SCIFACT, SCIFACT_ARCHIVE_SHA256, SCIFACT_URL
from rkv1.memory import Memory, _json
from rkv1.memory_model import exposed_hits
from rkv1.memory_paragraph import ParagraphIndex
from rkv1.qasper_audit import BUDGETS, score_selected
from scripts.run_context_selection import load, PLANS, SEED
from scripts.run_known_source import identity, selected_identity, SCORE_FIELDS, TIME_FIELDS
from scripts.run_memory_history import clean_env, inventory
from scripts.run_units import save

TASKS=('qasper-dev','qasper-train','scifact-dev','scifact-train')
RETRIEVERS=('whole-paper','best-unit')
KS=(1,5,10,20)


def dataset(task):
    kind,split=task.split('-')
    if kind=='qasper':
        path,raw,jobs=load(split)
        return path,raw,[{**c,'gold_keys':[c['paper_key']]} for c in jobs]
    path=Path('data/scifact/corpus.jsonl');raw=path.read_bytes();assert digest(raw)==SCIFACT[path.name]
    name='claims_'+split+'.jsonl';labels=Path('data/scifact')/name;assert digest(labels.read_bytes())==SCIFACT[name]
    claims=[json.loads(x) for x in labels.read_bytes().splitlines()];jobs=[]
    assert len(claims)==(300 if split=='dev' else 809)
    for c in sorted(claims,key=lambda c:c['id']):
        if not c['evidence']:continue
        assert all(isinstance(rs,list) and rs for rs in c['evidence'].values())
        jobs.append({'question':c['claim'],'question_id_sha256':digest(('scifact:'+str(c['id'])).encode()),
            'question_sha256':digest(c['claim'].encode()),'claim_id':c['id'],'gold_keys':sorted('doc:'+str(k) for k in c['evidence'])})
    assert len(jobs)==(188 if split=='dev' else 505)
    return path,raw,jobs


def parent_metrics(gold,keys):
    gold=set(gold);assert gold
    return {str(k):{'gold_document_recall':len(gold & set(keys[:k]))/len(gold),
                    'any_gold_hit':bool(gold & set(keys[:k])),'all_gold_hit':gold<=set(keys[:k])} for k in KS}


def worker(args):
    _,_,jobs=dataset(args.task);random.Random(SEED+args.round).shuffle(jobs)
    m=Memory(args.memory);side=ParagraphIndex(args.sidecar);sid=m.current();before=inventory(m.root);aux_before=inventory(side.root)
    m.search(jobs[0]['question'],top_k=20,snapshot=sid);side.search(m,jobs[0]['question'],top_k=20,snapshot=sid)
    rows=[]
    for n,c in enumerate(jobs):
        rng=random.Random(SEED+args.round+int(c['question_id_sha256'][:8],16));plans=list(RETRIEVERS);rng.shuffle(plans)
        found={};observations={}
        for plan in plans:
            start=time.perf_counter();cpu=time.process_time()
            result=m.search(c['question'],top_k=20,snapshot=sid) if plan=='whole-paper' else side.search(m,c['question'],top_k=20,snapshot=sid)
            wall=time.perf_counter()-start;cpu=time.process_time()-cpu;hits=result['hits'];found[plan]=hits
            assert all(h['source_bytes_verified'] is True for h in hits)
            keys=[h['key'] for h in hits];assert len(keys)==len(set(keys)) and len(keys)<=20
            record={'keys':keys,'ranks':[h['rank'] for h in hits],'evidence_identity_sha256':digest(_json(identity(hits))),
                'parent_metrics':parent_metrics(c['gold_keys'],keys),'read_wall_s':wall,'read_cpu_s':cpu}
            if plan=='best-unit':record['winning_source_units']=result['winning_source_units']
            if args.task.startswith('qasper'):
                small=hits[:5];start=time.perf_counter();cpu=time.process_time();order=lexical_order(c['question'],small)
                prep=[time.perf_counter()-start,time.process_time()-cpu];settings=[(p,b) for p in PLANS for b in BUDGETS];rng.shuffle(settings)
                scores={};times={};bindings={}
                for selector,budget in settings:
                    key=selector+'/'+str(budget);start=time.perf_counter();cpu=time.process_time()
                    visible=exposed_hits(small,budget=budget) if selector=='source-order' else choose(small,order,budget=budget)
                    cw=time.perf_counter()-start;cc=time.process_time()-cpu;start=time.perf_counter()
                    score=score_selected(c,hits,visible,budget=budget)
                    scores[key]=[score[f] for f in SCORE_FIELDS]
                    times[key]=[*(prep if selector=='lexical' else [0,0]),cw,cc,time.perf_counter()-start]
                    bindings[key]=selected_identity(visible)
                record.update(scores=scores,selection_timing=times,selection_source_identity_sha256=bindings)
            observations[plan]=record
        original={h['key']:identity([h])[0] for h in found['whole-paper']}
        for h in found['best-unit']:
            if h['key'] in original:assert original[h['key']]==identity([h])[0]
        rows.append({'question_id_sha256':c['question_id_sha256'],'question_sha256':c['question_sha256'],
            'paper_key':c.get('paper_key'),'claim_id':c.get('claim_id'),'gold_keys':c['gold_keys'],
            'has_nonempty_answerable_reference':bool(c.get('gold_sets')) if args.task.startswith('qasper') else None,
            'fully_text_mapped_reference':c.get('fully_text_mapped_reference'),'retrievers':observations})
        if n%250==0:print(args.task,args.round,n+1,'/',len(jobs),flush=True)
    assert before==inventory(m.root) and aux_before==inventory(side.root)
    with args.result.open('x',encoding='utf-8',newline='\n') as f:
        json.dump({'task':args.task,'round':args.round,'queries':rows,'warmup_read_operations':2,'peak_rss_bytes':peak_rss(),
                   'Memory_and_sidecar_trees_unchanged':True,'generation_calls':0},f,separators=(',',':'));f.write('\n')


def main(args):
    args.out.mkdir();args.work.mkdir();checks=implementation_checksums();save(args.out/'source-checksums.json',checks)
    paths=[*sorted(Path('rkv1').rglob('*.py')),Path('rkv1/memory_demo.html')]
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in paths}
    save(args.out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
        'candidate_module_bytes':Path('rkv1/memory_paragraph.py').stat().st_size,'native_specific_bytes':0,'model_bytes':0})
    provenance={};builds={};all_jobs={}
    for task in TASKS:
        path,raw,jobs=dataset(task);all_jobs[task]=jobs;family='scifact' if task.startswith('scifact') else task
        provenance[task]={'source_filename':path.name,'source_bytes':len(raw),'source_sha256':digest(raw),'question_instances':len(jobs),
            'unique_question_strings':len({c['question_sha256'] for c in jobs}),'gold_claim_document_pairs':sum(len(c['gold_keys']) for c in jobs),
            'reference_questions':sum(bool(c.get('gold_sets')) for c in jobs) if task.startswith('qasper') else None}
        if task.startswith('scifact'):
            name='claims_'+task.split('-')[1]+'.jsonl';provenance[task].update(labels_sha256=SCIFACT[name],archive_sha256=SCIFACT_ARCHIVE_SHA256,source_url=SCIFACT_URL,
                all_claims=300 if task.endswith('dev') else 809,excluded_without_evidence=112 if task.endswith('dev') else 304,
                licenses={'claims':'CC-BY-4.0','abstracts':'ODC-By-1.0'})
        if family in builds:continue
        source=args.work/(family+'-source');source.mkdir();shutil.copyfile(path,source/path.name)
        m=Memory.create(args.work/(family+'-memory'));start=time.perf_counter();cpu=time.process_time()
        label='v026-qasper-coverage' if task=='qasper-dev' else 'v027-qasper-train' if task=='qasper-train' else 'scifact-corpus-only'
        built=m.add(source,label=label);wall=time.perf_counter()-start;cpu=time.process_time()-cpu
        with m.store.snapshot(m.current()) as snap:assert snap.read_range(path.name)==raw
        start=time.perf_counter();aux_cpu=time.process_time();aux=ParagraphIndex.create(m,args.work/(family+'-sidecar'))
        aux_wall=time.perf_counter()-start;aux_cpu=time.process_time()-aux_cpu;side=aux.pop('index')
        builds[family]={'memory_build':built,'build_wall_s':wall,'build_cpu_s':cpu,'storage':m.stats(),'tree':inventory(m.root),
            'auxiliary_build':{**aux,'wall_including_checks_s':aux_wall,'cpu_s':aux_cpu},'auxiliary_tree':inventory(side.root),'full_original_source_bytewise_verified':True}
    provenance['overlaps']={kind+'_train_dev_question_string_overlap':len({c['question_sha256'] for c in all_jobs[kind+'-dev']} & {c['question_sha256'] for c in all_jobs[kind+'-train']}) for kind in ('qasper','scifact')}
    save(args.out/'dataset-provenance.json',provenance);save(args.out/'build.json',builds)
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,
        'logical_cpus':os.cpu_count(),'seed':SEED,'rounds':3,'generation_calls':0,'cold_cache':None,'cross_machine':None,'new_model_answer_quality':None,
        'score_fields':SCORE_FIELDS,'selection_timing_fields':TIME_FIELDS,'retrievers':RETRIEVERS,'rank_scope':'Whole-paper and unit BM25 scores are not numerically comparable across indexes'})
    for r in range(3):
        order=list(TASKS);random.Random(SEED+r).shuffle(order)
        for task in order:
            family='scifact' if task.startswith('scifact') else task;result=args.out/f'{task}-round{r}.json';start=time.perf_counter()
            subprocess.run([sys.executable,'-m','scripts.run_paragraph_retrieval','--worker','--task',task,'--round',str(r),
                '--memory',str(args.work/(family+'-memory')),'--sidecar',str(args.work/(family+'-sidecar')),'--result',str(result)],env=clean_env(),check=True)
            t=json.loads(result.read_text('utf-8'));t['process_wall_including_startup_s']=time.perf_counter()-start
            with result.open('w',encoding='utf-8',newline='\n') as f:json.dump(t,f,separators=(',',':'));f.write('\n')
    for family,b in builds.items():
        m=Memory(args.work/(family+'-memory'));side=ParagraphIndex(args.work/(family+'-sidecar'))
        assert b['tree']==inventory(m.root) and b['auxiliary_tree']==inventory(side.root)
        path,raw,_=dataset('scifact-dev' if family=='scifact' else family)
        with m.store.snapshot(m.current()) as snap:assert snap.read_range(path.name)==raw
    assert checks==implementation_checksums()
    save(args.out/'postconditions.json',{'all_Memory_and_auxiliary_trees_unchanged':True,'all_full_original_files_bytewise_restored':True,
        'checksums_unchanged':True,'remote_model_calls':0})
    print('Paragraph retrieval campaign complete',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--work',type=Path);p.add_argument('--worker',action='store_true')
    p.add_argument('--task',choices=TASKS);p.add_argument('--round',type=int);p.add_argument('--memory',type=Path);p.add_argument('--sidecar',type=Path);p.add_argument('--result',type=Path)
    a=p.parse_args()
    if a.worker:worker(a)
    else:main(a)
