"""Frozen whole-index lossless frame matrix; no scientific question inference."""
import argparse,json,os,platform,subprocess,sys,time
from pathlib import Path
from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from scripts.index_frame import encode,decode
from scripts.postings_transform import canonical
from scripts.run_source_alignment import exclusive

ROOT=Path(__file__).resolve().parents[1]
CELLS=(('plain','raw'),('typed','raw'),('plain','zlib'),('typed','zlib'),('plain','zstd'),('typed','zstd'),('plain','lzma'),('typed','lzma'))
TRACKED=('scripts/postings_transform.py','scripts/index_frame.py','scripts/index_frame_fixture.py','scripts/run_index_frames.py','scripts/analyze_index_frames.py','scripts/run_source_alignment.py','scripts/source_alignment.py','tests/test_index_frame.py','tests/test_index_frame_worker.py','docs/INDEX-FRAME.md','docs/index-frame-inputs.json')

def worker(args):
    begin=time.perf_counter();cpu=time.process_time();folder=Path(args.work);folder.mkdir(exist_ok=False);manifest=json.loads(Path(args.manifest).read_bytes());source=manifest['datasets'][args.dataset]
    raw=Path(source['path']).read_bytes();assert digest(raw)==source['sha256'] and len(raw)==source['bytes'];before=digest(raw)
    t=time.perf_counter();c=time.process_time();frame,stats=encode(raw,method=args.method,codec=args.codec);encode_cpu=time.process_time()-c;encode_wall=time.perf_counter()-t
    t=time.perf_counter();c=time.process_time();exclusive(folder/'index.rkvpost',frame);frame_write={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'bytes':len(frame),'fsyncs':1}
    t=time.perf_counter();c=time.process_time();stored=(folder/'index.rkvpost').read_bytes();frame_read={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'application_returned_bytes':len(stored)}
    assert digest(stored)==digest(frame)
    ready_begin=time.perf_counter();ready_cpu=time.process_time();t=time.perf_counter();c=time.process_time();restored=decode(stored);decode_cpu=time.process_time()-c;decode_wall=time.perf_counter()-t
    t=time.perf_counter();c=time.process_time();model=json.loads(restored);load_cpu=time.process_time()-c;load_wall=time.perf_counter()-t
    ready_wall=time.perf_counter()-ready_begin;ready_cpu_s=time.process_time()-ready_cpu
    assert restored==raw and canonical(model)==raw and type(model['shared']['postings']) is dict
    t=time.perf_counter();c=time.process_time();exclusive(folder/'restored-index.json',restored);restored_write={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'bytes':len(restored),'fsyncs':1}
    t=time.perf_counter();c=time.process_time();recovered=(folder/'restored-index.json').read_bytes();assert digest(recovered)==before and recovered==raw and digest(Path(source['path']).read_bytes())==before
    verification={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c,'restored_application_returned_bytes':len(recovered),'source_recheck_application_returned_bytes':len(raw)}
    files={p.name:{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in folder.iterdir() if p.is_file()}
    report={'round':args.round,'dataset':args.dataset,'role':source['role'],'method':args.method,'codec':args.codec,'source_sha256':before,'restored_sha256':digest(restored),'frame_sha256':digest(frame),'source_bytes':len(raw),'frame_bytes':len(frame),'encode_stats':stats,
        'encode_wall_s':encode_wall,'encode_cpu_s':encode_cpu,'decode_wall_s':decode_wall,'decode_cpu_s':decode_cpu,'model_json_load_wall_s':load_wall,'model_json_load_cpu_s':load_cpu,
        'decode_to_model_ready_wall_s':ready_wall,'decode_to_model_ready_cpu_s':ready_cpu_s,'frame_write':frame_write,'frame_disk_read':frame_read,'restored_write':restored_write,'verification':verification,
        'semantic_index_documents':len(model['shared']['doc_lengths']),'semantic_index_tokens':len(model['shared']['postings']),'exact_original_bytes_and_model_ready':True,'original_unchanged':True,'files':files,'worker_wall_s':time.perf_counter()-begin,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'new_scientific_question_trials':0,'new_training_runs':0,'new_remote_model_calls':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None}
    exclusive(Path(args.worker_report),canonical(report)+b'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','work','out','dataset','worker-report'):p.add_argument('--'+name)
    p.add_argument('--round',type=int,choices=(1,2,3));p.add_argument('--method',choices=('plain','typed'));p.add_argument('--codec',choices=('raw','zlib','zstd','lzma'));args=p.parse_args()
    if args.round:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False);manifest=json.loads(Path(args.manifest).read_bytes());checks=implementation_checksums();programs={n:digest((ROOT/n).read_bytes()) for n in TRACKED}
    import zstandard
    exclusive(out/'environment.json',canonical({'python':sys.version,'platform':platform.platform(),'zstandard':zstandard.__version__,'workers':72,'datasets':list(manifest['datasets']),'cells':CELLS,'orders':['ABCDEFGH','HGFEDCBA','EFGHABCD'],'implementation_checksums':checks,'program_protocol_sha256':programs,'scope':'Canonical index bytes/consumer-ready loading, not question retrieval, neural inference or answers'})+b'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n,order in enumerate(('ABCDEFGH','HGFEDCBA','EFGHABCD'),1):
        for dataset in manifest['datasets']:
            for letter in order:
                method,codec=CELLS[ord(letter)-65];label=f'round-{n}-{dataset}-{method}-{codec}';report=out/(label+'.json');code=None;error=None;t=time.perf_counter()
                with (out/(label+'.log')).open('xb') as log:
                    try:code=subprocess.run([sys.executable,'-m','scripts.run_index_frames','--manifest',str(Path(args.manifest).resolve()),'--work',str(work/label),'--round',str(n),'--dataset',dataset,'--method',method,'--codec',codec,'--worker-report',str(report)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
                    except subprocess.TimeoutExpired:error='TimeoutExpired'
                exclusive(out/(label+'-parent.json'),canonical({'return_code':code,'error':error,'parent_full_process_wall_s':time.perf_counter()-t,'child_sha256':digest(report.read_bytes()) if report.exists() else None})+b'\n')
                print(label,code,flush=True)
    assert checks==implementation_checksums() and programs=={n:digest((ROOT/n).read_bytes()) for n in TRACKED}

if __name__=='__main__':main()
