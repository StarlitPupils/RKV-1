import time,sys,os,json
T,C=time.perf_counter(),time.process_time()
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from rkv1.memory import Memory
from rkv1.benchmark import peak_rss
from rkv1.memory_writer import WriterScope
from scripts.writer_scope_fixture import source,publish,wait,authorize

root=Path(sys.argv[1]);n=int(sys.argv[2]);phase=sys.argv[3];role=sys.argv[4];ok=False;scope=None
publish(root/(role+'-STARTED'),{'producer_pid':os.getpid()})
try:
    m=Memory(root/'memory')
    if role=='A':
        import rkv1.memory as module
        authorize(root,n);scope=m.writer();old=module._head
        def head(path,value):
            if Path(path)==m.root/'HEAD.json' and phase=='before_HEAD':
                publish(root/'A-READY',{'producer_pid':os.getpid(),'known_sid':value['snapshot_id'],'scope_info':scope.info(),'ready_ns':time.perf_counter_ns()})
                wait(root/'A-RELEASE');authorize(root,n)
            answer=old(path,value)
            if Path(path)==m.root/'HEAD.json' and phase=='after_HEAD':
                publish(root/'A-READY',{'producer_pid':os.getpid(),'known_sid':value['snapshot_id'],'scope_info':scope.info(),'ready_ns':time.perf_counter_ns()})
                wait(root/'A-RELEASE');authorize(root,n)
            return answer
        try:
            module._head=head;answer=scope.add(root/'source-A',label='owned-intent-A')
        finally:module._head=old
        publish(root/'A-ADD-RETURNED',{'snapshot_id':answer['snapshot_id'],'producer_pid':os.getpid(),'returned_ns':time.perf_counter_ns()})
        if phase=='clean_close':
            publish(root/'A-READY',{'producer_pid':os.getpid(),'known_sid':answer['snapshot_id'],'scope_info':scope.info(),'ready_ns':time.perf_counter_ns()})
            wait(root/'A-RELEASE');authorize(root,n)
        scope.close();publish(root/'A-CLOSED',{'producer_pid':os.getpid(),'closed_ns':time.perf_counter_ns()})
    else:
        wait(root/'A-READY');authorize(root,n)
        try:m.writer()
        except BlockingIOError:
            publish(root/'B-CONTENTION',{'producer_pid':os.getpid(),'refused_before_add':True,'observed_ns':time.perf_counter_ns()})
        else:raise AssertionError('Competing writer acquired held OS scope')
        wait(root/'A-EXIT-OBSERVED');authorize(root,n)
        scope=m.writer();publish(root/'B-ACQUIRED',{'producer_pid':os.getpid(),'acquired_ns':time.perf_counter_ns(),'scope_info':scope.info()})
        answer=scope.add(root/'source-B',label='owned-distinct-intent-B')
        publish(root/'B-READY',{'producer_pid':os.getpid(),'snapshot_id':answer['snapshot_id'],'returned_ns':time.perf_counter_ns()})
        wait(root/'B-RELEASE');authorize(root,n);scope.close()
        denied=0
        for call in (lambda:scope.add(root/'source-B'),scope.__enter__):
            try:call()
            except ValueError:denied+=1
            else:raise AssertionError('Closed scope accepted use')
        publish(root/'B-CLOSED',{'producer_pid':os.getpid(),'closed_calls_refused':denied,'closed_ns':time.perf_counter_ns()})
    ok=True
finally:
    if scope is not None:scope.close()
    publish(root/(role+'-entry-finally.json'),{'success':ok,'producer_pid':os.getpid(),'entry_wall_s':time.perf_counter()-T,'self_CPU_s':time.process_time()-C,'peak_RSS_B':peak_rss(),'fulltree_CPU_RSS':None})
