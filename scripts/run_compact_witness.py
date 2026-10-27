"""Seen-proof transport candidate, no new query/science evaluation."""
import argparse,json,time
from pathlib import Path
from rkv1.store import Store
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from scripts.postings_transform import canonical
from scripts.proof_frame import encode_frame as plain_encode,decode_frame as plain_decode
from scripts.compact_witness import encode_frame as compact_encode,decode_frame as compact_decode
from scripts.audit_compact_witness import verify

def run(work,input_meta,method,codec,round_number):
 if method not in ('plain','compact') or codec not in ('zstd','zlib') or round_number not in (1,2,3):raise ValueError('Fixed method/codec/round required')
 start=time.perf_counter();cpu=time.process_time();work.mkdir(exist_ok=False);manifest=json.loads(input_meta.read_bytes());assert len(manifest['cases'])==96;stores={};records=[]
 for case in manifest['cases']:
  raw=Path(case['path']).read_bytes();assert len(raw)==case['bytes'] and digest(raw)==case['sha256'];key=case['store_path']
  if key not in stores:stores[key]=Store(key,io_backend='bounded')
  store=stores[key];sid=case['snapshot_id'];t=time.perf_counter();c=time.process_time();frame=(plain_encode(raw,method='plain',codec=codec) if method=='plain' else compact_encode(raw,method='compact',codec=codec));encode={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};t=time.perf_counter();c=time.process_time();restored=(plain_decode(frame,expected_root_sha256=case['sha256']) if method=='plain' else compact_decode(frame,store=store,snapshot_id=sid,expected_root_sha256=case['sha256']));decode={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};assert restored==raw;t=time.perf_counter();c=time.process_time();checked=verify(frame,raw,store,sid);verification={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};name=case['id']
  for suffix,value in (('.frame',frame),('.restored',restored)):
   with (work/(name+suffix)).open('xb') as f:f.write(value)
  records.append({'id':name,'source_snapshot_id':sid,'source_sha256':case['sha256'],'source_bytes':len(raw),'frame_bytes':len(frame),'frame_sha256':digest(frame),'restored_sha256':digest(restored),'encode':encode,'decode':decode,'independent_verify':verification,'independent_header_catalog_mapping_and_original_DAG':checked,'compact_requires_original_store_metadata':method=='compact'})
 retained={p.relative_to(work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in work.rglob('*') if p.is_file()}
 return {'method':method,'codec':codec,'round':round_number,'cases':records,'case_count':96,'all96_exact_canonical_roots_and_independent_original_DAG':True,'total_frame_bytes':sum(r['frame_bytes'] for r in records),'total_original_bytes':sum(r['source_bytes'] for r in records),'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss(),'retained_files':retained,'retained_bytes':sum(e['bytes'] for e in retained.values()),'new_scientific_evaluations':0,'new_remote_model_calls':0,'new_training_runs':0,'shared_original_store_context_required_for_original_DAG_both_methods':True,'candidate_expansion_needs_context_before_original_verification':True,'cold_cache':None,'cross_machine':None,'physical_SSD_bytes':None,'all_system_IO_bytes':None}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--input-meta',type=Path,required=True);p.add_argument('--method',required=True);p.add_argument('--codec',required=True);p.add_argument('--round',type=int,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=run(a.work,a.input_meta,a.method,a.codec,a.round)
 with a.report.open('xb') as f:f.write(canonical(r)+b'\n')
