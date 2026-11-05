"""One actual writer or persistent reader process; fixed owned barriers only."""
import time,sys,os,json
T,C=time.perf_counter(),time.process_time()
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from rkv1.memory import Memory
from rkv1.benchmark import peak_rss
from scripts.read_view_fixture import source,publish,wait,check_result,check_authorization
from rkv1.memory_view import ReadView

def writer(root,n):
    import rkv1.memory as module
    m=Memory(root/'memory');old=module._head
    try:
        for epoch in (1,2):
            wait(root/f'WRITE-{epoch}')
            check_authorization(root,n)
            (root/'source'/'corpus.jsonl').write_bytes(source(n,epoch))
            def head(path,value):
                if Path(path)==m.root/'HEAD.json':
                    publish(root/f'WRITER-READY-{epoch}',{'producer_pid':os.getpid(),'epoch':epoch,'new_sid':value['snapshot_id'],'before_head_ns':time.perf_counter_ns()})
                    wait(root/f'PUBLISH-{epoch}')
                    check_authorization(root,n)
                return old(path,value)
            module._head=head
            answer=m.add(root/'source',label=f'owned-revision-{epoch}')
            publish(root/f'PUBLISHED-{epoch}',{'producer_pid':os.getpid(),'epoch':epoch,'new_sid':answer['snapshot_id'],'after_head_ns':time.perf_counter_ns()})
        publish(root/'WRITER-COMPLETE',{'producer_pid':os.getpid(),'success':True})
    finally:module._head=old

def reader(root,n,role):
    folder=root/role;folder.mkdir(exist_ok=False)
    m=Memory(root/'memory');old_sid=m.current();view=m.pin() if role=='pinned' else None
    rows=[];expected_sids={0:old_sid};original=m._manifest
    def operation(op,epoch,label):
        check_authorization(root,n)
        if role=='pinned':target=view
        else:target=m
        kwargs={'snapshot':old_sid} if role=='explicit' else {}
        if op=='batch' and role=='current':kwargs={'snapshot':m.current()}
        if op=='search':result=target.search('RKV98PROBE',top_k=8,**kwargs)
        elif op=='lookup':result=target.lookup('doc:2',**kwargs)
        else:result=target.lookup_many(['doc:0','doc:1','doc:0'],max_source_bytes=4096,**kwargs)
        sid=expected_sids[epoch];audit=check_result(m,result,source(n,epoch),sid,op)
        row={'role':role,'operation':op,'phase':label,'expected_epoch':epoch,'result':result,'primary_audit':audit,'finished_ns':time.perf_counter_ns()}
        publish(folder/f'row-{len(rows):02}.json',row);rows.append(row)
    for op in ('search','lookup','batch'):operation(op,0,'baseline')
    if 'fail-after-baseline' in sys.argv[4:]:os._exit(76)
    publish(folder/'BASELINE-DONE',{'reader_pid':os.getpid(),'old_sid':old_sid})
    for epoch in (1,2):
        wait(root/f'QUERY-{epoch}')
        info=wait(root/f'WRITER-READY-{epoch}');expected_sids[epoch]=info['new_sid']
        def held(sid,query=None):
            publish(folder/f'QUERY-ENTERED-{epoch}',{'reader_pid':os.getpid(),'selected_sid':sid,'entered_ns':time.perf_counter_ns()})
            wait(root/f'READ-RELEASE-{epoch}')
            check_authorization(root,n)
            return original(sid,query)
        m._manifest=held
        try:operation('search',epoch-1 if role=='current' else 0,f'overlap-{epoch}')
        finally:m._manifest=original
        for op in ('search','lookup','batch'):operation(op,epoch if role=='current' else 0,f'after-{epoch}')
        publish(folder/f'AFTER-DONE-{epoch}',{'reader_pid':os.getpid(),'rows_saved':len(rows)})
    if view:
        copy=view.info();copy['snapshot_id']='0'*64
        assert view.snapshot_id==old_sid
        view.close();view.close();denied=0
        for call in (lambda:view.search('RKV98PROBE'),lambda:view.lookup('doc:2'),lambda:view.lookup_many(['doc:0']),view.__enter__):
            try:call()
            except ValueError:denied+=1
            else:raise AssertionError('Closed view accepted operation')
        assert denied==4
        publish(folder/'CLOSED-CONTROLS',{'refused_calls':denied,'closed':view.closed,'info_mutation_did_not_change_sid':True})
    publish(folder/'READER-COMPLETE',{'reader_pid':os.getpid(),'saved_operations':len(rows),'success':True})

if __name__=='__main__':
    root=Path(sys.argv[1]);n=int(sys.argv[2]);role=sys.argv[3];ok=False
    try:
        publish(root/(role+'-STARTED'),{'actual_pid':os.getpid(),'role':role})
        if role=='writer':writer(root,n)
        else:reader(root,n,role)
        ok=True
    finally:publish(root/(role+'-entry-finally.json'),{'success':ok,'actual_pid':os.getpid(),'entry_wall_s':time.perf_counter()-T,'self_CPU_s':time.process_time()-C,'peak_RSS_B':peak_rss(),'full_process_tree_CPU_RSS':None})
