"""Frozen-parser application to actual human sentences; no canonical/mapping input."""
from rkv1.core import digest
from scripts.logic_fixture import encode
from scripts.proofwriter_english import EnglishCompiler
class HumanSourceCompiler(EnglishCompiler):
 def compile_sentences(self,sentences):
  if type(sentences) is not dict or not 1<=len(sentences)<=1024 or any(type(k) is not str or not k for k in sentences):raise ValueError('Bounded original human sentence map required')
  records={'facts.logic.jsonl':[],'rules.logic.jsonl':[]};bindings=[];offsets={k:0 for k in records}
  for index,sentence_id in enumerate(sorted(sentences)):
   text=sentences[sentence_id]
   try:record={'id':'f'+str(index),'kind':'fact','atom':self.ground(text)};path='facts.logic.jsonl'
   except ValueError:
    representation=self.rule_representation(text);head,premises=self.symbolic.rule(representation);record={'id':'r'+str(index),'kind':'rule','head':head,'premises':premises};path='rules.logic.jsonl'
   raw=encode([record]);records[path].append(raw);bindings.append({'path':path,'compiled_record_id':record['id'],'offset':offsets[path],'length':len(raw),'compiled_record_sha256':digest(raw),'original_JSON_pointer':['sentences',sentence_id],'original_English_sentence_sha256':digest(text.encode('utf-8'))});offsets[path]+=len(raw)
  return {path:b''.join(lines) for path,lines in records.items() if lines},bindings
