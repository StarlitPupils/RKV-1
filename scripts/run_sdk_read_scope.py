"""Explicit SDK correctness worker, no new performance claim."""
import argparse,json,time,atexit
from pathlib import Path
from rkv1.store import Store
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from scripts.catalog_fixture import sources,queries,PATHS,COUNTS
from scripts.selected_witness import Witness
from scripts.audit_selected_witness import audit
from scripts.pinned_metadata import PinnedMetadata
from scripts.postings_transform import canonical

def run(work,count,round_number):
 if type(count) is not int or count not in COUNTS or type(round_number) is not int or round_number not in (1,2,3):raise ValueError('Fixed known-owned geometry required')
 start=time.perf_counter();cpu=time.process_time();work.mkdir(exist_ok=False);status={'success':False}
 def done():
  with (work/'finally-timing.json').open('x',encoding='utf-8') as f:json.dump({**status,'worker_full_wall_s':time.perf_counter()-start,'worker_full_cpu_s':time.process_time()-cpu,'peak_RSS_B':peak_rss()},f,indent=2);f.write('\n')
 atexit.register(done);src=work/'source';src.mkdir();data=sources(count)
 for p,b in data.items():(src/p).write_bytes(b)
 store=Store.create(work/'store',compression='zlib');sid=store.add(src)['snapshot_id'];records=[];controls=[];file_checks=range_checks=0;totalB=0
 with store.snapshot(sid) as original,store.read_scope(sid) as sdk,PinnedMetadata(store,sid) as ref:
  assert sdk.snapshot_id==sid and not sdk.closed
  for path,raw in data.items():
   a=sdk.read_range(path);b=original.read_range(path);assert a==b==raw;file_checks+=1;length=min(10,len(raw)-1);assert sdk.read_range(path,1,length)==original.read_range(path,1,length)==raw[1:1+length];range_checks+=1;totalB+=len(a)
  verify_report=sdk.verify();assert verify_report==original.process()
  for j,(q,s,o) in enumerate(queries()):
   a=Witness(sdk,sid,PATHS).infer(q,work_budget=100000);b=Witness(ref,sid,PATHS).infer(q,work_budget=100000);assert a==b and a['support_evidence_found'] is s and a['opposite_evidence_found'] is o and a['global_verdict'] is None;assert audit(sdk,sid,a)['original_selected_DAG_verified'];assert audit(ref,sid,b)['original_selected_DAG_verified'];raw=canonical(a)
   for name,value in (('sdk-'+str(j)+'.json',a),('reference-'+str(j)+'.json',b)):
    with (work/name).open('xb') as f:f.write(canonical(value)+b'\n')
   records.append({'query_index':j,'query':q,'expected_support':s,'expected_opposite':o,'certificate_sha256':digest(raw),'certificate_bytes':len(raw),'SDK_reference_same':True,'original_DAG_verified':True})
  with sdk.snapshot(sid) as view:
   try:view.files[PATHS[0]]['size']=0
   except TypeError:controls.append('nested_readonly_refusal')
   else:raise AssertionError('Mutable SDK scope')
  try:
   with sdk.snapshot('0'*64):pass
  except ValueError:controls.append('differentSID_refusal')
  else:raise AssertionError('SDK followed differentSID')
  tracked=sdk.tracked_metadata_bytes
 assert sdk.closed
 try:view.read_range(PATHS[0])
 except ValueError:controls.append('closed_read_refusal')
 else:raise AssertionError('SDK afterclose read')
 try:
  with store.read_scope(sid,metadata_budget=0):pass
 except ValueError:controls.append('zero_cap_refusal')
 else:raise AssertionError('Zero capaccepted')
 assert len(controls)==4 and len(records)==8 and file_checks==count+1 and range_checks==count+1
 files={p.relative_to(work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in work.rglob('*') if p.is_file()};status['success']=True
 return {'round':round_number,'count':count,'snapshot_id':sid,'records':records,'controls':controls,'full_file_comparisons':file_checks,'range_comparisons':range_checks,'source_recovery_B':totalB,'full_verify_report':verify_report,'tracked_metadata_B':tracked,'worker_wall_beforefinally_s':time.perf_counter()-start,'worker_cpu_beforefinally_s':time.process_time()-cpu,'peak_RSS_B':peak_rss(),'all_worker_files_before_finally':files,'retained_B_before_finally':sum(e['bytes'] for e in files.values()),'speed_measurement_or_claim':False,'new_model_calls':0,'scientific_entailment_verified':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--count',type=int,required=True);p.add_argument('--round',type=int,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=run(a.work,a.count,a.round)
 with a.report.open('xb') as f:f.write(canonical(r)+b'\n')
