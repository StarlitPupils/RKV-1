"""48 frozen encode/restore pairs, 96 fresh subprocesses, full self-contained models."""
import argparse
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
from rkv1.neural_frame import encode,decode
from scripts.neural_inputs import load
from scripts.run_memory_concurrency import save

ROOT=Path(__file__).resolve().parents[1]
METHODS=('neural','zlib','zstd','lzma')
ROUNDS=3


def worker(args):
    start=time.perf_counter();jobs=load(args.inputs,'test');meta,truth=next(x for x in jobs if x[0]['id']==args.id)
    loaded=time.perf_counter();directory=Path(args.work);frame_path=directory/'frame.rkvnn';result={}
    before={name:name in sys.modules for name in ('rkv1.neural_small','rkv1.arithmetic','zstandard','numpy')}
    if args.phase=='pack':
        model_start=time.perf_counter();model=Path(args.model).read_bytes() if args.method=='neural' else None
        if model is not None:assert digest(model)==args.model_sha
        model_wall=time.perf_counter()-model_start;operation=time.perf_counter()
        frame,info=encode(truth,method=args.method,**({'model':model} if model is not None else {}));codec_wall=time.perf_counter()-operation
        write=time.perf_counter()
        with frame_path.open('xb') as f:f.write(frame);f.flush();os.fsync(f.fileno())
        write_wall=time.perf_counter()-write
        result={'info':info,'frame_sha256':digest(frame),'frame_bytes':len(frame),'model_load_wall_s':model_wall,
                'codec_wall_s':codec_wall,'write_fsync_wall_s':write_wall,'fsyncs':1}
    else:
        read=time.perf_counter();frame=frame_path.read_bytes();read_wall=time.perf_counter()-read;operation=time.perf_counter()
        raw=decode(frame);codec_wall=time.perf_counter()-operation;write=time.perf_counter();restored=directory/'prefix.restored'
        with restored.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        write_wall=time.perf_counter()-write;audit=time.perf_counter();actual=restored.read_bytes()
        assert actual==truth and digest(actual)==meta['prefix_sha256']
        result={'frame_sha256':digest(frame),'frame_bytes':len(frame),'frame_read_wall_s':read_wall,'codec_wall_s':codec_wall,
                'write_fsync_wall_s':write_wall,'bytewise_and_SHA_equal':True,'restored_bytes':len(actual),'audit_wall_s':time.perf_counter()-audit,'fsyncs':1}
    result.update({'id':args.id,'method':args.method,'phase':args.phase,'input_load_wall_s':loaded-start,
                   'stage_wall_s':time.perf_counter()-start,'peak_rss_bytes':peak_rss(),'modules_preloaded_before_codec':before,
                   'no_numpy_imported':'numpy' not in sys.modules,'no_input_project_imported':not any(x in sys.modules for x in ('scipy','sympy'))})
    save(args.worker_report,result)


def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--model',required=True);p.add_argument('--model-freeze');p.add_argument('--out');p.add_argument('--work',required=True)
    p.add_argument('--phase',choices=('pack','restore'));p.add_argument('--id');p.add_argument('--method',choices=METHODS);p.add_argument('--model-sha');p.add_argument('--worker-report')
    args=p.parse_args()
    if args.phase:worker(args);return
    assert args.model_freeze and args.out
    model=Path(args.model).read_bytes();freeze=json.loads(Path(args.model_freeze).read_text('utf-8'));assert digest(model)==freeze['model_sha256']
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    jobs=load(args.inputs,'test');checks=implementation_checksums()
    tracked=('scripts/run_neural_small.py','scripts/train_neural_small.py','scripts/neural_inputs.py','docs/NEURAL-SMALL.md','docs/text-lanes-inputs.json')
    source_sha={name:digest((ROOT/name).read_bytes()) for name in tracked}
    save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'cpu_count':os.cpu_count(),'rounds':ROUNDS,'methods':METHODS,
                                'inputs':[m for m,_ in jobs],'model_sha256':digest(model),'model_bytes':len(model),'model_freeze':freeze,
                                'implementation_checksums':checks,'protocol_driver_and_training_sha256':source_sha,
                                'fresh_subprocess_phase_timeout_s':180,'remote_model_calls':0,'cold_cache':None,'cross_machine':None,
                                'scope':'Fixed archival-file prefixes, not entire scientific source files or unseen project domains; no model quality/production compression claim.'})
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n in range(1,ROUNDS+1):
        order=[(m['id'],method) for m,_ in jobs for method in METHODS];random.Random(20261026+n).shuffle(order);trials=[]
        for index,(name,method) in enumerate(order):
            directory=work/f'round-{n}'/f'{index:02d}-{method}';directory.mkdir(parents=True);trial={'round':n,'id':name,'method':method,'order':index,'error':None}
            try:
                for phase in ('pack','restore'):
                    report=directory/(phase+'.json');command=[sys.executable,'-m','scripts.run_neural_small','--inputs',str(Path(args.inputs).resolve()),'--model',str(Path(args.model).resolve()),
                             '--work',str(directory),'--phase',phase,'--id',name,'--method',method,'--model-sha',digest(model),'--worker-report',str(report)]
                    started=time.perf_counter()
                    with (directory/(phase+'.log')).open('wb') as log:subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    trial[phase]=json.loads(report.read_text('utf-8'));trial[phase]['process_wall_s']=time.perf_counter()-started
            except Exception as exc:trial['error']={'type':type(exc).__name__,'message':'Owned child failed or timed out; see retained private stage log','return_code':getattr(exc,'returncode',None)}
            trials.append(trial);save(out/f'round-{n}.json',{'round':n,'trials':trials})
            print(n,index,name,method,'ok' if not trial['error'] else trial['error']['type'],flush=True)
    assert checks==implementation_checksums() and digest(Path(args.model).read_bytes())==digest(model)
    assert source_sha=={name:digest((ROOT/name).read_bytes()) for name in tracked}


if __name__=='__main__':main()
