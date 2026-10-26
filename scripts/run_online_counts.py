"""Frozen CPU-only online statistics versus ordinary codecs,75 pairs."""
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
from rkv1.online_frame import encode,decode,METHODS
from scripts.online_inputs import load
from scripts.run_memory_concurrency import save

ROOT=Path(__file__).resolve().parents[1]


def worker(args):
    start=time.perf_counter();cpu=time.process_time()
    jobs=load(args.inputs);meta,raw=next((m,r) for m,r in jobs if m['id']==args.id)
    loaded=time.perf_counter();directory=Path(args.work);frame_path=directory/'frame.rkvonline'
    if args.phase=='pack':
        operation=time.perf_counter();operation_cpu=time.process_time()
        frame,info=encode(raw,method=args.method)
        codec_cpu=time.process_time()-operation_cpu;codec_wall=time.perf_counter()-operation
        writing=time.perf_counter()
        with frame_path.open('xb') as stream:stream.write(frame);stream.flush();os.fsync(stream.fileno())
        result={'info':info,'codec_wall_s':codec_wall,'codec_cpu_s':codec_cpu,
                'write_fsync_wall_s':time.perf_counter()-writing}
    else:
        reading=time.perf_counter();frame=frame_path.read_bytes();read_wall=time.perf_counter()-reading
        operation=time.perf_counter();operation_cpu=time.process_time()
        restored=decode(frame)
        codec_cpu=time.process_time()-operation_cpu;codec_wall=time.perf_counter()-operation
        writing=time.perf_counter();restored_path=directory/'slice.restored'
        with restored_path.open('xb') as stream:stream.write(restored);stream.flush();os.fsync(stream.fileno())
        write_wall=time.perf_counter()-writing;checking=time.perf_counter()
        actual=restored_path.read_bytes();assert actual==raw and digest(actual)==meta['sha256']
        result={'codec_wall_s':codec_wall,'codec_cpu_s':codec_cpu,'frame_read_wall_s':read_wall,
                'write_fsync_wall_s':write_wall,'audit_wall_s':time.perf_counter()-checking,
                'bytewise_and_SHA_equal':True}
    result.update({'id':args.id,'method':args.method,'phase':args.phase,'frame_sha256':digest(frame),
                   'frame_bytes':len(frame),'fsyncs':1,'input_load_wall_s':loaded-start,
                   'stage_wall_s':time.perf_counter()-start,'stage_cpu_s':time.process_time()-cpu,
                   'peak_rss_bytes':peak_rss(),'no_numpy_imported':'numpy' not in sys.modules,
                   'no_input_project_imported':not any(x in sys.modules for x in ('scipy','sympy'))})
    save(args.worker_report,result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',required=True);p.add_argument('--manifest');p.add_argument('--out')
    p.add_argument('--work',required=True);p.add_argument('--phase',choices=('pack','restore'))
    p.add_argument('--method',choices=METHODS);p.add_argument('--id');p.add_argument('--worker-report')
    args=p.parse_args()
    if args.phase:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve()
    work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    jobs=load(args.inputs);manifest=json.loads(Path(args.manifest).read_text('utf-8'))
    assert [m for m,_ in jobs]==manifest['inputs']
    checks=implementation_checksums()
    old=json.loads((ROOT/'results/v0.38.0/source-checksums.json').read_text('utf-8'))
    assert set(checks)==set(old)|{'online_counts.py','online_frame.py'}
    for name,value in old.items():
        if name!='__init__.py':assert checks[name]==value
    tracked=('scripts/run_online_counts.py','scripts/online_inputs.py','docs/ONLINE-COUNTS.md')
    identity={rel:digest((ROOT/rel).read_bytes()) for rel in tracked}
    save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'cpu_count':os.cpu_count(),
         'inputs':manifest,'implementation_checksums':checks,'driver_protocol_sha256':identity,
         'methods':list(METHODS),'rounds':3,'fresh_subprocess_phase_timeout_s':180,
         'remote_model_calls':0,'cold_cache':None,'cross_machine':None})
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n in range(1,4):
        order=[(m['id'],method) for m,_ in jobs for method in METHODS]
        random.Random(20261026+n).shuffle(order);trials=[]
        for index,(name,method) in enumerate(order):
            directory=work/f'round-{n}'/f'{index:02d}-{method}';directory.mkdir(parents=True)
            trial={'round':n,'id':name,'method':method,'order':index,'error':None}
            try:
                for phase in ('pack','restore'):
                    report=directory/(phase+'.json')
                    command=[sys.executable,'-m','scripts.run_online_counts','--inputs',str(Path(args.inputs).resolve()),
                             '--work',str(directory),'--phase',phase,'--id',name,'--method',method,'--worker-report',str(report)]
                    started=time.perf_counter()
                    with (directory/(phase+'.log')).open('wb') as log:
                        subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
                                       timeout=180,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    trial[phase]=json.loads(report.read_text('utf-8'))
                    trial[phase]['process_wall_s']=time.perf_counter()-started
            except Exception as exc:
                trial['error']={'type':type(exc).__name__,'message':'Owned child failed; original private log retained',
                                'return_code':getattr(exc,'returncode',None)}
            trials.append(trial);save(out/f'round-{n}.json',{'round':n,'trials':trials})
            print(n,index,name,method,'ok' if trial['error'] is None else trial['error']['type'],flush=True)
    assert checks==implementation_checksums()
    assert identity=={rel:digest((ROOT/rel).read_bytes()) for rel in tracked}


if __name__=='__main__':main()
