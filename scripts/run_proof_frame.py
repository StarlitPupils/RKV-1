"""Fixed proof frame worker/controller, no scientific prediction or semantic audit."""
import argparse,json,random,subprocess,time
from pathlib import Path
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from scripts.proof_frame import encode_frame,decode_frame,HEADER
from scripts.postings_transform import parse
from scripts.evidence_retrieval import encoded
from scripts.run_source_alignment import exclusive
ROOT=Path(__file__).resolve().parents[1]
METHODS={'A':('plain','zlib'),'B':('shared','zlib'),'C':('plain','zstd'),'D':('shared','zstd')};ORDERS=('ABCD','BADC','CDAB')
TRACKED=('scripts/proof_frame.py','scripts/audit_proof_frame.py','scripts/run_proof_frame.py','scripts/analyze_proof_frame.py','tests/test_proof_frame.py','docs/PROOF-FRAME.md','docs/proof-frame-inputs.json')
def load_inputs():return parse((ROOT/'docs/proof-frame-inputs.json').read_bytes())
def worker(a):
 t=time.perf_counter();cpu=time.process_time();folder=Path(a.work);folder.mkdir(exist_ok=False);manifest=load_inputs();method,codec=METHODS[a.role];rows=[];order=list(range(64));random.Random(20261027+a.round).shuffle(order)
 for index in order:
  entry=manifest['files'][index];source=Path(entry['path']);rt=time.perf_counter();rc=time.process_time();raw=source.read_bytes();read_wall=time.perf_counter()-rt;read_cpu=time.process_time()-rc
  if len(raw)!=entry['bytes'] or digest(raw)!=entry['sha256']:raise ValueError('Frozen original proof root differs')
  et=time.perf_counter();ec=time.process_time();frame=encode_frame(raw,method=method,codec=codec);encode_wall=time.perf_counter()-et;encode_cpu=time.process_time()-ec
  dt=time.perf_counter();dc=time.process_time();restored=decode_frame(frame,expected_root_sha256=entry['sha256']);decode_wall=time.perf_counter()-dt;decode_cpu=time.process_time()-dc
  if restored!=raw:raise ValueError('Actual frame failed byte-exact root recovery')
  restored_values=parse(restored)
  if len(restored_values)!=entry['certificate_count'] or [digest(encoded(c)) for c in restored_values]!=entry['original_certificate_SHA256_in_order']:raise ValueError('Reconstructed per-query certificate identity/order differs')
  wt=time.perf_counter();wc=time.process_time();exclusive(folder/('case-'+str(index)+'.rkvproof'),frame);exclusive(folder/('case-'+str(index)+'.restored'),restored);write_wall=time.perf_counter()-wt;write_cpu=time.process_time()-wc
  rows.append({'case_index':index,'certificate_count':entry['certificate_count'],'root_bytes':len(raw),'root_sha256':entry['sha256'],'frame_bytes':len(frame),'frame_sha256':digest(frame),'header_bytes':HEADER.size,'read_wall_s':read_wall,'read_cpu_s':read_cpu,'encode_wall_s':encode_wall,'encode_cpu_s':encode_cpu,'decode_wall_s':decode_wall,'decode_cpu_s':decode_cpu,'write_frame_and_restored_wall_s':write_wall,'write_cpu_s':write_cpu,'per_query_certificate_SHA_exact':True})
 metadata=encoded({'format':'RKVPRF1','method':method,'codec':codec,'cases':[{'case_index':e['case_index'],'root_sha256':e['sha256'],'root_bytes':e['bytes']} for e in manifest['files']]})+b'\n';exclusive(folder/'format-metadata.json',metadata)
 files={p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in folder.rglob('*') if p.is_file()};report={'round':a.round,'role':a.role,'method':method,'codec':codec,'case_roots':64,'format_metadata_bytes':len(metadata),'query_certificates':sum(r['certificate_count'] for r in rows),'rows':rows,'all_roundtrips_and_perquery_SHA_exact':True,'retained_frame_and_restored_files':files,'retained_frame_and_restored_total_bytes':sum(e['bytes'] for e in files.values()),'worker_wall_s':time.perf_counter()-t,'worker_cpu_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss(),'new_scientific_evaluations':0,'new_semantic_source_DAG_audits':0,'new_training_runs':0,'new_remote_model_calls':0,'frame_root_SHA_not_semantic_verification':True,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None};exclusive(Path(a.worker_report),encoded(report)+b'\n');print('role',a.role,'round',a.round,'exact64roots',flush=True)

def campaign(a):
 work=Path(a.work);out=Path(a.out);work.mkdir(exist_ok=False);out.mkdir(exist_ok=False);checks=implementation_checksums();manifest=load_inputs()
 for index,e in enumerate(manifest['files']):
  raw=Path(e['path']).read_bytes()
  if index!=e['case_index'] or len(raw)!=e['bytes'] or digest(raw)!=e['sha256']:raise ValueError('Input proof-root SHA/size differs')
 context={'runtime_checksums':checks,'tracked':{n:{'bytes':(ROOT/n).stat().st_size,'sha256':digest((ROOT/n).read_bytes())} for n in TRACKED},'input_manifest':manifest,'formal_workers':12,'orders':list(ORDERS),'formal_retries':0,'scope':'Seen certificate byte-layout transform only, no new reasoning or prediction/scientificscores'};exclusive(out/'worker-environment.json',encoded(context)+b'\n')
 for number,order in enumerate(ORDERS,1):
  for role in order:
   report=out/('round-'+str(number)+'-'+role+'.json');log=out/('round-'+str(number)+'-'+role+'.log');start=time.perf_counter();code=None;failure=None
   try:
    with log.open('xb') as f:subprocess.run([__import__('sys').executable,'-m','scripts.run_proof_frame','--worker','--work',str(work/('round-'+str(number)+'-'+role)),'--worker-report',str(report),'--round',str(number),'--role',role],check=True,stdout=f,stderr=subprocess.STDOUT,timeout=600)
    code=0
   except BaseException as exc:failure=type(exc).__name__;raise
   finally:exclusive(out/('round-'+str(number)+'-'+role+'-parent.json'),encoded({'parent_full_process_wall_s':time.perf_counter()-start,'return_code':code,'error':failure,'timeout_s':600,'retries':0})+b'\n')
 print('Frozen12proof-frameworkers complete, no science/NLI/answergain claim',flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path);p.add_argument('--worker-report',type=Path);p.add_argument('--round',type=int);p.add_argument('--role',choices=METHODS);a=p.parse_args();worker(a) if a.worker else campaign(a)
if __name__=='__main__':main()
