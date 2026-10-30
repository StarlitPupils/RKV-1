"""Independent toy view byte/choice/admission reference, no candidate imports."""
import json
import re
from rkv1.experiments.paper_retriever import STOP
from scripts.independent_span_reference import reference_tokens, original_record, sha


def encode(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',', ':'),allow_nan=False).encode('utf-8')


def check(source, question, records, method, encoded, cap, *, record_resolver=None):
    first = records[0]['binding']
    header = {k:first[k] for k in ('snapshot_id','path','source_sha256')}
    header.update(view_schema='original-evidence-draft-1',question=question)
    query=[w for w in re.findall('[a-z0-9]+',question.casefold()) if len(w)>1 and w not in STOP]
    packet={'header':header,'items':[]}
    available={}
    for r in records:
        b=r['binding']
        raw=(original_record(source,expected_source_sha256=b['source_sha256'],record_offset=b['record_offset'],record_length=b['record_length'])
             if record_resolver is None else record_resolver(b))
        assert sha(raw)==b['record_sha256']
        obj=json.loads(raw)
        if method=='whole_record':
            item={'id':r['id'],'binding':b,'record_hex':raw.hex()};indices=list(range(len(obj['abstract'])))
        else:
            if method=='first_two':indices=list(range(min(2,len(obj['abstract']))))
            else:
                scores=[]
                for i,sentence in enumerate(obj['abstract']):
                    words=[w for w in re.findall('[a-z0-9]+',sentence.casefold()) if len(w)>1 and w not in STOP]
                    score=sum(min(query.count(w),words.count(w)) for w in set(query))
                    scores.append((score,i))
                indices=sorted(i for _,i in sorted(scores,key=lambda x:(-x[0],x[1]))[:2])
            spans=reference_tokens(raw,field='abstract');chosen=[spans[i] for i in indices]
            item={'id':r['id'],'witness':{'schema':'experimental-source-span-1','binding':b,'sentences':chosen,'application_record_return_B':len(raw)},
                  'original_token_hex':[raw[s['offset']:s['offset']+s['length']].hex() for s in chosen]}
        trial={'header':header,'items':packet['items']+[item]}
        if len(encode(trial))<=cap:
            packet=trial;available[r['id']]=indices
    assert encoded==encode(packet) and len(encoded)<=cap
    return available
