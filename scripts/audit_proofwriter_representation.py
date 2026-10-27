"""Independent source-JSON-to-derived-record translation audit, no English entailment."""
import hashlib,json,re
from rkv1.core import digest
from scripts.postings_transform import canonical
from scripts.audit_signed_logic import unique
ATOMS=re.compile(r'\(\s*("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")\s*\)')
class UnsupportedTranslation(ValueError):pass
def symbol(role,value):
 if type(value) is not str or not value or re.fullmatch('[A-Za-z][A-Za-z ]{0,63}',value) is None:raise UnsupportedTranslation('Exact bounded symbol')
 return role+'_'+hashlib.sha256(value.encode('utf-8')).hexdigest()[:24]
def ground(parts,variables=False,premise=False):
 if len(parts)!=4 or parts[3] not in (('+','-','~') if premise else ('+','-')) or parts[1]=='is' and parts[2] in ('someone','something'):raise UnsupportedTranslation('Explicit signed tuple')
 def arg(value):
  if value in ('someone','something'):
   if not variables:raise UnsupportedTranslation('Ungrounded query/fact')
   return '?v'
  return symbol('c',value)
 return {'predicate':symbol('u',parts[2]) if parts[1]=='is' else symbol('r',parts[1]),'arguments':[arg(parts[0]),'z_unit' if parts[1]=='is' else arg(parts[2])],'positive':parts[3]=='+'}
def single(value,variables=False):
 if type(value) is not str:raise UnsupportedTranslation('String formal representation')
 match=ATOMS.fullmatch(value.strip())
 if not match:raise UnsupportedTranslation('Atomic representation grammar')
 return ground([json.loads(x) for x in match.groups()],variables)
def rule(value):
 if type(value) is not str or value.count('->')!=1:raise UnsupportedTranslation('Single rule arrow')
 left,right=value.strip().split('->');left=left.strip();right=right.strip()
 if not left.startswith('((') or not right.endswith(')'):raise UnsupportedTranslation('Rule wrappers')
 inner=left[2:].strip();head=right[:-1].strip()
 if not inner.endswith(')'):raise UnsupportedTranslation('Premise outer wrapper')
 inner=inner[:-1].strip();matches=list(ATOMS.finditer(inner));remaining=ATOMS.sub('',inner)
 if remaining.strip() or not 1<=len(matches)<=3:raise UnsupportedTranslation('Bounded full-premise syntax')
 raw_parts=[[json.loads(x) for x in m.groups()] for m in matches];h=ATOMS.fullmatch(head)
 if not h:raise UnsupportedTranslation('Rule head atom')
 head_parts=[json.loads(x) for x in h.groups()];terms={t for parts in raw_parts+[head_parts] for t in (parts[0],parts[2]) if t in ('someone','something')}
 if len(terms)>1:raise UnsupportedTranslation('Mixed variable spellings')
 return ground(head_parts,True),[ground(parts,True,True) for parts in raw_parts]
def audit_compilation(store,sid,source_mapping,source_paths,*,world):
 if world!='OWA':raise UnsupportedTranslation('Explicit OWA hard-negation policy required')
 with store.snapshot(sid) as snap:
  original=snap.read_range('original.json');row=json.loads(original,object_pairs_hook=unique);expected_sources={};expected_bindings=[];returned=len(original)
  for kind,field,path,prefix in (('fact','triples','facts.logic.jsonl','f'),('rule','rules','rules.logic.jsonl','r')):
   lines=[];offset=0
   for i,key in enumerate(sorted(row[field])):
    value=row[field][key]['representation'];record={'id':prefix+str(i),'kind':kind}
    if kind=='fact':record['atom']=single(value)
    else:record['head'],record['premises']=rule(value)
    raw=canonical(record)+b'\n';lines.append(raw);expected_bindings.append({'path':path,'compiled_record_id':record['id'],'offset':offset,'length':len(raw),'compiled_record_sha256':digest(raw),'original_JSON_pointer':[field,key,'representation'],'original_representation_sha256':digest(value.encode('utf-8'))});offset+=len(raw)
   if lines:expected_sources[path]=b''.join(lines)
  if source_mapping!=expected_bindings or sorted(source_paths)!=sorted(expected_sources):raise ValueError('Derived/original representation binding differs')
  for path,expected in expected_sources.items():
   actual=snap.read_range(path);returned+=len(actual)
   if actual!=expected:raise ValueError('Derived source does not match original representation')
  return {'original_file_sha256':digest(original),'original_file_bytes':len(original),'derived_files':{p:{'bytes':len(raw),'sha256':digest(raw)} for p,raw in expected_sources.items()},'original_representation_bindings':len(expected_bindings),'independent_compilation_verified':True,'application_returned_bytes':returned,'scientific_entailment_verified':False,'English_translation_verified':False,'scope':'Only supplied formal representation consistency; generated logic files are derived source, not original dataset offsets'}
