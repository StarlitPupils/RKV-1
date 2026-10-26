"""Frozen synthetic single-writer/four-reader snapshot consistency campaign."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from rkv1.memory import Memory

ROUNDS=3
UPDATES=80
READERS=4
DOCUMENTS=2048
QUERY='RKV33EPOCH'
ROOT=Path(__file__).resolve().parents[1]


def save(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def corpus(epoch):
    docs=[]
    for i in range(DOCUMENTS):
        sentences=([f'RKV33EPOCH epoch {epoch:04d} sentinel {i}.','Escaped snow: \u96ea; quoted "evidence".'] if i<4
                   else [f'Background calibration record {i:04d}.','Unchanged background observation.'])
        docs.append({'doc_id':i,'title':f'Synthetic record {i:04d}','abstract':sentences})
    return b''.join(json.dumps(d,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()+b'\r\n' for d in docs)


def expected_hashes():return {digest(corpus(g)):g for g in range(UPDATES+1)}


def audit(memory, result, hashes, retained_sid=None):
    """Independent source hash and every returned locator/text binding."""
    sid=result['snapshot_id'];hits=result['hits']
    assert len(hits)==4 and {h['key'] for h in hits}=={f'doc:{i}' for i in range(4)},'Sentinel set'
    if retained_sid is not None:assert sid==retained_sid,'Retained SID'
    with memory.store.snapshot(sid) as snap:
        assert set(snap.files)=={'corpus.jsonl'},'Source file set'
        raw=snap.read_range('corpus.jsonl');sha=digest(raw);epoch=hashes[sha]
    if retained_sid is not None:assert epoch==0,'Retained epoch'
    offset=0;expected={}
    for line in raw.splitlines(keepends=True)[:4]:
        doc=json.loads(line);expected['doc:'+str(doc['doc_id'])]=(offset,line,doc);offset+=len(line)
    for hit in hits:
        loc=hit['locator'];start,line,doc=expected[hit['key']]
        assert loc=={'snapshot_id':sid,'path':'corpus.jsonl','offset':start,'length':len(line),'sha256':digest(line)},'Locator'
        assert hit['title']==doc['title'] and hit['sentences']==doc['abstract'],'Projected text'
        assert hit['source_bytes_verified'] is True,'Source verification flag'
        assert f'epoch {epoch:04d} ' in hit['sentences'][0],'Mixed epoch'
    return {'epoch':epoch,'source_sha256':sha,'verified_records':len(hits),'source_bytes':len(raw)}


def wait_file(path, deadline):
    while not path.exists():
        if time.monotonic()>deadline:raise TimeoutError('Barrier deadline')
        time.sleep(.005)


def worker(args):
    base=Path(args.work);coord=base/'coord';m=Memory(base/'memory')
    if args.worker=='writer':
        events=[];error=None
        try:
            wait_file(coord/'START',time.monotonic()+30)
            for epoch in range(1,UPDATES+1):
                event={'epoch':epoch,'start_s':time.perf_counter()};events.append(event)
                raw=corpus(epoch);(base/'source/corpus.jsonl').write_bytes(raw)
                event['add_start_s']=time.perf_counter()
                result=m.add(base/'source',label=f'epoch-{epoch:04d}')
                event.update({'end_s':time.perf_counter(),'snapshot_id':result['snapshot_id'],
                              'source_sha256':digest(raw),'result':result})
        except Exception as exc:
            error={'type':type(exc).__name__,'message':str(exc).replace(str(base),'<work>')}
        finally:
            save(base/'writer.json',{'events':events,'error':error})
            (coord/'STOP').write_bytes(b'stop')
        return
    queries=[];error=None;reason=None;previous=-1
    try:
        hashes=expected_hashes();sid=(base/'initial-sid').read_text('ascii')
        audit(m,m.search(QUERY,top_k=20,snapshot=sid),hashes,sid)
        (coord/f'READY-{args.reader}').write_bytes(b'ready')
        wait_file(coord/'START',time.monotonic()+30)
        deadline=time.monotonic()+90;tail=0
        for q in range(20000):
            if time.monotonic()>deadline:raise TimeoutError('Reader duration cap')
            retained=(q%10==0);event={'query':q,'retained':retained,'start_s':time.perf_counter()};queries.append(event)
            result=m.search(QUERY,top_k=20,snapshot=sid if retained else None)
            event['end_s']=time.perf_counter();event['snapshot_id']=result['snapshot_id']
            event['reported_search_wall_s']=result['wall_s'];event['search_wall_s']=event['end_s']-event['start_s']
            audit_start=time.perf_counter();event.update(audit(m,result,hashes,sid if retained else None))
            event['audit_wall_s']=time.perf_counter()-audit_start
            if not retained:
                assert event['epoch']>=previous,'HEAD epoch went backward'
                previous=event['epoch']
            if (coord/'STOP').exists():
                tail+=1
                if tail>=20:reason='writer-stop-plus-20';break
        else:raise TimeoutError('Reader query cap')
    except Exception as exc:
        error={'type':type(exc).__name__,'message':str(exc).replace(str(base),'<work>')}
    finally:save(base/f'reader-{args.reader}.json',{'queries':queries,'error':error,'exit_reason':reason,'excluded_warm_queries':1})


def immutable(root):
    return {p.relative_to(root).as_posix():digest(p.read_bytes()) for p in sorted(root.rglob('*'))
            if p.is_file() and p.relative_to(root).as_posix()!='HEAD.json'}


def round_run(work, number):
    base=work/f'round-{number}';base.mkdir();(base/'coord').mkdir();source=base/'source';source.mkdir()
    raw=corpus(0);(source/'corpus.jsonl').write_bytes(raw)
    m=Memory.create(base/'memory');initial=m.add(source,label='epoch-0000');sid=initial['snapshot_id']
    (base/'initial-sid').write_text(sid,encoding='ascii');before=immutable(m.root);stats_before=m.stats()
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    processes=[];logs=[];parent_errors=[]
    def launch(role,reader=0):
        log=(base/f'{role}-{reader}.log').open('wb');logs.append(log)
        p=subprocess.Popen([sys.executable,'-m','scripts.run_memory_concurrency','--worker',role,'--reader',str(reader),'--work',str(base)],
                           cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        processes.append(p);return p
    try:
        readers=[launch('reader',i) for i in range(READERS)]
        deadline=time.monotonic()+30
        for i in range(READERS):wait_file(base/'coord'/f'READY-{i}',deadline)
        writer=launch('writer');(base/'coord/START').write_bytes(b'start')
        writer.wait(timeout=100)
    except Exception as exc:parent_errors.append({'type':type(exc).__name__,'message':str(exc).replace(str(base),'<work>')})
    finally:
        (base/'coord/STOP').write_bytes(b'stop')
        for p in processes:
            try:p.wait(timeout=35)
            except subprocess.TimeoutExpired:
                p.terminate();p.wait(timeout=10);parent_errors.append({'type':'TimeoutError','message':'Terminated this campaign owned child only'})
        for f in logs:f.close()
    def load(name):
        path=base/name
        return json.loads(path.read_text('utf-8')) if path.exists() else {'error':{'type':'MissingResult','message':name},'queries':[],'events':[]}
    writer=load('writer.json');readers=[load(f'reader-{i}.json') for i in range(READERS)]
    hashes=expected_hashes();history=[];history_errors=[]
    for epoch,which in [(0,sid)]+[(e['epoch'],e['snapshot_id']) for e in writer['events'] if 'snapshot_id' in e]:
        try:
            checked=audit(m,m.search(QUERY,top_k=20,snapshot=which),hashes)
            assert checked['epoch']==epoch
            history.append({'epoch':epoch,'snapshot_id':which,**checked})
        except Exception as exc:history_errors.append({'epoch':epoch,'type':type(exc).__name__,'message':str(exc).replace(str(base),'<work>')})
    after=immutable(m.root);unchanged=all(after.get(k)==v for k,v in before.items())
    completed=[e for e in writer['events'] if 'snapshot_id' in e]
    overlap=[]
    for reader in readers:
        current=[q for q in reader['queries'] if not q['retained'] and 'verified_records' in q]
        overlap.append(sum(any(q['start_s']<e['end_s'] and q['end_s']>e['add_start_s'] for e in completed) for q in current))
    good=(not parent_errors and not writer['error'] and len(completed)==UPDATES and not history_errors and len(history)==UPDATES+1
          and unchanged and not list((m.root/'answers').iterdir()) and m.current()==completed[-1]['snapshot_id']
          and all(not r['error'] and r['exit_reason']=='writer-stop-plus-20' for r in readers) and all(n>0 for n in overlap)
          and all(p.returncode==0 for p in processes)
          and all([q for q in r['queries'] if not q['retained'] and 'epoch' in q][-1]['epoch']==UPDATES for r in readers))
    return {'round':number,'writer':writer,'readers':readers,'parent_errors':parent_errors,'child_return_codes':[p.returncode for p in processes],
            'history':history,'history_errors':history_errors,'initial_immutable_files':len(before),'initial_immutable_files_unchanged':unchanged,
            'stats_before':stats_before,'stats_after':m.stats(),'current_searches_overlapping_actual_add_intervals_by_reader':overlap,
            'final_head':m.current(),'answers_files':len(list((m.root/'answers').iterdir())),'gate_passed':good}


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',required=True);p.add_argument('--out');p.add_argument('--worker',choices=('reader','writer'));p.add_argument('--reader',type=int,default=0)
    args=p.parse_args()
    if args.worker:worker(args);return
    assert args.out
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    checks=implementation_checksums();hashes=expected_hashes()
    context={'python':sys.version,'platform':platform.platform(),'cpu_count':os.cpu_count(),'clock':vars(time.get_clock_info('perf_counter')),
             'rounds':ROUNDS,'updates_per_round':UPDATES,'readers_per_round':READERS,'synthetic_documents':DOCUMENTS,
             'source_bytes':len(corpus(0)),'source_hashes_by_epoch':{str(g):sha for sha,g in hashes.items()},
             'implementation_checksums':checks,'driver_sha256':digest(Path(__file__).read_bytes()),
             'protocol_sha256':digest((ROOT/'docs/MEMORY-CONCURRENCY.md').read_bytes()),'remote_model_calls':0,'cold_cache':None,'cross_machine':None,
             'scope':'Synthetic mechanical single-writer/multiple-reader check; no process crash/power loss, multiwriter, production concurrency or inference quality claim.'}
    save(out/'environment.json',context)
    for n in range(1,ROUNDS+1):
        result=round_run(work,n);save(out/f'round-{n}.json',result)
        print('round',n,'gate',result['gate_passed'],'updates',len(result['writer']['events']),'queries',sum(len(r['queries']) for r in result['readers']),flush=True)
    assert checks==implementation_checksums(),'Runtime changed during campaign'
    assert context['driver_sha256']==digest(Path(__file__).read_bytes())
    assert context['protocol_sha256']==digest((ROOT/'docs/MEMORY-CONCURRENCY.md').read_bytes())


if __name__=='__main__':main()
