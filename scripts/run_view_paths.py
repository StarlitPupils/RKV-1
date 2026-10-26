"""Fixed layout x single-trace view reuse x traffic meter, CPU/offline only."""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from scripts.query_view import QueryView
from scripts.cas_traffic import CASTraffic
from scripts.run_memory_concurrency import save
import scripts.run_layout_paths as legacy

ROOT=Path(__file__).resolve().parents[1]
CONDITIONS=(('clustered','off','off'),('clustered','on','off'),('clustered','off','on'),('clustered','on','on'),
            ('separated','off','off'),('separated','on','off'),('separated','off','on'),('separated','on','on'))
ORDERS=('ABCDEFGH','BADCFEHG','GHCDEFAB')
TRACKED=('scripts/query_view.py','scripts/run_view_paths.py','scripts/run_layout_paths.py','scripts/path_layout_fixture.py',
         'scripts/evidence_path_fixture.py','scripts/cas_traffic.py','docs/QUERY-VIEW.md','docs/path-layout-inputs.json')


def worker(args):
    original=legacy.trace;records=[]
    def measured(memory,key,**kwargs):
        view=QueryView(memory,kwargs['snapshot']) if args.view=='on' else None
        meter=CASTraffic(memory.store) if args.meter=='on' else None
        with meter if meter is not None else nullcontext():
            with view if view is not None else nullcontext():proof=original(memory,key,**kwargs)
        encoded=json.dumps(proof,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        records.append({'index':len(records),'root_key':key,'snapshot_id':kwargs['snapshot'],'proof_sha256':digest(encoded),
                        'traffic':meter.result() if meter is not None else None,'view':view.result() if view is not None else None})
        return proof
    legacy.trace=measured
    try:legacy.base_worker(args)
    finally:legacy.trace=original
    legacy.exclusive(Path(args.meter_report),json.dumps({'round':args.round,'layout':args.layout,'view':args.view,'meter':args.meter,
        'traces':records},sort_keys=True,indent=2).encode()+b'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('work','out','worker-report','meter-report'):p.add_argument('--'+key,required=key=='work')
    p.add_argument('--round',type=int);p.add_argument('--layout',choices=('clustered','separated'))
    p.add_argument('--view',choices=('off','on'));p.add_argument('--meter',choices=('off','on'));args=p.parse_args()
    if args.round:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    checks=implementation_checksums();old=json.loads((ROOT/'results/v0.44.0/source-checksums.json').read_text('utf-8'))
    assert set(checks)==set(old)
    for name,sha in old.items():
        if name!='__init__.py':assert checks[name]==sha
    tracked={name:digest((ROOT/name).read_bytes()) for name in TRACKED}
    save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'implementation_checksums':checks,
        'program_protocol_sha256':tracked,'conditions':CONDITIONS,'orders':ORDERS,'rounds':3,'worker_timeout_s':600,
        'scope':'Known synthetic records, fixed-SID v3 preverified request view; no decoded block cache/default change/new scientific QA',
        'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,'remote_model_calls':0})
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n,order in enumerate(ORDERS,1):
        for letter in order:
            layout,view,meter=CONDITIONS[ord(letter)-ord('A')];label=f'round-{n}-{layout}-v{view}-m{meter}'
            report=out/(label+'.json');sidecar=out/(label+'-meter.json')
            command=[sys.executable,'-m','scripts.run_view_paths','--work',str(work/label),'--round',str(n),
                '--layout',layout,'--view',view,'--meter',meter,'--worker-report',str(report),'--meter-report',str(sidecar)]
            code=None;error=None
            with (out/(label+'.log')).open('wb') as log:
                began=time.perf_counter()
                try:
                    result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));code=result.returncode
                except subprocess.TimeoutExpired:error='TimeoutExpired'
                elapsed=time.perf_counter()-began
            legacy.exclusive(out/(label+'-parent.json'),json.dumps({'round':n,'layout':layout,'view':view,'meter':meter,
                'return_code':code,'error':error,'parent_full_process_wall_s':elapsed,
                'child_report_sha256':digest(report.read_bytes()) if report.exists() else None,
                'meter_report_sha256':digest(sidecar.read_bytes()) if sidecar.exists() else None},sort_keys=True,indent=2).encode()+b'\n')
            print(label,'return_code',code,'parent_wall_s',elapsed,flush=True)
    assert checks==implementation_checksums() and tracked=={name:digest((ROOT/name).read_bytes()) for name in TRACKED}


if __name__=='__main__':main()
