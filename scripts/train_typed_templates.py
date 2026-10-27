"""One supervised supervised training campaign; controls derived without second fit."""
import argparse,json,time,zipfile,hashlib,atexit
from pathlib import Path
from scripts.typed_templates import train
from scripts.postings_transform import parse,canonical
from rkv1.core import digest
from rkv1.benchmark import peak_rss
MEMBER='proofwriter-dataset-V2020.12.3/OWA/NatLang/meta-train.jsonl';MAX_TRAIN_BYTES=64<<20

def run(archive,expected_sha,expected_bytes,work):
 start=time.perf_counter();cpu=time.process_time();work.mkdir(exist_ok=False)
 # Internal finally preserves CPU/wall even when a one-attempt campaign fails.
 status={'exit_success':False,'training_attempts':1,'new_remote_model_calls':0}
 def finalize():
  p=work/'training-finally-timing.json'
  with p.open('x',encoding='utf-8') as f:json.dump({**status,'full_worker_wall_s':time.perf_counter()-start,'full_worker_cpu_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss()},f,indent=2);f.write('\n')
 atexit.register(finalize)
 assert archive.stat().st_size==expected_bytes;h=hashlib.sha256()
 with archive.open('rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 assert h.hexdigest()==expected_sha
 with zipfile.ZipFile(archive) as z,z.open(MEMBER) as f:raw=f.read(MAX_TRAIN_BYTES+1)
 if len(raw)>MAX_TRAIN_BYTES:raise ValueError('Full train member exceeds fixed64MiB cap')
 with (work/'private-raw-train.jsonl').open('xb') as f:f.write(raw)
 lines=raw.splitlines(keepends=True)
 if not 0<len(lines)<=10000:raise ValueError('Full physical training row cap')
 rows=[parse(line) for line in lines];t=time.perf_counter();c=time.process_time();model,control=train(rows);fit={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};models={}
 for name,value in (('learned',model),('control',control)):
  b=canonical(value)+b'\n';p=work/('private-'+name+'-model.json')
  with p.open('xb') as f:f.write(b)
  models[name]={'path':str(p),'bytes':len(b),'sha256':digest(b)}
 assert models['learned']['bytes']==models['control']['bytes'];metadata={'models':models,'full_training_member':MEMBER,'training_member_bytes':len(raw),'training_member_sha256':digest(raw),'physical_training_rows':len(lines),'training_attempts':1,'complete_fits':1,'control_derived_fixed_cyclic_permutation_no_fit':True,'fit':fit,'statistics':model['statistics'],'archive_sha256':expected_sha,'training_questions_answers_not_used_as_fit_fields':True,'NatLang_test_opened_during_train':False,'new_remote_model_calls':0,'worker_wall_before_finalmeta_s':time.perf_counter()-start,'worker_cpu_before_finalmeta_s':time.process_time()-cpu,'peak_RSS_bytes':peak_rss()}
 with (work/'model-freeze.json').open('x',encoding='utf-8') as f:json.dump(metadata,f,indent=2);f.write('\n')
 status['exit_success']=True;print(json.dumps({'models_SHA_bytes_only':models,'training_rows':len(lines),'fit':fit,'stats':model['statistics']}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--archive-sha256',required=True);p.add_argument('--archive-bytes',type=int,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();run(a.archive,a.archive_sha256,a.archive_bytes,a.work)
