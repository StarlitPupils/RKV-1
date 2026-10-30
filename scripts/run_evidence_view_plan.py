"""Fresh fixed nine-child plan with complete parent clocks, no retries."""
import json,os,subprocess,sys,time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rkv1.benchmark import peak_rss

ORDER=(('whole_record','first_two','overlap_two'),('first_two','overlap_two','whole_record'),('overlap_two','whole_record','first_two'))


def run_plan(config_path,out,*,guard=None):
    config_path=Path(config_path).resolve();config=json.loads(config_path.read_bytes())
    out=Path(out);out.mkdir(exist_ok=False);start,cpu,success,rows=time.perf_counter(),time.process_time(),False,[]
    try:
        for round_index,methods in enumerate(ORDER,1):
            for method in methods:
                if time.perf_counter()-start>=1800:raise TimeoutError('Fixed whole-plan timeout; no later child')
                if guard:guard()
                name=f'round-{round_index}-{method}';t,c,code=time.perf_counter(),time.process_time(),None
                env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
                try:
                    with (out/(name+'.log')).open('xb') as log:
                        command=[sys.executable,str(Path(__file__).with_name('run_evidence_view_worker.py')),str(config_path),method,str((out/name).resolve())]
                        remaining=1800-(time.perf_counter()-start)
                        limit=60 if config['owned_fixture'] else min(600,max(0,config['deadline']-time.time()))
                        if min(limit,remaining)<=0:raise TimeoutError('No authorized time remains')
                        code=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=min(limit,remaining)).returncode
                finally:
                    parent={'round':round_index,'method':method,'case':name,'exit_code':code,'parent_full_wall_s':time.perf_counter()-t,'parent_CPU_s':time.process_time()-c,'retries':0}
                    (out/(name+'-parent.json')).write_text(json.dumps(parent,indent=2)+'\n',encoding='utf-8')
                if code!=0:raise RuntimeError('Fixed child failed; no retry or later child')
                rows.append(parent)
        (out/'plan.json').write_text(json.dumps({'planned_workers':9,'completed_workers':len(rows),'questions_per_worker':config['expected_questions'],'planned_predictions':9*config['expected_questions'],'rows':rows,'new_model_API_calls':0},indent=2)+'\n',encoding='utf-8')
        success=True
        return rows
    finally:
        (out/'plan-finally.json').write_text(json.dumps({'success':success,'planned_workers':9,'completed_workers':len(rows),'planned_predictions':9*config['expected_questions'],'full_wall_s':time.perf_counter()-start,'full_CPU_s':time.process_time()-cpu,'peak_RSS_B':peak_rss(),'scope':'Plan process only; each child has separate full clocks'},indent=2)+'\n',encoding='utf-8')
