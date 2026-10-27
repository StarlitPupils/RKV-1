"""Fixed owned finite signed programs and truth-preserving syntactic transforms."""
import copy,random
from scripts.logic_fixture import literal,fact,rule,encode
PREDICATES=('edge','reach','flag');CONSTANTS=('c0','c1','c2');SEED=2026102700;PROGRAMS=12;VARIANTS=('base','rename','record_order','polarity_flip')
def programs():
 result=[]
 for i in range(PROGRAMS):
  rng=random.Random(SEED+i);facts=[fact('f0','edge','c0','c1'),fact('f1','edge','c1','c2'),fact('f2','edge','c2','c0'),fact('f3','edge','c1','c0',False)];used={(v['atom']['predicate'],tuple(v['atom']['arguments']),v['atom']['positive']) for v in facts};remaining=[(p,a,b,sign) for p in PREDICATES for a in CONSTANTS for b in CONSTANTS for sign in (False,True) if (p,(a,b),sign) not in used]
  for j,(p,a,b,sign) in enumerate(rng.sample(remaining,4),4):facts.append(fact('f'+str(j),p,a,b,sign))
  rules=[rule('r0',literal('reach','?x','?y'),literal('edge','?x','?y')),rule('r1',literal('reach','?x','?z'),literal('reach','?x','?y'),literal('edge','?y','?z')),rule('r2',literal('flag','?x','?y',False),literal('edge','?x','?y',False)),rule('r3',literal('flag','?x','?z',False),literal('flag','?x','?y',False),literal('edge','?y','?z')),rule('r4',literal('flag','?x','?x'),literal('reach','?x','?x')),rule('r5',literal('flag','c0','?x'),literal('edge','c0','?x')),rule('r6',literal('reach','?x','?y'),literal('flag','?x','?y'))]
  result.append(facts+rules)
 return result
def transform_atom(value,variant):
 v=copy.deepcopy(value)
 if variant=='rename':
  v['predicate']=dict(zip(PREDICATES,('p2','p0','p1')))[v['predicate']];mapping=dict(zip(CONSTANTS,('d2','d0','d1')));v['arguments']=[mapping.get(x,x) for x in v['arguments']]
 elif variant=='polarity_flip':v['positive']=not v['positive']
 elif variant not in ('base','record_order'):raise ValueError('Unsupported frozen transformation')
 return v
def transformed(records,variant,index):
 result=copy.deepcopy(records)
 for row in result:
  if row['kind']=='fact':row['atom']=transform_atom(row['atom'],variant)
  else:row['head']=transform_atom(row['head'],variant);row['premises']=[transform_atom(p,variant) for p in row['premises']]
 if variant=='record_order':random.Random(SEED+1000+index).shuffle(result)
 return result
def queries():return [literal(p,a,b) for p in PREDICATES for a in CONSTANTS for b in CONSTANTS]
