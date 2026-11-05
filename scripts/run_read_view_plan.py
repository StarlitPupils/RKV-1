"""A single writer and three real reader processes, not a random stress test."""
import sys,time,json,subprocess,contextlib
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from rkv1.memory import Memory
from rkv1.benchmark import peak_rss
from scripts.run_memory_fault_matrix import Producer
from scripts.read_view_fixture import source,ROLES,ledger,publish,wait,meta

def run(root,n=9,guard=None,failure_role=None):
    if type(n) is not int or n not in (9,17,129,513):raise ValueError('Fixed owned size required')
    if failure_role is not None and (failure_role!='pinned' or n!=9):raise ValueError('Failure injection only in tiny owned preparation')
    if n!=9 and guard is None:raise ValueError('Formal owned sizes require an external authorization guard')
    root=Path(root);root.mkdir(exist_ok=False);T,C=time.perf_counter(),time.process_time();ok=False;handles={};procs={};parents=[]
    auth_count=0
    def authorize():
        nonlocal auth_count
        if guard:
            evidence=guard()
            publish(root/f'AUTH-{auth_count:03}.json',evidence);auth_count+=1
    try:
        authorize()
        publish(root/'plan.json',{'size':n,'readers':list(ROLES),'writers':1,'updates':2,'operations_per_reader':11,'automatic_replay':False,'preparation_failure_role':failure_role})
        (root/'source').mkdir();(root/'originals').mkdir()
        for epoch in (0,1,2):(root/'originals'/f'{epoch}.jsonl').write_bytes(source(n,epoch))
        (root/'source'/'corpus.jsonl').write_bytes(source(n,0))
        m=Memory.create(root/'memory',compression='zlib',chunk_size=4096);old=m.add(root/'source',label='owned-revision-0')['snapshot_id']
        publish(root/'baseline-identities.json',ledger(root/'memory'));publish(root/'BASELINE',{'old_sid':old})
        def wait_marker(path):
            end=time.monotonic()+30
            while not path.exists():
                for role,(proc,t,c) in procs.items():
                    code=proc.poll()
                    if code is not None and code!=0:raise RuntimeError('Owned process failed; stop remaining schedule without replay')
                if time.monotonic()>end:raise TimeoutError('Owned barrier timed out: '+path.name)
                time.sleep(.005)
            return json.loads(path.read_bytes())
        with contextlib.ExitStack() as stack:
            for role in (*ROLES,'writer'):
                authorize()
                publish(root/(role+'-RESERVED'),{'before_spawn':True,'role':role,'missing_execution_unknown':True})
                log=stack.enter_context((root/(role+'.log')).open('xb'));t,c=time.perf_counter(),time.process_time()
                proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).with_name('run_read_view_worker.py')),str(root.resolve()),str(n),role,*(['fail-after-baseline'] if failure_role==role else [])],stdout=log,stderr=subprocess.STDOUT)
                procs[role]=(proc,t,c)
                started=wait_marker(root/(role+'-STARTED'));handles[role]=Producer(started['actual_pid'],proc)
                publish(root/(role+'-PARENT-STARTED'),{'launcher_pid':proc.pid,'actual_pid':started['actual_pid'],'role':role})
            for role in ROLES:wait_marker(root/role/'BASELINE-DONE')
            for epoch in (1,2):
                authorize()
                publish(root/f'WRITE-{epoch}',{'epoch':epoch});ready=wait_marker(root/f'WRITER-READY-{epoch}')
                publish(root/f'QUERY-{epoch}',{'epoch':epoch})
                for role in ROLES:wait_marker(root/role/f'QUERY-ENTERED-{epoch}')
                authorize()
                publish(root/f'PUBLISH-{epoch}',{'epoch':epoch,'all_three_queries_selected_SID':True})
                after=wait_marker(root/f'PUBLISHED-{epoch}');assert after['new_sid']==ready['new_sid'] and m.current()==after['new_sid']
                publish(root/f'READ-RELEASE-{epoch}',{'epoch':epoch,'after_actual_HEAD_publication':True})
                for role in ROLES:wait_marker(root/role/f'AFTER-DONE-{epoch}')
            for role,(proc,t,c) in procs.items():
                code=handles[role].exit();launch=proc.wait(timeout=30)
                row={'role':role,'actual_pid':handles[role].pid,'launcher_pid':proc.pid,'producer_observed_exit_code':code,'launcher_exit_code':launch,'whole_parent_wall_s':time.perf_counter()-t,'parent_self_CPU_s':time.process_time()-c,'retry':0}
                publish(root/(role+'-PARENT-EXIT'),row);parents.append(row)
                if code!=0 or launch!=0:raise RuntimeError('Stop fixed plan, no child replay')
        final=ledger(root/'memory');before=json.loads((root/'baseline-identities.json').read_bytes())
        for name,v in before.items():
            if name!='HEAD.json' and final.get(name)!=v:raise ValueError('Old source/index changed during concurrent reads')
        publish(root/'summary.json',{'size':n,'old_sid':old,'final_sid':m.current(),'reader_processes':3,'writer_processes':1,'updates':2,'saved_operations':33,'parent_exits':parents,'old_files_unchanged_except_HEAD':True,'private_owned_preparation':n==9,'no_model_calls_or_original_science':True})
        ok=True
    finally:
        for role,(proc,t,c) in procs.items():
            handle=handles.get(role)
            cleanup=False
            if proc.poll() is None:
                if handle:handle.kill()
                else:proc.kill()
                cleanup=True
                proc.wait(timeout=30)
            if handle:
                observed=handle.exit();handle.close()
            else:observed=None
            publish(root/(role+'-cleanup.json'),{'actual_pid':handle.pid if handle else None,'launcher_pid':proc.pid,'observed_producer_exit_code':observed,'launcher_exit_code':proc.returncode,'terminated_by_cleanup':cleanup,'execution_complete_not_inferred_from_cleanup':True})
        publish(root/'plan-finally.json',{'success':ok,'planned_operations':33,'planned_readers':3,'planned_writers':1,'whole_wall_s':time.perf_counter()-T,'self_CPU_s':time.process_time()-C,'peak_RSS_B':peak_rss(),'fulltree_CPU_RSS':None})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--size',type=int,default=9);a=p.parse_args();run(a.output,a.size)
