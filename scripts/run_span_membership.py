"""Experimental IPC worker/parent; timing gates are algorithm phase plus full parent wall."""
import argparse,atexit,json,queue,subprocess,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from scripts.span_membership import SpanMembership
from rkv1.store import Store
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from scripts.catalog_fixture import sources,COUNTS
from scripts.catalog_commitment import from_store
from scripts.audit_catalog_commitment import verify
from scripts.postings_transform import canonical,parse
from scripts.late_membership import LateMembership
from scripts.bounded_membership import BoundedMembership

def write(path,value):
 with path.open('xb') as f:f.write(canonical(value)+b'\n')

def worker(work,count,round_number,method,report):
 if count not in COUNTS or round_number not in (1,2,3) or method not in ('retained','ephemeral','bounded','span'):raise ValueError('Fixed owned geometry/method required')
 start=time.perf_counter();cpu=time.process_time();work.mkdir(exist_ok=False);status={'success':False}
 def done():write(work/'finally-timing.json',{**status,'worker_full_wall_s':time.perf_counter()-start,'worker_full_CPU_s':time.process_time()-cpu,'peak_RSS_B':peak_rss()})
 atexit.register(done);src=work/'source';src.mkdir();data=sources(count)
 for n,b in data.items():(src/n).write_bytes(b)
 store=Store.create(work/'store',compression='zlib');sid=store.add(src)['snapshot_id'];rows=[];controls=[];application_B=0;prover=None;cache_trace=[]
 try:
  setup_t=time.perf_counter();setup_c=time.process_time()
  with store.read_scope(sid) as scope:
   setup={'wall_s':time.perf_counter()-setup_t,'CPU_s':time.process_time()-setup_c,'tracked_metadata_B':scope.tracked_metadata_bytes}
   t=time.perf_counter();c=time.process_time();prover=SpanMembership(scope,sid) if method=='span' else BoundedMembership(scope,sid) if method=='bounded' else LateMembership(scope,sid,method);build={'wall_s':time.perf_counter()-t,'CPU_s':time.process_time()-c}
   t=time.perf_counter();c=time.process_time();state_initial=prover.retained_state_B();state_timer={'wall_s':time.perf_counter()-t,'CPU_s':time.process_time()-c};constructed=time.time_ns()
   if method in ('bounded','span'):cache_trace.append({k:getattr(prover.cache,k) for k in ('hits','misses','hash_nodes','evictions','rewrites','max_retained_bound_B','max_provisional_bound_B')})
   print(canonical({'event':'ready','snapshot_id':sid,'anchor':prover.anchor,'constructed_at_ns':constructed,'count':count}).decode(),flush=True)
   message=parse(sys.stdin.buffer.readline());assert set(message)=={'event','expected_anchor_sha256','requests','generated_at_ns','request_sha256'} and message['event']=='late_requests' and len(message['requests'])==8 and message['generated_at_ns']>=constructed and digest(canonical(message['requests']))==message['request_sha256'] and prover.anchor_sha256==message['expected_anchor_sha256'];write(work/'late-requests.json',message)
   phase_wall=build['wall_s'];phase_CPU=build['CPU_s']
   for j,request in enumerate(message['requests']):
    assert set(request)=={'query_index','paths'} and request['query_index']==j and len(request['paths'])==2
    t=time.perf_counter();c=time.process_time();packet=prover.issue(request['paths']);read_B=0
    for proof in packet['members']:
     path=proof['entry']['path'];raw=scope.read_range(path);checked=verify(packet['anchor'],proof,raw,expected_anchor_sha256=message['expected_anchor_sha256'],expected_snapshot_id=sid,expected_path=path);assert checked['original_selected_bytes_membership_verified'];read_B+=len(raw)
    encoded=canonical(packet);write(work/('query-'+str(j)+'.json'),packet);wall=time.perf_counter()-t;CPU=time.process_time()-c;phase_wall+=wall;phase_CPU+=CPU;application_B+=read_B;rows.append({'query_index':j,'paths':request['paths'],'packet_sha256':digest(encoded),'packet_B':len(encoded),'application_returned_B':read_B,'wall_s':wall,'CPU_s':CPU})
   if method in ('bounded','span'):cache_trace.append({k:getattr(prover.cache,k) for k in ('hits','misses','hash_nodes','evictions','rewrites','max_retained_bound_B','max_provisional_bound_B')})
   t=time.perf_counter();c=time.process_time();state_final=prover.retained_state_B();state_timer['wall_s']+=time.perf_counter()-t;state_timer['CPU_s']+=time.process_time()-c;assert (state_final==state_initial if method not in ('bounded','span') else prover.cache.bound_B()<=65536)
   last=packet['members'][0];lastpath=last['entry']['path'];lastbytes=scope.read_range(lastpath)
   for name,expected_sha,payload in (('wrong_anchor','0'*64,lastbytes),('wrong_original',message['expected_anchor_sha256'],lastbytes+b'!')):
    try:verify(packet['anchor'],last,payload,expected_anchor_sha256=expected_sha,expected_snapshot_id=sid,expected_path=lastpath)
    except ValueError:controls.append(name)
    else:raise AssertionError('Accepted '+name)
   try:prover.issue(['missing.logic.jsonl'])
   except ValueError:controls.append('missing_path')
   else:raise AssertionError('Missing path accepted')
  try:prover.issue([lastpath])
  except ValueError:controls.append('closed_owner')
  else:raise AssertionError('Prover escaped finite read scope')
 finally:
  if prover is not None:prover.close()
 assert len(rows)==8 and len(controls)==4 and (prover.tree is None if method not in ('bounded','span') else len(prover.cache.entries)==0) and prover.anchor is None
 files={p.relative_to(work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in work.rglob('*') if p.is_file()};status['success']=True
 result={'round':round_number,'count':count,'method':method,'snapshot_id':sid,'queries':rows,'negative_controls':controls,'build':build,'scope_setup':setup,'algorithm_phase_wall_s':phase_wall,'algorithm_phase_CPU_s':phase_CPU,'state_measurement_outside_phase':state_timer,'bounded_cache_trace':cache_trace if method in ('bounded','span') else None,'bounded_cache_capacity_B':65536 if method in ('bounded','span') else None,'retained_extra_state_initial_B':state_initial,'retained_extra_state_final_B':state_final,'query_application_returned_B':application_B,'control_extra_application_returned_B':len(lastbytes),'request_sha256':message['request_sha256'],'constructor_completed_before_requests_generated':True,'closed_prover_fields_released':True,'all_worker_files_before_finally':files,'retained_B_before_finally':sum(e['bytes'] for e in files.values()),'new_model_calls':0,'logic_DAG_or_science_verified':False}
 write(report,result);print(canonical({'event':'done','report_sha256':digest(report.read_bytes())}).decode(),flush=True)

def execute_case(work,count,round_number,method,report,python,*,timeout_s=600):
 start=time.perf_counter();cpu=time.process_time();remaining=lambda:max(.01,timeout_s-(time.perf_counter()-start));q=queue.Queue();proc=None;code=None;error=None;stderr=report.with_suffix('.stderr.log');stdout=report.with_suffix('.stdout.log');ready=None;ref_timer=None;thread=None
 try:
  with stderr.open('xb') as err,stdout.open('xb') as out:
   proc=subprocess.Popen([str(python),'-u','-m','scripts.run_span_membership','--worker','--work',str(work),'--count',str(count),'--round',str(round_number),'--method',method,'--report',str(report)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err)
   def pump():
    for line in iter(proc.stdout.readline,b''):out.write(line);out.flush();q.put(line)
    q.put(None)
   thread=threading.Thread(target=pump,daemon=True);thread.start();line=q.get(timeout=remaining());assert line is not None;ready=parse(line);assert ready['event']=='ready' and ready['count']==count
   t=time.perf_counter();c=time.process_time();expected=sources(count);store=Store(work/'store');trusted=from_store(store,ready['snapshot_id']);assert trusted.anchor==ready['anchor'];names=sorted(n for n in expected if n.endswith('.logic.jsonl'));requests=[]
   for j in range(8):
    x=j%count;y=(count-1-j)%count
    if y==x:y=(y+1)%count
    requests.append({'query_index':j,'paths':sorted([names[x],names[y]])})
   ref_timer={'wall_s':time.perf_counter()-t,'CPU_s':time.process_time()-c};message={'event':'late_requests','expected_anchor_sha256':trusted.anchor_sha256,'requests':requests,'generated_at_ns':time.time_ns(),'request_sha256':digest(canonical(requests))};assert message['generated_at_ns']>=ready['constructed_at_ns'];write(report.with_suffix('.parent-requests.json'),message);proc.stdin.write(canonical(message)+b'\n');proc.stdin.flush();proc.stdin.close();code=proc.wait(timeout=remaining());assert code==0;line=q.get(timeout=remaining());assert line is not None;done=parse(line);assert done['event']=='done' and done['report_sha256']==digest(report.read_bytes());thread.join(timeout=remaining())
 except BaseException as exc:error=type(exc).__name__;raise
 finally:
  if proc is not None and proc.poll() is None:proc.kill();proc.wait()
  if thread is not None:thread.join(timeout=1)
  if proc is not None:
   for stream in (proc.stdin,proc.stdout):
    if stream is not None and not stream.closed:stream.close()
  write(report.with_suffix('.parent.json'),{'parent_full_wall_s':time.perf_counter()-start,'parent_own_CPU_s':time.process_time()-cpu,'parent_reference_validation':ref_timer,'exit_code':code,'error':error,'timeout_s':timeout_s,'formal_retries':0,'ready_observed':ready is not None})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true',required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--count',type=int,required=True);p.add_argument('--round',type=int,required=True);p.add_argument('--method',choices=('retained','ephemeral','bounded','span'),required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();worker(a.work,a.count,a.round,a.method,a.report)
