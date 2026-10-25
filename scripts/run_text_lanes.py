"""Frozen byte-lane source-text experiment with fresh pack/restore processes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import time

from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.datasets import _download
from rkv1.text_frame import encode,decode,CODECS,MODES
from scripts.run_context_selection import SEED
from scripts.run_memory_history import clean_env
from scripts.run_units import save

INPUTS=Path('docs/text-lanes-inputs.json')
NOISE_SEED=b'RKV-1 text lanes v032 fixed noise seed20261025'


def inputs(data,fetch=False):
    spec=json.loads(INPUTS.read_text('utf-8'));rows=[*spec['files'],spec['negative_control']]
    if fetch:data.mkdir(parents=True,exist_ok=True)
    for r in rows:
        assert Path(r['id']).name==r['id']
        p=data/r['id']
        if not p.exists():
            if r['id']==spec['negative_control']['id']:raw=hashlib.shake_256(NOISE_SEED).digest(262144)
            elif fetch:raw=_download(r['source_url'],r['sha256'])
            else:raise FileNotFoundError(p)
            assert len(raw)==r['bytes'] and digest(raw)==r['sha256']
            with p.open('xb') as f:f.write(raw)
        assert p.stat().st_size==r['bytes'] and digest(p.read_bytes())==r['sha256']
    return rows


def timed(call):
    start=time.perf_counter();cpu=time.process_time();result=call()
    return result,{'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-cpu}


def write_synced(path,raw):
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())


def worker(args):
    def load_truth():
        raw=args.input.read_bytes();assert digest(raw)==args.sha;return raw
    raw,truth_time=timed(load_truth)
    preloaded={name:name in sys.modules for name in ('zlib','zstandard','lzma')}
    if args.phase=='pack':
        start=time.perf_counter();cpu=time.process_time()
        (frame,info),compute=timed(lambda:encode(raw,codec=args.codec,mode=args.mode))
        _,write=timed(lambda:write_synced(args.frame,frame))
        phase={'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-cpu}
        result={'phase':'pack','input_id':args.input_id,'input_sha256':args.sha,'round':args.round,'codec':args.codec,'mode':args.mode,
            'source_load':truth_time,'compute':compute,'output_write_fsync':write,'phase_wall_excluding_source_load':phase,
            'frame_bytes':len(frame),'frame_sha256':digest(frame),'encoder':info,'file_fsync_count':1}
    else:
        start=time.perf_counter();cpu=time.process_time();frame,read=timed(args.frame.read_bytes)
        restored,compute=timed(lambda:decode(frame));_,write=timed(lambda:write_synced(args.restored,restored))
        phase={'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-cpu}
        def audit():assert restored==raw and args.restored.read_bytes()==raw and digest(restored)==args.sha
        _,audit_time=timed(audit)
        result={'phase':'restore','input_id':args.input_id,'input_sha256':args.sha,'round':args.round,'codec':args.codec,'mode':args.mode,
            'benchmark_truth_load':truth_time,'frame_read':read,'compute':compute,'output_write_fsync':write,'phase_wall_excluding_truth_load_and_audit':phase,
            'bytewise_audit':audit_time,'frame_bytes':len(frame),'frame_sha256':digest(frame),'restored_bytes':len(restored),'bytewise_equal':True,'file_fsync_count':1}
    result.update(codec_preloaded_before_phase=preloaded,peak_rss_bytes=peak_rss(),remote_model_calls=0)
    assert not any(name=='scipy' or name.startswith('scipy.') or name=='sympy' or name.startswith('sympy.') for name in sys.modules)
    result['scientific_input_projects_not_imported']=True
    save(args.result,result)


def main(args):
    rows=inputs(args.data,args.fetch);args.out.mkdir();args.work.mkdir();checks=implementation_checksums();pin=digest(INPUTS.read_bytes())
    save(args.out/'source-checksums.json',checks);save(args.out/'dataset-provenance.json',json.loads(INPUTS.read_text('utf-8')))
    paths=[*sorted(Path('rkv1').rglob('*.py')),Path('rkv1/memory_demo.html')]
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in paths}
    save(args.out/'source-resource.json',{'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),
        'common_text_frame_source_bytes':Path('rkv1/text_frame.py').stat().st_size,'candidate_text_lanes_source_bytes':Path('rkv1/text_lanes.py').stat().st_size,
        'model_bytes':0,'dictionary_bytes':0,'native_specific_bytes':0})
    import zstandard
    save(args.out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'logical_cpus':os.cpu_count(),
        'zstandard':zstandard.__version__,'seed':SEED,'rounds':3,'codecs':list(CODECS),'modes':MODES,'source_manifest_sha256':pin,
        'raw_code_executed':False,'remote_model_calls':0,'cold_cache':None,'cross_machine':None,'directory_sync_or_power_loss':None,'inference_quality':None})
    trials=[]
    for rr in range(3):
        jobs=[(r,c,m) for r in rows for c in CODECS for m in MODES];random.Random(SEED+rr).shuffle(jobs)
        for n,(r,codec,mode) in enumerate(jobs):
            name=f'r{rr}-{n:03d}';frame=args.work/(name+'.rkvtext');restored=args.work/(name+'.restored')
            record={'input_id':r['id'],'family':r['family'],'round':rr,'codec':codec,'mode':mode,'stages':{}}
            for phase in ('pack','restore'):
                result=args.work/(name+'-'+phase+'.json');start=time.perf_counter()
                subprocess.run([sys.executable,'-m','scripts.run_text_lanes','--worker','--phase',phase,'--input',str((args.data/r['id']).resolve()),
                    '--input-id',r['id'],'--sha',r['sha256'],'--round',str(rr),'--codec',codec,'--mode',mode,'--frame',str(frame.resolve()),
                    '--restored',str(restored.resolve()),'--result',str(result.resolve())],env=clean_env(),check=True)
                v=json.loads(result.read_text('utf-8'));v['process_wall_including_startup_s']=time.perf_counter()-start;record['stages'][phase]=v
            assert record['stages']['pack']['frame_sha256']==record['stages']['restore']['frame_sha256']
            trials.append(record)
            if n%9==0:print(rr,n+1,'/',len(jobs),flush=True)
    inputs(args.data);assert pin==digest(INPUTS.read_bytes()) and checks==implementation_checksums()
    save(args.out/'trials.json',{'trials':trials,'all_189_restores_bytewise_equal':True,'source_manifest_and_inputs_unchanged':True,'remote_model_calls':0})
    print('Text lane 189 pack/restore pairs complete; no input code executed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=Path('data/text-lanes'));p.add_argument('--fetch',action='store_true')
    p.add_argument('--out',type=Path);p.add_argument('--work',type=Path);p.add_argument('--worker',action='store_true');p.add_argument('--phase',choices=('pack','restore'))
    p.add_argument('--input',type=Path);p.add_argument('--input-id');p.add_argument('--sha');p.add_argument('--round',type=int);p.add_argument('--codec',choices=CODECS);p.add_argument('--mode',choices=MODES)
    p.add_argument('--frame',type=Path);p.add_argument('--restored',type=Path);p.add_argument('--result',type=Path)
    a=p.parse_args()
    if a.worker:worker(a)
    else:
        if a.out is None or a.work is None:p.error('--out and --work are required')
        main(a)
