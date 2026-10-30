"""Fixed balanced fresh-child plan; exclusive outputs and no retries."""
import json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from rkv1.benchmark import peak_rss
from scripts.reader_session_fixture import ORDER,SIZES


def write(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,allow_nan=False)


def run(config_path,out,*,guard=None):
    config=json.loads(Path(config_path).read_bytes());owned=config['owned_test']
    if type(owned) is not bool or config['revisions']!=(2 if owned else 12):raise ValueError('Fixed owned or formal scope required')
    sizes=(9,) if owned else SIZES;order=ORDER[:1] if owned else ORDER
    planned=len(sizes)*sum(len(r) for r in order);queries=planned*config['revisions']*8
    out=Path(out);out.mkdir(exist_ok=False);start,cpu=time.perf_counter(),time.process_time();success=False;rows=[]
    try:
        for rnd,roles in enumerate(order,1):
            for size in sizes:
                for role in roles:
                    if guard:guard()
                    elapsed=time.perf_counter()-start
                    if elapsed>=3600:raise TimeoutError('Overall fixed plan timeout; no new worker')
                    name=f'round-{rnd}-size-{size}-{role}';t,c,code=time.perf_counter(),time.process_time(),None
                    try:
                        env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
                        limit=120 if owned else min(600,max(0,config['authorized_reference']-time.time()))
                        if limit<=0:raise TimeoutError('Authorized window ended before child')
                        with (out/(name+'.log')).open('xb') as log:
                            code=subprocess.run([sys.executable,str(Path(__file__).with_name('run_reader_session_worker.py').resolve()),str(Path(config_path).resolve()),str(size),role,str((out/name).resolve())],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=min(limit,3600-elapsed)).returncode
                    finally:
                        row={'round':rnd,'size':size,'role':role,'name':name,'exit_code':code,'parent_full_wall_s':time.perf_counter()-t,'parent_CPU_s':time.process_time()-c,'retries':0};write(out/(name+'-parent.json'),row)
                    if code!=0:raise RuntimeError('Fixed worker failed; no retry or later workers')
                    rows.append(row)
        write(out/'plan.json',{'planned_workers':planned,'planned_queries':queries,'completed_workers':len(rows),'rows':rows,'owned_test':owned,'model_HTTP_calls':0});success=True;return rows
    finally:write(out/'plan-finally.json',{'success':success,'planned_workers':planned,'planned_queries':queries,'completed_workers':len(rows),'full_wall_s':time.perf_counter()-start,'full_CPU_s':time.process_time()-cpu,'process_peak_RSS_B':peak_rss()})
