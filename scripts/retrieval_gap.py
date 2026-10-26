"""Gold-aware diagnostic bounds only; never an implementable query selector."""
from collections import Counter

CATEGORIES=('recovered','unresolved_source','no_candidate','below_count_prefix','byte_budget_excluded')


def oracle(locators,targets,*,candidates=None,max_facts=12,max_source_bytes=4096):
    if type(max_facts) is not int or max_facts<1 or type(max_source_bytes) is not int or max_source_bytes<0:
        raise ValueError('Invalid diagnostic budget')
    available=set(targets)&set(locators)
    if candidates is not None:available&=set(candidates)
    used=0;picked=[]
    for key in sorted(available,key=lambda k:(locators[k]['length'],k)):
        size=locators[key]['length']
        if type(size) is not int or size<=0:raise ValueError('Invalid original member length')
        if len(picked)==max_facts or used+size>max_source_bytes:break
        used+=size;picked.append(key)
    return {'known_gold_selected_ids':picked,'selected_bytes':used,'recovered_groups':len(picked),
        'gold_groups':len(set(targets)),'complete_possible':len(picked)==len(set(targets)),
        'recall_ceiling':len(picked)/len(set(targets)) if targets else 0.0,
        'scope':'Gold-aware shortest-record unit-value upper bound; not a deployable retrieval method'}


def partition(locators,ranked,selected,targets,*,max_facts=12):
    ranked=list(dict.fromkeys(ranked));selected=set(selected);targets=set(targets)
    if not selected<=set(ranked) or not selected<=set(locators) or len(selected)>max_facts:raise ValueError('Selected list outside candidate/count contract')
    prefix=set(ranked[:max_facts]);categories={};counts=Counter({name:0 for name in CATEGORIES})
    for key in sorted(targets):
        if key in selected:category='recovered'
        elif key not in locators:category='unresolved_source'
        elif key not in ranked:category='no_candidate'
        elif key not in prefix:category='below_count_prefix'
        else:category='byte_budget_excluded'
        categories[key]=category;counts[category]+=1
    assert sum(counts.values())==len(targets)
    return {'categories_by_group':categories,'counts':dict(counts),'gold_groups':len(targets),
        'scope':'Mutually exclusive positions of frozen candidates; labels do not prove a causal intervention gain'}
