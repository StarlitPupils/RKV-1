"""Experimental catalogue scaling candidate; fixed evidence, no algorithm/semantic change."""
import copy,json,time,argparse
from pathlib import Path
from rkv1.store import Store
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from scripts.selected_witness import Witness
from scripts.audit_selected_witness import audit
from scripts.postings_transform import canonical
from scripts.catalog_fixture import sources,queries,PATHS,COUNTS
from scripts.catalog_observer import observe_snapshots

def run(work,count,round_number):
 if type(count) is not int or count not in COUNTS or type(round_number) is not int or round_number not in (1,2,3):raise ValueError('Frozen geometry required')
 start=time.perf_counter();cpu=time.process_time();work.mkdir(exist_ok=False);source=work/'source';source.mkdir();t=time.perf_counter();c=time.process_time();data=sources(count)
 for p,raw in data.items():(source/p).write_bytes(raw)
 generation={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};t=time.perf_counter();c=time.process_time();store=Store.create(work/'store',compression='zlib');sid=store.add(source)['snapshot_id'];ingest={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};snapshot=work/'store/snapshots'/(sid+'.rkvs');manifest={'bytes':snapshot.stat().st_size,'sha256':digest(snapshot.read_bytes()),'scope':'Stored file bytes only; not measured file read or physical IO'};selected=sum(len(data[p]) for p in PATHS);rows=[]
 for number,(query,support,opposite) in enumerate(queries()):
  with observe_snapshots() as meter:
   t=time.perf_counter();c=time.process_time();proof=Witness(store,sid,PATHS,source_byte_budget=selected).infer(query,work_budget=100000);producer={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};cut=len(meter['source_read_calls']);t=time.perf_counter();c=time.process_time();checked=audit(store,sid,proof);auditor={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c}
  assert proof['support_evidence_found'] is support and proof['opposite_evidence_found'] is opposite and proof['global_verdict'] is None and proof['selected_closure_complete'] and checked['original_selected_DAG_verified'] and checked['selected_closure_verified'];assert len(proof['selection']['eligible_paths'])==count and proof['selection']['selected_payload_bytes']==selected and not proof['selection']['full_eligible_selection']
  producer_B=sum(x['returned_bytes'] for x in meter['source_read_calls'][:cut]);audit_B=sum(x['returned_bytes'] for x in meter['source_read_calls'][cut:]);assert producer_B==selected and audit_B==checked['auditor_selected_source_application_returned_bytes'] and all(x['path'] in PATHS for x in meter['source_read_calls'])
  normalized=copy.deepcopy(proof['nodes'])
  for node in normalized:node['citation']['snapshot_id']=None
  raw=canonical(proof);path=work/('query-'+str(number)+'.json')
  with path.open('xb') as f:f.write(raw+b'\n')
  rows.append({'query_index':number,'query':query,'expected_support':support,'expected_opposite':opposite,'support_found':proof['support_evidence_found'],'opposite_found':proof['opposite_evidence_found'],'global_verdict':None,'selected_closure_complete':proof['selected_closure_complete'],'certificate_sha256':digest(raw),'canonical_certificate_bytes_excluding_newline':len(raw),'normalized_original_nodes_sha256':digest(canonical(normalized)),'selected_payload_bytes':selected,'producer_returned_bytes':producer_B,'auditor_returned_bytes':audit_B,'producer':producer,'auditor':auditor,'constructor_observer':meter})
 retained={p.relative_to(work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in work.rglob('*') if p.is_file()}
 return {'count':count,'round':round_number,'snapshot_id':sid,'generation':generation,'ingest':ingest,'snapshot_manifest':manifest,'rows':rows,'queries':8,'source_eligible_count':count,'selected_paths':PATHS,'unselected_explicit_opposite_present':True,'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss(),'retained_files':retained,'retained_bytes':sum(v['bytes'] for v in retained.values()),'metadata_file_bytes_not_application_read_bytes':True,'snapshot_observer_ON_overhead_unmeasured':True,'new_remote_model_calls':0,'new_training_runs':0,'scientific_entailment_verified':False,'cold_cache':None,'cross_machine':None,'physical_SSD_bytes':None,'all_system_IO_bytes':None}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--count',type=int,required=True);p.add_argument('--round',type=int,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=run(a.work,a.count,a.round)
 with a.report.open('xb') as f:f.write(canonical(r)+b'\n')
