"""Supervised typed-template candidate, only supplied TRAIN labels fit templates."""
import copy,re
from collections import Counter
from rkv1.core import digest
from scripts.postings_transform import canonical,parse
from scripts.proofwriter_representation import Compiler
from scripts.proofwriter_english import EnglishCompiler
from scripts.logic_fixture import encode
MAX_TEXT=4096;MAX_MODEL_BYTES=64<<20

def delex(text,registry):
 if type(text) is not str or not 0<len(text)<=MAX_TEXT or '$' in text or any(ord(c)>127 for c in text):raise ValueError('Bounded ASCII sentence, no reserved slot markers')
 text=' '.join(text.lower().split());lookup={n.lower():n for n in registry}
 if len(lookup)!=len(registry):raise ValueError('Case-ambiguous training entity registry')
 pattern=re.compile(r'(?<![a-z])(?:'+'|'.join(re.escape(n) for n in sorted(lookup,key=lambda s:(-len(s),s)))+r')(?![a-z])') if lookup else None
 names=[]
 def replace(match):
  name=lookup[match.group()]
  if name not in names:names.append(name)
  return '$'+str(names.index(name))
 return (pattern.sub(replace,text) if pattern else text),names

def records_for_row(row):
 sentences=row['sentences'];mapping=row['mappings'];triples=row['triples'];rules=row['rules']
 if type(sentences) is not dict or not 1<=len(sentences)<=1024 or type(triples) is not dict or type(rules) is not dict or len(triples)+len(rules)>1024 or len(rules)>64 or type(mapping) is not dict or set(mapping)!=set(triples)|set(rules) or set(triples)&set(rules) or set(mapping.values())!=set(sentences):raise ValueError('Complete training annotation mapping required')
 symbolic=Compiler(world='OWA');groups={sid:[] for sid in sentences}
 for field,kind in ((triples,'fact'),(rules,'rule')):
  for identifier,entry in field.items():
   record={'kind':kind}
   if kind=='fact':record['atom']=symbolic.ground(entry['representation'])
   else:record['head'],record['premises']=symbolic.rule(entry['representation'])
   groups[mapping[identifier]].append(record)
 return groups,{v[1] for v in symbolic.identities.values() if v[0]=='c'}

def canonical_target(record,identities,names):
 record=copy.deepcopy(record)
 for a in ([record['atom']] if record['kind']=='fact' else [record['head'],*record['premises']]):
  for i,arg in enumerate(a['arguments']):
   if arg in identities:
    name=identities[arg]
    if name not in names:raise ValueError('Training ground entity not explicitly mentioned in human sentence')
    a['arguments'][i]={'slot':names.index(name)}
 if record['kind']=='rule':record['premises']=sorted(record['premises'],key=canonical)
 return record

def train(rows):
 if type(rows) is not list or not rows or len(rows)>10000:raise ValueError('Bounded full train list required')
 prepared=[];registry=set();invalid=0
 for row in rows:
  try:g,n=records_for_row(row);prepared.append((row,g,n));registry.update(n)
  except ValueError:invalid+=1
 registry=sorted(registry)
 if len(registry)>4096:raise ValueError('Training entity registry cap exceeded')
 lookup={n.lower() for n in registry}
 if len(lookup)!=len(registry):raise ValueError('Case-conflicting training registry unsupported')
 targets={};stats=Counter(training_rows=len(rows),valid_training_rows=len(prepared),invalid_training_rows=invalid)
 for row,groups,nameset in prepared:
  identities={'c_'+__import__('hashlib').sha256(n.encode()).hexdigest()[:24]:n for n in nameset}
  for sid,text in row['sentences'].items():
   stats['all_training_sentences']+=1
   try:key,names=delex(text,registry);target=canonical(sorted((canonical_target(r,identities,names) for r in groups[sid]),key=canonical)).decode()
   except ValueError:stats['unrepresentable_training_sentences']+=1;continue
   targets.setdefault(key,set()).add(target);stats['eligible_training_sentences']+=1
 if len(targets)>100000:raise ValueError('Training template count cap exceeded')
 templates={k:parse(next(iter(v)).encode()) for k,v in sorted(targets.items()) if len(v)==1};ambiguous=sorted(k for k,v in targets.items() if len(v)!=1);stats['ambiguous_template_keys']=len(ambiguous);stats['unambiguous_template_keys']=len(templates)
 if len(templates)<2:raise ValueError('At least2unambiguous keys needed for fixed control')
 model={'format':'RKVTYPEDTEMPLATE1','role':'learned','registry':registry,'templates':templates,'ambiguous_keys':ambiguous,'statistics':dict(stats),'normalization':'ASCII lower whitespace; only training-ground entity names to equality-preserving ordered slots','scientific_entailment_verified':False};control=copy.deepcopy(model);keys=sorted(templates)
 for i,key in enumerate(keys):control['templates'][key]=copy.deepcopy(templates[keys[(i+1)%len(keys)]])
 unchanged=sum(canonical(templates[k])==canonical(control['templates'][k]) for k in keys)
 model['statistics']['control_permutation_identical_target_keys']=unchanged;control['statistics']['control_permutation_identical_target_keys']=unchanged
 control['role']='control';assert len(canonical(model))==len(canonical(control))
 if len(canonical(model))>MAX_MODEL_BYTES:raise ValueError('Complete model bytes cap exceeded')
 return model,control

