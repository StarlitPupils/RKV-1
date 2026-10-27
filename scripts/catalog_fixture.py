"""Experimental candidate fixture: growing eligible catalogue, fixed selected evidence."""
from scripts.source_set_fixture import sources as core
from scripts.logic_fixture import fact,encode,literal
COUNTS=(9,64,512,4096)
ORDERS=(COUNTS,(64,9,4096,512),(512,4096,9,64))
PATHS=['one.logic.jsonl','two.logic.jsonl']
def sources(count):
 if type(count) is not int or not 9<=count<=4096:raise ValueError('Owned scale bound9..4096')
 result=core(True)
 for i in range(count-3):result['filler'+str(i).zfill(4)+'.logic.jsonl']=encode([fact('same','dummy','a','b')])
 assert sum(p.endswith('.logic.jsonl') for p in result)==count
 return result
def queries():
 return [(literal('reach','a','c'),True,False),(literal('reach','c','b'),False,True),(literal('edge','a','b'),True,False),(literal('edge','c','a'),False,False)]*2
