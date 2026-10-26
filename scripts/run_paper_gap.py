"""Replay diagnostic of already verified paper proofs; no source range I/O."""
import argparse,json,os,subprocess,sys,time
from collections import Counter
from pathlib import Path
from rkv1.benchmark import peak_rss
from rkv1.core import digest
from rkv1.controlled import implementation_checksums
from scripts.evidence_retrieval import encoded,ranking,admit,lexical,question_identity
from scripts.paper_gap import admission_trace,graph_exposure,CATEGORIES
from scripts.run_source_alignment import exclusive

ROOT=Path(__file__).resolve().parents[1]
METHODS=('lexical','graph','permuted_graph')
TRACKED=('scripts/paper_gap.py','scripts/run_paper_gap.py','scripts/evidence_retrieval.py','scripts/source_alignment.py','scripts/run_source_alignment.py','tests/test_paper_gap.py','docs/PAPER-GAP.md','docs/paper-gap-inputs.json')

def checked(path,sha,cost):
    raw=Path(path).read_bytes();cost['application_input_returned_bytes']+=len(raw)
    if digest(raw)!=sha:raise ValueError('Frozen diagnostic input SHA differs')
    return raw

def worker(args):
    begin=time.perf_counter();cpu=time.process_time();cost=Counter()
    manifest=json.loads(Path(args.manifest).read_bytes());entry=manifest['methods'][args.method]
    model_raw=checked(args.model,manifest['model_sha256'],cost);model=json.loads(model_raw)
    report=json.loads(checked(args.report,entry['report_sha256'],cost))
    queries=json.loads(checked(args.queries,entry['queries_sha256'],cost))
    assert report['method']==args.method and report['round']==1 and report['model_sha256']==manifest['model_sha256']
    assert report['source_sha256']==model['shared']['source_sha256']==manifest['source_sha256']
    assert model['shared']['parameters']=={'k1':1.2,'b':.75,'max_facts':12,'source_budget':4096,'seeds':6,'neighbors':6}
    query_by_row={q['row_index']:q for q in queries};assert len(query_by_row)==len(queries)==report['retrieved_rows']
    records=[];totals=Counter({k:0 for k in CATEGORIES})
    for rec in report['records']:
        proof={k:v for k,v in rec.items() if k not in ('proof_sha256','query_wall_s','query_cpu_s','gold_audit_wall_s','gold_audit_cpu_s','ranked_candidates')}
        assert digest(encoded(proof))==rec['proof_sha256']
        q=query_by_row.pop(rec['row_index']);assert question_identity(q['question'])==rec['question_sha256'] and q['selected_ids']==rec['selected_ids']
        ordered=ranking(model,q['question'],args.method);selected,used=admit(model,ordered)
        assert selected==rec['selected_ids'] and used==rec['admitted_record_bytes'] and len(ordered)==rec['ranked_candidates']
        trace=admission_trace(model['shared']['locators'],ordered,rec['gold_paper_ids'])
        assert trace['selected_ids']==selected and trace['admitted_bytes']==used
        if rec['paper_metrics'] is None:assert not rec['gold_paper_ids']
        else:assert trace['counts']['recovered']==rec['paper_metrics']['recovered_groups']
        lex,_=lexical(model['shared'],q['question']);lexsel,_=admit(model,lex)
        exposure=graph_exposure(model,lex,args.method);totals.update(trace['counts'])
        records.append({'row_index':rec['row_index'],'question_id':rec['question_id'],'question_sha256':rec['question_sha256'],
            'prior_proof_sha256':rec['proof_sha256'],'annotated':rec['paper_metrics'] is not None,**trace,**exposure,
            'selected_order_differs_from_lexical':selected!=lexsel})
    assert not query_by_row and len(records)==report['retrieved_rows'] and len({r['row_index'] for r in records})==len(records)
    result={'method':args.method,'records':records,'counts':dict(totals),'retrieved_rows':len(records),
        'annotated_rows':sum(r['annotated'] for r in records),'model_sha256':manifest['model_sha256'],
        'model_loaded_bytes':len(model_raw),'application_input_returned_bytes':cost['application_input_returned_bytes'],
        'application_input_scope':'Model and prior public report/private query checks via read_bytes only; excludes manifest and interpreter/module loads',
        'new_source_range_bindings':0,'new_scientific_trials':0,'new_training_runs':0,'new_remote_model_calls':0,
        'worker_wall_s':time.perf_counter()-begin,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None}
    exclusive(Path(args.output),encoded(result)+b'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','model','manifest','queries','report','output','freeze'):p.add_argument('--'+name)
    p.add_argument('--method',choices=METHODS);args=p.parse_args()
    if args.method:worker(args);return
    out=Path(args.out);out.mkdir(exist_ok=False);begin=time.perf_counter();cpu=time.process_time()
    manifest_raw=Path(args.manifest).read_bytes();manifest=json.loads(manifest_raw);reports={};parents={}
    assert manifest['methods'].keys()==set(METHODS)
    checks=implementation_checksums();programs={n:{'bytes':(ROOT/n).stat().st_size,'sha256':digest((ROOT/n).read_bytes())} for n in TRACKED}
    env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')}
    for method in METHODS:
        entry=manifest['methods'][method];path=out/(method+'.json');code=None;error=None;t=time.perf_counter()
        with (out/(method+'.log')).open('xb') as log:
            try:code=subprocess.run([sys.executable,'-m','scripts.run_paper_gap','--method',method,'--model',args.model,'--manifest',args.manifest,
                '--report',entry['report_path'],'--queries',entry['queries_path'],'--output',str(path)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
                timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
            except subprocess.TimeoutExpired:error='TimeoutExpired'
        parent={'return_code':code,'error':error,'parent_full_process_wall_s':time.perf_counter()-t,'child_sha256':digest(path.read_bytes()) if path.exists() else None}
        exclusive(out/(method+'-parent.json'),encoded(parent)+b'\n');parents[method]=parent
        assert code==0 and error is None,'Preserve failed diagnostic; do not rerun'
        reports[method]=json.loads(path.read_bytes());print(method,reports[method]['counts'],flush=True)
    # Read-only post-worker aggregate: count categories directly from each row rather than trust cached totals.
    rows=[];exposure=[]
    for method,report in reports.items():
        counted=Counter({k:0 for k in CATEGORIES});annotated=0;active=0;changed=0
        for r in report['records']:
            cats=r['gold_categories'];assert set(cats.values())<=set(CATEGORIES)
            assert Counter(cats.values())==Counter(r['counts'])
            assert all((category=='recovered')==(key in r['selected_ids']) for key,category in cats.items())
            counted.update(cats.values());annotated+=r['annotated'];active+=bool(r['annotated'] and r['active_seed_count']);changed+=r['selected_order_differs_from_lexical']
        assert dict(counted)==report['counts'] and annotated==report['annotated_rows']==188 and len(report['records'])==298 and sum(counted.values())==209
        rows.append({'method':method,**dict(counted),'input_application_bytes':report['application_input_returned_bytes'],
            'worker_wall_s':report['worker_wall_s'],'worker_cpu_s':report['worker_cpu_s'],'observed_peak_rss_bytes':report['observed_peak_rss_bytes'],**parents[method]})
        exposure.append({'method':method,'annotated_claims':annotated,'annotated_seed_graph_active_claims':active,
            'all_claims_changed_selected_order':changed,'all_claims':len(report['records'])})
    graph=reports['graph'];counts=graph['counts'];misses=sum(counts.values())-counts['recovered'];e=next(x for x in exposure if x['method']=='graph')
    metrics={'rows':rows,'exposure':exposure,'H1_graph_missing_gold_byte_reject_at_least_half':bool(misses) and counts['byte_rejected']*2>=misses,
        'H1_fraction':counts['byte_rejected']/misses if misses else None,'H2_annotated_graph_seed_active_at_least_half':e['annotated_seed_graph_active_claims']*2>=e['annotated_claims'],
        'diagnostic_records':894,'gold_groups_across_methods':627,'new_scientific_trials':0,'new_training_runs':0,'new_source_range_bindings':0,
        'model_bytes':len(Path(args.model).read_bytes()),'model_sha256':manifest['model_sha256'],'input_manifest_sha256':digest(manifest_raw),
        'freeze':args.freeze,'scope':'Already verified SciFact result replay diagnostic; no intervention or new scientific/source validation'}
    exclusive(out/'derived-metrics.json',encoded(metrics)+b'\n')
    files={'rkv1/'+k:{'bytes':(ROOT/'rkv1'/k).stat().st_size,'sha256':sha} for k,sha in checks.items()}
    html=ROOT/'rkv1/memory_demo.html';files['rkv1/memory_demo.html']={'bytes':html.stat().st_size,'sha256':digest(html.read_bytes())}
    exclusive(out/'source-checksums.json',encoded(checks)+b'\n');exclusive(out/'source-resource.json',encoded({'files':files,'total_bytes':sum(v['bytes'] for v in files.values()),'assessment_programs':{n:meta for n,meta in programs.items() if n.startswith('scripts/')}})+b'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13,5));bottom=[0]*3
    for category,color in zip(CATEGORIES,('#2563eb','#9ca3af','#ef4444','#f59e0b')):
        values=[r[category] for r in rows];axes[0].bar(METHODS,values,bottom=bottom,label=category,color=color);bottom=[x+y for x,y in zip(bottom,values)]
    axes[0].set_ylim(0,235);axes[0].set_ylabel('Previously annotated gold paper groups');axes[0].set_title('Frozen admission trace: 209 groups per method');axes[0].legend(fontsize=8)
    axes[1].bar(METHODS,[x['annotated_seed_graph_active_claims'] for x in exposure],color=('#64748b','#2563eb','#f59e0b'));axes[1].set_ylim(0,210);axes[1].set_ylabel('Annotated claims /188');axes[1].set_title('Any top6 seed has a graph edge')
    fig.suptitle('RKV-1 v0.54: known SciFact diagnostic only, no new retrieval trials');fig.tight_layout();fig.savefig(out/'paper-gap.png',dpi=160);plt.close(fig)
    assert checks==implementation_checksums() and programs=={n:{'bytes':(ROOT/n).stat().st_size,'sha256':digest((ROOT/n).read_bytes())} for n in TRACKED}
    exclusive(out/'analysis-timing.json',encoded({'driver_plus_worker_and_plot_wall_s':time.perf_counter()-begin,'driver_only_cpu_s':time.process_time()-cpu,
        'scope':'Parent includes 3 subprocess waits; CPU excludes child CPU listed separately; initial interpreter and timing-record write excluded','observed_peak_rss_bytes':peak_rss()})+b'\n')
    print(json.dumps({k:v for k,v in metrics.items() if k.startswith('H')}),flush=True)

if __name__=='__main__':main()
