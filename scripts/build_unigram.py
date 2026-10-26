"""Build one static training-frequency model; no neural retraining or test scoring."""
import argparse,json,time,os,zlib
from pathlib import Path
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from rkv1.unigram_frame import build_model
from scripts.neural_inputs import load
from scripts.run_memory_concurrency import save

def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--model',required=True);p.add_argument('--report',required=True);args=p.parse_args()
 assert not Path(args.model).exists() and not Path(args.report).exists()
 start=time.perf_counter();jobs=load(args.inputs,'train');model=build_model([raw for _,raw in jobs]);target=Path(args.model);target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(model);f.flush();os.fsync(f.fileno())
 wall=time.perf_counter()-start
 r={'model_sha256':digest(model),'model_bytes':len(model),'model_zlib6_bytes':len(zlib.compress(model,6)),'training_inputs':[m for m,_ in jobs],
    'training_symbols':sum(len(raw) for _,raw in jobs),'builds':1,'new_neural_training_runs':0,'test_evaluations_before_model_freeze':0,
    'build_through_model_fsync_wall_s':wall,'peak_rss_bytes':peak_rss(),'remote_model_calls':0,
    'scope':'Static frequency count on exactly v0.36 training inputs. Diagnostic on previously seen prefixes; original neural weights unchanged.'}
 save(args.report,r);print(json.dumps({k:r[k] for k in ('model_sha256','model_bytes','model_zlib6_bytes','training_symbols','build_through_model_fsync_wall_s')}))

if __name__=='__main__':main()
