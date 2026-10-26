"""Independent raw-member training audit. Strict readiness can fail honestly."""
import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path
import re
import subprocess
import time
from rkv1.benchmark import peak_rss
from rkv1.controlled import implementation_checksums
from rkv1.core import digest
from rkv1.store import Store
from scripts.run_source_alignment import encoded,ledger
from scripts.run_memory_concurrency import save


def main():
    begin=time.perf_counter();cpu=time.process_time();p=argparse.ArgumentParser()
    for k in ('work','out','inputs','freeze','test-log'):p.add_argument('--'+k,required=True)
    args=p.parse_args();out=Path(args.out);work=Path(args.work);inputs=Path(args.inputs)
    raw=(inputs/'corpus.json').read_bytes();labels_raw=(inputs/'labels-train.jsonl').read_bytes();corpus=json.loads(raw);training=[json.loads(x) for x in labels_raw.splitlines()]
    manifest=json.loads(Path('docs/entailment-inputs.json').read_text('utf-8'));assert digest(raw)==manifest['files']['corpus.json']['sha256'] and digest(labels_raw)==manifest['files']['labels-train.jsonl']['sha256']
    bytext=defaultdict(list)
    for key,text in corpus.items():bytext[text].append(key)
    aliases={k:min(group) for group in bytext.values() for k in group};text_rep={t:min(group) for t,group in bytext.items()}
    env=json.loads((out/'environment.json').read_text('utf-8'));checks=implementation_checksums();assert checks==env['implementation_checksums']
    for k,v in checks.items():assert digest(subprocess.check_output(['git','show',args.freeze+':rkv1/'+k]))==v
    for k,v in env['program_protocol_sha256'].items():assert digest(Path(k).read_bytes())==v==digest(subprocess.check_output(['git','show',args.freeze+':'+k]))
    log=Path(args.test_log).read_text('utf-8');assert 'Ran 263 tests' in log and 'OK (skipped=1)' in log
    rows=[];reference=None;reference_tree=None;raw_bytes=0;total_bindings=0;total_leaves=0
    for n in (1,2,3):
        child_raw=(out/f'round-{n}.json').read_bytes();pr=(out/f'round-{n}-parent.json').read_bytes();raw_bytes+=len(child_raw)+len(pr)
        data=json.loads(child_raw);parent=json.loads(pr);assert data['source_SHA']==digest(raw) and data['training_SHA']==digest(labels_raw)
        assert parent['return_code']==0 and parent['error'] is None
        assert parent['child_report_sha256']==digest(child_raw) and parent['parent_full_process_wall_s']>=data['worker_wall_s']>0
        assert data['no_dev_file_opened'] and not data['retrieval_scores_computed'] and data['new_model_training_runs']==0
        store=Store(work/f'round-{n}'/'store',io_backend='bounded');sid=data['ingest']['commit']['snapshot_id'];counts=Counter();i=0
        with store.snapshot(sid) as snapshot:
            for index,doc in enumerate(training):
                for leaf in sorted(set(re.findall(r'\bsent\d+\b',doc['proof']))):
                    rec=data['records'][i];i+=1;uid=doc['meta']['worldtree_provenance'][leaf]['uuid'];text=doc['meta']['triples'][leaf]
                    assert (rec['row_index'],rec['question_id'],rec['leaf_id'])==(index,doc['id'],leaf)
                    if uid in corpus:key=aliases[uid];method='provided_UUID'
                    elif text in text_rep:key=text_rep[text];method='exact_decoded_text'
                    else:key=None;method='unresolved'
                    assert rec['fact_id']==key and rec['resolution']==method and rec['annotation_text_sha256']==digest(text.encode())
                    counts[method]+=1
                    if key is None:assert rec['locator'] is None and rec['annotation_exact'] is None
                    else:
                        loc=rec['locator'];assert loc['snapshot_id']==sid and loc['path']=='corpus.json'
                        original=raw[loc['offset']:loc['offset']+loc['length']]
                        assert digest(original)==loc['sha256'] and json.loads(b'{'+original+b'}')=={key:corpus[key]}
                        assert snapshot.read_range('corpus.json',loc['offset'],loc['length'])==original
                        assert rec['annotation_exact']==(text==corpus[key]);counts['original_bindings']+=1
                        counts['annotation_literal_exact' if text==corpus[key] else 'UUID_bound_annotation_different']+=1
            assert snapshot.read_range('corpus.json')==raw
        assert i==len(data['records']) and dict(counts)==data['counts'];total_bindings+=counts['original_bindings'];total_leaves+=i
        if reference is None:reference=data['records']
        else:assert reference==data['records']
        tree=ledger(store.root);saved=json.loads((work/f'round-{n}'/'ledger.json').read_bytes());assert tree==saved['before']==saved['after']
        assert digest(encoded(tree))==data['store_tree_sha256'] and data['store_unchanged'] and data['source_full_recovery']
        assert sum(v['bytes'] for v in tree.values())==data['files']['store_bytes']
        if reference_tree is None:reference_tree=tree
        else:assert tree==reference_tree
        rows.append({'round':n,'counts':dict(counts),'worker_wall_s':data['worker_wall_s'],'worker_cpu_s':data['worker_cpu_s'],
            'parent_full_process_wall_s':parent['parent_full_process_wall_s'],'observed_peak_rss_bytes':data['observed_peak_rss_bytes'],
            'files':data['files'],'ingest':{k:data['ingest'][k] for k in ('wall_s','cpu_s')},'physical_audit':data['physical_audit']})
    counts=rows[0]['counts'];assert len(training)==1313 and len(corpus)==11941 and len(text_rep)==11521
    assert counts=={'provided_UUID':3982,'exact_decoded_text':1529,'unresolved':253,'original_bindings':5511,'annotation_literal_exact':2142,'UUID_bound_annotation_different':3369}
    save(out/'derived-metrics.json',{'rows':rows,'training_rows':len(training),'unique_training_ids':len({r['id'] for r in training}),
        'source_ids':len(corpus),'exact_unique_source_sentences':len(text_rep),'source_aliases':len(corpus)-len(text_rep),
        'total_repeated_leaf_checks':total_leaves,'total_repeated_original_bindings':total_bindings,'source_full_recoveries':3,'raw_report_json_bytes':raw_bytes,
        'all_training_leaves_source_resolvable_gate':counts['unresolved']==0,'all_training_annotations_literal_equal_source_gate':counts['annotation_literal_exact']==sum(counts[k] for k in ('provided_UUID','exact_decoded_text','unresolved')),
        'retrieval_quality_gate':None,'model_training_runs':0,'dev_unparsed':True})
    save(out/'source-checksums.json',checks)
    files={p.as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(Path('rkv1').rglob('*')) if p.suffix in ('.py','.html')}
    assert set(files)=={'rkv1/'+k for k in checks}|{'rkv1/memory_demo.html'}
    save(out/'source-resource.json',{'files':files,'total_bytes':sum(x['bytes'] for x in files.values()),
        'assessment_programs':{k:{'bytes':Path(k).stat().st_size,'sha256':digest(Path(k).read_bytes())} for k in env['program_protocol_sha256'] if k.startswith('scripts/')},'new_model_bytes':0,'new_training_runs':0})
    save(out/'validation.json',{'mechanical_source_bindings_pass':True,'strict_all_resolvable_gate':False,'strict_all_literal_gate':False,
        'workers':3,'parent_timing_records':3,'repeated_leaf_checks':total_leaves,'repeated_original_bindings':total_bindings,'source_full_recoveries':3,
        'dev_unparsed':True,'retrieval_scores_computed':False,'new_model_training_runs':0,'new_remote_model_calls':0,'unit_tests_run':263,'unit_tests_passed':262,'unit_tests_skipped':1,
        'runtime_module_count':len(checks),'html_files':1,'freeze':args.freeze,'physical_SSD_bytes':None,'all_system_file_bytes':None,'cold_cache':None,'cross_machine':None})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained')
    axes[0].bar(['Existing UUID','Exact text','Unresolved'],[3982,1529,253],color=['#2563eb','#10b981','#dc2626'])
    axes[0].set_title('Training leaf source mapping');axes[0].set_ylabel('Occurrences / 5764 leaves')
    axes[1].bar(['Literal equal','UUID + rewrite','Unresolved'],[2142,3369,253],color=['#10b981','#f59e0b','#dc2626'])
    axes[1].set_title('Annotation versus actual source');axes[1].set_ylabel('Occurrences / 5764 leaves')
    for name,dx,color in (('worker_cpu_s',-.18,'#64748b'),('parent_full_process_wall_s',.18,'#2563eb')):
        axes[2].bar([r['round']+dx for r in rows],[r[name] for r in rows],.34,label='Worker CPU' if dx<0 else 'Parent full wall',color=color)
    axes[2].set_title('Diagnostic cost only');axes[2].set_ylabel('Seconds / worker');axes[2].set_xticks((1,2,3));axes[2].set_xlabel('Round');axes[2].legend(frameon=False)
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.margins(y=.12)
    fig.suptitle('RKV-1 v0.49: training-source readiness audit; strict gates fail, dev not opened')
    fig.savefig(out/'source-alignment.png',dpi=160);plt.close(fig)
    save(out/'analysis-timing.json',{'analysis_wall_s':time.perf_counter()-begin,'analysis_cpu_s':time.process_time()-cpu,'observed_peak_rss_bytes':peak_rss()})
    print(json.dumps({'bindings':total_bindings,'source_readiness_gate':False,'literal_equality_gate':False,'dev_unparsed':True}))


if __name__=='__main__':main()
