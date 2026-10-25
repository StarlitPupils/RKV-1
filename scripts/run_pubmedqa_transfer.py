"""Exact original PubMedQA members and unchanged open-retriever transfer."""
import argparse
import ast
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
import tempfile
import time

from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.datasets import _download, fetch_public, SCIFACT
from rkv1.memory import Memory, STOP, _json
from rkv1.memory_paragraph import ParagraphIndex
from rkv1.memory_pubmedqa import records
from rkv1.memory_qasper import unique
from rkv1.version_data import VERSIONS
from scripts.run_context_selection import load as qasper_load, SEED
from scripts.run_known_source import identity
from scripts.run_memory_history import clean_env, inventory
from scripts.run_paragraph_retrieval import RETRIEVERS, KS, parent_metrics
from scripts.run_units import save

COMMIT='1cbae8e92f72f20c8d3747cbb3bf5bc53554d997'
URL=f'https://raw.githubusercontent.com/pubmedqa/pubmedqa/{COMMIT}/data/ori_pqal.json'
SHA='8b3276be8942ebbd77f3ddcda12c1749bf0e490045a736fd8438ee40cf37a41d'
OLD_WHEEL_SHA='f97a92f1c89dfc6b1c60514a9ad39125975a0ec5e83a947d1a797f1177875950'
SOURCE_NAME='ori_pqal.pubmedqa.json'


def load(path,fetch=False):
    if not path.exists() and fetch:
        raw=_download(URL,SHA);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as f:f.write(raw)
    raw=path.read_bytes();assert digest(raw)==SHA and len(raw)==2584787
    docs=json.loads(raw,object_pairs_hook=unique);jobs=[]
    for pmid,obj in sorted(docs.items()):
        question=obj.get('QUESTION');assert isinstance(question,str) and 1<=len(question)<=4096
        jobs.append({'question':question,'paper_key':'pubmedqa:'+pmid,'question_id_sha256':digest(('pubmedqa:'+pmid).encode()),
                     'question_sha256':digest(question.encode()),'gold_keys':['pubmedqa:'+pmid]})
    assert len(jobs)==1000 and len({c['question_sha256'] for c in jobs})==1000
    return raw,jobs


