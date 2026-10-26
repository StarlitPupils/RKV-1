"""Text-free assessment plans and independent original SciFact hit auditor."""
import json
import os
import random
from rkv1.core import digest

SOURCE_SHA='b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62'
SOURCE_BYTES=8307875


def exclusive(path,raw):
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())


def ledger(folder):
    return {p.relative_to(folder).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
            for p in sorted(folder.rglob('*')) if p.is_file()}


def catalog(raw):
    result={};offset=0
    for line in raw.splitlines(keepends=True):
        obj=json.loads(line);key='doc:'+str(obj['doc_id'])
        if key in result:raise ValueError('Duplicate source key')
        if not isinstance(obj['title'],str) or not isinstance(obj['abstract'],list) or not all(isinstance(s,str) for s in obj['abstract']):
            raise ValueError('Invalid source record')
        result[key]={'offset':offset,'length':len(line),'sha256':digest(line),'object':obj}
        offset+=len(line)
    return result


def bundles(index,workload,round_number,count=32):
    if workload not in ('spread','repeated'):raise ValueError('Unknown workload')
    ordered=sorted(index,key=lambda k:(digest(('rkv046:'+k).encode('ascii')),k))
    if len(ordered)<4*count:raise ValueError('Insufficient distinct source records')
    result=[{'case_id':f'{workload}-{i:02d}',
             'keys':ordered[3*i:3*i+3] if workload=='spread' else [ordered[3*count+i]]*3}
            for i in range(count)]
    random.Random(20261026+round_number).shuffle(result)
    return result


def audit(index,proof,snapshot):
    if proof['snapshot_id']!=snapshot or len(proof['keys'])!=3 or len(proof['hits'])!=3:
        raise ValueError('Bundle identity/count differs')
    for key,group in zip(proof['keys'],proof['hits']):
        rec=index[key];obj=rec['object']
        locator={'snapshot_id':snapshot,'path':'corpus.jsonl','offset':rec['offset'],
                 'length':rec['length'],'sha256':rec['sha256']}
        expected={'citation_id':'D0','key':key,'title':obj['title'],'sentences':obj['abstract'],
                  'rank':None,'source_bytes_verified':True,'locator':locator}
        if group!=[expected]:raise ValueError('Original byte/JSON member binding differs')
    return 3


def canonical(proof):
    return json.dumps(proof,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')


def public_proof(proof):
    return {'snapshot_id':proof['snapshot_id'],'keys':proof['keys'],'proof_sha256':digest(canonical(proof)),
        'hits':[{'key':g[0]['key'],'locator':g[0]['locator'],'hit_sha256':digest(canonical(g))} for g in proof['hits']]}


def assert_text_free(value):
    if isinstance(value,dict):
        if set(value)&{'title','abstract','sentences','quote','body','text','object'}:raise ValueError('Scientific text field in public output')
        for item in value.values():assert_text_free(item)
    elif isinstance(value,list):
        for item in value:assert_text_free(item)
