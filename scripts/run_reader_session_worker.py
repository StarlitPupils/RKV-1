"""One fixed owned update/history workload; no human/scientific answer evaluation."""
import sys,time
from pathlib import Path
ENTRY,ENTRY_CPU=time.perf_counter(),time.process_time()
sys.path.insert(0,str(Path.cwd()))
import hashlib,json
from rkv1.store import Store
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from rkv1.experiments.paper_retriever import PaperRetriever
from scripts.scifact_graph import build_model,encoded
from rkv1.experiments.paper_session import PaperSession
from scripts.reader_session_fixture import corpus,requests,ROLES


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def write(path,v):
    with Path(path).open('xb') as stream:stream.write(canonical(v)+b'\n')


def run(size,role,out,*,revisions=12,guard=None):
    if type(size) is not int or not 1<=size<=257 or role not in ROLES or type(revisions) is not int or not 2<=revisions<=12:raise ValueError('Fixed bounded owned workload required')
    out=Path(out);out.mkdir(exist_ok=False);start,cpu=time.perf_counter(),time.process_time();success=False;completed=0;versions=[];trajectory=None
    source=out/'source';source.mkdir();models=out/'models';models.mkdir();originals=out/'originals';originals.mkdir()
    session=None if role=='fresh' else PaperSession(out/'store',reader_capacity=2 if role=='reuse_two' else 0)
    snapshots=[];query_wall=query_CPU=0.0;fresh_load_B=0
    try:
        if guard:guard()
        store=Store.create(out/'store',compression='zlib',chunk_size=65536,io_backend='bounded')
        begin,begin_CPU=time.perf_counter(),time.process_time()
        for revision in range(revisions):
            if guard:guard()
            raw=corpus(size,revision);(source/'corpus.jsonl').write_bytes(raw);(originals/(str(revision)+'.jsonl')).write_bytes(raw)
            t,c=time.perf_counter(),time.process_time()
            sid=store.add(source,label='owned-session')['snapshot_id'];model,_=build_model(raw,[]);payload=encoded(model)
            model_path=models/(str(revision)+'.json');model_path.write_bytes(payload)
            current={'revision':revision,'sid':sid,'source_SHA':digest(raw),'source_B':len(raw),'model_SHA':digest(payload),'model_B':len(payload),'model_path':str(model_path.resolve()),'update_and_model_wall_s':time.perf_counter()-t,'update_and_model_CPU_s':time.process_time()-c}
            snapshots.append(current);versions.append((sid,model_path,digest(payload)))
            for old,q in requests(revision):
                if guard:guard()
                target_sid,path,sha=versions[old];t,c=time.perf_counter(),time.process_time()
                if role=='fresh':
                    reader=PaperRetriever(store.root,target_sid,path,model_sha256=sha);result=reader.query(q);fresh_load_B+=reader.model_info()['model_bytes']
                else:result=session.query(q,snapshot_id=target_sid,model_path=path,model_sha256=sha)
                wall,CPU=time.perf_counter()-t,time.process_time()-c;query_wall+=wall;query_CPU+=CPU
                info=None if session is None else session.info()
                if info is not None and info['retained_readers']>info['reader_capacity']:raise AssertionError('Session exceeded explicit reader count bound')
                write(out/f'query-{completed:03}.json',{'index':completed,'revision':revision,'requested_revision':old,'question':q,'result':result,'packet_SHA':digest(canonical(result)),'query_wall_s':wall,'query_CPU_s':CPU,'session_info':info})
                completed+=1
        trajectory={'wall_s':time.perf_counter()-begin,'CPU_s':time.process_time()-begin_CPU,'query_wall_sum_s':query_wall,'query_CPU_sum_s':query_CPU,'scope':'All updates, originalsource copies, model builds, queries and exclusive response persistence; Store.create/session constructor in full worker scope'}
        counters={'fresh_model_load_return_B':fresh_load_B} if session is None else session.info()
        # Formal refusal checks use the same final state but are outside trajectory timing.
        checks=[];checker=PaperSession(store.root,reader_capacity=2)
        sid,path,sha=versions[-1];good=path.read_bytes();checker.query('alpha',snapshot_id=sid,model_path=path,model_sha256=sha)
        controls=out/'controls';controls.mkdir();(controls/'changed-model.bin').write_bytes(b'{}')
        path.write_bytes(b'{}')
        try:
            checker.query('alpha',snapshot_id=sid,model_path=path,model_sha256=sha)
        except ValueError:checks.append({'kind':'changed_model_file_on_hit','refused':True})
        else:raise AssertionError('Changed model not refused')
        finally:path.write_bytes(good)
        with store.snapshot(sid) as snap:ref=snap.files['corpus.jsonl']['chunks'][0]
        objpath=store.object_path(ref['id']);original=objpath.read_bytes();corrupt=original[:-1]+bytes([original[-1]^1]);(controls/'changed-selected-CAS.bin').write_bytes(corrupt);objpath.write_bytes(corrupt)
        try:
            checker.query('alpha',snapshot_id=sid,model_path=path,model_sha256=sha)
        except ValueError:checks.append({'kind':'changed_selected_CAS_on_hit','refused':True})
        else:raise AssertionError('Changed selected CAS not refused')
        finally:objpath.write_bytes(original)
        checker.close()
        try:checker.query('alpha',snapshot_id=sid,model_path=path,model_sha256=sha)
        except ValueError:checks.append({'kind':'closed_session','refused':True})
        else:raise AssertionError('Closed session not refused')
        if digest(path.read_bytes())!=sha or digest(objpath.read_bytes())!=digest(original):raise AssertionError('Refusal fixture original bytes not restored')
        write(controls/'identities.json',{'original_model_SHA':sha,'changed_model_SHA':digest(b'{}'),'original_selected_CAS_SHA':digest(original),'changed_selected_CAS_SHA':digest(corrupt),'original_bytes_restored':True,'negative_inputs_preserved':True})
        result={'size':size,'role':role,'revisions':revisions,'planned_queries':revisions*8,'completed_queries':completed,'snapshots':snapshots,'trajectory':trajectory,'session_counters':counters,'negative_controls':checks,'negative_control_session_counters':checker.info(),'new_training_labels':0,'new_model_API_calls':0,'new_provider_requests':0,'owned_process_workload_not_real_long_dialogue':True}
        write(out/'worker.json',result);success=True;return result
    finally:
        if session is not None:session.close()
        write(out/'worker-finally.json',{'success':success,'completed_queries':completed,'planned_queries':revisions*8,'full_wall_s':time.perf_counter()-start,'full_CPU_s':time.process_time()-cpu,'process_peak_RSS_B':peak_rss(),'reader_count_after_close':None if session is None else session.info()['retained_readers']})