def compatibility(root):
    old=subprocess.check_output(['git','show','v0.30.0:rkv1/memory_paragraph.py'])
    assert old==Path('rkv1/memory_paragraph.py').read_bytes()
    old_mem=ast.parse(subprocess.check_output(['git','show','v0.30.0:rkv1/memory.py']).decode())
    new_mem=ast.parse(Path('rkv1/memory.py').read_text('utf-8'))
    methods=lambda module:{n.name:ast.dump(n,include_attributes=False) for c in module.body if isinstance(c,ast.ClassDef) and c.name=='Memory' for n in c.body if isinstance(n,ast.FunctionDef)}
    a,b=methods(old_mem),methods(new_mem)
    assert all(a[k]==b[k] for k in ('search','_search','_verified_hits','lookup'))
    stop=lambda module:next(ast.dump(n,include_attributes=False) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STOP' for t in n.targets))
    assert stop(old_mem)==stop(new_mem)
    save(root/'algorithm-compatibility.json',{'reference_tag':'v0.30.0','best_unit_module_byte_identical':True,'best_unit_module_sha256':digest(old),
        'whole_paper_search_verified_hits_and_lookup_AST_identical':True,'STOP_definition_AST_identical':True,'no_ranking_parameter_change':True})


def overlaps(raw,jobs):
    normalized=lambda ss:digest(' '.join(' '.join(s.split()) for s in ss).encode())
    bodies={normalized(body) for _,_,body,_,_,_ in records(raw,1<<20)};questions={c['question_sha256'] for c in jobs}
    sc_raw=Path('data/scifact/corpus.jsonl').read_bytes();assert digest(sc_raw)==SCIFACT['corpus.jsonl']
    sc_bodies={normalized(json.loads(line)['abstract']) for line in sc_raw.splitlines()}
    out={'body_normalization':'Concatenate original array items with spaces, collapse whitespace only; retain case and punctuation. This is overlap detection, not source normalization.',
         'SciFact_exact_normalized_body_overlap':len(bodies & sc_bodies),'near_duplicates_or_true_paper_independence':None}
    for split in ('dev','train'):
        path=Path('data/scifact')/f'claims_{split}.jsonl';assert digest(path.read_bytes())==SCIFACT[path.name]
        sc_questions={digest(json.loads(line)['claim'].encode()) for line in path.read_bytes().splitlines()}
        _,qraw,qjobs=qasper_load(split);assert digest(qraw)==VERSIONS['0.3'][split]
        from rkv1.memory_qasper import records as qrecords
        q_bodies={normalized(body) for _,_,body,_,_,_ in qrecords(qraw,1<<20)}
        out['SciFact_'+split+'_question_text_overlap']=len(questions & sc_questions)
        out['QASPER_'+split+'_exact_normalized_body_overlap']=len(bodies & q_bodies)
        out['QASPER_'+split+'_question_text_overlap']=len(questions & {c['question_sha256'] for c in qjobs})
    return out


def legacy_probe(memory,wheel,query,key):
    assert digest(wheel.read_bytes())==OLD_WHEEL_SHA
    before=inventory(memory.root)
    with tempfile.TemporaryDirectory(prefix='rkv-legacy-v030-') as temp:
        work=Path(temp);target=work/'installed';assert not target.resolve().is_relative_to(Path.cwd().resolve())
        env={**clean_env(),'PIP_DISABLE_PIP_VERSION_CHECK':'1'}
        subprocess.run([sys.executable,'-m','pip','install','--no-index','--no-deps','--target',str(target),str(wheel.resolve())],cwd=work,env=env,check=True,stdout=subprocess.DEVNULL)
        code="""import pathlib,rkv1
from rkv1.memory import Memory
assert rkv1.__version__=='0.30.0' and pathlib.Path(rkv1.__file__).is_relative_to(pathlib.Path(TARGET))
m=Memory(MEMORY)
for call in (lambda:m.lookup(KEY),lambda:m.search(QUERY,top_k=20)):
 try:call()
 except ValueError as e:assert 'QASPER' in str(e),str(e)
 else:raise AssertionError('Old reader silently accepted new source')
""".replace('TARGET',repr(str(target))).replace('MEMORY',repr(str(memory.root))).replace('KEY',repr(key)).replace('QUERY',repr(query))
        subprocess.run([sys.executable,'-c',code],cwd=work,env={**env,'PYTHONPATH':str(target)},check=True)
    assert before==inventory(memory.root)
    return {'actual_v030_wheel_sha256':OLD_WHEEL_SHA,'installed_physically_outside_repository':True,
            'lookup_and_search_refuse_new_source_with_QASPER_schema_error':True,'Memory_tree_and_HEAD_unchanged':True}


def worker(args):
    _,jobs=load(args.input);random.Random(SEED+args.round).shuffle(jobs)
    m=Memory(args.memory);side=ParagraphIndex(args.sidecar);sid=m.current();before=inventory(m.root);aux=inventory(side.root)
    m.search(jobs[0]['question'],top_k=20);side.search(m,jobs[0]['question'],top_k=20)
    rows=[]
    for n,c in enumerate(jobs):
        plans=list(RETRIEVERS);random.Random(SEED+args.round+int(c['question_id_sha256'][:8],16)).shuffle(plans)
        found={};observations={}
        for plan in plans:
            start=time.perf_counter();cpu=time.process_time()
            result=m.search(c['question'],top_k=20,snapshot=sid) if plan=='whole-paper' else side.search(m,c['question'],top_k=20,snapshot=sid)
            wall=time.perf_counter()-start;cpu=time.process_time()-cpu;hits=result['hits'];found[plan]=hits
            assert all(h['source_bytes_verified'] is True for h in hits)
            keys=[h['key'] for h in hits];assert len(keys)==len(set(keys)) and len(keys)<=20
            rank=next((i+1 for i,k in enumerate(keys) if k==c['paper_key']),None)
            observations[plan]={'keys':keys,'ranks':[h['rank'] for h in hits],'evidence_identity_sha256':digest(_json(identity(hits))),
                'parent_metrics':parent_metrics(c['gold_keys'],keys),'reciprocal_rank_at20':1/rank if rank else 0,
                'read_wall_s':wall,'read_cpu_s':cpu,'winning_source_units':result.get('winning_source_units')}
        old={h['key']:identity([h])[0] for h in found['whole-paper']}
        for h in found['best-unit']:
            if h['key'] in old:assert identity([h])[0]==old[h['key']]
        rows.append({'question_id_sha256':c['question_id_sha256'],'question_sha256':c['question_sha256'],'paper_key':c['paper_key'],'retrievers':observations})
        if n%250==0:print(args.round,n+1,'/',len(jobs),flush=True)
    assert before==inventory(m.root) and aux==inventory(side.root)
    with args.result.open('x',encoding='utf-8',newline='\n') as f:
        json.dump({'round':args.round,'queries':rows,'warmup_read_operations':2,'peak_rss_bytes':peak_rss(),
            'Memory_and_auxiliary_trees_unchanged':True,'generation_calls':0},f,separators=(',',':'));f.write('\n')


def main(args):
    raw,jobs=load(args.input,args.fetch)
    if args.fetch:
        fetch_public(Path('data/scifact'),'scifact')
        fetch_public(Path('data/qasper-versions/v0.3'),'qasper')
    args.out.mkdir();args.work.mkdir();checks=implementation_checksums();save(args.out/'source-checksums.json',checks)
    compatibility(args.out)
    paths=[*sorted(Path('rkv1').rglob('*.py')),Path('rkv1/memory_demo.html')]
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in paths}
    save(args.out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
        'reader_module_bytes':Path('rkv1/memory_pubmedqa.py').stat().st_size,'native_specific_bytes':0,'model_bytes':0})
    projected=list(records(raw,1<<20));assert len(projected)==1000
    for _,_,_,off,original,_ in projected:assert raw[off:off+len(original)]==original
    save(args.out/'dataset-provenance.json',{'repository':'https://github.com/pubmedqa/pubmedqa','source_url':URL,'commit':COMMIT,'source_sha256':SHA,
        'source_bytes':len(raw),'original_filename':'ori_pqal.json','stored_filename':SOURCE_NAME,'records':1000,'unique_questions':1000,
        'context_items':sum(len(r[2]) for r in projected),'empty_context_records':sum(not r[2] for r in projected),
        'all_1000_original_member_offsets_lengths_and_raw_bytes_verified':True,'license_url':f'https://github.com/pubmedqa/pubmedqa/blob/{COMMIT}/LICENSE',
        'not_official_QA_or_test_score':True,'all_question_answer_prediction_metadata_excluded_from_projection':True,'overlap':overlaps(raw,jobs)})
    source=args.work/'source';source.mkdir();(source/SOURCE_NAME).write_bytes(raw)
    m=Memory.create(args.work/'memory');start=time.perf_counter();cpu=time.process_time();built=m.add(source,label='v031-pubmedqa-pqal')
    wall=time.perf_counter()-start;cpu=time.process_time()-cpu
    with m.store.snapshot(m.current()) as snap:assert snap.read_range(SOURCE_NAME)==raw
    start=time.perf_counter();ac=time.process_time();aux=ParagraphIndex.create(m,args.work/'sidecar');aw=time.perf_counter()-start;ac=time.process_time()-ac;side=aux.pop('index')
    build={'memory_build':built,'build_wall_s':wall,'build_cpu_s':cpu,'storage':m.stats(),'tree':inventory(m.root),
        'auxiliary_build':{**aux,'wall_including_checks_s':aw,'cpu_s':ac},'auxiliary_tree':inventory(side.root),'full_original_source_bytewise_verified':True}
    save(args.out/'build.json',build)
    body=next(s for _,_,ss,_,_,_ in projected for s in ss if s.strip())
    token=next(t for t in re.findall(r'[\w]+',body) if t.lower() not in STOP and len(t)>1)
    save(args.out/'legacy-reader-probe.json',legacy_probe(m,args.legacy_wheel,token,jobs[0]['paper_key']))
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,'logical_cpus':os.cpu_count(),
        'seed':SEED,'rounds':3,'generation_calls':0,'official_answer_accuracy':None,'evidence_coverage':None,'cold_cache':None,'cross_machine':None})
    for r in range(3):
        result=args.out/f'round{r}.json';start=time.perf_counter()
        subprocess.run([sys.executable,'-m','scripts.run_pubmedqa_transfer','--worker','--input',str(args.input.resolve()),'--round',str(r),
            '--memory',str(m.root),'--sidecar',str(side.root),'--result',str(result.resolve())],env=clean_env(),check=True)
        t=json.loads(result.read_text('utf-8'));t['process_wall_including_startup_s']=time.perf_counter()-start
        with result.open('w',encoding='utf-8',newline='\n') as f:json.dump(t,f,separators=(',',':'));f.write('\n')
    assert build['tree']==inventory(m.root) and build['auxiliary_tree']==inventory(side.root)
    with m.store.snapshot(m.current()) as snap:assert snap.read_range(SOURCE_NAME)==raw
    assert checks==implementation_checksums()
    save(args.out/'postconditions.json',{'all_original_bytes_restored':True,'Memory_and_auxiliary_trees_unchanged':True,'checksums_unchanged':True,'remote_model_calls':0})
    print('PubMedQA frozen transfer complete',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path('data/pubmedqa/ori_pqal.json'));p.add_argument('--fetch',action='store_true')
    p.add_argument('--legacy-wheel',type=Path);p.add_argument('--out',type=Path);p.add_argument('--work',type=Path);p.add_argument('--worker',action='store_true')
    p.add_argument('--round',type=int);p.add_argument('--memory',type=Path);p.add_argument('--sidecar',type=Path);p.add_argument('--result',type=Path)
    a=p.parse_args()
    if a.worker:worker(a)
    else:
        if a.legacy_wheel is None or a.out is None or a.work is None:p.error('--legacy-wheel, --out and --work are required for a campaign')
        main(a)
