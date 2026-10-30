"""Gold is loaded only after every fixed campaign and independent row audit."""
import hashlib,json
from pathlib import Path
from scripts.source_availability_metrics import score


def score_completed(folders, questions, gold_loader, independent_row_verifier):
    if type(folders) is not list or len(folders)!=9 or len({str(p) for p in folders})!=9:
        raise ValueError('Nine distinct planned fresh campaigns required before gold')
    expected={q['id']:q['question'] for q in questions}
    if len(expected)!=len(questions):raise ValueError('Duplicate question cohort')
    verified=[];identities=set();counts={m:0 for m in ('whole_record','first_two','overlap_two')}
    for folder in folders:
        folder=Path(folder)
        final=json.loads((folder/'worker-finally.json').read_bytes())
        if not final['success'] or final['completed_queries']!=len(questions) or final['planned_queries']!=len(questions):
            raise ValueError('Incomplete campaign; no gold access')
        worker=json.loads((folder/'worker.json').read_bytes())
        if worker['method'] not in counts or worker['completed_queries']!=len(questions) or worker['planned_queries']!=len(questions) or worker['gold_read_by_worker'] is not False:
            raise ValueError('Campaign method/denominator or phase differs')
        counts[worker['method']]+=1;identities.add((worker['model_SHA'],worker['snapshot_id']))
        files=sorted(folder.glob('prediction-*.json'))
        if len(files)!=len(questions):raise ValueError('Prediction file count differs')
        seen=set()
        for p in files:
            row=json.loads(p.read_bytes());qid=row['id']
            if qid not in expected or qid in seen or row['question']!=expected[qid] or type(row['index']) is not int or not 0<=row['index']<len(questions) or questions[row['index']]['id']!=qid:
                raise ValueError('Prediction identity or original question differs')
            seen.add(qid)
            result=row['result'];view=result['view'];encoded=bytes.fromhex(view['encoded_hex'])
            if len(encoded)!=view['encoded_B'] or len(encoded)>20000 or hashlib.sha256(encoded).hexdigest()!=view['sha256']:
                raise ValueError('Prediction view identity or full byte cap differs')
            actual=independent_row_verifier(row,worker['method'])
            canonical=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
            if canonical(actual)!=canonical(result['source_verification']['available_original_sentence_indices']):
                raise ValueError('Independent original source availability differs')
            verified.append((folder.name,worker['method'],qid,actual))
        if seen!=set(expected):raise ValueError('Missing original cohort IDs')
    if len(identities)!=1 or any(n!=3 for n in counts.values()):raise ValueError('Frozen model/SID or balanced repetitions differ')
    # This is the first possible annotation-file callback; selections are immutable.
    gold=gold_loader()
    if set(gold)!=set(expected):raise ValueError('Original annotation denominator differs')
    return [{'campaign':name,'method':method,'id':qid,'source_only':score(available,gold[qid])} for name,method,qid,available in verified]
