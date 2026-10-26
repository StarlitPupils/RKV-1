"""Six heavy diagnostic workers, exclusive original CAS work roles, cache OFF."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from scripts.path_roles import PathRoles
from scripts.run_memory_concurrency import save
import scripts.run_layout_paths as legacy

ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/path_roles.py','scripts/run_path_roles.py','scripts/run_layout_paths.py','scripts/path_layout_fixture.py',
         'scripts/evidence_path_fixture.py','scripts/cas_traffic.py','docs/PATH-ROLES.md','docs/path-layout-inputs.json')


def worker(args):
    original=legacy.trace;records=[]
    def measured(memory,key,**kwargs):
        observer=PathRoles(memory)
        with observer:proof=original(memory,key,**kwargs)
        encoded=json.dumps(proof,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        records.append({'index':len(records),'root_key':key,'snapshot_id':kwargs['snapshot'],
                        'proof_sha256':digest(encoded),'roles':observer.result()})
        return proof
    legacy.trace=measured
    try:legacy.base_worker(args)
    finally:legacy.trace=original
    legacy.exclusive(Path(args.meter_report),json.dumps({'round':args.round,'layout':args.layout,'traces':records},
        sort_keys=True,indent=2).encode()+b'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('work','out','worker-report','meter-report'):p.add_argument('--'+key,required=key=='work')
    p.add_argument('--round',type=int);p.add_argument('--layout',choices=('clustered','separated'));args=p.parse_args()
    if args.round:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    checks=implementation_checksums();old=json.loads((ROOT/'results/v0.43.0/source-checksums.json').read_text('utf-8'))
    assert set(checks)==set(old)
    for key,sha in old.items():
        if key!='__init__.py':assert checks[key]==sha
    tracked={name:digest((ROOT/name).read_bytes()) for name in TRACKED}
    save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'implementation_checksums':checks,
        'program_protocol_sha256':tracked,'rounds':3,'worker_timeout_s':600,'cache':'off','meter':'on',
        'orders':[['clustered','separated'],['separated','clustered'],['clustered','separated']],
        'scope':'Heavy work-attribution diagnostic, not timing benefit test or new scientific/QA validation',
        'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,'remote_model_calls':0})
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n in (1,2,3):
        for layout in (('separated','clustered') if n==2 else ('clustered','separated')):
            label=f'round-{n}-{layout}';report=out/(label+'.json');roles=out/(label+'-roles.json')
            command=[sys.executable,'-m','scripts.run_path_roles','--work',str(work/label),'--round',str(n),
                '--layout',layout,'--worker-report',str(report),'--meter-report',str(roles)]
            code=None;error=None
            with (out/(label+'.log')).open('wb') as log:
                began=time.perf_counter()
                try:
                    result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));code=result.returncode
                except subprocess.TimeoutExpired:error='TimeoutExpired'
                elapsed=time.perf_counter()-began
            legacy.exclusive(out/(label+'-parent.json'),json.dumps({'round':n,'layout':layout,'return_code':code,'error':error,
                'parent_full_process_wall_s':elapsed,'child_report_sha256':digest(report.read_bytes()) if report.exists() else None,
                'role_report_sha256':digest(roles.read_bytes()) if roles.exists() else None},sort_keys=True,indent=2).encode()+b'\n')
            print(label,'return_code',code,'parent_wall_s',elapsed,flush=True)
    assert checks==implementation_checksums() and tracked=={name:digest((ROOT/name).read_bytes()) for name in TRACKED}


if __name__=='__main__':main()
