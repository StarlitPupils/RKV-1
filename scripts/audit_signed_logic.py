"""Independent source-bound Horn DAG and finite grounding closure checker."""
import itertools,json
from rkv1.core import digest
from scripts.postings_transform import canonical

class VerificationCapacityExceeded(ValueError):pass

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate logic JSON key')
        result[key]=value
    return result

def name(value,variable=False):
    if type(value) is not str:return False
    if variable and value.startswith('?'):value=value[1:];limit=16
    else:limit=32
    return 1<=len(value)<=limit and 'a'<=value[0]<='z' and all('a'<=c<='z' or '0'<=c<='9' or c=='_' for c in value)

def literal(value,variables=False):
    if type(value) is not dict or set(value)!={'predicate','arguments','positive'} or not name(value['predicate']) or type(value['positive']) is not bool or type(value['arguments']) is not list or len(value['arguments'])!=2 or not all(name(v,variables) for v in value['arguments']):raise ValueError('Invalid signed literal')
    return (value['predicate'],tuple(value['arguments']),value['positive'])

def replace(value,binding):return (value[0],tuple(binding[x] if x.startswith('?') else x for x in value[1]),value[2])

def parse_source(raw,sid,path):
    records={};offset=0;rules=0
    for line in raw.splitlines(keepends=True):
        obj=json.loads(line,object_pairs_hook=unique,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite logic source')))
        if type(obj) is not dict or not name(obj.get('id')) or obj['id'] in records:raise ValueError('Invalid source identity')
        kind=obj.get('kind')
        if kind=='fact' and set(obj)=={'id','kind','atom'}:entry={'kind':kind,'atom':literal(obj['atom'])}
        elif kind=='rule' and set(obj)=={'id','kind','head','premises'} and type(obj['premises']) is list and 1<=len(obj['premises'])<=3:
            head=literal(obj['head'],True);premises=[literal(v,True) for v in obj['premises']];variables={x for atom in premises for x in atom[1] if x.startswith('?')}
            if len(variables)>3 or any(x.startswith('?') and x not in variables for x in head[1]):raise ValueError('Unsafe explicit rule')
            entry={'kind':kind,'head':head,'premises':premises};rules+=1
        else:raise ValueError('Unsupported explicit source record')
        entry['citation']={'snapshot_id':sid,'path':path,'offset':offset,'length':len(line),'sha256':digest(line)};records[obj['id']]=entry;offset+=len(line)
    if not 1<=len(records)<=1024 or rules>64:raise ValueError('Source grammar record bounds')
    return records

def grounded_steps(records,constants,limit=100000):
    count=0
    for identifier,record in sorted(records.items()):
        if record['kind']!='rule':continue
        variables=sorted({x for value in record['premises'] for x in value[1] if x.startswith('?')});size=len(constants)**len(variables)
        if count+size>limit:raise VerificationCapacityExceeded('Independent grounding capacity exceeded; cannot certify completeness')
        for values in itertools.product(sorted(constants),repeat=len(variables)):
            binding=dict(zip(variables,values));count+=1;yield identifier,replace(record['head'],binding),[replace(v,binding) for v in record['premises']]

def oracle(records,query):
    constants={x for r in records.values() for atom in ([r['atom']] if r['kind']=='fact' else [r['head'],*r['premises']]) for x in atom[1] if not x.startswith('?')}|set(query[1]);steps=list(grounded_steps(records,constants));known={r['atom'] for r in records.values() if r['kind']=='fact'}
    while True:
        extra={head for _,head,premises in steps if all(p in known for p in premises)}-known
        if not extra:return known,len(steps)
        known|=extra

def verify_certificate(store,snapshot_id,path,certificate):
    c=certificate
    if type(c) is not dict or c.get('format')!='RKVLOGIC1' or c.get('snapshot_id')!=snapshot_id or c.get('path')!=path or c.get('scientific_entailment_verified') is not False or c.get('generated_answer') is not None or type(c.get('complete')) is not bool:raise ValueError('Explicit source/certificate scope differs')
    if type(c.get('work_budget')) is not int or type(c.get('work_used')) is not int or not 0<=c['work_used']<=c['work_budget']<=100000:raise ValueError('Invalid recorded logical work bounds')
    query=literal(c['query']);application_bytes=0
    with store.snapshot(snapshot_id) as snapshot:
        if path not in snapshot.files or not 0<snapshot.files[path]['size']<=1<<20:raise ValueError('Source path/size outside bound')
        raw=snapshot.read_range(path);application_bytes+=len(raw)
        if len(raw)!=c['source_bytes'] or digest(raw)!=c['source_sha256']:raise ValueError('Original logic source SHA differs')
        records=parse_source(raw,snapshot_id,path);nodes=c.get('nodes')
        if type(nodes) is not list or len(nodes)>101024:raise ValueError('Proof node bound')
        atoms=[];seen=set();derived=0
        for i,node in enumerate(nodes):
            if type(node) is not dict or node.get('source_record_id') not in records:raise ValueError('Unknown proof source record')
            record=records[node['source_record_id']];expected_keys={'kind','atom','source_record_id','citation'}|({'binding','premise_proofs'} if record['kind']=='rule' else set())
            if set(node)!=expected_keys or node['kind']!=record['kind'] or node['citation']!=record['citation']:raise ValueError('Proof kind/offset/citation differs')
            citation=record['citation'];original=snapshot.read_range(path,citation['offset'],citation['length']);application_bytes+=len(original)
            if digest(original)!=citation['sha256']:raise ValueError('Original axiom/rule bytes differ')
            value=literal(node['atom'])
            if value in seen:raise ValueError('Noncanonical duplicate atom proof')
            if record['kind']=='fact':
                if value!=record['atom']:raise ValueError('Fact proof does not match original signed atom')
            else:
                binding=node['binding'];refs=node['premise_proofs'];variables={v for p in record['premises'] for v in p[1] if v.startswith('?')}
                if type(binding) is not dict or set(binding)!=variables or not all(name(v) for v in binding.values()) or type(refs) is not list or len(refs)!=len(record['premises']) or any(type(ref) is not int or not 0<=ref<i for ref in refs):raise ValueError('Invalid binding or topological premises')
                if replace(record['head'],binding)!=value or any(replace(pattern,binding)!=atoms[ref] for pattern,ref in zip(record['premises'],refs)):raise ValueError('Rule inference differs from original grounded rule')
                derived+=1
            atoms.append(value);seen.add(value)
    if derived>c['work_used']:raise ValueError('Derived proof count exceeds recorded work')
    for key,target in (('support_proof',query),('refute_proof',(query[0],query[1],not query[2]))):
        ref=c.get(key)
        if ref is not None and (type(ref) is not int or not 0<=ref<len(atoms) or atoms[ref]!=target):raise ValueError('Query witness differs')
        if (ref is not None)!=(target in seen):raise ValueError('Missing/extra query witness')
    groundings=None
    if c['complete']:
        expected,groundings=oracle(records,query)
        if expected!=seen:raise ValueError('Claimed complete closure differs from independent ground oracle')
    support=query in seen;refute=(query[0],query[1],not query[2]) in seen;verdict='incomplete' if not c['complete'] else 'inconsistent' if support and refute else 'supported' if support else 'refuted' if refute else 'unknown'
    if c['verdict']!=verdict:raise ValueError('Unsupported query verdict')
    return {'certificate_sha256':digest(canonical(c)),'formal_derivation_verified':True,'closure_completeness_verified':c['complete'],'verdict':verdict,'independent_groundings':groundings,'original_source_application_returned_bytes':application_bytes,'scientific_entailment_verified':False,'generated_answer':None,'scope':'Only explicit signed binary Horn source axioms; no natural-language or scientific truth validation','work_metadata_is_not_a_CPU_or_physical_IO_certificate':True}
