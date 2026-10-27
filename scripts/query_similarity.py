"""Known split exact token-set Jaccard audit; not a semantic leakage detector."""
from fractions import Fraction
from scripts.evidence_retrieval import tokens,question_identity

def best_training_match(question,training):
    if type(question) is not str:raise ValueError('Original question required')
    query=set(tokens(question));best=Fraction(0);identities=[];best_intersection=0;best_union=0
    for other in training:
        if type(other) is not str:raise ValueError('Training questions must be strings')
        candidate=set(tokens(other));intersection=len(query&candidate);union=len(query|candidate);score=Fraction(intersection,union) if union else Fraction(0)
        identity=question_identity(other)
        if score>best:best=score;identities=[identity];best_intersection=intersection;best_union=union
        elif score==best and score>0:identities.append(identity)
    return {'max_jaccard_numerator':best.numerator,'max_jaccard_denominator':best.denominator,'best_train_question_sha256':sorted(set(identities)),'is_exact_normalized_question':any(question_identity(question)==question_identity(q) for q in training),'near_at_least_four_fifths':best>=Fraction(4,5),'query_token_types':len(query)}

def classify(base,candidate,near):
    if type(base) is not dict or type(candidate) is not dict or set(base)!=set(candidate) or set(base)!=set(near):raise ValueError('Full identical claim denominator required')
    rows=[]
    for key in sorted(base):
        b=base[key];c=candidate[key]
        if type(b) is not Fraction or type(c) is not Fraction or not 0<=b<=1 or not 0<=c<=1 or type(near[key]) is not bool:raise ValueError('Exact bounded recall and boolean overlap required')
        rows.append({'identity':key,'near':near[key],'direction':'win' if c>b else 'loss' if c<b else 'tie','delta_numerator':(c-b).numerator,'delta_denominator':(c-b).denominator,'base_complete':b==1,'candidate_complete':c==1})
    return rows
