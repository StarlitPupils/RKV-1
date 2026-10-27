"""Independent source-relevance association structure and scoring audit."""
from collections import Counter,defaultdict
from fractions import Fraction
import math
from rkv1.core import digest
from scripts.evidence_retrieval import encoded,tokens

PARAMETERS={'document_terms':16,'mapping_terms':8,'query_terms':8,'alpha':.25,'question_grouping':'normalized-question-SHA union original gold IDs; one vote per group'}

def validate(base,model):
    if type(model) is not dict or model.get('schema')!='training-only-lexical-association-v1' or model.get('base_model_sha256')!=digest(encoded(base)) or model.get('parameters')!=PARAMETERS:raise ValueError('Sidecar schema/base identity/frozen parameters differ')
    mapping=model.get('expansion');control=model.get('permuted_expansion');permutation=model.get('control_key_permutation')
    if type(mapping) is not dict or type(control) is not dict or type(permutation) is not dict or set(mapping)!=set(control) or set(permutation)!=set(mapping) or set(permutation.values())!=set(mapping):raise ValueError('Incomplete control permutation')
    for query,edges in mapping.items():
        if type(query) is not str or tokens(query)!=[query] or type(edges) is not list or not 1<=len(edges)<=8:raise ValueError('Invalid query mapping shape')
        seen=set();denominators=set()
        for edge in edges:
            if type(edge) is not list or len(edge)!=3:raise ValueError('Invalid association edge')
            target,support,denominator=edge
            if type(target) is not str or target not in base['shared']['postings'] or target==query or target in seen or type(support) is not int or type(denominator) is not int or not 1<=support<=denominator:raise ValueError('Invalid target/vote/denominator')
            seen.add(target);denominators.add(denominator)
        if len(denominators)!=1 or edges!=sorted(edges,key=lambda row:(-row[1],row[0])):raise ValueError('Inconsistent query denominator/order')
        if control[query]!=mapping[permutation[query]]:raise ValueError('Control changed association values')
        if len(mapping)>=2 and permutation[query]==query:raise ValueError('Control fixed point')
    if len(encoded(mapping))!=len(encoded(control)):raise ValueError('Unequal control serialized bytes')
    return {'control_available':len(mapping)>=2,'query_terms':len(mapping),'edges':sum(len(v) for v in mapping.values())}

def reference_ranking(base,model,question,method):
    if type(question) is not str or method not in ('lexical','expansion','permuted_expansion'):raise ValueError('Question-only/frozen method required')
    original=Counter(tokens(question));terms=[(term,frequency,False) for term,frequency in sorted(original.items())]
    if method!='lexical':
        votes=defaultdict(Fraction)
        for query,frequency in sorted(original.items()):
            for target,support,denominator in model[method].get(query,[]):
                if target not in original:votes[target]+=Fraction(frequency*support,denominator)
        selected=sorted(votes,key=lambda term:(-votes[term],term))[:8];total=sum(votes[t] for t in selected)
        if total:terms.extend((term,.25*float(votes[term]/total),True) for term in sorted(selected))
    shared=base['shared'];scores=defaultdict(float)
    for term,weight,extra in terms:
        posting=shared['postings'].get(term,{})
        if not posting:continue
        idf=math.log(1+(shared['N']-len(posting)+.5)/(len(posting)+.5))
        for document,frequency in sorted(posting.items()):
            denominator=frequency+1.2*(.25+.75*shared['doc_lengths'][document]/shared['avgdl'])
            score=idf*frequency*2.2/denominator
            scores[document]+=weight*score if extra else weight*idf*frequency*2.2/denominator
    return sorted(scores,key=lambda document:(-scores[document],document))
