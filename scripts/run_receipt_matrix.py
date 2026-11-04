"""Private owned integration preparation, not a public/frozen scientific run."""
import sys,os,json,time,subprocess,shutil,hashlib
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from scripts.execution_receipts import create,inspect,encoded,sha,exclusive,append
from rkv1.benchmark import peak_rss
def meta(p):
 raw=p.read_bytes();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def ledger(root):return {p.relative_to(root).as_posix():meta(p) for p in root.rglob('*') if p.is_file()}
def save(path,v):exclusive(path,(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
def run(out,guard=None,preparation_only=True):
 out=Path(out);out.mkdir(exist_ok=False)
 start,cpu=time.perf_counter(),time.process_time();ok=False;rows=[];refusals=[]
 modes=('before_reserve','after_reserve','after_started','partial_artifact','after_artifact','after_receipt','after_stage_footer','all_stages_no_witness','success','kill_after_reserve','kill_after_artifact','exit_nonzero_allstages')
 expected_two=('unreserved','reserved','started','started','started','artifact_verified','stage_completed','stage_completed','stage_completed','reserved','started','stage_completed')
 try:
  for mode,two in zip(modes,expected_two):
   if guard:guard()
   folder=out/mode;anchor=create(folder,'owned_'+mode,['one','two','three']);t,c=time.perf_counter(),time.process_time()
   with (out/(mode+'.log')).open('xb') as stream:
    proc=subprocess.Popen([sys.executable,str(Path(__file__).with_name('run_receipt_worker.py')),str(folder.resolve()),anchor,mode],stdout=stream,stderr=subprocess.STDOUT)
    try:
     if mode.startswith('kill_'):
      end=time.monotonic()+10
      while not (folder/'READY').exists():
       if proc.poll() is not None or time.monotonic()>=end:raise RuntimeError('Owned kill fixture not ready')
       time.sleep(.005)
      proc.kill()
     code=proc.wait(timeout=20)
    finally:
     if proc.poll() is None:proc.kill();proc.wait()
   parent={'wall_s':time.perf_counter()-t,'self_CPU_s':time.process_time()-c,'actual_pid':proc.pid,'observed_exit_code':code,'child_CPU_s':None,'full_process_tree_peak_RSS_B':None}
   assert code==(0 if mode in ('success','all_stages_no_witness') else 76) if not mode.startswith('kill_') else code!=0
   lograw=(folder/'events.jsonl').read_bytes();wpath=out/(mode+'-witness.json')
   if mode!='all_stages_no_witness':
    exclusive(wpath,encoded({'schema':1,'run_id':'owned_'+mode,'plan_SHA':anchor,'events_SHA':sha(lograw),'child_pid':proc.pid,'observed_exit_code':code}))
   before=ledger(folder);r=inspect(folder,anchor,**({'witness_path':wpath,'expected_witness_SHA':sha(wpath.read_bytes())} if wpath.exists() else {}))
   assert before==ledger(folder) and r['states']['two']==two and r['campaign_complete']==(mode=='success')
   assert r['automatic_replay_permitted'] is False and r['unreserved_implies_unattempted'] is False
   if mode=='success':assert not inspect(folder,anchor)['campaign_complete']
   # Independent reference: exact external fixture bytes, event order and SHA chain.
   prev=anchor;states={i:'unreserved' for i in ('one','two','three')}
   for n,line in enumerate(lograw.splitlines()):
    e=json.loads(line);assert e['seq']==n and e['prev']==prev
    transitions={'reserved':'unreserved','started':'reserved','artifact_verified':'started','stage_completed':'artifact_verified'}
    assert states[e['stage']]==transitions[e['event']];states[e['stage']]=e['event'];prev=hashlib.sha256(line).hexdigest()
    if e['event']=='artifact_verified':
     payload=('owned-'+e['stage']).encode();assert (folder/'artifacts'/(e['stage']+'.bin')).read_bytes()==payload
     assert e['artifact']=={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
   assert states==r['states'] and prev==r['tip_SHA']
   parent.update(plan_SHA=anchor,events_SHA=sha(lograw));save(out/(mode+'-parent.json'),parent)
   rows.append({'case':mode,'parent':parent,'inspection':{k:v for k,v in r.items() if k not in ('records','plan')},'file_identities':before})
  baseline=out/'success';anchor=sha((baseline/'plan.json').read_bytes());basew=json.loads((out/'success-witness.json').read_bytes())
  controls=('unknown_event_field','bool_seq','bool_artifact_bytes','bool_plan_schema','duplicate_stage','bool_exit','wrong_run','wrong_events','wrong_witness_anchor','torn_log','artifact_corruption','truncated_with_witness','unknown_event','stale_writer_lock','duplicate_reserve')
  for mode in controls:
   folder=out/('control_'+mode);shutil.copytree(baseline,folder);w=dict(basew);wa=None;expected=anchor
   if mode in ('unknown_event_field','bool_seq','bool_artifact_bytes','unknown_event'):
    es=[json.loads(line) for line in (folder/'events.jsonl').read_bytes().splitlines()]
    if mode=='unknown_event_field':es[0]['unexpected']=True
    elif mode=='bool_seq':es[0]['seq']=False
    elif mode=='unknown_event':es[0]['event']='unknown'
    else:
     (folder/'artifacts'/'one.bin').write_bytes(b'');es[2]['artifact']={'bytes':False,'sha256':sha(b'')}
    prev=anchor;lines=[]
    for e in es:e['prev']=prev;b=encoded(e);prev=sha(b);lines.append(b)
    (folder/'events.jsonl').write_bytes(b'\n'.join(lines)+b'\n');w['events_SHA']=sha((folder/'events.jsonl').read_bytes())
   elif mode in ('bool_plan_schema','duplicate_stage'):
    p=json.loads((folder/'plan.json').read_bytes());p['schema']=True if mode=='bool_plan_schema' else 1
    if mode=='duplicate_stage':p['stages']=['one','one']
    (folder/'plan.json').write_bytes(encoded(p));expected=sha(encoded(p))
   elif mode=='bool_exit':w['observed_exit_code']=False
   elif mode=='wrong_run':w['run_id']='other'
   elif mode=='wrong_events':w['events_SHA']='0'*64
   elif mode=='torn_log':
    with (folder/'events.jsonl').open('ab') as stream:stream.write(b'{')
   elif mode=='artifact_corruption':(folder/'artifacts'/'one.bin').write_bytes(b'corrupt')
   elif mode=='truncated_with_witness':(folder/'events.jsonl').write_bytes((folder/'events.jsonl').read_bytes().splitlines(keepends=True)[0])
   elif mode=='stale_writer_lock':exclusive(folder/'writer.lock',b'uncertain')
   witness=out/(mode+'-witness.json');exclusive(witness,encoded(w));wa='0'*64 if mode=='wrong_witness_anchor' else sha(witness.read_bytes())
   if mode=='stale_writer_lock':
    assert not inspect(folder,expected,witness_path=witness,expected_witness_SHA=wa)['campaign_complete']
    try:append(folder,expected,'one','reserved')
    except FileExistsError:pass
    else:raise AssertionError('Stale lock allowed append')
   else:
    try:
     if mode=='duplicate_reserve':append(folder,expected,'one','reserved')
     else:inspect(folder,expected,witness_path=witness,expected_witness_SHA=wa)
    except ValueError:pass
    else:raise AssertionError('Corrupt fixture accepted '+mode)
   refusals.append(mode)
  save(out/'summary.json',{'private_preparation_only':preparation_only,'planned_owned_cases':12,'completed_owned_cases':12,'actual_OS_kill_cases':2,'intentional_nonzero_exit_cases':8,'success_exit_controls':2,'witness_bound_complete_controls':1,'corruption_and_stale_lock_controls':refusals,'independent_external_fixture_byte_and_chain_reference':True,'rows':rows,'model_provider_calls_or_scientific_inputs':0,'automatic_replay':False,'powerloss_directorysync_or_concurrent_writer_proof':False})
  ok=True
 finally:save(out/'check-finally.json',{'success':ok,'full_wall_s':time.perf_counter()-start,'self_CPU_s':time.process_time()-cpu,'peak_RSS_B':peak_rss(),'child_CPU_or_full_process_tree_RSS':None})

if __name__=="__main__":
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument("output",type=Path);args=parser.parse_args();run(args.output)
