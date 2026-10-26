"""Explicit synthetic-reference evidence paths, not natural-language reasoning.

The byte budget limits admitted source records, not physical CAS I/O: lookup
must first verify a record to discover its size. No implicit HEAD fallback.
"""
import re
from .core import digest,valid_hash

NEXT=re.compile(r'RKVNEXT (doc:[0-9]+)')
VALUE=re.compile(r'RKVVALUE ([^\r\n]{1,512})')


def trace(memory,key,*,snapshot,max_hops=3,max_evidence_bytes=4096):
    if (not isinstance(snapshot,str) or not valid_hash(snapshot)
            or not isinstance(key,str) or not re.fullmatch(r'doc:[0-9]+',key)
            or type(max_hops) is not int or not 1<=max_hops<=16
            or type(max_evidence_bytes) is not int or not 1<=max_evidence_bytes<=1<<20):
        raise ValueError('Invalid explicit evidence-path request')
    result={'snapshot_id':snapshot,'root_key':key,'status':None,'value':None,'evidence':[],
            'lookup_calls':0,'verified_record_bytes':0,'admitted_record_bytes':0,
            'physical_read_or_decompressed_bytes':None,'primary_evidence':False,
            'scope':'Synthetic explicit references, known root and specified snapshot; not model reasoning'}
    seen=set()
    def finish(status):result['status']=status;return result
    while len(result['evidence'])<max_hops:
        if key in seen:return finish('cycle')
        seen.add(key);looked=memory.lookup(key,snapshot=snapshot);result['lookup_calls']+=1
        if looked['snapshot_id']!=snapshot:raise ValueError('Evidence path snapshot mismatch')
        if not looked['hits']:return finish('missing')
        if len(looked['hits'])!=1:raise ValueError('Evidence key is not unique')
        hit=looked['hits'][0];loc=hit['locator']
        if hit['key']!=key or loc['snapshot_id']!=snapshot or not hit['source_bytes_verified']:
            raise ValueError('Evidence path binding mismatch')
        size=loc['length'];result['verified_record_bytes']+=size
        if result['admitted_record_bytes']+size>max_evidence_bytes:return finish('budget')
        directives=[]
        for index,sentence in enumerate(hit['sentences']):
            next_match=NEXT.fullmatch(sentence);value_match=VALUE.fullmatch(sentence)
            if next_match or value_match:
                directives.append((index,sentence,'next' if next_match else 'value',
                                   (next_match or value_match).group(1)))
        if len(directives)!=1:return finish('invalid-reference')
        index,quote,kind,target=directives[0]
        result['evidence'].append({'key':key,'locator':dict(loc),'sentence_index':index,'quote':quote,
                                   'quote_utf8_sha256':digest(quote.encode('utf-8')),'directive':kind})
        result['admitted_record_bytes']+=size
        if kind=='value':result['value']=target;return finish('complete')
        key=target
    return finish('hop-limit')
