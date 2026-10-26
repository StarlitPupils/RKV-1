"""Admission and graph exposure diagnostic; never a new retrieval evaluation."""
from collections import Counter

CATEGORIES=('recovered','no_candidate','byte_rejected','count_stop')

def admission_trace(locators,ranked,gold,*,max_facts=12,budget=4096):
    if type(max_facts) is not int or max_facts<1 or type(budget) is not int or budget<0:raise ValueError('Invalid diagnostic limit')
    ordered=list(dict.fromkeys(ranked));gold=set(gold)
    if not set(ordered)|gold<=set(locators):raise ValueError('Unknown original source identity')
    selected=[];used=0;status={}
    for key in ordered:
        length=locators[key]['length']
        if type(length) is not int or length<1:raise ValueError('Invalid original source length')
        if len(selected)==max_facts:status[key]='count_stop'
        elif used+length>budget:status[key]='byte_rejected'
        else:status[key]='recovered';selected.append(key);used+=length
    categories={k:status.get(k,'no_candidate') for k in sorted(gold)}
    counts=Counter({k:0 for k in CATEGORIES});counts.update(categories.values())
    assert sum(counts.values())==len(gold)
    return {'selected_ids':selected,'admitted_bytes':used,'gold_categories':categories,'counts':dict(counts)}

def graph_exposure(model,lexical_order,method):
    if method not in ('lexical','graph','permuted_graph'):raise ValueError('Unknown diagnostic method')
    seeds=lexical_order[:6];graph={} if method=='lexical' else model[method]
    neighbors=set().union(*(set(graph.get(k,{})) for k in seeds)) if seeds else set()
    return {'active_seed_count':sum(bool(graph.get(k)) for k in seeds),
        'neighbor_union_count':len(neighbors),'novel_nonlexical_neighbor_count':len(neighbors-set(lexical_order))}
