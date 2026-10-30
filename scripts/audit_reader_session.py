"""Independent original JSONL ranking/ranges and immutable history audit."""
import hashlib,json,math
from collections import Counter
from pathlib import Path
from scripts.audit_evidence_view_index import ReferenceIndex


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def rank_all(ref,question):
    counts=Counter(ref.tokenize(question));scores={}
    for term in sorted(counts):
        posting=ref.postings.get(term,{})
        if not posting:continue
        weight=math.log(1+(ref.n-len(posting)+.5)/(len(posting)+.5))
        for key in sorted(posting):
            tf=posting[key];score=counts[term]*weight*tf*2.2/(tf+1.2*(.25+.75*ref.lengths[key]/ref.average))
            scores[key]=scores.get(key,0)+score
    return sorted(scores,key=lambda key:(-scores[key],key))
def audit(folder,*,expected_source_identities=None):
    folder=Path(folder);worker=json.loads((folder/'worker.json').read_bytes());n=worker['revisions']
    if worker['completed_queries']!=8*n or len(list(folder.glob('query-*.json')))!=8*n:raise ValueError('Incomplete planned query denominator')
    from rkv1.store import Store
    store=Store(folder/'store',io_backend='bounded');refs=[];source_B=0
    for i,meta in enumerate(worker['snapshots']):
        raw=(folder/'originals'/f'{i}.jsonl').read_bytes()
        if sha(raw)!=meta['source_SHA'] or len(raw)!=meta['source_B']:raise ValueError('Original input source identity differs')
        if expected_source_identities is not None:
            expected=expected_source_identities[str(worker['size'])+':'+str(i)]
            if expected!={'bytes':len(raw),'sha256':sha(raw)}:raise ValueError('Externally frozen owned source fixture differs')
        with store.snapshot(meta['sid']) as snap:restored=snap.read_range('corpus.jsonl')
        if restored!=raw:raise ValueError('Original historical Store source differs')
        source_B+=len(restored);refs.append(ReferenceIndex(raw,expected_source_sha256=sha(raw)))
        if refs[-1].n!=worker['size']:raise ValueError('Original document count differs')
        model=(folder/'models'/f'{i}.json').read_bytes()
        if sha(model)!=meta['model_SHA'] or len(model)!=meta['model_B']:raise ValueError('Original model identity differs')
    packet_SHAs=[];bindings=returned=0
    for index in range(8*n):
        row=json.loads((folder/f'query-{index:03}.json').read_bytes());r=row['result'];old=row['requested_revision'];ref=refs[old];meta=worker['snapshots'][old]
        # Independent request schedule; no candidate fixture/reader/selector import.
        revision=index//8;pos=index%8
        expect_old=(revision,revision,max(0,revision-1),revision,0,revision,max(0,revision-1),revision)[pos]
        question=('alpha beta','gamma delta','alpha epoch0','zzznomatchterm','beta epsilon','alpha gamma','beta delta','group3')[pos]
        if row['index']!=index or row['revision']!=revision or old!=expect_old or row['question']!=question:raise ValueError('Fixed original request schedule differs')
        selected=[];used=0
        for key in rank_all(ref,question):
            length=ref.raws[key][1]
            if used+length>4096:continue
            selected.append(key);used+=length
            if len(selected)==12:break
        if r['selected_ids']!=selected or r['admitted_record_bytes']!=used or r['source_byte_budget']!=4096 or r['max_papers']!=12 or r['method']!='lexical' or r['model_sha256']!=meta['model_SHA'] or r['snapshot_id']!=meta['sid'] or r['source_sha256']!=ref.sha or r['generated_answer'] is not None or r['scientific_entailment_verified'] is not False:raise ValueError('Independent ranking/budget/context differs')
        hits=[]
        for key in selected:
            offset,length,digest,raw=ref.raws[key];obj=json.loads(raw)
            hits.append({'paper_id':key,'title':obj['title'],'abstract':obj['abstract'],'locator':{'snapshot_id':meta['sid'],'path':'corpus.jsonl','offset':offset,'length':length,'sha256':digest},'title_sha256':sha(obj['title'].encode()),'abstract_sha256':sha(canonical(obj['abstract']))})
            bindings+=1;returned+=length
        if canonical(hits)!=canonical(r['hits']) or sha(canonical(r))!=row['packet_SHA'] or r['selected_source_identity_verified'] is not True:raise ValueError('Original literal evidence/range/packet differs')
        if row['session_info'] is not None:
            info=row['session_info']
            if info['retained_readers']>info['reader_capacity'] or info['retained_model_payload_B']>info['max_retained_model_payload_B'] or info['implicit_HEAD'] is not False or info['decoded_source_cache'] is not False:raise ValueError('Session bound or source-cache contract violated')
        packet_SHAs.append(row['packet_SHA'])
    if len(worker['negative_controls'])!=3 or not all(c['refused'] is True for c in worker['negative_controls']):raise ValueError('Formal fault controls incomplete')
    return {'verified_queries':8*n,'original_source_restores':n,'source_application_return_B':source_B,'independent_original_record_bindings':bindings,'independent_record_reference_B':returned,'packet_SHAs':packet_SHAs,'model_HTTP_calls':0,'real_human_or_scientific_dialogue_validation':False}
