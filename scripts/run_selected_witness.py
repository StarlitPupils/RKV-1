"""One fresh owned-fixture worker, partial evidence correctness only; no speed gate."""
import argparse,copy,json,time
from pathlib import Path
from unittest.mock import patch
from rkv1.core import digest
from rkv1.store import Store,Snapshot
from rkv1.benchmark import peak_rss
from scripts.selected_witness import Witness
from scripts.audit_selected_witness import audit
from scripts.selected_witness_fixture import sources,cases
from scripts.source_set_logic import SourceSetVerifier
from scripts.audit_source_set_logic import verify_set_certificate
from scripts.postings_transform import canonical

def exclusive(path,value):
 with path.open('xb') as f:f.write(canonical(value)+b'\n')

def run(work):
 start=time.perf_counter();cpu=time.process_time();work.mkdir(exist_ok=False);source=work/'source';source.mkdir()
 for p,b in sources().items():(source/p).write_bytes(b)
 store=Store.create(work/'store',compression='zlib');old=store.add(source)['snapshot_id'];updated=None;records=[];oldproofs={};preflights=[];strict=[];proofs=[]
 for stage in ('initial','updated','historical'):
  if stage=='updated':
   for p,b in sources(True).items():(source/p).write_bytes(b)
   updated=store.add(source)['snapshot_id'];assert updated!=old
  sid=updated if stage=='updated' else old
  rows=cases(stage)
  for row in rows:
   with store.snapshot(sid) as snap:size=sum(snap.files[p]['size'] for p in row['paths'])
   calls=[];original=Snapshot.read_range
   def measured(s,p,*args,**kwargs):
    raw=original(s,p,*args,**kwargs);calls.append({'path':p,'returned_bytes':len(raw)});return raw
   t=time.perf_counter();cput=time.process_time()
   with patch.object(Snapshot,'read_range',measured):
    c=Witness(store,sid,row['paths'],source_byte_budget=size).infer(row['query'],work_budget=row['work_budget']);cut=len(calls);a=audit(store,sid,c)
   assert c['support_evidence_found'] is row['support'] and c['opposite_evidence_found'] is row['opposite'] and c['global_verdict'] is None and a['global_verdict'] is None and a['original_selected_DAG_verified']
   assert all(x['path'] in row['paths'] for x in calls) and sum(x['returned_bytes'] for x in calls[:cut])==size and sum(x['returned_bytes'] for x in calls[cut:])==a['auditor_selected_source_application_returned_bytes']
   assert len(c['selection']['eligible_paths']) in (9,10) and not c['selection']['full_eligible_selection']
   key=row['id'].replace(stage+'-','')
   if stage=='initial':oldproofs[key]=copy.deepcopy(c)
   if stage=='historical':assert c==oldproofs[key]
   entry={'id':row['id'],'snapshot_id':sid,'expected_support':row['support'],'expected_opposite':row['opposite'],'support_found':c['support_evidence_found'],'opposite_found':c['opposite_evidence_found'],'global_verdict':None,'selected_closure_complete':c['selected_closure_complete'],'source_byte_budget':size,'producer_source_returned_bytes':sum(x['returned_bytes'] for x in calls[:cut]),'auditor_source_returned_bytes':sum(x['returned_bytes'] for x in calls[cut:]),'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-cput,'certificate_sha256':digest(canonical(c)),'independent_audit':a,'read_calls':calls};records.append(entry);proofs.append((sid,c));exclusive(work/(row['id']+'.json'),c)
  # One minus-one preflight per ordinary selection mode; zero returned payload.
  for row in rows[:8:2]:
   with store.snapshot(sid) as snap:size=sum(snap.files[p]['size'] for p in row['paths'])
   calls=[]
   with patch.object(Snapshot,'read_range',side_effect=lambda *a,**kw:calls.append(True)):
    try:Witness(store,sid,row['paths'],source_byte_budget=size-1)
    except ValueError:pass
    else:raise AssertionError('Undersized selection accepted')
   assert not calls;preflights.append({'id':row['id']+'-minus-one','rejected':True,'source_returned_bytes':0})
  with store.snapshot(sid) as snap:paths=sorted(p for p in snap.files if p.endswith('.logic.jsonl'))
  with patch.object(Snapshot,'read_range',side_effect=AssertionError('Old full-source refusal must not read payload')):
   oldc=SourceSetVerifier(store,sid,paths).infer(rows[0]['query']);olda=verify_set_certificate(store,sid,oldc)
  assert oldc['verdict']=='incomplete_source_set' and not olda['formal_derivation_verified'];strict.append({'stage':stage,'old_source_set_strict_refusal':True,'source_returned_bytes':0})
 # Ten falsifications, original full metadata/DAG and non-global contract.
 sid,base=proofs[1];tamper=[]
 for kind in ('global','universe','size','sha','path','flag','coverage','extra','work','closure'):
  bad=copy.deepcopy(base)
  if kind=='global':bad['global_verdict']='supported'
  elif kind=='universe':bad['selection']['eligible_paths']=bad['selection']['selected_paths']
  elif kind=='size':bad['selection']['selected_payload_bytes']+=1
  elif kind=='sha':bad['nodes'][0]['citation']['sha256']='0'*64
  elif kind=='path':bad['nodes'][0]['citation']['path']='filler0.logic.jsonl'
  elif kind=='flag':bad['opposite_evidence_found']=True
  elif kind=='coverage':bad['selection']['full_eligible_selection']=True
  elif kind=='extra':bad['verdict']='unknown'
  elif kind=='work':bad['work_budget']=True
  else:sid,before=proofs[0];bad=copy.deepcopy(before);bad['selected_closure_complete']=True
  try:audit(store,sid,bad)
  except ValueError:tamper.append({'kind':kind,'rejected':True})
  else:raise AssertionError('Tampered witness accepted: '+kind)
 assert len(records)==26 and len(preflights)==12 and len(strict)==3 and len(tamper)==10
 files={p.relative_to(work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in work.rglob('*') if p.is_file()}
 return {'H1_all_explicit_witness_flags_and_original_DAG':True,'H2_null_global_catalog_bounds_and_negative_controls':True,'cases':records,'preflight_controls':preflights,'old_strict_controls':strict,'tamper_controls':tamper,'historical_certificates_equal':8,'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss(),'all_retained_files':files,'retained_total_bytes':sum(x['bytes'] for x in files.values()),'scientific_entailment_verified':False,'new_training_runs':0,'new_remote_model_calls':0,'physical_SSD_bytes':None,'all_system_IO_bytes':None,'cold_cache':None,'cross_machine':None,'timing_scope':'Snapshot read observer ON only, no speed gate or observer overhead experiment'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();exclusive(a.report,run(a.work))
