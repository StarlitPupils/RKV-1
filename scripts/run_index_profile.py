"""Paired profiler OFF/ON of unchanged stored typed/LZMA index frames."""
import argparse,cProfile,json,os,platform,pstats,subprocess,sys,time
from pathlib import Path
from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from scripts.index_frame import decode
from scripts.postings_transform import canonical
from scripts.run_source_alignment import exclusive
ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/run_index_profile.py','scripts/analyze_index_profile.py','scripts/index_frame.py','scripts/postings_transform.py','scripts/run_source_alignment.py','tests/test_index_profile.py','docs/INDEX-PROFILE.md','docs/index-profile-inputs.json')

def load(frame,profile=False):
    if type(profile) is not bool:raise ValueError('Explicit boolean profiler switch required')
    profiler=cProfile.Profile() if profile else None
    start=time.perf_counter();cpu=time.process_time()
    if profiler is not None:profiler.enable()
    try:
        raw=decode(frame);model=json.loads(raw)
    finally:
        if profiler is not None:profiler.disable()
    elapsed=time.perf_counter()-start;cpu_s=time.process_time()-cpu
    rows=None;total=None
    if profiler is not None:
        stats=pstats.Stats(profiler);rows=[];total=stats.total_tt
        for (file,line,name),(primitive,calls,self_s,cumulative,_) in stats.stats.items():
            path=Path(file)
            try:label=path.resolve().relative_to(ROOT).as_posix()
            except (ValueError,OSError):label=path.name
            rows.append({'file':label,'line':line,'function':name,'primitive_calls':primitive,'calls':calls,'instrumented_self_s':self_s,'instrumented_cumulative_s':cumulative})
        rows.sort(key=lambda r:(r['file'],r['line'],r['function']))
    return raw,model,{'model_ready_wall_s':elapsed,'model_ready_cpu_s':cpu_s,'profiler_total_self_s':total,'functions':rows}

def worker(args):
    start=time.perf_counter();cpu=time.process_time();entry=json.loads(Path(args.manifest).read_bytes())['datasets'][args.dataset]
    raw=Path(entry['path']).read_bytes();frame=Path(entry['frame_path']).read_bytes()
    if len(raw)!=entry['bytes'] or digest(raw)!=entry['sha256'] or len(frame)!=entry['frame_bytes'] or digest(frame)!=entry['frame_sha256']:raise ValueError('Frozen original/frame identity differs')
    restored,model,metrics=load(frame,args.profiler=='on')
    assert restored==raw and canonical(model)==raw
    assert digest(Path(entry['path']).read_bytes())==entry['sha256'] and digest(Path(entry['frame_path']).read_bytes())==entry['frame_sha256']
    posts=model['shared']['postings'];pairs=sum(len(x) for x in posts.values())
    report={'round':args.round,'dataset':args.dataset,'role':entry['role'],'profiler':args.profiler,'source_sha256':digest(raw),'frame_sha256':digest(frame),'restored_sha256':digest(restored),'source_bytes':len(raw),'frame_bytes':len(frame),'exact_original_and_model':True,'documents':len(model['shared']['doc_lengths']),'tokens':len(posts),'posting_pairs':pairs,**metrics,'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'new_scientific_question_trials':0,'new_training_runs':0,'new_remote_model_calls':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None}
    exclusive(Path(args.worker_report),canonical(report)+b'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','out','dataset','worker-report'):p.add_argument('--'+name)
    p.add_argument('--round',type=int,choices=(1,2,3));p.add_argument('--profiler',choices=('off','on'));args=p.parse_args()
    if args.round:worker(args);return
    out=Path(args.out).resolve();out.mkdir(exist_ok=False);manifest=json.loads(Path(args.manifest).read_bytes());checks=implementation_checksums();programs={n:digest((ROOT/n).read_bytes()) for n in TRACKED}
    exclusive(out/'environment.json',canonical({'python':sys.version,'platform':platform.platform(),'workers':18,'datasets':list(manifest['datasets']),'orders':['AB','BA','AB'],'A':'profiler off','B':'profiler on','implementation_checksums':checks,'program_protocol_sha256':programs,'scope':'Known index loading diagnostic. Instrumented self-time is not an unprofiled CPU fraction or Rust speed prediction.'})+b'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n,order in enumerate(('AB','BA','AB'),1):
        for dataset in manifest['datasets']:
            for letter in order:
                mode='off' if letter=='A' else 'on';label=f'round-{n}-{dataset}-{mode}';report=out/(label+'.json');code=None;error=None;start=time.perf_counter()
                with (out/(label+'.log')).open('xb') as log:
                    try:code=subprocess.run([sys.executable,'-m','scripts.run_index_profile','--manifest',str(Path(args.manifest).resolve()),'--out',str(out),'--round',str(n),'--dataset',dataset,'--profiler',mode,'--worker-report',str(report)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
                    except subprocess.TimeoutExpired:error='TimeoutExpired'
                exclusive(out/(label+'-parent.json'),canonical({'return_code':code,'error':error,'parent_full_process_wall_s':time.perf_counter()-start,'child_sha256':digest(report.read_bytes()) if report.exists() else None})+b'\n');print(label,code,flush=True)
    assert checks==implementation_checksums() and programs=={n:digest((ROOT/n).read_bytes()) for n in TRACKED}

if __name__=='__main__':main()
