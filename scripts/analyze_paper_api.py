"""Independent known-source API binding audit; not a quality/answer assessment."""
import argparse,json,time
from pathlib import Path
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.store import Store
from scripts.evidence_retrieval import encoded
from scripts.run_source_alignment import exclusive

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('work','out','source','manifest','freeze','test-log'):p.add_argument('--'+name,required=True)
    args=p.parse_args();begin=time.perf_counter();cpu=time.process_time();root=Path.cwd();out=Path(args.out);work=Path(args.work)
    raw=Path(args.source).read_bytes();manifest=json.loads(Path(args.manifest).read_bytes());assert digest(raw)==manifest['source_sha256']
    rows=[];bindings=0;methods=('lexical','graph','permuted_graph')
    for method in methods:
        report_raw=(out/(method+'.json')).read_bytes();report=json.loads(report_raw);parent=json.loads((out/(method+'-parent.json')).read_bytes())
        prior_raw=Path(manifest['methods'][method]['report_path']).read_bytes();assert digest(prior_raw)==manifest['methods'][method]['report_sha256']
        prior={r['row_index']:r for r in json.loads(prior_raw)['records']};assert len(prior)==len(report['records'])==298
        assert parent['return_code']==0 and parent['error'] is None and parent['child_sha256']==digest(report_raw)
        store=Store(work/method/'store',io_backend='bounded');sid=report['ingest']['commit']['snapshot_id'];checked=0
        with store.snapshot(sid) as snapshot:
            for rec in report['records']:
                old=prior.pop(rec['row_index']);assert rec['prior_proof_sha256']==old['proof_sha256']
                assert rec['selected_ids']==old['selected_ids'] and rec['admitted_record_bytes']==old['admitted_record_bytes'] and rec['hits']==old['hits']
                proof={k:v for k,v in rec.items() if k not in ('proof_sha256','query_wall_s','query_cpu_s')};assert digest(encoded(proof))==rec['proof_sha256']
                for hit in rec['hits']:
                    loc=hit['locator'];assert loc['snapshot_id']==sid and loc['path']=='corpus.jsonl'
                    original=raw[loc['offset']:loc['offset']+loc['length']]
                    assert len(original)==loc['length'] and digest(original)==loc['sha256'] and snapshot.read_range('corpus.jsonl',loc['offset'],loc['length'])==original
                    obj=json.loads(original);assert 'doc:'+str(obj['doc_id'])==hit['paper_id']
                    assert digest(obj['title'].encode('utf-8'))==hit['title_sha256'] and digest(encoded(obj['abstract']))==hit['abstract_sha256'];checked+=1
            assert not prior and snapshot.read_range('corpus.jsonl')==raw
        assert checked==report['bindings'];bindings+=checked
        rows.append({'method':method,'query_wall_s':sum(r['query_wall_s'] for r in report['records']),'query_cpu_s':sum(r['query_cpu_s'] for r in report['records']),
            'constructor':report['constructor'],'worker_wall_s':report['worker_wall_s'],'worker_cpu_s':report['worker_cpu_s'],'observed_peak_rss_bytes':report['observed_peak_rss_bytes'],
            'parent_full_process_wall_s':parent['parent_full_process_wall_s'],'files':report['files'],'selected_source_bindings':checked,'queries':298})
    assert bindings==2559
    checks=implementation_checksums();files={'rkv1/'+name:{'bytes':(root/'rkv1'/name).stat().st_size,'sha256':sha} for name,sha in checks.items()}
    files['rkv1/memory_demo.html']={'bytes':(root/'rkv1/memory_demo.html').stat().st_size,'sha256':digest((root/'rkv1/memory_demo.html').read_bytes())}
    programs={name:{'bytes':(root/name).stat().st_size,'sha256':digest((root/name).read_bytes())} for name in ('scripts/run_paper_api.py','scripts/analyze_paper_api.py','scripts/evidence_retrieval.py','scripts/source_alignment.py','scripts/run_source_alignment.py')}
    testlog=Path(args.test_log).read_text('utf-8');assert 'Ran 285 tests' in testlog and 'OK (skipped=1)' in testlog
    exclusive(out/'source-checksums.json',encoded(checks)+b'\n');exclusive(out/'source-resource.json',encoded({'files':files,'total_bytes':sum(x['bytes'] for x in files.values()),'assessment_programs':programs})+b'\n')
    exclusive(out/'derived-metrics.json',encoded({'rows':rows,'mechanism_workers':3,'mechanism_queries':894,'formal_selected_bindings':bindings,'additional_audit_selected_bindings':bindings,
        'new_scientific_quality_trials':0,'new_training_runs':0,'new_remote_model_calls':0,'all_frozen_prior_proofs_equal':True,'freeze':args.freeze,
        'scope':'Known-proof compatibility and original selected-source audit; not algorithm benefit, unknown data, NLI, answers or production performance'})+b'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4));axes[0].bar(methods,[r['queries'] for r in rows]);axes[0].set_ylim(0,335);axes[0].set_ylabel('Exact previous-proof matches /298')
    axes[1].bar(methods,[r['query_wall_s'] for r in rows]);axes[1].set_ylabel('Query wall seconds /298 (one worker each)');axes[1].set_ylim(bottom=0)
    fig.suptitle('Experimental public API: known-proof mechanical compatibility only');fig.tight_layout();fig.savefig(out/'paper-api.png',dpi=160);plt.close(fig)
    exclusive(out/'analysis-timing.json',encoded({'wall_s':time.perf_counter()-begin,'cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss(),'scope':'Additional raw-source and actual API Store recheck plus plot; separate from mechanism query timings'})+b'\n')

if __name__=='__main__':main()