if __name__=='__main__':
    import subprocess
    config=json.loads(Path(sys.argv[1]).read_bytes());size=int(sys.argv[2]);role=sys.argv[3];out=sys.argv[4]
    last=[0.0]
    def guard():
        if config['owned_test']:return
        if time.time()>=config['authorized_reference']:raise RuntimeError('Current authorized window ended')
        if time.monotonic()-last[0]<30:return
        subprocess.run([sys.executable,'.tools/read_quota.py'],check=True,stdout=subprocess.DEVNULL)
        q=json.loads(Path('.tools/last-quota-read.json').read_bytes())['result'];v=q['rateLimitsByLimitId']['codex']['primary']
        if not(q['ordinaryUsageAllowed'] is True and v['usedPercent']<100 and abs(v['resetsAt']-config['authorized_reference'])<=60):raise RuntimeError('Quota denied/unknown/changed')
        last[0]=time.monotonic()
    ok=False
    try:run(size,role,out,revisions=config['revisions'],guard=guard);ok=True
    finally:
        if Path(out).is_dir():write(Path(out)/'process-entry-finally.json',{'success':ok,'full_wall_s':time.perf_counter()-ENTRY,'full_CPU_s':time.process_time()-ENTRY_CPU,'process_peak_RSS_B':peak_rss(),'scope':'Before candidate imports to worker/body finally; parent includes interpreter startup and footer write'})
