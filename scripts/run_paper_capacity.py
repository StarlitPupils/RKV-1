"""Known SciFact gold-aware capacity diagnostic, no source-range reads or queries."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from scripts.evidence_retrieval import encoded
from scripts.paper_capacity import capacity,support
from scripts.run_source_alignment import exclusive

ROOT=Path(__file__).resolve().parents[1]
METHODS=('lexical','graph','permuted_graph')
TRACKED=('scripts/paper_capacity.py','scripts/run_paper_capacity.py','scripts/retrieval_gap.py','scripts/evidence_retrieval.py','scripts/source_alignment.py','scripts/run_source_alignment.py','tests/test_paper_capacity.py','docs/PAPER-CAPACITY.md','docs/paper-capacity-inputs.json')

def worker(args):
    begin=time.perf_counter();cpu=time.process_time();manifest=json.loads(Path(args.manifest).read_bytes());input_bytes=0
    raw=Path(args.model).read_bytes();input_bytes+=len(raw);assert digest(raw)==manifest['model_sha256'];model=json.loads(raw);loc=model['shared']['locators']
    assert model['shared']['source_sha256']==manifest['source_sha256'] and model['shared']['source_kind']=='scifact-whole-original-record-v1'
    assert model['shared']['parameters']=={'k1':1.2,'b':.75,'max_facts':12,'source_budget':4096,'seeds':6,'neighbors':6}
    reports={}
    for method in METHODS:
        entry=manifest['methods'][method];raw=Path(entry['report_path']).read_bytes();input_bytes+=len(raw);assert digest(raw)==entry['report_sha256']
        report=json.loads(raw);assert report['model_sha256']==manifest['model_sha256'] and report['source_sha256']==manifest['source_sha256'] and report['method']==method and report['round']==1
        byrow={r['row_index']:r for r in report['records']};assert len(byrow)==298==report['retrieved_rows']
        for rec in byrow.values():
            proof={k:v for k,v in rec.items() if k not in ('proof_sha256','query_wall_s','query_cpu_s','gold_audit_wall_s','gold_audit_cpu_s','ranked_candidates')}
            assert digest(encoded(proof))==rec['proof_sha256']
            assert sum(loc[k]['length'] for k in rec['selected_ids'])==rec['admitted_record_bytes']<=4096 and len(rec['selected_ids'])<=12
            assert len(rec['selected_ids'])==len(set(rec['selected_ids']))
        reports[method]=byrow
    base=reports['lexical'];assert all(set(r)==set(base) for r in reports.values());bounds=[];comparisons=[];unannotated=0
    for index,rec in sorted(base.items()):
        gold=set(rec['gold_paper_ids'])
        assert all(set(r[index]['gold_paper_ids'])==gold and r[index]['question_sha256']==rec['question_sha256'] for r in reports.values())
        if not gold:
            assert all(r[index]['paper_metrics'] is None for r in reports.values());unannotated+=1;continue
        bound=capacity(loc,gold);bounds.append({'row_index':index,'question_id':rec['question_id'],'question_sha256':rec['question_sha256'],**bound})
        for method in METHODS:
            r=reports[method][index];selected=set(r['selected_ids']);missed=gold-selected;recovered=len(gold&selected)
            assert recovered==r['paper_metrics']['recovered_groups'] and len(gold)==r['paper_metrics']['gold_groups']
            assert bool(recovered==len(gold))==r['paper_metrics']['complete_coverage']
            assert recovered<=bound['gold_aware_max_recovered']
            comparisons.append({'method':method,'row_index':index,'prior_proof_sha256':r['proof_sha256'],'gold_groups':len(gold),'actual_recovered':recovered,
                'actual_complete':recovered==len(gold),'gold_complete_possible':bound['gold_complete_possible'],'gold_aware_max_recovered':bound['gold_aware_max_recovered'],
                'missed_gold_groups':len(missed),'missed_gold_single_record_over_budget':sum(loc[k]['length']>4096 for k in missed),
                'selected_non_gold_original_bytes':sum(loc[k]['length'] for k in selected-gold),
                'original_proof_source':manifest['methods'][method]['report_sha256']})
    assert len(bounds)==188 and unannotated==110 and sum(r['gold_groups'] for r in bounds)==209 and len(comparisons)==564
    rows=[]
    for method in METHODS:
        selected=[r for r in comparisons if r['method']==method];incomplete=[r for r in selected if not r['actual_complete']]
        rows.append({'method':method,'annotated_claims':len(selected),'actual_complete':sum(r['actual_complete'] for r in selected),
            'actual_incomplete':len(incomplete),'incomplete_intrinsically_impossible':sum(not r['gold_complete_possible'] for r in incomplete),
            'incomplete_capacity_possible':sum(r['gold_complete_possible'] for r in incomplete),
            'actual_recovered_groups':sum(r['actual_recovered'] for r in selected),'missed_gold_groups':sum(r['missed_gold_groups'] for r in selected),
            'missed_gold_single_record_over_budget':sum(r['missed_gold_single_record_over_budget'] for r in selected)})
    graph=next(r for r in rows if r['method']=='graph')
    result={'rows':rows,'capacity_cases':bounds,'method_comparisons':comparisons,'gold_aware_complete_ceiling':sum(r['gold_complete_possible'] for r in bounds),
        'gold_aware_macro_recall_ceiling':sum(r['gold_aware_recall_ceiling'] for r in bounds)/188,
        'gold_aware_micro_recovered_ceiling':sum(r['gold_aware_max_recovered'] for r in bounds),
        'H1_incomplete_at_least_half_intrinsically_impossible':support(graph['incomplete_intrinsically_impossible'],graph['actual_incomplete']),
        'H2_missed_gold_at_least_half_single_over_budget':support(graph['missed_gold_single_record_over_budget'],graph['missed_gold_groups']),
        'source_sha256':manifest['source_sha256'],'model_sha256':manifest['model_sha256'],'loaded_full_model_bytes':Path(args.model).stat().st_size,
        'application_model_and_report_input_returned_bytes':input_bytes,'application_input_scope':'Only model+three prior reports read_bytes, excludes manifest and module loads; no raw science/Store range reads',
        'capacity_unique_annotated_claims':188,'gold_groups_unique_claim_groups':209,'method_comparison_rows':564,'unannotated_rows':110,
        'diagnostic_workers':1,'new_scientific_trials':0,'new_training_runs':0,'new_source_range_bindings':0,'new_remote_model_calls':0,
        'worker_wall_s':time.perf_counter()-begin,'worker_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),
        'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None,
        'scope':'Known gold-aware capacity bound diagnostic, not deployable retrieval or intervention gain'}
    exclusive(Path(args.worker_report),encoded(result)+b'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','model','manifest','worker-report','freeze'):p.add_argument('--'+name)
    args=p.parse_args()
    if args.worker_report:worker(args);return
    out=Path(args.out);out.mkdir(exist_ok=False);checks=implementation_checksums();programs={n:{'bytes':(ROOT/n).stat().st_size,'sha256':digest((ROOT/n).read_bytes())} for n in TRACKED}
    code=None;error=None;report=out/'capacity-worker.json';t=time.perf_counter()
    with (out/'capacity-worker.log').open('xb') as log:
        try:code=subprocess.run([sys.executable,'-m','scripts.run_paper_capacity','--model',args.model,'--manifest',args.manifest,'--worker-report',str(report)],cwd=ROOT,env={k:v for k,v in os.environ.items() if not k.startswith('RKV_LLM_')},stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
        except subprocess.TimeoutExpired:error='TimeoutExpired'
    parent={'return_code':code,'error':error,'parent_full_process_wall_s':time.perf_counter()-t,'child_sha256':digest(report.read_bytes()) if report.exists() else None}
    exclusive(out/'capacity-parent.json',encoded(parent)+b'\n');assert code==0 and error is None,'Preserve failed diagnostic; no retries'
    begin=time.perf_counter();cpu=time.process_time();d=json.loads(report.read_bytes());assert digest(report.read_bytes())==parent['child_sha256']
    # Independent aggregate from per-claim details, with a direct all-record sum feasibility check.
    model_raw=Path(args.model).read_bytes();manifest=json.loads(Path(args.manifest).read_bytes());assert digest(model_raw)==manifest['model_sha256'];model=json.loads(model_raw)
    base_raw=Path(manifest['methods']['lexical']['report_path']).read_bytes();assert digest(base_raw)==manifest['methods']['lexical']['report_sha256'];base=json.loads(base_raw);byrow={r['row_index']:r for r in base['records']}
    for bound in d['capacity_cases']:
        gold=set(byrow[bound['row_index']]['gold_paper_ids']);size=sum(model['shared']['locators'][key]['length'] for key in gold)
        assert size==bound['gold_total_original_bytes'] and bound['gold_complete_possible']==(len(gold)<=12 and size<=4096)
    assert len({r['row_index'] for r in d['capacity_cases']})==188 and sum(r['gold_complete_possible'] for r in d['capacity_cases'])==d['gold_aware_complete_ceiling']
    for row in d['rows']:
        assert row['actual_complete']+row['actual_incomplete']==188 and row['incomplete_intrinsically_impossible']+row['incomplete_capacity_possible']==row['actual_incomplete']
    exclusive(out/'derived-metrics.json',encoded({k:v for k,v in d.items() if k not in ('capacity_cases','method_comparisons') }|{'freeze':args.freeze,'parent_full_process_wall_s':parent['parent_full_process_wall_s']})+b'\n')
    files={'rkv1/'+n:{'bytes':(ROOT/'rkv1'/n).stat().st_size,'sha256':sha} for n,sha in checks.items()};html=ROOT/'rkv1/memory_demo.html';files['rkv1/memory_demo.html']={'bytes':html.stat().st_size,'sha256':digest(html.read_bytes())}
    exclusive(out/'source-checksums.json',encoded(checks)+b'\n');exclusive(out/'source-resource.json',encoded({'files':files,'total_bytes':sum(r['bytes'] for r in files.values()),'assessment_programs':{n:v for n,v in programs.items() if n.startswith('scripts/')}})+b'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows=d['rows'];methods=list(METHODS);fig,axes=plt.subplots(1,2,figsize=(13,5));axes[0].bar(methods,[r['actual_complete'] for r in rows],label='Actual previous complete',color='#2563eb');axes[0].axhline(d['gold_aware_complete_ceiling'],color='#ef4444',linestyle='--',label='Gold-aware whole-paper bound (not deployable)');axes[0].set_ylim(0,210);axes[0].set_ylabel('Annotated claims /188');axes[0].legend(fontsize=8)
    a=[r['incomplete_intrinsically_impossible'] for r in rows];axes[1].bar(methods,a,label='Whole gold cannot fit',color='#ef4444');axes[1].bar(methods,[r['incomplete_capacity_possible'] for r in rows],bottom=a,label='Whole gold can fit, actual incomplete',color='#f59e0b');axes[1].set_ylim(0,max(r['actual_incomplete'] for r in rows)*1.18);axes[1].set_ylabel('Previous incomplete claims');axes[1].legend(fontsize=8)
    fig.suptitle('Known SciFact capacity diagnosis, frozen 12 whole papers /4096 bytes');fig.tight_layout();fig.savefig(out/'paper-capacity.png',dpi=160);plt.close(fig)
    assert checks==implementation_checksums() and programs=={n:{'bytes':(ROOT/n).stat().st_size,'sha256':digest((ROOT/n).read_bytes())} for n in TRACKED}
    exclusive(out/'analysis-timing.json',encoded({'wall_s':time.perf_counter()-begin,'cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'scope':'Additional independent per-gold byte-sum feasibility/aggregate and plot; not query time'})+b'\n')
    print(json.dumps({k:v for k,v in d.items() if k.startswith('H') or k.startswith('gold_aware')}),flush=True)

if __name__=='__main__':main()
