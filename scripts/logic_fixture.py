"""Owned exact symbolic cases; not extracted from scientific natural language."""
import json

def literal(predicate,left,right,positive=True):return {'predicate':predicate,'arguments':[left,right],'positive':positive}
def fact(identifier,predicate,left,right,positive=True):return {'id':identifier,'kind':'fact','atom':literal(predicate,left,right,positive)}
def rule(identifier,head,*premises):return {'id':identifier,'kind':'rule','head':head,'premises':list(premises)}
def fixture():
    records=[];queries=[];pairs=[]
    for i,predicate in enumerate(('activate','inhibit','increase','reduce','precede','follow','bind','block')):
        left='a'+str(i);right='b'+str(i);records.extend([fact('f_forward_'+str(i),predicate,left,right),fact('f_reverse_'+str(i),predicate,right,left,False)])
        queries.extend([{'id':'forward_'+str(i),'query':literal(predicate,left,right),'initial':'supported','updated':'supported'},{'id':'reverse_'+str(i),'query':literal(predicate,right,left),'initial':'refuted','updated':'refuted'}])
        pairs.append({'claims':[left+' units '+predicate+' '+right+' units.',right+' units '+predicate+' '+left+' units.'],'document':left+' units '+predicate+' '+right+' units. '+right+' units do not '+predicate+' '+left+' units.','gold':['SUPPORT','CONTRADICT']})
    records.extend([fact('f_chain_first','activate','c0','c1'),fact('f_chain_second','activate','c1','c2'),fact('f_chain_negative','activate','c2','c1',False),rule('r_twohop',literal('influence','?x','?z'),literal('activate','?x','?y'),literal('activate','?y','?z')),rule('r_connect',literal('connected','?x','?y'),literal('influence','?x','?y')),rule('r_cycle',literal('influence','?x','?y'),literal('connected','?x','?y')),rule('r_negative',literal('trust','?x','?y',False),literal('activate','?x','?y',False)),rule('r_repeat',literal('reflexive','?x','?x'),literal('activate','?x','?x')),rule('r_constant',literal('reachable','c0','?x'),literal('activate','c0','?x')),rule('r_counter',literal('connected','?x','?y',False),literal('influence','?x','?y',False))])
    for identifier,q,initial,updated in [('twohop',literal('influence','c0','c2'),'supported','inconsistent'),('cycle',literal('connected','c0','c2'),'supported','inconsistent'),('negative_premise',literal('trust','c2','c1'),'refuted','refuted'),('reverse_unknown',literal('activate','c2','c0'),'unknown','unknown'),('no_default_negative',literal('trust','c0','c2'),'unknown','unknown'),('no_explosion',literal('unrelated','c0','c1'),'unknown','unknown'),('repeated_variable',literal('reflexive','c0','c0'),'unknown','unknown'),('constant',literal('reachable','c0','c1'),'supported','supported')]:queries.append({'id':identifier,'query':q,'initial':initial,'updated':updated})
    return {'initial':records,'updated':records+[fact('f_late_counter','influence','c0','c2',False)],'queries':queries,'collision_pairs':pairs}
def encode(records):return b''.join(json.dumps(r,sort_keys=True,separators=(',',':')).encode()+b'\n' for r in records)
