"""Exactly one seeded CPU epoch; freeze quantized weights before test scoring."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'

from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.neural_small import model_bytes,Q,PARAMETERS
from scripts.neural_inputs import load
from scripts.run_memory_concurrency import save


def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--model',required=True);p.add_argument('--report',required=True)
    args=p.parse_args();assert not Path(args.model).exists() and not Path(args.report).exists()
    start=time.perf_counter();import numpy as np
    imported=time.perf_counter();assert np.__version__=='2.4.4','Frozen training NumPy version differs'
    jobs=load(args.inputs,'train');rng=np.random.default_rng(20261026)
    xs=[];ys=[]
    for meta,raw in jobs:
        symbols=np.frombuffer(raw,dtype=np.uint8).astype(np.int64)
        xs.append(np.lib.stride_tricks.sliding_window_view(np.concatenate((np.full(4,256,dtype=np.int64),symbols)),4)[:-1].copy());ys.append(symbols)
    X=np.concatenate(xs);Y=np.concatenate(ys);N=len(Y)
    params=[rng.normal(0,.1,(257,4)),rng.normal(0,.25,(16,8)),np.zeros(8),rng.normal(0,1/np.sqrt(8),(8,256)),np.zeros(256)]
    moment=[np.zeros_like(a) for a in params];variance=[np.zeros_like(a) for a in params]
    order=rng.permutation(N);steps=[];loss_sum=0
    for step,offset in enumerate(range(0,N,256),1):
        if time.perf_counter()-start>300:raise TimeoutError('Frozen300s training cap exceeded; no reduced-data retry')
        ix=order[offset:offset+256];xb=X[ix];yb=Y[ix];B=len(ix);E,W1,b1,W2,b2=params
        embedded=E[xb].reshape(B,16);pre=embedded@W1+b1;hidden=np.maximum(pre,0);logits=hidden@W2+b2;logits-=logits.max(axis=1,keepdims=True)
        probs=np.exp(logits);probs/=probs.sum(axis=1,keepdims=True)
        loss=float(-np.log(probs[np.arange(B),yb]).sum());loss_sum+=loss
        probs[np.arange(B),yb]-=1;probs/=B
        gW2=hidden.T@probs;gb2=probs.sum(axis=0);dh=(probs@W2.T)*(pre>0);gW1=embedded.T@dh;gb1=dh.sum(axis=0)
        gE=np.zeros_like(E);np.add.at(gE,xb,(dh@W1.T).reshape(B,4,4));grad=[gE,gW1,gb1,gW2,gb2]
        norm=float(np.sqrt(sum(float((g*g).sum()) for g in grad)));scale=min(1.,5/max(norm,1e-30))
        for i,g in enumerate(grad):
            g*=scale;moment[i]*=.9;moment[i]+=.1*g;variance[i]*=.999;variance[i]+=.001*g*g
            params[i]-=.002*(moment[i]/(1-.9**step))/(np.sqrt(variance[i]/(1-.999**step))+1e-8)
        steps.append({'step':step,'samples':B,'loss_sum_nats_before_update':loss,'gradient_norm_before_clip':norm})
    trained=time.perf_counter();flat=np.concatenate([v.ravel() for v in params]);assert len(flat)==PARAMETERS and np.isfinite(flat).all()
    quant=np.clip(np.rint(flat*Q),-32768,32767).astype(np.int64);model=model_bytes([int(v) for v in quant]);quantized=time.perf_counter()
    target=Path(args.model);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(model);f.flush();os.fsync(f.fileno())
    total_wall=time.perf_counter()-start
    if total_wall>300:raise TimeoutError('Frozen training-to-model-fsync cap exceeded; do not retry')
    training_peak=peak_rss();inventory_start=time.perf_counter();distribution=importlib.metadata.distribution('numpy');files={}
    for rel in distribution.files or []:
        path=Path(distribution.locate_file(rel))
        if path.is_file():files[str(rel).replace('\\','/')]= {'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    report={'seed':20261026,'epochs':1,'batch':256,'learning_rate':.002,'optimizer':'Adam(0.9,0.999,eps1e-8),global L2 clip5',
            'training_inputs':[m for m,_ in jobs],'training_symbols':N,'steps':steps,'weighted_training_loss_nats':loss_sum/N,
            'numpy_version':np.__version__,'python':sys.version,'thread_env':{k:os.environ[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')},
            'numpy_distribution_files':files,'numpy_installed_distribution_bytes':sum(x['bytes'] for x in files.values()),
            'numpy_import_wall_s':imported-start,'training_without_quantization_wall_s':trained-imported,'training_and_quantization_wall_s':quantized-imported,'training_to_model_fsync_wall_s':total_wall,
            'peak_rss_bytes':training_peak,'dependency_inventory_wall_s':time.perf_counter()-inventory_start,'process_peak_rss_after_dependency_inventory_bytes':peak_rss(),
            'model_bytes':len(model),'model_sha256':digest(model),'quantization_Q':Q,'parameters':PARAMETERS,
            'quantized_saturations':int(np.count_nonzero((flat*Q<-32768)|(flat*Q>32767))),
            'test_evaluations':0,'remote_model_calls':0,'scope':'Single CPU training run. Pure integer inference has no NumPy dependency; cross-machine float training reproducibility untested.'}
    save(args.report,report);print(json.dumps({k:report[k] for k in ('training_symbols','parameters','model_bytes','model_sha256','training_to_model_fsync_wall_s','weighted_training_loss_nats')}))


if __name__=='__main__':main()
