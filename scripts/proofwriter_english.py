"""Strict controlled-English OWA grammar, no representation/gold input."""
import hashlib,json,re
from scripts.proofwriter_representation import Compiler,UnsupportedRepresentation
VERBS={'eats':'eat','likes':'like','needs':'need','sees':'see','visits':'visit','chases':'chase'}
class UnsupportedEnglish(ValueError):pass
SUBJECT=r'(The (?:bald eagle|[a-z]+)|the (?:bald eagle|[a-z]+)|[A-Z][a-z]+|someone|something|it|they)'
class EnglishCompiler:
 def __init__(self,*,world):
  if world!='OWA':raise UnsupportedEnglish('Explicit OWA controlled-language policy required')
  self.symbolic=Compiler(world=world)
 @staticmethod
 def sentence(value):
  if type(value) is not str or not 0<len(value)<=8192 or not value.endswith('.') or '\n' in value or '  ' in value:raise UnsupportedEnglish('Bounded single controlled sentence required')
  return value[:-1]
 @staticmethod
 def entity(value,context):
  if value in ('It','They','He','She','Them','This','That','Someone','Something','All','If','The'):raise UnsupportedEnglish('Unbound or reserved controlled subject')
  if value in ('it','they'):
   if context is None:raise UnsupportedEnglish('Unbound controlled pronoun')
   return context
  if value.startswith(('The ','the ')):return value[4:]
  return value
 def clause(self,value,context=None,inherited=None):
  attribute=re.fullmatch(SUBJECT+r' (?:is|are) (not )?([a-z]+)',value)
  if attribute:
   raw_subject,negative,obj=attribute.groups();subject=self.entity(raw_subject,context);return [subject,'is',obj,'-' if negative else '+'],subject if subject in ('someone','something') else context,subject
  relation=re.fullmatch(SUBJECT+r' (eats|likes|needs|sees|visits|chases) (the (?:bald eagle|[a-z]+)|[A-Z][a-z]+)',value)
  if relation:
   raw_subject,verb,obj=relation.groups();subject=self.entity(raw_subject,context);return [subject,verb,self.entity(obj,context),'+'],subject if subject in ('someone','something') else context,subject
  plural=re.fullmatch(r'they (eat|like|need|see|visit|chase) (the (?:bald eagle|[a-z]+)|[A-Z][a-z]+)',value)
  if plural:
   verb,obj=plural.groups();subject=self.entity('they',context);present={v:k for k,v in VERBS.items()}[verb];return [subject,present,self.entity(obj,context),'+'],context,subject
  negative=re.fullmatch(SUBJECT+r' (?:does|do) not (eat|like|need|see|visit|chase) (the (?:bald eagle|[a-z]+)|[A-Z][a-z]+)',value)
  if negative:
   raw_subject,verb,obj=negative.groups();subject=self.entity(raw_subject,context);present={v:k for k,v in VERBS.items()}[verb];return [subject,present,self.entity(obj,context),'-'],subject if subject in ('someone','something') else context,subject
  ellipse=re.fullmatch(r'(not )?([a-z]+)',value)
  if ellipse and inherited is not None:
   negative,obj=ellipse.groups();return [inherited,'is',obj,'-' if negative else '+'],context,inherited
  raise UnsupportedEnglish('Unsupported controlled clause; no fuzzy or semantic fallback')
 @staticmethod
 def representation(parts):return '('+' '.join(json.dumps(x) for x in parts)+')'
 def ground(self,value):
  clause,_,_=self.clause(self.sentence(value))
  if clause[0] in ('someone','something'):raise UnsupportedEnglish('Variable in ground English sentence')
  return self.symbolic.ground(self.representation(clause))
 def rule_representation(self,value):
  sentence=self.sentence(value);generic=re.fullmatch(r'(?:All )?([A-Za-z]+(?:, [a-z]+)*) (people|things) are (not )?([a-z]+)',sentence)
  if generic:
   attributes,noun,negative,head=generic.groups();attributes=attributes.split(', ');attributes[0]=attributes[0].lower()
   if not 1<=len(attributes)<=3:raise UnsupportedEnglish('Controlled premise cap')
   variable='someone' if noun=='people' else 'something';premises=[[variable,'is',a,'+'] for a in attributes];conclusion=[variable,'is',head,'-' if negative else '+']
  else:
   if not sentence.startswith('If ') or sentence.count(' then ')!=1:raise UnsupportedEnglish('Explicit controlled rule required')
   antecedent,consequent=sentence[3:].split(' then ');parts=antecedent.split(' and ')
   if not 1<=len(parts)<=3:raise UnsupportedEnglish('Controlled premise cap')
   premises=[];context=None;inherited=None
   for part in parts:
    atom,context,inherited=self.clause(part,context,inherited);premises.append(atom)
   conclusion,_,_=self.clause(consequent,context)
  # OWA hard negation uses ~ in rule premises, never negation-as-failure.
  for atom in premises:
   if atom[3]=='-':atom[3]='~'
  return '('+'('+' '.join(self.representation(p) for p in premises)+') -> '+self.representation(conclusion)+')'
 def compile(self,triples,rules):
  facts={};rule_inputs={}
  for identifier,row in triples.items():
   value=row['text'];clause,_,_=self.clause(self.sentence(value));facts[identifier]={'representation':self.representation(clause)}
  for identifier,row in rules.items():rule_inputs[identifier]={'representation':self.rule_representation(row['text'])}
  files,bindings=self.symbolic.compile(facts,rule_inputs)
  for binding in bindings:
   field,identifier,_=binding['original_JSON_pointer'];entry=(triples if field=='triples' else rules)[identifier];binding['original_JSON_pointer'][-1]='text';del binding['original_representation_sha256'];binding['original_English_sentence_sha256']=hashlib.sha256(entry['text'].encode('utf-8')).hexdigest()
  return files,bindings
