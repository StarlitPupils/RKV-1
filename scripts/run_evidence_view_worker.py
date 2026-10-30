"""Private explicit child entry; real inputs may run only after frozen CI guard."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
entry_start,entry_CPU=time.perf_counter(),time.process_time()
sys.path.insert(0,str(Path.cwd()))
from scripts.evidence_view_campaign import run
from rkv1.benchmark import peak_rss


def main(config_path,method,out):
    config=json.loads(Path(config_path).read_bytes())
    required={'store_root','sid','model_path','model_sha','questions_path','questions_sha','expected_questions','owned_fixture','deadline'}
    if set(config)!=required:raise ValueError('Exact question-only campaign config required')
    raw=Path(config['questions_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=config['questions_sha']:raise ValueError('Original question cohort SHA differs')
    values=json.loads(raw)
    if type(values) is not list or len(values)!=config['expected_questions'] or any(type(q) is not dict or set(q)!={'claim_id','claim'} for q in values):raise ValueError('Original question-only cohort schema differs')
    questions=[{'id':str(q['claim_id']),'question':q['claim']} for q in values]
    if config['owned_fixture'] is True:
        if config['expected_questions']>9 or config['deadline'] is not None:raise ValueError('Tiny owned-only child scope required')
        guard=None
    else:
        if config['expected_questions']!=270 or (type(config['deadline']) is not int or config['deadline']<=0):raise ValueError('Frozen real cohort/window required')
        last=[0.0]
        def guard():
            if time.time()>=config['deadline']:raise RuntimeError('Authorized window ended')
            if time.monotonic()-last[0]<30:return
            subprocess.run([sys.executable,'.tools/read_quota.py'],check=True,stdout=subprocess.DEVNULL)
            q=json.loads(Path('.tools/last-quota-read.json').read_bytes())['result'];p=q['rateLimitsByLimitId']['codex']['primary']
            if not(q['ordinaryUsageAllowed'] and p['usedPercent']<100 and abs(p['resetsAt']-config['deadline'])<=60):raise RuntimeError('Quota denied, exhausted or changed')
            last[0]=time.monotonic()
    return run(config['store_root'],config['sid'],config['model_path'],config['model_sha'],questions,method=method,out=out,guard=guard)


if __name__=='__main__':
    entry_success=False
    try:
        main(*sys.argv[1:]);entry_success=True
    finally:
        folder=Path(sys.argv[3]) if len(sys.argv)>3 else None
        if folder is not None and folder.is_dir():
            with (folder/'process-entry-finally.json').open('x',encoding='utf-8') as stream:
                json.dump({'success':entry_success,'entry_full_wall_s':time.perf_counter()-entry_start,'entry_full_CPU_s':time.process_time()-entry_CPU,'process_peak_RSS_B':peak_rss(),'scope':'After stdlib imports, before candidate imports/question SHA+parse; through complete worker/body finally; parent includes interpreter startup and this footer write'},stream,indent=2)
