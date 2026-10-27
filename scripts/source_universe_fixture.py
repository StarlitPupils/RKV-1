"""Owned source coverage fixture and fixed36case plan, no logical query."""
from scripts.logic_fixture import fact,rule,literal,encode
def sources(updated=False):
 result={'one.logic.jsonl':encode([fact('a','activate','alpha','beta')]),'two.logic.jsonl':encode([rule('r',literal('influence','?x','?y'),literal('activate','?x','?y'))]),'notes.txt':b'Noneligible natural-language file; no assertion of knowledge completeness.\n'}
 if updated:result['late.logic.jsonl']=encode([fact('late','activate','alpha','beta',False)])
 return result
def plan():
 rows=[]
 for stage,updated in (('initial',False),('updated',True),('historical',False)):
  data=sources(updated);paths=sorted(p for p in data if p.endswith('.logic.jsonl'));total=sum(len(data[p]) for p in paths)
  for path_role in ('full','omit_last','reverse_full'):
   selected=paths if path_role=='full' else paths[:-1] if path_role=='omit_last' else list(reversed(paths))
   for budget_role,budget in (('zero',0),('minus_one',total-1),('exact',total),('plus_one',total+1)):
    rows.append({'id':stage+'-'+path_role+'-'+budget_role,'stage':stage,'paths':selected,'source_byte_budget':budget,'expected_complete':path_role!='omit_last' and budget_role in ('exact','plus_one'),'payload_total_bytes':total})
 return rows
