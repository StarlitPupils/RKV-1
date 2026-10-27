"""Restricted signed binary Horn closure, explicit source and bounded work."""
import json,re
from dataclasses import dataclass
from rkv1.core import digest
from scripts.postings_transform import canonical,parse
MAX_SOURCE=1<<20
MAX_RECORDS=1024
MAX_RULES=64
MAX_WORK=100000
NAME=re.compile(r'[a-z][a-z0-9_]{0,31}\Z')
VARIABLE=re.compile(r'\?[a-z][a-z0-9_]{0,15}\Z')

@dataclass(frozen=True,order=True)
class Atom:
    predicate:str
    arguments:tuple
    positive:bool
    def value(self):return {'predicate':self.predicate,'arguments':list(self.arguments),'positive':self.positive}

def atom(value,*,variables=False):
    if type(value) is not dict or set(value)!={'predicate','arguments','positive'} or type(value['predicate']) is not str or not NAME.fullmatch(value['predicate']) or type(value['positive']) is not bool or type(value['arguments']) is not list or len(value['arguments'])!=2:raise ValueError('Strict signed binary atom required')
    args=value['arguments']
    if any(type(v) is not str or not (NAME.fullmatch(v) or variables and VARIABLE.fullmatch(v)) for v in args):raise ValueError('Unsupported constant or query variable')
    return Atom(value['predicate'],tuple(args),value['positive'])

def variables(value):return {v for v in value.arguments if v.startswith('?')}

def compile_records(raw,snapshot_id,path):
    if type(raw) is not bytes or len(raw)>MAX_SOURCE:raise ValueError('Bounded signed source bytes required')
    records={};offset=0;rules=0
    for line in raw.splitlines(keepends=True):
        if not line.strip():raise ValueError('Blank logic source record')
        obj=parse(line);identifier=obj.get('id') if type(obj) is dict else None
        if type(identifier) is not str or not NAME.fullmatch(identifier) or identifier in records:raise ValueError('Unique bounded source record ID required')
        kind=obj.get('kind');expected={'id','kind','atom'} if kind=='fact' else {'id','kind','head','premises'}
        if kind not in ('fact','rule') or set(obj)!=expected:raise ValueError('Unsupported explicit logic record')
        entry={'kind':kind,'citation':{'snapshot_id':snapshot_id,'path':path,'offset':offset,'length':len(line),'sha256':digest(line)}}
        if kind=='fact':entry['atom']=atom(obj['atom'])
        else:
            if type(obj['premises']) is not list or not 1<=len(obj['premises'])<=3:raise ValueError('One to three explicit signed premises required')
            entry['head']=atom(obj['head'],variables=True);entry['premises']=tuple(atom(v,variables=True) for v in obj['premises']);bound=set().union(*(variables(v) for v in entry['premises']))
            if not variables(entry['head'])<=bound or len(bound)>3:raise ValueError('Range-restricted head and at most3variables required')
            rules+=1
        records[identifier]=entry;offset+=len(line)
        if len(records)>MAX_RECORDS or rules>MAX_RULES:raise ValueError('Logic source record/rule cap exceeded')
    if not records:raise ValueError('Empty logic source')
    return records

def substitute(pattern,binding):return Atom(pattern.predicate,tuple(binding[v] if v.startswith('?') else v for v in pattern.arguments),pattern.positive)

def unify(pattern,value,binding):
    if pattern.predicate!=value.predicate or pattern.positive!=value.positive:return None
    result=dict(binding)
    for left,right in zip(pattern.arguments,value.arguments):
        if left.startswith('?'):
            if left in result and result[left]!=right:return None
            result[left]=right
        elif left!=right:return None
    return result

class WorkExhausted(Exception):pass

class SignedVerifier:
    def __init__(self,store,snapshot_id,path):
        if type(snapshot_id) is not str or not snapshot_id or type(path) is not str or not path:raise ValueError('Explicit snapshot and source path required')
        with store.snapshot(snapshot_id) as snap:
            if path not in snap.files or not 0<snap.files[path]['size']<=MAX_SOURCE:raise ValueError('Logic source metadata size/path outside bound')
            raw=snap.read_range(path)
        self._snapshot=snapshot_id;self._path=path;self._sha=digest(raw);self._source_bytes=len(raw);self._records=compile_records(raw,snapshot_id,path)
    def infer(self,query,*,work_budget=10000):
        query=atom(query)
        if type(work_budget) is not int or not 0<=work_budget<=MAX_WORK:raise ValueError('Bounded explicit logical-work budget required')
        known={};nodes=[];work=0;complete=True
        for identifier,record in sorted(self._records.items()):
            if record['kind']=='fact' and record['atom'] not in known:
                known[record['atom']]=len(nodes);nodes.append({'kind':'fact','atom':record['atom'].value(),'source_record_id':identifier,'citation':dict(record['citation'])})
        def spend():
            nonlocal work
            if work>=work_budget:raise WorkExhausted()
            work+=1
        def join(premises,index,binding,proofs):
            if index==len(premises):yield binding,proofs;return
            for value,proof in sorted(known.items()):
                spend();next_binding=unify(premises[index],value,binding)
                if next_binding is not None:yield from join(premises,index+1,next_binding,proofs+[proof])
        try:
            changed=True
            while changed:
                changed=False
                for identifier,record in sorted(self._records.items()):
                    if record['kind']!='rule':continue
                    for binding,proofs in join(record['premises'],0,{},[]):
                        head=substitute(record['head'],binding)
                        if head in known:continue
                        spend();known[head]=len(nodes);nodes.append({'kind':'rule','atom':head.value(),'source_record_id':identifier,'citation':dict(record['citation']),'binding':dict(sorted(binding.items())),'premise_proofs':proofs});changed=True
        except WorkExhausted:complete=False
        positive=known.get(query);negative=known.get(Atom(query.predicate,query.arguments,not query.positive));verdict='incomplete' if not complete else 'inconsistent' if positive is not None and negative is not None else 'supported' if positive is not None else 'refuted' if negative is not None else 'unknown'
        return {'format':'RKVLOGIC1','snapshot_id':self._snapshot,'path':self._path,'source_sha256':self._sha,'source_bytes':self._source_bytes,'query':query.value(),'complete':complete,'verdict':verdict,'work_used':work,'work_budget':work_budget,'nodes':nodes,'support_proof':positive,'refute_proof':negative,'scientific_entailment_verified':False,'generated_answer':None,'scope':'Explicit signed binary Horn axioms only; no natural-language extraction or scientific truth guarantee'}