class LearnedCompiler(EnglishCompiler):
 def __init__(self,model,*,world):
  super().__init__(world=world)
  if type(model) is not dict or model.get('format')!='RKVTYPEDTEMPLATE1' or model.get('role') not in ('learned','control'):raise ValueError('Explicit training model required')
  self.model=copy.deepcopy(model)
 def compile_sentences(self,sentences):
  if type(sentences) is not dict or not 1<=len(sentences)<=1024 or any(type(k) is not str or not k for k in sentences):raise ValueError('Bounded original sentences required')
  records={'facts.logic.jsonl':[],'rules.logic.jsonl':[]};bindings=[];offsets={p:0 for p in records};total=rules=0
  for i,sid in enumerate(sorted(sentences)):
   text=sentences[sid];key,names=delex(text,self.model['registry'])
   if key not in self.model['templates']:raise ValueError('Unknown or ambiguous learned human template')
   templates=copy.deepcopy(self.model['templates'][key])
   for j,record in enumerate(templates):
    for a in ([record['atom']] if record['kind']=='fact' else [record['head'],*record['premises']]):
     for k,arg in enumerate(a['arguments']):
      if type(arg) is dict:
       if set(arg)!={'slot'} or type(arg['slot']) is not int or not 0<=arg['slot']<len(names):raise ValueError('Bound entity slot missing')
       a['arguments'][k]=self.symbolic.symbol('c',names[arg['slot']])
    record['id']=('f' if record['kind']=='fact' else 'r')+str(i)+'_'+str(j);path='facts.logic.jsonl' if record['kind']=='fact' else 'rules.logic.jsonl';raw=encode([record]);records[path].append(raw);bindings.append({'path':path,'compiled_record_id':record['id'],'offset':offsets[path],'length':len(raw),'compiled_record_sha256':digest(raw),'original_JSON_pointer':['sentences',sid],'original_English_sentence_sha256':digest(text.encode())});offsets[path]+=len(raw);total+=1;rules+=record['kind']=='rule'
    if total>1024 or rules>64:raise ValueError('Combined learned source caps exceeded')
  return {p:b''.join(v) for p,v in records.items() if v},bindings

def load_model(path,expected_sha):
 from pathlib import Path
 raw=Path(path).read_bytes()
 if type(expected_sha) is not str or len(expected_sha)!=64 or len(raw)>MAX_MODEL_BYTES+1 or digest(raw)!=expected_sha:raise ValueError('Explicit full model SHA/byte bound required')
 model=parse(raw);expected={'format','role','registry','templates','ambiguous_keys','statistics','normalization','scientific_entailment_verified'}
 if type(model) is not dict or set(model)!=expected or model['format']!='RKVTYPEDTEMPLATE1' or model['role'] not in ('learned','control') or model['scientific_entailment_verified'] is not False or type(model['registry']) is not list or len(model['registry'])>4096 or type(model['templates']) is not dict or not 2<=len(model['templates'])<=100000:raise ValueError('Strict training model schema required')
 return model
