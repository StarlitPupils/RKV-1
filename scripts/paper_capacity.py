"""Gold-aware whole-record capacity bound; never a deployable retriever."""
from scripts.retrieval_gap import oracle

def capacity(locators,gold,*,budget=4096,limit=12):
    if type(budget) is not int or not 0<=budget<=4096 or type(limit) is not int or not 1<=limit<=12:raise ValueError('Invalid fixed whole-paper limit')
    gold=set(gold)
    if not gold<=set(locators):raise ValueError('Unknown original gold source')
    if any(type(locators[k]['length']) is not int or locators[k]['length']<1 for k in gold):raise ValueError('Invalid original source length')
    chosen=oracle(locators,gold,max_facts=limit,max_source_bytes=budget)
    dp=[-1]*(budget+1);dp[0]=0
    for key in sorted(gold):
        size=locators[key]['length']
        for b in range(budget,size-1,-1):
            previous=dp[b-size]
            if 0<=previous<limit:dp[b]=max(dp[b],previous+1)
    best=max(dp);assert best==chosen['recovered_groups']
    full_bytes=sum(locators[k]['length'] for k in gold)
    possible=bool(gold) and len(gold)<=limit and full_bytes<=budget
    if gold:assert possible==(best==len(gold))
    return {'gold_groups':len(gold),'gold_total_original_bytes':full_bytes,'gold_single_record_over_budget':sum(locators[k]['length']>budget for k in gold),
        'gold_aware_max_recovered':best,'gold_aware_minimal_selected_bytes':chosen['selected_bytes'],
        'gold_aware_recall_ceiling':best/len(gold) if gold else None,'gold_complete_possible':possible if gold else None,'greedy_DP_equal':True,
        'scope':'Gold-aware original-whole-record capacity upper bound only; not a query selector or intervention'}

def support(numerator,denominator):
    if type(numerator) is not int or type(denominator) is not int or not 0<=numerator<=denominator:raise ValueError('Invalid diagnostic denominator')
    return {'numerator':numerator,'denominator':denominator,'fraction':numerator/denominator if denominator else None,
        'at_least_half_supported':bool(denominator) and numerator*2>=denominator}
