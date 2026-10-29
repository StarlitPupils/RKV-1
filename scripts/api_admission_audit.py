"""Private explanatory audit: independent lexical and fixed whole-record admission reference."""
import math,re
from collections import Counter,defaultdict
from rkv1.memory import STOP

def independent_order(shared,question):
 if type(question) is not str or shared['parameters']['k1']!=1.2 or shared['parameters']['b']!=.75:raise ValueError('Frozen question/BM25 required')
 words=[w for w in re.findall('[a-z0-9]+',question.casefold()) if len(w)>1 and w not in STOP];scores=defaultdict(float);N=shared['N'];avg=shared['avgdl']
 for term,n in sorted(Counter(words).items()):
  posting=shared['postings'].get(term,{})
  if not posting:continue
  weight=math.log(1+(N-len(posting)+.5)/(len(posting)+.5))
  for key,tf in sorted(posting.items()):scores[key]+=n*weight*tf*2.2/(tf+1.2*(.25+.75*shared['doc_lengths'][key]/avg))
 return sorted(scores,key=lambda key:(-scores[key],key)),dict(scores)

def trace(locators,ranked,gold):
 ranked=list(dict.fromkeys(ranked));gold=set(gold)
 if not (set(ranked)|gold)<=set(locators):raise ValueError('Unknown source identity')
 if any(type(v.get('length')) is not int or v['length']<1 for v in locators.values()):raise ValueError('Invalid original record length')
 selected=[];used=0;events={};positions={k:i+1 for i,k in enumerate(ranked)}
 for key in ranked:
  n=locators[key]['length'];before=used
  if len(selected)>=12:category='count_stop'
  elif used+n>4096:category='byte_rejected'
  else:category='recovered';selected.append(key);used+=n
  if key in gold:events[key]={'category':category,'rank':positions[key],'original_record_B':n,'selected_count_before':len(selected)-(category=='recovered'),'used_B_before':before,'remaining_B_before':4096-before,'self_exceeds_entire_budget':n>4096}
 for key in gold-set(events):events[key]={'category':'no_candidate','rank':None,'original_record_B':locators[key]['length'],'selected_count_before':None,'used_B_before':None,'remaining_B_before':None,'self_exceeds_entire_budget':locators[key]['length']>4096}
 assert len(events)==len(gold) and used<=4096 and len(selected)<=12
 return {'selected_ids':selected,'admitted_B':used,'gold_events':events}
