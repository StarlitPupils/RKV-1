"""Complete source audit and annotation gate; original packets stay private."""
from collections import defaultdict
from fractions import Fraction
import hashlib,json,math,time,sys
from pathlib import Path
from rkv1.store import Store
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rkv1.benchmark import peak_rss
from scripts.audit_evidence_view_index import ReferenceIndex
from scripts.score_evidence_view_cohort import score_completed

METHODS=('whole_record','first_two','overlap_two')
SCHEDULE=(METHODS,(METHODS[1],METHODS[2],METHODS[0]),(METHODS[2],METHODS[0],METHODS[1]))


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def read_json(path):
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('Duplicate JSON field')
            out[key]=value
        return out
    def invalid(value):raise ValueError('Nonfinite JSON value')
    return json.loads(Path(path).read_bytes(),object_pairs_hook=pairs,parse_constant=invalid)


def identity(path):
    raw=Path(path).read_bytes()
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def ledger(folder):
    folder=Path(folder)
    return {p.relative_to(folder).as_posix():identity(p) for p in sorted(folder.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def write_new(path,value):
    with Path(path).open('xb') as stream:stream.write(canonical(value)+b'\n')


def positive(value,*,allow_zero=False):
    return type(value) in (float,int) and math.isfinite(value) and (value>=0 if allow_zero else value>0)


def ratio(top,bottom):
    return top/bottom if positive(top,allow_zero=True) and positive(bottom) else None


def reachable_python_B(value):
    """One-time object graph sum, not allocator/OS/native total RSS."""
    seen=set();pending=[value];total=0
    while pending:
        item=pending.pop();key=id(item)
        if key in seen:continue
        seen.add(key);total+=sys.getsizeof(item)
        if type(item) is dict:pending.extend(item.keys());pending.extend(item.values())
        elif type(item) in (tuple,list,set,frozenset):pending.extend(item)
        elif hasattr(item,'__dict__'):pending.append(vars(item))
    return total


def source_metric(available,evidence):
    # Separate postprediction integer/set reference; does not import the primary scorer.
    if not evidence:return {'annotated':False,'paper_recall':None,'complete_rationale_available':None}
    selected={key[4:]:set(indices) for key,indices in available.items()}
    matched=sum(paper in selected for paper in evidence)
    complete=False
    for paper,alternatives in evidence.items():
        if type(paper) is not str or type(alternatives) is not list or not alternatives:raise ValueError('Invalid original rationale alternatives')
        for alternative in alternatives:
            indices=alternative.get('sentences') if type(alternative) is dict else None
            if type(indices) is not list or not indices or any(type(i) is not int or i<0 for i in indices) or len(set(indices))!=len(indices):raise ValueError('Invalid original rationale indices')
            if all(i in selected.get(paper,set()) for i in indices):complete=True
    return {'annotated':True,'paper_recall':float(Fraction(matched,len(evidence))),'complete_rationale_available':complete}


def load_questions(config):
    path=Path(config['questions_path'])
    if identity(path)['sha256']!=config['questions_sha']:raise ValueError('Original question SHA differs')
    values=read_json(path)
    if type(values) is not list or len(values)!=config['expected_questions']:raise ValueError('Fixed question count differs')
    questions=[];seen=set();normalized=set()
    for row in values:
        if type(row) is not dict or set(row)!={'claim_id','claim'} or type(row['claim']) is not str or not row['claim'].strip():raise ValueError('Original question-only schema differs')
        qid=str(row['claim_id']);text=row['claim'];key=' '.join(text.split()).casefold()
        if not qid or qid in seen or key in normalized:raise ValueError('Original cohort identity is not unique')
        seen.add(qid);normalized.add(key);questions.append({'id':qid,'question':text})
    return questions


def audit(config_path,audit_config_path,plan_path,out,*,guard=None):
    """No annotation parse unless all nine children and every reference row pass.

    A failure produces an exclusive partial-status/finally record and re-raises.
    It never resumes the plan, mutates a prediction or silently treats missing as zero.
    """
    out=Path(out);out.mkdir(exist_ok=False)
    start,cpu=time.perf_counter(),time.process_time();success=False;gold_parsed=False
    checked=0;expected_total=None;phase='preflight';before=None;store_before=None;inputs_before=None
    plan_path=Path(plan_path)
    try:
        config=read_json(config_path);audit_config=read_json(audit_config_path)
        required={'source_sha256','source_B','gold_path','gold_sha256','annotated','unannotated','selection_metadata_path','selection_metadata_sha256'}
        if set(audit_config)!=required:raise ValueError('Exact separate audit-only configuration required')
        questions=load_questions(config);n=len(questions);expected_total=9*n
        if type(config['owned_fixture']) is not bool or type(audit_config['annotated']) is not int or type(audit_config['unannotated']) is not int or audit_config['annotated']+audit_config['unannotated']!=n:raise ValueError('Fixed quality denominators differ')
        if not config['owned_fixture'] and (n!=270 or audit_config['annotated']!=168 or audit_config['unannotated']!=102):raise ValueError('Frozen real denominators differ')
        if guard:guard()
        protected=[Path(config_path),Path(audit_config_path),Path(config['questions_path']),Path(config['model_path']),Path(audit_config['gold_path'])]
        if audit_config['selection_metadata_path'] is not None:protected.append(Path(audit_config['selection_metadata_path']))
        inputs_before={str(p.resolve()):identity(p) for p in protected}
        if identity(config['model_path'])['sha256']!=config['model_sha'] or identity(audit_config['gold_path'])['sha256']!=audit_config['gold_sha256']:raise ValueError('Pinned model or annotation identity differs')
        if audit_config['selection_metadata_path'] is not None:
            if identity(audit_config['selection_metadata_path'])['sha256']!=audit_config['selection_metadata_sha256']:raise ValueError('Original cohort selection provenance differs')
        before=ledger(plan_path);store_before=ledger(config['store_root'])
        final=read_json(plan_path/'plan-finally.json');plan=read_json(plan_path/'plan.json')
        if final['success'] is not True or final['planned_workers']!=9 or final['completed_workers']!=9 or final['planned_predictions']!=expected_total or plan['planned_predictions']!=expected_total or plan['questions_per_worker']!=n or len(plan['rows'])!=9:raise ValueError('Incomplete fixed plan; annotations remain unopened')
        folders=[];workers=[];private_rows=[];by_campaign={};packet_repetitions=defaultdict(list)
        for round_number,methods in enumerate(SCHEDULE,1):
            for method in methods:
                name=f'round-{round_number}-{method}';row=plan['rows'][len(folders)];parent=read_json(plan_path/(name+'-parent.json'))
                if canonical(parent)!=canonical(row) or parent['round']!=round_number or parent['method']!=method or parent['case']!=name or parent['exit_code']!=0 or parent['retries']!=0:raise ValueError('Exact parent order/identity/status differs')
                folder=plan_path/name;worker=read_json(folder/'worker.json');body=read_json(folder/'worker-finally.json');process=read_json(folder/'process-entry-finally.json')
                if worker['model_SHA']!=config['model_sha'] or worker['snapshot_id']!=config['sid'] or worker['method']!=method or worker['new_model_API_calls']!=0 or body['formal_retries']!=0:raise ValueError('Frozen model/SID/method or zero-call scope differs')
                if process['success'] is not True or not positive(body['full_wall_s']) or not positive(process['entry_full_wall_s']) or not positive(process['entry_full_CPU_s'],allow_zero=True) or not positive(parent['parent_full_wall_s']) or not positive(body['full_CPU_s'],allow_zero=True) or not body['full_wall_s']<=process['entry_full_wall_s']<=parent['parent_full_wall_s'] or body['full_CPU_s']>process['entry_full_CPU_s']:raise ValueError('Worker/body/process/parent clocks invalid')
                query_wall=query_cpu=preparation_B=verification_B=view_B=bindings=0
                for i in range(n):
                    r=read_json(folder/f'prediction-{i}.json');r['campaign']=name;private_rows.append(r)
                    query_wall+=r['query_wall_s'];query_cpu+=r['query_CPU_s']
                    v=r['result'];preparation_B+=v['view']['preparation_record_return_B'];verification_B+=v['source_verification']['verification_record_return_B'];view_B+=v['view']['encoded_B'];bindings+=v['view']['prepared_record_count']
                    if not positive(r['query_wall_s'],allow_zero=True) or not positive(r['query_CPU_s'],allow_zero=True):raise ValueError('Query clocks invalid')
                    packet_repetitions[(method,r['id'])].append(v['view']['sha256'])
                if worker['constructor']['wall_s']+query_wall>body['full_wall_s']+1e-7 or worker['constructor']['CPU_s']+query_cpu>body['full_CPU_s']+1e-7:raise ValueError('Incomplete full-worker clock scope')
                w={'round':round_number,'campaign':name,'method':method,'worker_full_wall_s':process['entry_full_wall_s'],'worker_CPU_s':process['entry_full_CPU_s'],'worker_peak_RSS_B':process['process_peak_RSS_B'],'worker_body_wall_s':body['full_wall_s'],'worker_body_CPU_s':body['full_CPU_s'],'parent_full_wall_s':parent['parent_full_wall_s'],'parent_CPU_s':parent['parent_CPU_s'],'constructor':worker['constructor'],'query_wall_sum_s':query_wall,'query_CPU_sum_s':query_cpu,'preparation_record_return_B':preparation_B,'selected_verification_record_return_B':verification_B,'complete_view_B':view_B,'source_bindings':bindings}
                # Constructor model_info is metadata only, never contains source text.
                workers.append(w);by_campaign[name]=w;folders.append(folder)
        if any(len(v)!=3 or len(set(v))!=1 for v in packet_repetitions.values()) or len(packet_repetitions)!=3*n:raise ValueError('Mechanical packet repetitions differ')
        phase='fresh_original_source_and_independent_index';t,c=time.perf_counter(),time.process_time()
        with Store(config['store_root'],io_backend='bounded').snapshot(config['sid']) as snapshot:
            source=snapshot.read_range('corpus.jsonl')
        if len(source)!=audit_config['source_B']:raise ValueError('Original source byte count differs')
        reference=ReferenceIndex(source,expected_source_sha256=audit_config['source_sha256'])
        postings_B=len(canonical({'lengths':reference.lengths,'postings':reference.postings}));object_B=reachable_python_B(reference)
        index_stats={'wall_s':time.perf_counter()-t,'CPU_s':time.process_time()-c,'process_peak_RSS_B':peak_rss(),'source_application_return_B':len(source),'original_records':reference.n,'posting_terms':len(reference.postings),'posting_entries':sum(len(p) for p in reference.postings.values()),'postings_and_lengths_JSON_B':postings_B,'reference_reachable_python_object_B':object_B,'Python_object_sum_not_allocator_native_or_RSS':True,'original_source_SHA':reference.sha,'CAS_decode_B':None,'physical_SSD_read_B':None}
        available={};phase='all_independent_rows_before_gold'
        def verify(row,method):
            nonlocal checked
            if guard:guard()
            actual=reference.verify_prediction(row,method,expected_sid=config['sid']);checked+=1
            available[(method,row['id'])]=actual
            return actual
        def gold_loader():
            nonlocal gold_parsed,phase
            if checked!=expected_total:raise ValueError('Independent rows incomplete before gold')
            if ledger(plan_path)!=before or ledger(config['store_root'])!=store_before or any(identity(p)!=value for p,value in inputs_before.items()):raise ValueError('Immutable inputs or predictions changed before gold')
            if guard:guard()
            phase='postprediction_annotations';gold_parsed=True;values=read_json(audit_config['gold_path'])
            if type(values) is not list or len(values)!=n or any(type(v) is not dict or 'id' not in v or 'evidence' not in v for v in values):raise ValueError('Original annotation schema differs')
            gold={str(v['id']):v['evidence'] for v in values}
            if len(gold)!=n or set(gold)!={q['id'] for q in questions} or sum(bool(v) for v in gold.values())!=audit_config['annotated']:raise ValueError('Original annotation identity/split differs')
            write_new(out/'gold-phase-marker.json',{'parsed_at_ns':time.time_ns(),'all_predictions_and_independent_rows_before_parse':True,'independent_rows':checked,'quality_annotated':audit_config['annotated'],'quality_null':audit_config['unannotated']})
            gold_loader.values=gold
            return gold
        primary=score_completed(folders,questions,gold_loader,verify)
        phase='independent_source_metric_and_gates';metric_by={};quality=[]
        for row in primary:
            independent=source_metric(available[(row['method'],row['id'])],gold_loader.values[row['id']])
            if any(canonical(row['source_only'][key])!=canonical(value) for key,value in independent.items()):raise ValueError('Independent original annotation metric differs')
            metric_by[(row['campaign'],row['id'])]=independent
            quality.append({'campaign':row['campaign'],'method':row['method'],'id':row['id'],**independent})
        groups=[]
        for w in workers:
            values=[metric_by[(w['campaign'],q['id'])] for q in questions];annotated=[v for v in values if v['annotated']]
            g={**w,'questions':n,'annotated':len(annotated),'quality_null':n-len(annotated),'complete_rationale_available':sum(v['complete_rationale_available'] for v in annotated),'macro_paper_recall':sum(v['paper_recall'] for v in annotated)/len(annotated) if annotated else None}
            groups.append(g)
        repeated=all(len({canonical(metric_by[(f'round-{rnd}-{method}',q['id'])]) for rnd in (1,2,3)})==1 for method in METHODS for q in questions)
        first={g['method']:g for g in groups if g['round']==1}
        h2=repeated and audit_config['annotated']>0 and all(first['overlap_two']['complete_rationale_available']>first[m]['complete_rationale_available'] for m in ('whole_record','first_two'))
        pairs=[]
        for rnd in (1,2,3):
            a=by_campaign[f'round-{rnd}-whole_record'];c=by_campaign[f'round-{rnd}-overlap_two']
            pairs.append({'round':rnd,**{field:ratio(c[field],a[field]) for field in ('worker_full_wall_s','worker_CPU_s','parent_full_wall_s')}})
        h3=all(value is not None and value<=1 for p in pairs for key,value in p.items() if key!='round')
        if ledger(plan_path)!=before or ledger(config['store_root'])!=store_before or any(identity(p)!=value for p,value in inputs_before.items()):raise ValueError('Immutable inputs or predictions changed during audit')
        rows_public=[]
        for r in private_rows:
            m=next(w['method'] for w in workers if w['campaign']==r['campaign']);v=r['result']
            rows_public.append({'campaign':r['campaign'],'method':m,'id':r['id'],'index':r['index'],'question_SHA':hashlib.sha256(r['question'].encode()).hexdigest(),'ordered_candidate_ids':v['ordered_candidate_ids'],'view_B':v['view']['encoded_B'],'view_SHA':v['view']['sha256'],'available_original_sentence_indices':available[(m,r['id'])],**metric_by[(r['campaign'],r['id'])]})
        result={'status':'complete_source_only_diagnostic','planned_workers':9,'completed_workers':9,'planned_predictions':expected_total,'verified_predictions':checked,'unique_questions':n,'H1':True,'H2':bool(h2),'H3':h3,'joint':bool(h2 and h3),'gold_parsed_only_after_all_independent_rows':True,'metrics_identical_three_repetitions':repeated,'groups':groups,'timing_ratios_C_over_A':pairs,'reference_index':index_stats,'rows':rows_public,'new_model_API_calls':0,'new_provider_requests':0,'annotation_source_availability_not_answer_quality':True,'worker_CPU_scope':'Python process_time only; quota subprocess CPU and full process-tree CPU uninstrumented null','full_system_IO_B':None,'query_clocks_exclude_final_prediction_write':True}
        write_new(out/'aggregate.json',result)
        write_new(out/'resources.json',{'protected_inputs':inputs_before,'private_predictions':before,'original_store_all_files':store_before,'plan_files_B':sum(v['bytes'] for v in before.values()),'store_files_B':sum(v['bytes'] for v in store_before.values()),'reference_index':index_stats,'retained_RSS_is_not_full_reference_index_RSS':True,'all_historical_resources_still_chargeable':True})
        success=True;return result
    except Exception as error:
        write_new(out/'partial-status.json',{'status':'incomplete_or_audit_failed','phase':phase,'error_class':type(error).__name__,'planned_predictions':expected_total,'verified_predictions':checked,'gold_parsed':gold_parsed,'H1':False,'H2':None,'H3':None,'joint':False,'no_remaining_plan_or_slot_replay':True,'incomplete_is_not_evidence_of_algorithm_inefficacy':True,'new_model_API_calls':0})
        raise
    finally:
        unchanged=None if before is None else ledger(plan_path)==before
        write_new(out/'analysis-finally.json',{'success':success,'phase':phase,'gold_parsed':gold_parsed,'verified_predictions':checked,'planned_predictions':expected_total,'prediction_files_unchanged':unchanged,'full_wall_s':time.perf_counter()-start,'full_CPU_s':time.process_time()-cpu,'process_peak_RSS_B':peak_rss(),'self_process_not_children_CPU':True})


if __name__=='__main__':
    import sys
    audit(*sys.argv[1:])
