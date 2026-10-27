"""Owned selection cases; expected witness flags are explicit, never engine-derived."""
from scripts.source_set_fixture import sources as basis
from scripts.logic_fixture import literal,fact,encode

def sources(updated=False):
 result=basis()
 for i in range(7):result['filler'+str(i)+'.logic.jsonl']=encode([fact('same','dummy','a','b')])
 if updated:result['late.logic.jsonl']=encode([fact('same','reach','a','c',False)])
 return result

def cases(stage):
 rows=[]
 for mode,paths,query in (
  ('basis',['one.logic.jsonl','two.logic.jsonl'],literal('reach','a','c')),
  ('facts',['one.logic.jsonl'],literal('edge','a','b')),
  ('rules',['two.logic.jsonl'],literal('reach','a','c')),
  ('negative',['one.logic.jsonl','two.logic.jsonl'],literal('reach','c','b'))):
  for work in (0,100000):
   rows.append({'id':stage+'-'+mode+'-'+str(work),'paths':paths,'query':query,'work_budget':work,'support':mode=='facts' or mode=='basis' and work>0,'opposite':mode=='negative' and work>0})
 if stage=='updated':
  for work in (0,100000):rows.append({'id':stage+'-expanded-'+str(work),'paths':['one.logic.jsonl','two.logic.jsonl','late.logic.jsonl'],'query':literal('reach','a','c'),'work_budget':work,'support':work>0,'opposite':True})
 return rows
