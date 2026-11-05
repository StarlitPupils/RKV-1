"""Two owned writers; no retry of terminated operation A, B is a distinct intent."""
import time,sys,json,subprocess,contextlib
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from rkv1.memory import Memory
from rkv1.benchmark import peak_rss
from scripts.run_memory_fault_matrix import Producer
from rkv1.memory_writer import WriterScope
from scripts.writer_scope_fixture import PHASES,source,publish,wait,ledger,verify

def run(root,n=9,guard=None):
    if type(n) is not int or n not in (9,17,129,513) or n!=9 and guard is None:raise ValueError('Fixed owned size and formal authorization required')
    root=Path(root);root.mkdir(exist_ok=False);T,C=time.perf_counter(),time.process_time();rows=[];ok=False
    publish(root/'plan.json',{'size':n,'phases':list(PHASES),'writer_processes':6,'operations':18,'corruption_controls':9,'retries':0,'B_new_intent_never_replays_A':True})
    def auth(folder):
        if guard:
            i=len(list(folder.glob('AUTH-*.json')));publish(folder/f'AUTH-{i:03}.json',guard())
    try:
        for phase in PHASES:
            folder=root/phase;folder.mkdir();auth(folder);procs={};handles={};parents={}
            for name,epoch in [('originals',None),('source-old',0),('source-A',1),('source-B',2)]:
                (folder/name).mkdir()
                if epoch is not None:(folder/name/'corpus.jsonl').write_bytes(source(n,epoch))
            for e in (0,1,2):(folder/'originals'/f'{e}.jsonl').write_bytes(source(n,e))
            m=Memory.create(folder/'memory',compression='zlib',chunk_size=4096);sid0=m.add(folder/'source-old',label='owned-old')['snapshot_id'];pin=m.pin();before=ledger(folder/'memory');publish(folder/'BASELINE',{'old_sid':sid0,'files':before})
            def healthy():
                for role,(proc,t,c) in procs.items():
                    if proc.poll() is not None and role not in parents:raise RuntimeError('Owned writer ended before expected barrier')
            def marker(name):return wait(folder/name,healthy)
            def finish(role):
                proc,t,c=procs[role];handle=handles[role];actual=handle.exit();launch=proc.wait(timeout=30)
                v={'producer_pid':handle.pid,'launcher_pid':proc.pid,'producer_observed_exit':actual,'launcher_observed_exit':launch,'parent_wall_s':time.perf_counter()-t,'parent_self_CPU_s':time.process_time()-c,'observed_ns':time.perf_counter_ns(),'no_child_clock_if_no_finally':None};parents[role]=v;publish(folder/(role+'-PARENT-EXIT'),v);return v
            try:
                with contextlib.ExitStack() as stack:
                    for role in ('A','B'):
                        if role=='B':
                            marker('A-READY');publish(folder/'BEFORE-CONTENTION-IDENTITIES',ledger(folder/'memory',held=True))
                        auth(folder);publish(folder/(role+'-RESERVED'),{'before_spawn':True,'missing_execution_unknown':True})
                        log=stack.enter_context((folder/(role+'.log')).open('xb'));t,c=time.perf_counter(),time.process_time()
                        proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).with_name('run_writer_scope_worker.py')),str(folder.resolve()),str(n),phase,role],stdout=log,stderr=subprocess.STDOUT)
                        procs[role]=(proc,t,c);started=marker(role+'-STARTED');handles[role]=Producer(started['producer_pid'],proc)
                    ready=marker('A-READY');blocked=marker('B-CONTENTION');held_epoch=0 if phase=='before_HEAD' else 1
                    # Guard acquisition failure precedes any B source/Store mutation.
                    sid_held=m.current();held_files=ledger(folder/'memory',held=True);publish(folder/'HELD-IDENTITIES',held_files)
                    if held_files!=json.loads((folder/'BEFORE-CONTENTION-IDENTITIES').read_bytes()):raise ValueError('Refused contender mutated held Memory files')
                    queries=[]
                    def querygroup(label,epoch):
                        auth(folder)
                        for role in ('current','pin','explicit'):
                            result=pin.search('RKV99PROBE',top_k=8) if role=='pin' else m.search('RKV99PROBE',top_k=8,**({'snapshot':sid0} if role=='explicit' else {}))
                            expected=epoch if role=='current' else 0;sid=m.current() if role=='current' else sid0
                            proof=verify(m,result,source(n,expected),sid);q={'phase':label,'reader':role,'source_epoch':expected,'result':result,'primary_audit':proof};publish(folder/f'{label}-{role}-query.json',q);queries.append(q)
                    querygroup('A-held',held_epoch)
                    if phase=='clean_close':publish(folder/'A-RELEASE',{'allow_clean_release':True})
                    else:handles['A'].kill()
                    observed=finish('A');assert (observed['producer_observed_exit']==0)==(phase=='clean_close')
                    assert (folder/'A-CLOSED').exists()==(phase=='clean_close')
                    assert (folder/'A-ADD-RETURNED').exists()==(phase=='clean_close')
                    auth(folder);publish(folder/'A-EXIT-OBSERVED',observed)
                    bready=marker('B-READY');acquired=marker('B-ACQUIRED')
                    auth(folder)
                    try:m.writer()
                    except BlockingIOError:publish(folder/'PARENT-B-CONTENTION',{'refused':True,'observed_ns':time.perf_counter_ns()})
                    else:raise AssertionError('Parent acquired scope while writer B held it')
                    assert acquired['acquired_ns']>observed['observed_ns'] and bready['snapshot_id']==m.current()
                    querygroup('B-held',2);publish(folder/'B-RELEASE',{'allow_close':True});bexit=finish('B');assert bexit['producer_observed_exit']==0
                auth(folder)
                with m.writer() as probe:
                    assert not probe.info()['handle_inheritable']
                after=ledger(folder/'memory')
                for name,v in before.items():
                    if name!='HEAD.json' and after[name]!=v:raise ValueError('Old immutable file changed')
                pin.close();rows.append({'phase':phase,'old_sid':sid0,'A_known_sid':ready['known_sid'],'A_visible_epoch_while_held':held_epoch,'A_call_completed':phase=='clean_close','A_scope_release_reason':'clean close' if phase=='clean_close' else 'observed OS process exit','B_distinct_source_sid':bready['snapshot_id'],'B_never_replayed_A':True,'parents':parents,'saved_queries':6,'primary_source_return_B':sum(q['primary_audit']['whole_source_application_return_B'] for q in queries),'retained_old_files_unchanged':True,'final_probe_scope_acquired':True})
            finally:
                for role,(proc,t,c) in procs.items():
                    handle=handles.get(role);cleanup=False
                    if proc.poll() is None:
                        if handle:handle.kill()
                        else:proc.kill()
                        cleanup=True;proc.wait(timeout=30)
                    actual=handle.exit() if handle else None
                    if handle:handle.close()
                    publish(folder/(role+'-CLEANUP'),{'actual_producer_exit':actual,'launcher_exit':proc.returncode,'terminated_by_cleanup':cleanup,'completion_not_inferred_from_cleanup':True})
        publish(root/'summary.json',{'size':n,'cases':3,'fresh_writer_processes':6,'actual_A_process_terminations':2,'saved_source_queries':18,'rows':rows,'retries':0,'original_science_or_model_calls':0});ok=True
    finally:publish(root/'plan-finally.json',{'success':ok,'planned_cases':3,'completed_cases':len(rows),'planned_processes':6,'planned_queries':18,'whole_wall_s':time.perf_counter()-T,'self_CPU_s':time.process_time()-C,'peak_RSS_B':peak_rss(),'fulltree_CPU_RSS':None})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output)
