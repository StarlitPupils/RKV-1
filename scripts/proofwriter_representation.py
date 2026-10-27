"""Strict supplied ProofWriter representation compiler, no English or label input."""
import hashlib,json,re
from scripts.logic_fixture import encode
from scripts.postings_transform import parse
TOKEN=re.compile(r'\s*(->|\(|\)|"(?:[^"\\]|\\.)*")')
VARIABLES={'someone','something'}
ARROW=object()
class UnsupportedRepresentation(ValueError):pass
class Compiler:
 def __init__(self,*,world):
  if world!='OWA':raise UnsupportedRepresentation('Explicit OWA policy required; CWA NAF is unsupported')
  self.identities={}
 def symbol(self,role,token):
  if type(token) is not str or not token or not re.fullmatch(r'[A-Za-z][A-Za-z ]{0,63}',token):raise UnsupportedRepresentation('Bounded exact representation symbol required')
  value=role+'_'+hashlib.sha256(token.encode('utf-8')).hexdigest()[:24];previous=self.identities.setdefault(value,(role,token))
  if previous!=(role,token):raise UnsupportedRepresentation('Representation symbol digest collision')
  return value
 def expression(self,source):
  if type(source) is not str or not 0<len(source)<=16384:raise UnsupportedRepresentation('Bounded supplied S-expression required')
  tokens=[];pos=0
  while pos<len(source):
   match=TOKEN.match(source,pos)
   if not match:
    if source[pos:].strip():raise UnsupportedRepresentation('Unrecognized representation token')
    break
   token=match.group(1);tokens.append((token.startswith('"'),json.loads(token) if token.startswith('"') else token));pos=match.end()
  index=0
  def node(level=0):
   nonlocal index
   if level>8 or index>=len(tokens):raise UnsupportedRepresentation('S-expression depth/length')
   quoted,token=tokens[index];index+=1
   if quoted:return token
   if token=='(':
    values=[]
    while index<len(tokens) and tokens[index]!=(False,')'):values.append(node(level+1))
    if index>=len(tokens):raise UnsupportedRepresentation('Unclosed S-expression')
    index+=1;return values
   if token==')':raise UnsupportedRepresentation('Unexpected closing token')
   return ARROW if token=='->' else token
  result=node()
  if index!=len(tokens):raise UnsupportedRepresentation('Trailing representation data')
  return result
 def atom(self,value,*,variables=False,premise=False):
  if type(value) is not list or len(value)!=4 or any(type(v) is not str for v in value) or value[3] not in (('+','-','~') if premise else ('+','-')):raise UnsupportedRepresentation('Explicit signed subject-relation-object tuple required')
  subject,relation,obj,sign=value
  def constant(token):
   if token in VARIABLES:
    if not variables:raise UnsupportedRepresentation('Variable in ground representation')
    return '?v'
   return self.symbol('c',token)
  if relation=='is':
   if obj in VARIABLES:raise UnsupportedRepresentation('Variable attribute predicate')
   predicate=self.symbol('u',obj);arguments=[constant(subject),'z_unit']
  else:predicate=self.symbol('r',relation);arguments=[constant(subject),constant(obj)]
  return {'predicate':predicate,'arguments':arguments,'positive':sign=='+'}
 def ground(self,source):return self.atom(self.expression(source))
 def rule(self,source):
  value=self.expression(source)
  if type(value) is not list or len(value)!=3 or value[1] is not ARROW or type(value[0]) is not list or not 1<=len(value[0])<=3:raise UnsupportedRepresentation('One-to-three explicit premises and one head required')
  atoms=[*value[0],value[2]]
  if any(type(a) is not list or len(a)!=4 or any(type(t) is not str for t in a) for a in atoms):raise UnsupportedRepresentation('Malformed explicit rule atom')
  terms={token for a in atoms if type(a) is list for token in (a[0],a[2]) if token in VARIABLES}
  if len(terms)>1:raise UnsupportedRepresentation('Mixed ambiguous variable spellings')
  return self.atom(value[2],variables=True),[self.atom(a,variables=True,premise=True) for a in value[0]]
 def compile(self,triples,rules):
  if type(triples) is not dict or not triples or type(rules) is not dict or len(triples)+len(rules)>1024 or len(rules)>64:raise UnsupportedRepresentation('Bounded explicit source facts/rules required')
  sources={};bindings=[]
  for kind,entries,path,prefix in (('fact',triples,'facts.logic.jsonl','f'),('rule',rules,'rules.logic.jsonl','r')):
   records=[];offset=0
   for i,identifier in enumerate(sorted(entries)):
    entry=entries[identifier]
    if type(identifier) is not str or not isinstance(entry,dict) or 'representation' not in entry:raise UnsupportedRepresentation('Explicit source representation member required')
    representation=entry['representation'];record={'id':prefix+str(i),'kind':kind}
    if kind=='fact':record['atom']=self.ground(representation)
    else:record['head'],record['premises']=self.rule(representation)
    raw=encode([record]);records.append(raw);bindings.append({'path':path,'compiled_record_id':record['id'],'offset':offset,'length':len(raw),'compiled_record_sha256':hashlib.sha256(raw).hexdigest(),'original_JSON_pointer':['triples' if kind=='fact' else 'rules',identifier,'representation'],'original_representation_sha256':hashlib.sha256(representation.encode('utf-8')).hexdigest()});offset+=len(raw)
   if records:sources[path]=b''.join(records)
  return sources,bindings
