"""Exact candidate-policy arithmetic. No data loading,execution,statistics or QA inference."""
from fractions import Fraction
def six(values,*,positive=False):
    if type(values) is not list or len(values)!=6 or any(type(v) is not int or v<0 or (positive and v==0) for v in values):return None
    return sorted(values)
def median(values):
    values=six(values)
    return None if values is None else Fraction(values[2]+values[3],2)
def space(candidate_B,baseline_B):
    if type(candidate_B) is not int or type(baseline_B) is not int or candidate_B<0 or baseline_B<=0:return 'unknown'
    saved=baseline_B-candidate_B
    return 'pass' if 10*saved>=baseline_B and saved>=65536 else 'fail'
def wall(candidate_ns,baseline_ns):
    candidate,baseline=median(candidate_ns),median(baseline_ns)
    if candidate is None or baseline is None:return 'unknown'
    return 'fail' if 2*candidate>3*baseline and candidate-baseline>20000000 else 'pass'
def rss(candidate_B,baseline_B):
    candidate,baseline=six(candidate_B,positive=True),six(baseline_B,positive=True)
    if candidate is None or baseline is None:return 'unknown'
    candidate,baseline=max(candidate),max(baseline)
    return 'fail' if 4*candidate>5*baseline and candidate-baseline>16<<20 else 'pass'
def joint(decisions):
    if not decisions or any(value not in ('pass','fail','unknown') for value in decisions) or 'unknown' in decisions:return 'insufficient_evidence'
    return 'candidate_for_limited_source_mode_adoption' if all(value=='pass' for value in decisions) else 'does_not_meet_frozen_targets'
