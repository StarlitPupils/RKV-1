"""Training-only sparse lexical associations; source relevance, not entailment."""
from collections import Counter,defaultdict
import math
from fractions import Fraction
from rkv1.core import digest
from scripts.evidence_retrieval import tokens,question_identity,lexical,encoded
DOCUMENT_TERMS=16
MAPPING_TERMS=8
QUERY_TERMS=8
ALPHA=.25

def learn(base,rows,*,base_sha256):
    if digest(encoded(base))!=base_sha256:raise ValueError('Original frozen base index SHA differs')
    shared=base['shared'];groups={};annotated_rows=0
    for row in rows:
        if type(row['question']) is not str or type(row['gold_ids']) is not list or any(type(k) is not str or k not in shared['locators'] for k in row['gold_ids']):raise ValueError('Invalid training question/gold source identity')
        q=question_identity(row['question']);group=groups.setdefault(q,{'question':row['question'],'gold_ids':set()});group['gold_ids'].update(row['gold_ids']);annotated_rows+=bool(row['gold_ids'])
    active={q:g for q,g in groups.items() if g['gold_ids']};wanted=set().union(*(g['gold_ids'] for g in active.values())) if active else set();per_doc=defaultdict(list)
    for token,posting in sorted(shared['postings'].items()):
        idf=math.log(1+(shared['N']-len(posting)+.5)/(len(posting)+.5))
        for key,tf in sorted(posting.items()):
            if key in wanted:
                score=idf*tf*2.2/(tf+1.2*(.25+.75*shared['doc_lengths'][key]/shared['avgdl']));per_doc[key].append((score,token))
    retained={key:[term for _,term in sorted(per_doc[key],key=lambda item:(-item[0],item[1]))[:DOCUMENT_TERMS]] for key in sorted(wanted)}
    df=Counter();pairs=defaultdict(Counter)
    for q,group in sorted(active.items()):
        query=set(tokens(group['question']));targets=set().union(*(set(retained[key]) for key in group['gold_ids']))
        df.update(query)
        for term in sorted(query):pairs[term].update(targets-{term})
    mapping={q:[[t,n,df[q]] for t,n in sorted(counts.items(),key=lambda item:(-item[1],item[0]))[:MAPPING_TERMS]] for q,counts in sorted(pairs.items()) if counts}
    keys=sorted(mapping,key=lambda q:(digest(('rkv061control:'+q).encode()),q));permutation=dict(zip(keys,keys[1:]+keys[:1]));control={q:[list(row) for row in mapping[permutation[q]]] for q in sorted(mapping)}
    model={'schema':'training-only-lexical-association-v1','base_model_sha256':base_sha256,'parameters':{'document_terms':DOCUMENT_TERMS,'mapping_terms':MAPPING_TERMS,'query_terms':QUERY_TERMS,'alpha':ALPHA,'question_grouping':'normalized-question-SHA union original gold IDs; one vote per group'},'expansion':mapping,'permuted_expansion':control,'control_key_permutation':permutation}
    costs={'input_training_rows':len(rows),'annotated_training_rows':annotated_rows,'unique_training_questions':len(groups),'annotated_unique_questions':len(active),'gold_training_documents':len(wanted),'learned_query_terms':len(mapping),'retained_target_edges':sum(len(v) for v in mapping.values()),'control_available':len(keys)>=2,'control_fixed_points':sum(q==v for q,v in permutation.items()),'component_bytes':{k:len(encoded(v)) for k,v in model.items()},'component_sha256':{k:digest(encoded(v)) for k,v in model.items()},'new_remote_model_calls':0}
    return model,costs

def query_expansion(sidecar,question,method):
    if type(question) is not str:raise ValueError('Only original question string permitted')
    if method not in ('expansion','permuted_expansion'):raise ValueError('Unknown expansion method')
    original=Counter(tokens(question));scores=defaultdict(Fraction)
    for query,qf in sorted(original.items()):
        for target,support,denominator in sidecar[method].get(query,[]):
            if target not in original:scores[target]+=Fraction(qf*support,denominator)
    selected=sorted(scores,key=lambda target:(-scores[target],target))[:QUERY_TERMS];total=sum(scores[t] for t in selected)
    return {t:ALPHA*float(scores[t]/total) for t in selected} if total else {}

def ranking(base,sidecar,question,method):
    ordered,scores=lexical(base['shared'],question)
    if method=='lexical':return ordered
    weights=query_expansion(sidecar,question,method)
    for token,weight in sorted(weights.items()):
        _,extra=lexical(base['shared'],token)
        for key,score in extra.items():scores[key]=scores.get(key,0)+weight*score
    return sorted(scores,key=lambda key:(-scores[key],key))
