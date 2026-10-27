"""Owned cross-file axioms with repeated local IDs and late counterevidence."""
from scripts.logic_fixture import literal,fact,rule,encode
def sources(updated=False):
 result={'one.logic.jsonl':encode([fact('same','edge','a','b'),fact('second','edge','b','c'),fact('negative','edge','c','b',False)]),'two.logic.jsonl':encode([rule('same',literal('reach','?x','?y'),literal('edge','?x','?y')),rule('chain',literal('reach','?x','?z'),literal('reach','?x','?y'),literal('edge','?y','?z')),rule('negative',literal('reach','?x','?y',False),literal('edge','?x','?y',False)),rule('cycle',literal('edge','?x','?y'),literal('reach','?x','?y'))]),'notes.txt':b'Owned noneligible prose; no scientific completeness claim.\n'}
 if updated:result['late.logic.jsonl']=encode([fact('same','reach','a','c',False)])
 return result
def queries():
 return [('edge_forward',literal('edge','a','b'),'supported','supported'),('cross_file_two_hop',literal('reach','a','c'),'supported','inconsistent'),('explicit_negative',literal('reach','c','b'),'refuted','refuted'),('reverse_unknown',literal('edge','c','a'),'unknown','unknown'),('no_explosion',literal('unrelated','a','c'),'unknown','unknown'),('negative_query',literal('reach','a','c',False),'refuted','inconsistent')]
def plan():
 rows=[]
 for stage,updated in (('initial',False),('updated',True),('historical',False)):
  data=sources(updated);paths=sorted(n for n in data if n.endswith('.logic.jsonl'));size=sum(len(data[n]) for n in paths)
  for path_mode in ('full','reverse_full','omit_last'):
   selected=paths if path_mode=='full' else list(reversed(paths)) if path_mode=='reverse_full' else paths[:-1]
   for budget_mode,budget in (('minus_one',size-1),('exact',size)):
    for work in (0,100000):
     for qi,(identifier,query,initial,updated_value) in enumerate(queries()):
      ready=path_mode!='omit_last' and budget_mode=='exact';verdict='incomplete_source_set' if not ready else 'incomplete' if work==0 else updated_value if stage=='updated' else initial;rows.append({'id':stage+'-'+path_mode+'-'+budget_mode+'-'+str(work)+'-'+str(qi),'stage':stage,'paths':selected,'source_byte_budget':budget,'work_budget':work,'query_id':identifier,'query':query,'expected_verdict':verdict,'expected_complete':ready and work>0})
 return rows
