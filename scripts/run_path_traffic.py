"""Paired scope OFF/ON cost measurement on the unchanged v0.40 fixture."""
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
from scripts.cas_traffic import CASTraffic
import scripts.run_evidence_paths as legacy
from scripts.run_memory_concurrency import save

ROOT=Path(__file__).resolve().parents[1]


def exclusive_json(path,value):
    raw=json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2).encode('utf-8')+b'\n'
    with Path(path).open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())


def worker(args):
    original=legacy.trace;records=[]
    def measured(memory,key,**kwargs):
        if args.condition=='on':
            meter=CASTraffic(memory.store)
            with meter:proof=original(memory,key,**kwargs)
            counters=meter.result()
        else:proof=original(memory,key,**kwargs);counters=None
        encoded=json.dumps(proof,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
        records.append({'index':len(records),'root_key':key,'snapshot_id':kwargs['snapshot'],
                        'proof_sha256':digest(encoded),'traffic':counters})
        return proof
    legacy.trace=measured
    try:legacy.worker(args)
    finally:legacy.trace=original
    exclusive_json(args.meter_report,{'round':args.round,'condition':args.condition,'traces':records,
                    'scope':'Only trace calls; original child report unchanged; OFF recorder still computes proof hashes'})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True);p.add_argument('--out')
    p.add_argument('--round',type=int);p.add_argument('--condition',choices=('off','on'))
    p.add_argument('--worker-report');p.add_argument('--meter-report');args=p.parse_args()
    if args.round:worker(args);return
    work=Path(args.work).resolve();out=Path(args.out).resolve();work.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
    checks=implementation_checksums();old=json.loads((ROOT/'results/v0.40.0/source-checksums.json').read_text('utf-8'))
    assert set(checks)==set(old)
    for name,sha in old.items():
        if name!='__init__.py':assert checks[name]==sha
    tracked=('scripts/cas_traffic.py','scripts/run_path_traffic.py','docs/PATH-TRAFFIC.md',
             'scripts/run_evidence_paths.py','scripts/evidence_path_fixture.py','docs/evidence-path-inputs.json')
    identity={rel:digest((ROOT/rel).read_bytes()) for rel in tracked}
    save(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'implementation_checksums':checks,
         'program_protocol_sha256':identity,'conditions':['off','on'],'paired_rounds':3,'timeout_s':600,
         'source_fixture':'unchanged known v0.40 fixture; no new scientific validation',
         'physical_SSD_bytes':None,'cold_cache':None,'cross_machine':None,'remote_model_calls':0})
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for n in range(1,4):
        for condition in (('off','on') if n%2 else ('on','off')):
            label=f'round-{n}-{condition}';report=out/(label+'.json');meter=out/(label+'-meter.json')
            command=[sys.executable,'-m','scripts.run_path_traffic','--work',str(work/label),
                     '--round',str(n),'--condition',condition,'--worker-report',str(report),'--meter-report',str(meter)]
            code=None;error=None
            with (out/(label+'.log')).open('wb') as log:
                started=time.perf_counter()
                try:
                    result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
                        timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));code=result.returncode
                except subprocess.TimeoutExpired:error='TimeoutExpired'
                elapsed=time.perf_counter()-started
            exclusive_json(out/(label+'-parent.json'),{'round':n,'condition':condition,'return_code':code,'error':error,
                 'parent_full_process_wall_s':elapsed,'child_report_sha256':digest(report.read_bytes()) if report.exists() else None,
                 'meter_report_sha256':digest(meter.read_bytes()) if meter.exists() else None,
                 'scope':'perf_counter immediately before subprocess.run to after child exit or timeout; parent record written separately'})
            print(label,'return_code',code,'parent_wall_s',elapsed,flush=True)
    assert checks==implementation_checksums()
    assert identity=={rel:digest((ROOT/rel).read_bytes()) for rel in tracked}


if __name__=='__main__':main()
