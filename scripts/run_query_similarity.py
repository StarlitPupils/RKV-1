"""One frozen known-split diagnostic; no retrieval, training or answers."""
import argparse,json,subprocess,sys,time
from pathlib import Path
from fractions import Fraction
from collections import Counter
from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from scripts.evidence_retrieval import encoded,question_identity
from scripts.query_similarity import best_training_match,classify
from scripts.run_source_alignment import exclusive
ROOT=Path(__file__).resolve().parents[1]
TRACKED=('scripts/query_similarity.py','scripts/run_query_similarity.py','scripts/analyze_query_similarity.py','scripts/evidence_retrieval.py','scripts/source_alignment.py','scripts/run_source_alignment.py','tests/test_query_similarity.py','docs/QUERY-SIMILARITY.md','docs/query-similarity-inputs.json')

def worker(args):
    start=time.perf_counter();cpu=time.process_time();manifest=json.loads(Path(args.manifest).read_bytes());inputs={}
    for name,e in manifest['files'].items():
        raw=Path(e['path']).read_bytes()
        if len(raw)!=e['bytes'] or digest(raw)!=e['sha256']:raise ValueError('Frozen input identity differs')
        inputs[name]=raw
    training=[json.loads(x) for x in inputs['train'].splitlines()];dev=[json.loads(x) for x in inputs['dev'].splitlines()];questions={question_identity(r['claim']):r['claim'] for r in training};train_queries=[questions[k] for k in sorted(questions)];data={m:json.loads(inputs[m]) for m in ('lexical','expansion','permuted_expansion')};index={m:{r['row_index']:r for r in d['records']} for m,d in data.items()}
    assert len({tuple(sorted(v)) for v in index.values()})==1
    rows=[];base={};candidate={};near={}
    for i in sorted(index['lexical']):
        doc=dev[i];assert all(index[m][i]['question_sha256']==question_identity(doc['claim']) for m in index)
        match=best_training_match(doc['claim'],train_queries);assert not match['is_exact_normalized_question']
        r={'row_index':i,'question_id':doc['id'],'question_sha256':question_identity(doc['claim']),**match,'annotation_status':index['lexical'][i]['annotation_status'],'method_metrics':{m:index[m][i]['paper_metrics'] for m in index},'prior_proof_sha256':{m:index[m][i]['proof_sha256'] for m in index}}
        gold=index['lexical'][i]['gold_paper_ids'];assert all(index[m][i]['gold_paper_ids']==gold for m in index)
        if gold:
            base[i]=Fraction(index['lexical'][i]['paper_metrics']['recovered_groups'],len(gold));candidate[i]=Fraction(index['expansion'][i]['paper_metrics']['recovered_groups'],len(gold));near[i]=match['near_at_least_four_fifths']
        rows.append(r)
    directions=classify(base,candidate,near);report={'records':rows,'annotated_directions':directions,'training_rows':len(training),'unique_training_questions':len(questions),'raw_dev_rows':len(dev),'retrieved_rows':len(rows),'annotated_rows':len(directions),'unannotated_rows':len(rows)-len(directions),'excluded_prior_overlap':data['lexical']['excluded'],'worker_wall_s':time.perf_counter()-start,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'source_range_bindings':0,'new_scientific_trials':0,'new_training_runs':0,'new_query_calls':0,'new_remote_model_calls':0,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None}
    exclusive(Path(args.worker_report),encoded(report)+b'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);p.add_argument('--worker-report');args=p.parse_args()
    if args.worker_report:worker(args);return
    out=Path(args.out).resolve();out.mkdir(exist_ok=False);checks=implementation_checksums();programs={n:digest((ROOT/n).read_bytes()) for n in TRACKED};exclusive(out/'environment.json',encoded({'implementation_checksums':checks,'program_protocol_sha256':programs,'python':sys.version,'workers':1,'scope':'Known train/dev token-set Jaccard and prior raw reports only; not new retrieval or semantic leakage assurance'})+b'\n')
    start=time.perf_counter();code=None;error=None;report=out/'worker.json'
    with (out/'worker.log').open('xb') as log:
        try:code=subprocess.run([sys.executable,'-m','scripts.run_query_similarity','--manifest',str(Path(args.manifest).resolve()),'--out',str(out),'--worker-report',str(report)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
        except subprocess.TimeoutExpired:error='TimeoutExpired'
    exclusive(out/'parent.json',encoded({'return_code':code,'error':error,'parent_full_process_wall_s':time.perf_counter()-start,'child_sha256':digest(report.read_bytes()) if report.exists() else None})+b'\n');assert checks==implementation_checksums() and programs=={n:digest((ROOT/n).read_bytes()) for n in TRACKED};print('Diagnosticworker',code,flush=True)

if __name__=='__main__':main()
