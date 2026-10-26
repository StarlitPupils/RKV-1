"""Fixed-boundary process hard exits, visible snapshots and single-shot recovery."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.memory import Memory
import rkv1.memory as memory_module
from rkv1.store import Store, OBJECT_MAGIC
from scripts.run_memory_concurrency import corpus, audit, save, QUERY

ROOT=Path(__file__).resolve().parents[1]
ROUNDS=3
CASES=('before-add','before-first-new-CAS-object','after-first-new-CAS-object',
       'after-CAS-snapshot-before-index','after-index-manifest-before-HEAD',
       'after-HEAD-temp-fsync-before-name','after-HEAD-name-before-add-return','success-control')
EXIT_CODE=77


def inventory(root):
    files={p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
           for p in sorted(root.rglob('*')) if p.is_file()}
    return {'files':files,'file_count':len(files),'logical_file_bytes':sum(v['bytes'] for v in files.values())}


def message(exc,base):
    text=str(exc)
    for name in (str(base).replace('\\','\\\\'),str(base)):text=text.replace(name,'<case>')
    return {'type':type(exc).__name__,'message':text,'errno':getattr(exc,'errno',None),'winerror':getattr(exc,'winerror',None)}


def worker(base,stage):
    """Hooks live only in this owned child; os._exit skips Python cleanup."""
    def stop(point,details=None):
        marker={'stage':point,'exit_code':EXIT_CODE,'details':details,'clock_s':time.perf_counter()}
        raw=(json.dumps(marker,sort_keys=True)+'\n').encode()
        with (base/'marker.json').open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os._exit(EXIT_CODE)
    if stage=='before-add':stop(stage)
    if stage in ('before-first-new-CAS-object','after-first-new-CAS-object'):
        original=Store._publish
        def publish(self,path,data):
            is_object=data.startswith(OBJECT_MAGIC)
            details={'relative_path':Path(path).relative_to(self.root).as_posix(),'published_bytes':len(data),'published_sha256':digest(data)}
            if is_object and stage.startswith('before-'):stop(stage,details)
            result=original(self,path,data)
            if is_object and stage.startswith('after-'):stop(stage,details)
            return result
        Store._publish=publish
    if stage=='after-CAS-snapshot-before-index':
        original=Store.add
        def add(self,*args,**kwargs):
            result=original(self,*args,**kwargs);stop(stage,{'snapshot_id':result['snapshot_id']})
        Store.add=add
    if stage in ('after-index-manifest-before-HEAD','after-HEAD-name-before-add-return'):
        original=memory_module._head
        def head(path,value):
            is_head=Path(path).name=='HEAD.json'
            if is_head and stage=='after-index-manifest-before-HEAD':stop(stage,value)
            result=original(path,value)
            if is_head and stage=='after-HEAD-name-before-add-return':stop(stage,value)
            return result
        memory_module._head=head
    if stage=='after-HEAD-temp-fsync-before-name':
        original=memory_module._replace_head
        def replace(source,target):
            if Path(target).name=='HEAD.json':
                raw=Path(source).read_bytes()
                stop(stage,{'pending_name':Path(source).name,'pending_bytes':len(raw),'pending_sha256':digest(raw)})
            return original(source,target)
        memory_module._replace_head=replace
    result=Memory(base/'memory').add(base/'source',label='e1')
    save(base/'worker-result.json',{'stage':stage,'result':result})
    # A non-control reaching here means the expected boundary was not triggered.
    if stage!='success-control':raise RuntimeError('Expected hard-exit hook did not fire')


def verify(memory,hashes,epoch,sid=None):
    result=memory.search(QUERY,top_k=20,snapshot=sid);checked=audit(memory,result,hashes)
    assert checked['epoch']==epoch,'Unexpected visible epoch'
    if sid is not None:assert result['snapshot_id']==sid
    return {'snapshot_id':result['snapshot_id'],**checked}


def case_run(work,round_index,stage):
    base=work/f'round-{round_index}'/stage;base.mkdir(parents=True)
    source=base/'source';source.mkdir();(source/'corpus.jsonl').write_bytes(corpus(0))
    memory=Memory.create(base/'memory');initial=memory.add(source,label='e0');sid0=initial['snapshot_id']
    before=inventory(memory.root);hashes={digest(corpus(n)):n for n in range(3)}
    initial_audit=verify(memory,hashes,0,sid0);(source/'corpus.jsonl').write_bytes(corpus(1))
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    start=time.perf_counter();timeout=False
    with (base/'worker.log').open('wb') as log:
        process=subprocess.Popen([sys.executable,'-m','scripts.run_memory_interruptions','--worker',stage,'--work',str(base)],
                                 cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:code=process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            timeout=True;process.terminate();code=process.wait(timeout=10)
    process_wall=time.perf_counter()-start
    errors=[];marker=None;control=None;observed={};recovery={};history=[]
    def check(label,fn):
        try:return fn()
        except Exception as exc:errors.append({'step':label,**message(exc,base)});return None
    after_exit=inventory(memory.root);exit_stats=check('stats-after-exit',memory.stats)
    if stage=='success-control':
        control=check('success-worker-result',lambda:json.loads((base/'worker-result.json').read_text('utf-8')))
        hook_ok=(code==0 and control is not None and control.get('stage')==stage and not (base/'marker.json').exists())
    else:
        marker=check('exit-marker',lambda:json.loads((base/'marker.json').read_text('utf-8')))
        hook_ok=(code==EXIT_CODE and marker is not None and marker.get('stage')==stage and marker.get('exit_code')==EXIT_CODE)
    expected_epoch=1 if stage in ('after-HEAD-name-before-add-return','success-control') else 0
    observed['current']=check('visible-HEAD-after-exit',lambda:verify(memory,hashes,expected_epoch))
    if expected_epoch==0 and observed['current'] is not None:
        if observed['current']['snapshot_id']!=sid0:errors.append({'step':'old-HEAD-identity','type':'AssertionError','message':'Initial SID advanced before expected publication'})
    observed['initial']=check('initial-SID-after-exit',lambda:verify(memory,hashes,0,sid0))
    def recover_one():
        started=time.perf_counter();added=memory.add(source,label='e1')
        return {'result':added,'wall_s':time.perf_counter()-started,'audit':verify(memory,hashes,1,added['snapshot_id'])}
    recovery['epoch1']=check('single-recovery-add-e1',recover_one)
    if recovery['epoch1'] is not None:
        def future():
            (source/'corpus.jsonl').write_bytes(corpus(2));started=time.perf_counter();added=memory.add(source,label='e2')
            return {'result':added,'wall_s':time.perf_counter()-started,'audit':verify(memory,hashes,2,added['snapshot_id'])}
        recovery['epoch2']=check('single-future-add-e2',future)
        pairs=[(0,sid0),(1,recovery['epoch1']['result']['snapshot_id'])]
        if recovery.get('epoch2') is not None:pairs.append((2,recovery['epoch2']['result']['snapshot_id']))
        for epoch,sid in pairs:
            result=check('retained-epoch-'+str(epoch),lambda epoch=epoch,sid=sid:verify(memory,hashes,epoch,sid))
            if result is not None:history.append(result)
    final=inventory(memory.root);final_stats=check('final-stats',memory.stats)
    originals={k:v for k,v in before['files'].items() if k!='HEAD.json'}
    exit_unchanged=all(after_exit['files'].get(k)==v for k,v in originals.items())
    final_unchanged=all(final['files'].get(k)==v for k,v in originals.items())
    staged_unchanged=all(final['files'].get(k)==v for k,v in after_exit['files'].items() if k!='HEAD.json')
    retained_pending={k:v for k,v in after_exit['files'].items() if k.startswith('.memory-head-')}
    pending_unchanged=all(final['files'].get(k)==v for k,v in retained_pending.items())
    expected_pending=(len(retained_pending)==1 if stage=='after-HEAD-temp-fsync-before-name' else len(retained_pending)==0)
    gate=(not timeout and hook_ok and not errors and exit_unchanged and final_unchanged and staged_unchanged and pending_unchanged and expected_pending
          and len(history)==3 and recovery.get('epoch2') is not None and not list((memory.root/'answers').iterdir()))
    return {'round':round_index,'stage':stage,'exit_code':code,'timeout':timeout,'process_wall_s':process_wall,
            'marker':marker,'worker_result':control,'hook_matched':hook_ok,'expected_visible_epoch':expected_epoch,'initial_snapshot_id':sid0,
            'initial_audit':initial_audit,'observed_after_exit':observed,'recovery':recovery,'history':history,'errors':errors,
            'initial_inventory':before,'after_exit_inventory':after_exit,'final_inventory':final,'after_exit_stats':exit_stats,'final_stats':final_stats,
            'initial_immutable_files_unchanged_after_exit':exit_unchanged,'initial_immutable_files_unchanged_after_recovery':final_unchanged,
            'all_staged_non_HEAD_files_unchanged_after_recovery':staged_unchanged,
            'pending_HEAD_files_retained_unchanged':pending_unchanged,'expected_pending_HEAD_count_observed':expected_pending,'gate_passed':gate}


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',required=True);p.add_argument('--out');p.add_argument('--worker',choices=CASES)
    args=p.parse_args();work=Path(args.work).resolve()
    if args.worker:worker(work,args.worker);return
    assert args.out;work.mkdir(exist_ok=False);out=Path(args.out).resolve();out.mkdir(exist_ok=False)
    checks=implementation_checksums()
    for name in checks:
        if name!='__init__.py':assert (ROOT/'rkv1'/name).read_bytes()==subprocess.check_output(['git','show','v0.34.0:rkv1/'+name],cwd=ROOT)
    tracked=('scripts/run_memory_interruptions.py','scripts/run_memory_concurrency.py','docs/MEMORY-INTERRUPTIONS.md')
    frozen={name:digest((ROOT/name).read_bytes()) for name in tracked}
    env={'python':sys.version,'platform':platform.platform(),'cpu_count':os.cpu_count(),'rounds':ROUNDS,'stages':CASES,
         'hard_exit_code':EXIT_CODE,'source_bytes':len(corpus(0)),'source_sha256_by_epoch':{str(n):digest(corpus(n)) for n in range(3)},
         'implementation_checksums':checks,'protocol_and_driver_sha256':frozen,'remote_model_calls':0,'cold_cache':None,'cross_machine':None,
         'scope':'Owned child os._exit(77), fixed Python hook boundaries, no Python cleanup; not power loss, kernel crash, external kill, multiwriter or inference quality proof.'}
    save(out/'environment.json',env)
    for n in range(1,ROUNDS+1):
        cases=[]
        for stage in CASES:
            result=case_run(work,n,stage);cases.append(result)
            save(out/f'round-{n}.json',{'round':n,'cases':cases})
            print('round',n,stage,'gate',result['gate_passed'],'exit',result['exit_code'],'errors',len(result['errors']),flush=True)
    assert checks==implementation_checksums()
    assert frozen=={name:digest((ROOT/name).read_bytes()) for name in tracked}


if __name__=='__main__':main()
