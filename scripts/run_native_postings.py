"""Frozen existing-frame plain/Python-typed/native-typed load comparison."""
import argparse,json,os,platform,subprocess,sys,time
from pathlib import Path
from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from scripts.index_frame import decode
from scripts.postings_transform import canonical
from scripts.run_source_alignment import exclusive
ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/native_postings.py','scripts/postings_native_metadata.py','scripts/run_native_postings.py','scripts/analyze_native_postings.py','scripts/index_frame.py','scripts/postings_transform.py','scripts/run_source_alignment.py','rust/postings/Cargo.toml','rust/postings/src/lib.rs','tests/test_native_postings.py','docs/NATIVE-POSTINGS.md','docs/native-postings-inputs.json')

def load(frame,mode,binary):
    start=time.perf_counter();cpu=time.process_time()
    if mode=='native':
        from scripts.native_postings import decode_native
        raw=decode_native(frame,binary['path'],binary['sha256'])
    else:raw=decode(frame)
    model=json.loads(raw)
    return raw,model,{'model_ready_wall_s':time.perf_counter()-start,'model_ready_cpu_s':time.process_time()-cpu}

def worker(args):
    start=time.perf_counter();cpu=time.process_time();entry=json.loads(Path(args.manifest).read_bytes())['datasets'][args.dataset];binary=json.loads(Path(args.binary_manifest).read_bytes());frame_entry=entry['frames']['plain' if args.mode=='plain' else 'typed']
    source=Path(entry['path']).read_bytes();frame=Path(frame_entry['path']).read_bytes()
    if len(source)!=entry['bytes'] or digest(source)!=entry['sha256'] or len(frame)!=frame_entry['bytes'] or digest(frame)!=frame_entry['sha256']:raise ValueError('Frozen original/frame identity differs')
    restored,model,metrics=load(frame,args.mode,binary);assert restored==source and canonical(model)==source
    restored_on_disk=Path(frame_entry['existing_restored_path']).read_bytes();assert restored_on_disk==source
    assert digest(Path(entry['path']).read_bytes())==entry['sha256'] and digest(Path(frame_entry['path']).read_bytes())==frame_entry['sha256']
    native_sha=None
    if args.mode=='native':
        native_sha=digest(Path(binary['path']).read_bytes());assert native_sha==binary['sha256'] and Path(binary['path']).stat().st_size==binary['bytes']
    posts=model['shared']['postings'];maximum=max((len(v) for v in posts.values()),default=0)
    report={'round':args.round,'dataset':args.dataset,'role':entry['role'],'mode':args.mode,'source_sha256':digest(source),'frame_sha256':digest(frame),'restored_sha256':digest(restored),'source_bytes':len(source),'frame_bytes':len(frame),'existing_restored_on_disk_bytes':len(restored_on_disk),'exact_original_and_model':True,'native_binary_sha256':native_sha,'documents':len(model['shared']['doc_lengths']),'tokens':len(posts),'posting_pairs':sum(len(v) for v in posts.values()),'native_max_owned_u64_buffer_payload_bytes':16*maximum if args.mode=='native' else None,'native_buffer_transient_payload_upper_bound_bytes':32*maximum if args.mode=='native' else None,**metrics,'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'new_frame_encoding_calls':0,'new_scientific_question_trials':0,'new_training_runs':0,'new_remote_model_calls':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None}
    exclusive(Path(args.worker_report),canonical(report)+b'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','binary-manifest','out','dataset','worker-report'):p.add_argument('--'+name)
    p.add_argument('--round',type=int,choices=(1,2,3));p.add_argument('--mode',choices=('plain','typed','native'));args=p.parse_args()
    if args.round:worker(args);return
    out=Path(args.out).resolve();out.mkdir(exist_ok=False);manifest=json.loads(Path(args.manifest).read_bytes());checks=implementation_checksums();programs={n:digest((ROOT/n).read_bytes()) for n in TRACKED};binary_raw=Path(args.binary_manifest).read_bytes()
    exclusive(out/'environment.json',canonical({'python':sys.version,'platform':platform.platform(),'workers':27,'datasets':list(manifest['datasets']),'orders':['ABC','BCA','CAB'],'A':'plain/Python/LZMA','B':'typed/Python/LZMA','C':'typed/native/LZMA','implementation_checksums':checks,'program_protocol_sha256':programs,'binary_manifest_sha256':digest(binary_raw),'scope':'Known same-frame native kernel and complete-load diagnostic, not question inference/answers or general unseen science validation.'})+b'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n,order in enumerate(('ABC','BCA','CAB'),1):
        for dataset in manifest['datasets']:
            for letter in order:
                mode={'A':'plain','B':'typed','C':'native'}[letter];label=f'round-{n}-{dataset}-{mode}';report=out/(label+'.json');code=None;error=None;start=time.perf_counter()
                with (out/(label+'.log')).open('xb') as log:
                    try:code=subprocess.run([sys.executable,'-m','scripts.run_native_postings','--manifest',str(Path(args.manifest).resolve()),'--binary-manifest',str(Path(args.binary_manifest).resolve()),'--out',str(out),'--round',str(n),'--dataset',dataset,'--mode',mode,'--worker-report',str(report)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
                    except subprocess.TimeoutExpired:error='TimeoutExpired'
                exclusive(out/(label+'-parent.json'),canonical({'return_code':code,'error':error,'parent_full_process_wall_s':time.perf_counter()-start,'child_sha256':digest(report.read_bytes()) if report.exists() else None})+b'\n');print(label,code,flush=True)
    assert checks==implementation_checksums() and programs=={n:digest((ROOT/n).read_bytes()) for n in TRACKED} and binary_raw==Path(args.binary_manifest).read_bytes()

if __name__=='__main__':main()
