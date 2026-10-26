"""Three independent workers, delayed explicit-SID synthetic evidence queries."""
import argparse
import copy
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time

from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from rkv1.evidence_path import trace
from rkv1.memory import Memory
from scripts.evidence_path_fixture import corpus,gold,audit
from scripts.run_memory_concurrency import save

ROOT=Path(__file__).resolve().parents[1]


def exclusive(path,raw):
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())


def ledger(folder):
    return {p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
            for p in sorted(folder.rglob('*')) if p.is_file()}


def worker(args):
    begin=time.perf_counter();cpu=time.process_time();work=Path(args.work)
    work.mkdir(exist_ok=False);src=work/'source';src.mkdir();path=src/'records.jsonl'
    m=Memory.create(work/'memory');snapshots={};ingests=[]
    manifest=json.loads((ROOT/'docs/evidence-path-inputs.json').read_text('utf-8'))
    for epoch in range(13):
        raw=corpus(epoch)
        expected=manifest['epochs'][epoch]
        assert digest(raw)==expected['sha256'] and len(raw)==expected['bytes']
        with path.open('wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        started=time.perf_counter();started_cpu=time.process_time()
        added=m.add(src,label=f'epoch-{epoch:02d}')
        ingests.append({'epoch':epoch,'source_bytes':len(raw),'source_sha256':digest(raw),
                        'wall_s':time.perf_counter()-started,'cpu_s':time.process_time()-started_cpu,
                        'snapshot_id':added['snapshot_id'],'commit':added})
        snapshots[epoch]=added['snapshot_id']
    ingestion_finished=time.perf_counter()-begin
    before=ledger(m.root);head=m.current();head_sha=digest((m.root/'HEAD.json').read_bytes())
    questions=[{'case_id':f'e{epoch:02d}-c{chain:02d}','epoch':epoch,'chain':chain,
                'root_key':f'doc:{chain*3}','snapshot_id':snapshots[epoch]}
               for epoch in (0,6,12) for chain in range(32)]
    random.Random(20261026+args.round).shuffle(questions)
    question_raw=json.dumps(questions,sort_keys=True,separators=(',',':')).encode()
    exclusive(work/'questions.json',question_raw);questions_fsynced=time.perf_counter()-begin
    save(work/'question-freeze.json',{'sha256':digest(question_raw),'count':96,'head':head,
         'ingestion_finished_elapsed_s':ingestion_finished,'questions_fsynced_elapsed_s':questions_fsynced,
         'scope':'Operationally delayed generation; deterministic fixture structure and seed publicly known'})
    first_query=time.perf_counter()-begin;cases=[];controls=[];first_complete=None
    def execute(question,**limits):
        start=time.perf_counter();start_cpu=time.process_time()
        proof=trace(m,question['root_key'],snapshot=question['snapshot_id'],**limits)
        elapsed=time.perf_counter()-start;elapsed_cpu=time.process_time()-start_cpu
        check_start=time.perf_counter();check_cpu=time.process_time()
        binding=audit(m,proof,snapshot=question['snapshot_id'],root_key=question['root_key'])
        audit_wall=time.perf_counter()-check_start;audit_cpu=time.process_time()-check_cpu
        persisted=time.perf_counter();persisted_cpu=time.process_time()
        remembered=m.remember({'case_id':question['case_id'],'synthetic_path':proof})
        return {'question':question,'proof':proof,'audit':binding,'trace_wall_s':elapsed,'trace_cpu_s':elapsed_cpu,
                'independent_audit_wall_s':audit_wall,'independent_audit_cpu_s':audit_cpu,
                'derived_write_wall_s':time.perf_counter()-persisted,
                'derived_write_cpu_s':time.process_time()-persisted_cpu,'derived':remembered}
    for question in questions:
        rec=execute(question);status,value,keys=gold(question['chain'],question['epoch'])
        rec['expected_status']=status;rec['expected_value']=value
        rec['expected_keys']=keys
        rec['gate_pass']=(rec['proof']['status']==status and rec['proof']['value']==value
                          and [h['key'] for h in rec['proof']['evidence']]==keys)
        if rec['proof']['status']=='complete' and first_complete is None:first_complete=rec
        cases.append(rec)
        save(work/'partial-cases.json',cases)
    for name,root_key,limits,expected in (
        ('budget','doc:0',{'max_evidence_bytes':1},'budget'),
        ('hop-limit','doc:0',{'max_hops':2},'hop-limit'),
        ('invalid-reference','doc:10000',{},'invalid-reference'),
        ('unknown-key','doc:999999',{},'missing')):
        q={'case_id':'control-'+name,'root_key':root_key,'snapshot_id':snapshots[0]}
        rec=execute(q,**limits);rec['expected_status']=expected
        rec['gate_pass']=rec['proof']['status']==expected and rec['proof']['value'] is None
        controls.append(rec)
    negative=[]
    for kind in ('wrong-snapshot','changed-quote'):
        tampered=copy.deepcopy(first_complete['proof']);question=first_complete['question']
        if kind=='wrong-snapshot':tampered['evidence'][0]['locator']['snapshot_id']='0'*64
        else:
            hop=tampered['evidence'][-1];hop['quote']+=' CHANGED'
            hop['quote_utf8_sha256']=digest(hop['quote'].encode('utf-8'))
        start=time.perf_counter()
        try:audit(m,tampered,snapshot=question['snapshot_id'],root_key=question['root_key'])
        except ValueError:rejected=True
        else:rejected=False
        negative.append({'kind':kind,'rejected':rejected,'audit_wall_s':time.perf_counter()-start})
    after=ledger(m.root)
    old_unchanged=all(after.get(k)==v for k,v in before.items())
    added_files={k:v for k,v in after.items() if k not in before}
    assert m.current()==head and digest((m.root/'HEAD.json').read_bytes())==head_sha
    save(work/'full-file-ledger.json',{'before_queries':before,'after_queries':after})
    save(args.worker_report,{'round':args.round,'ingests':ingests,'questions':cases,'controls':controls,
         'negative_audits':negative,'old_files_unchanged':old_unchanged,'head_unchanged':True,
         'added_files_only_derived':all(k.startswith('answers/') for k in added_files),
         'file_accounting':{'before_query_bytes':sum(v['bytes'] for v in before.values()),
                            'final_memory_bytes':sum(v['bytes'] for v in after.values()),
                            'derived_added_bytes':sum(v['bytes'] for v in added_files.values()),
                            'final_files':len(after),'full_ledger_sha256':digest((work/'full-file-ledger.json').read_bytes()),
                            'memory_stats':m.stats()},
         'question_sha256':digest(question_raw),'ingestion_finished_elapsed_s':ingestion_finished,
         'questions_fsynced_elapsed_s':questions_fsynced,'first_query_started_elapsed_s':first_query,
         'worker_wall_s':time.perf_counter()-begin,'worker_cpu_s':time.process_time()-cpu,'peak_rss_bytes':peak_rss(),
         'fixture_input_fsyncs':13,'question_freeze_fsyncs':1,'internal_memory_fsync_count':None,
         'physical_read_or_decompressed_bytes':None,'remote_model_calls':0,
         'no_numpy_imported':'numpy' not in sys.modules,'cold_cache':None,'cross_machine':None})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True)
    p.add_argument('--out');p.add_argument('--round',type=int);p.add_argument('--worker-report')
    args=p.parse_args()
    if args.round:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    checks=implementation_checksums();old=json.loads((ROOT/'results/v0.39.0/source-checksums.json').read_text('utf-8'))
    assert set(checks)==set(old)|{'evidence_path.py'}
    for name,sha in old.items():
        if name!='__init__.py':assert checks[name]==sha
    paths=('docs/EVIDENCE-PATHS.md','scripts/run_evidence_paths.py','scripts/evidence_path_fixture.py')
    tracked={path:digest((ROOT/path).read_bytes()) for path in paths}
    save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'rounds':3,
         'implementation_checksums':checks,'driver_protocol_sha256':tracked,'round_timeout_s':600,
         'fixture_manifest':json.loads((ROOT/'docs/evidence-path-inputs.json').read_text('utf-8')),
         'scope':'Synthetic explicit reference paths with known root and specified SID; not language reasoning'})
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n in range(1,4):
        report=out/f'round-{n}.json';command=[sys.executable,'-m','scripts.run_evidence_paths',
            '--work',str(work/f'round-{n}'),'--round',str(n),'--worker-report',str(report)]
        try:
            with (out/f'round-{n}.log').open('wb') as log:
                subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,
                               check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except Exception as exc:
            save(out/f'round-{n}-failure.json',{'error':type(exc).__name__,'return_code':getattr(exc,'returncode',None)})
        print('round',n,'record exists',report.exists(),flush=True)
    assert checks==implementation_checksums()
    assert tracked=={path:digest((ROOT/path).read_bytes()) for path in paths}


if __name__=='__main__':main()
