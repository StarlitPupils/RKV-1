"""Fixed catalogue workload, fresh vs finite pinned metadata, meterOFF/ON."""
import argparse,time,contextlib
from pathlib import Path
from rkv1.store import Store
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from scripts.postings_transform import canonical
from scripts.catalog_fixture import sources,queries,PATHS,COUNTS
from scripts.catalog_observer import observe_snapshots
from scripts.selected_witness import Witness
from scripts.audit_selected_witness import audit
from scripts.pinned_metadata import PinnedMetadata

def run(work,count,round_number,method,meter):
 if count not in COUNTS or round_number not in (1,2,3) or method not in ('fresh','pinned') or meter not in ('off','on'):raise ValueError('Fixed paired geometry required')
 start=time.perf_counter();cpu=time.process_time();work.mkdir(exist_ok=False);src=work/'source';src.mkdir();t=time.perf_counter();c=time.process_time();data=sources(count)
 for p,b in data.items():(src/p).write_bytes(b)
 generation={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};t=time.perf_counter();c=time.process_time();store=Store.create(work/'store',compression='zlib');sid=store.add(src)['snapshot_id'];ingest={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};selected=sum(len(data[p]) for p in PATHS);results=[];tracked=None;setup=None;observer=None;tbatch=time.perf_counter();cbatch=time.process_time()
 with (observe_snapshots() if meter=='on' else contextlib.nullcontext(None)) as observed:
  t=time.perf_counter();c=time.process_time()
  with (PinnedMetadata(store,sid) if method=='pinned' else contextlib.nullcontext(store)) as reader:
   setup={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};tracked=reader.tracked_metadata_bytes if method=='pinned' else None
   for index,(q,s,o) in enumerate(queries()):
    cut=len(observed['source_read_calls']) if observed is not None else None;t=time.perf_counter();c=time.process_time();proof=Witness(reader,sid,PATHS,source_byte_budget=selected).infer(q,work_budget=100000);a=audit(reader,sid,proof);wall=time.perf_counter()-t;cp=time.process_time()-c;assert proof['support_evidence_found'] is s and proof['opposite_evidence_found'] is o and proof['global_verdict'] is None and proof['selected_closure_complete'] and a['original_selected_DAG_verified'];assert len(proof['selection']['eligible_paths'])==count
    calls=observed['source_read_calls'][cut:] if observed is not None else None
    if calls is not None:assert all(x['path'] in PATHS for x in calls) and sum(x['returned_bytes'] for x in calls)==selected+a['auditor_selected_source_application_returned_bytes']
    raw=canonical(proof)
    with (work/('query-'+str(index)+'.json')).open('xb') as f:f.write(raw+b'\n')
    results.append({'query_index':index,'query':q,'support':s,'opposite':o,'global_verdict':None,'certificate_sha256':digest(raw),'certificate_bytes':len(raw),'selected_payload_B':selected,'auditor_API_reported_returned_B':a['auditor_selected_source_application_returned_bytes'],'observed_source_calls':calls,'query_wall_s':wall,'query_cpu_s':cp})
  observer=observed
 batch={'wall_s':time.perf_counter()-tbatch,'cpu_s':time.process_time()-cbatch,'scope':'Includes metadata setup, all8querys/proofpersistence, metadata close and observer close'}
 if observer is not None and method=='pinned':assert observer['constructor_calls']==1
 retained={p.relative_to(work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in work.rglob('*') if p.is_file()}
 return {'round':round_number,'count':count,'method':method,'meter':meter,'snapshot_id':sid,'queries':results,'query_count':8,'generation':generation,'ingest':ingest,'batch':batch,'metadata_setup':setup,'tracked_pinned_metadata_B':tracked,'tracked_cap_B':16777216 if method=='pinned' else None,'observer':observer,'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'peak_RSS_B':peak_rss(),'retained_files':retained,'retained_B':sum(e['bytes'] for e in retained.values()),'new_model_calls':0,'scientific_entailment_verified':False,'physical_SSD_B':None,'all_system_IO_B':None,'cold_cache':None,'cross_machine':None,'no_source_byte_or_compression_gain_claim':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--count',type=int,required=True);p.add_argument('--round',type=int,required=True);p.add_argument('--method',required=True);p.add_argument('--meter',required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=run(a.work,a.count,a.round,a.method,a.meter)
 with a.report.open('xb') as f:f.write(canonical(r)+b'\n')
