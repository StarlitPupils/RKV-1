"""Reference-rate cost bands and small-sample descriptive intervals, never account invoices."""
import math

def wilson(correct,total):
 if type(correct) is not int or type(total) is not int or not 0<=correct<=total or total<=0:raise ValueError('Positive fixed denominator required')
 z=1.959963984540054;p=correct/total;d=1+z*z/total;center=(p+z*z/(2*total))/d;half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
 return {'point':p,'low':max(0,center-half),'high':min(1,center+half),'method':'Wilson95_descriptive_known_sample_not_independent_generalization'}
def cost_band(usage,book):
 if type(usage) is not dict:return None
 keys=('prompt_cache_hit_tokens','prompt_cache_miss_tokens','completion_tokens','prompt_tokens')
 if any(type(usage.get(k)) is not int or usage[k]<0 for k in keys):return None
 if usage['prompt_cache_hit_tokens']+usage['prompt_cache_miss_tokens']!=usage['prompt_tokens']:return None
 rates=book['official_reference_rates'];scale=book['unit_tokens']
 return {bound:sum(usage[k]*rates[category][bound]/scale for k,category in (('prompt_cache_hit_tokens','input_cache_hit'),('prompt_cache_miss_tokens','input_cache_miss'),('completion_tokens','output'))) for bound in ('low','high')}
