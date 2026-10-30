"""Source-rebuilt lexical BM25 reference; imports no candidate ranker/model."""
import json,math,re
from rkv1.memory import STOP


def rank_original(source,question):
    def tokenize(text):return [w for w in re.findall('[a-z0-9]+',text.casefold()) if len(w)>1 and w not in STOP]
    counts={}
    for line in source.splitlines():
        obj=json.loads(line);key='doc:'+str(obj['doc_id'])
        if key in counts:raise ValueError('Duplicate original document')
        words=tokenize('\n'.join([obj['title'],*obj['abstract']]))
        counts[key]={t:words.count(t) for t in set(words)}
    n=len(counts);lengths={k:sum(x.values()) for k,x in counts.items()};average=sum(lengths.values())/n
    query=tokenize(question);scores={}
    for token in sorted(set(query)):
        matching=[k for k in sorted(counts) if token in counts[k]]
        if not matching:continue
        inverse=math.log(1+(n-len(matching)+.5)/(len(matching)+.5))
        for key in matching:
            tf=counts[key][token]
            value=query.count(token)*inverse*tf*2.2/(tf+1.2*(1-.75+.75*lengths[key]/average))
            scores[key]=scores.get(key,0)+value
    return sorted(scores,key=lambda key:(-scores[key],key))[:12]
