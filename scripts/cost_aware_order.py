"""Private single parameter-free score-per-original-byte candidate; not semantic reasoning."""
import math
from fractions import Fraction
METHODS=('lexical','score_per_byte','length_only')
def order(locators,lexical_ids,scores,method):
 if method not in METHODS:raise ValueError('Unknown frozen method')
 ids=list(lexical_ids)
 if len(ids)!=len(set(ids)) or set(ids)!=set(scores) or not set(ids)<=set(locators):raise ValueError('Frozen candidate universe required')
 if any(type(locators[k].get('length')) is not int or locators[k]['length']<1 or type(scores[k]) not in (int,float) or not math.isfinite(scores[k]) or scores[k]<=0 for k in ids):raise ValueError('Positive finite score and original record byte cost required')
 if method=='lexical':return ids
 if method=='length_only':return sorted(ids,key=lambda k:(locators[k]['length'],k))
 # Fraction is exact for the already-computed float score; no tolerance or tuned threshold.
 return sorted(ids,key=lambda k:(-Fraction(scores[k])/locators[k]['length'],k))
