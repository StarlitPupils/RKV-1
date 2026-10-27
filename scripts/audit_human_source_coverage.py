"""Postprediction human-sentence semantic reference alignment; no oracle splitting input."""
from collections import Counter
from rkv1.core import digest
from scripts.postings_transform import canonical,parse
from scripts.audit_proofwriter_representation import single,rule

def signature(record):
 if record['kind']=='fact':return canonical({'kind':'fact','atom':record['atom']})
 return canonical({'kind':'rule','head':record['head'],'premises':sorted(record['premises'],key=canonical)})
def audit_human_compilation(store,sid,source_mapping,source_paths,*,world):
 if world!='OWA':raise ValueError('Explicit OWA policy required')
 with store.snapshot(sid) as snap:
  original=snap.read_range('original.json');row=parse(original);sentences=row['sentences'];mapping=row['mappings'];expected={key:Counter() for key in sentences};returned=len(original)
  if type(sentences) is not dict or type(mapping) is not dict or set(mapping)!=set(row['triples'])|set(row['rules']) or set(row['triples'])&set(row['rules']) or set(mapping.values())!=set(sentences):raise ValueError('Original reference-to-sentence coverage differs')
  for field,kind in (('triples','fact'),('rules','rule')):
   for identifier,entry in row[field].items():
    sentence_id=mapping[identifier];record={'kind':kind}
    if kind=='fact':record['atom']=single(entry['representation'])
    else:record['head'],record['premises']=rule(entry['representation'])
    expected[sentence_id][signature(record)]+=1
  actual={key:Counter() for key in sentences};bindings=[]
  for path in sorted(source_paths):
   if path not in ('facts.logic.jsonl','rules.logic.jsonl'):raise ValueError('Explicit derived source path')
   raw=snap.read_range(path);returned+=len(raw);offset=0
   for line in raw.splitlines(keepends=True):
    record=parse(line);matches=[b for b in source_mapping if b['path']==path and b['compiled_record_id']==record['id']]
    if len(matches)!=1:raise ValueError('Unique original sentence binding required')
    b=matches[0];pointer=b.get('original_JSON_pointer')
    if type(pointer) is not list or len(pointer)!=2 or pointer[0]!='sentences' or pointer[1] not in sentences:raise ValueError('Original human sentence pointer differs')
    sentence_id=pointer[1];expected_binding={'path':path,'compiled_record_id':record['id'],'offset':offset,'length':len(line),'compiled_record_sha256':digest(line),'original_JSON_pointer':['sentences',sentence_id],'original_English_sentence_sha256':digest(sentences[sentence_id].encode('utf-8'))}
    if b!=expected_binding:raise ValueError('Original human source/derived range SHA differs')
    actual[sentence_id][signature(record)]+=1;bindings.append(b);offset+=len(line)
  if len(bindings)!=len(source_mapping) or actual!=expected:raise ValueError('Human parser output does not cover exact per-sentence formal reference semantics')
 return {'original_file_sha256':digest(original),'original_file_bytes':len(original),'original_English_bindings':len(bindings),'controlled_English_alignment_with_supplied_reference_verified':True,'formal_reference_used_only_after_predictions':True,'human_sentence_mappings_used_only_after_predictions':True,'application_returned_bytes':returned,'scientific_entailment_verified':False,'unrestricted_English_NLI_verified':False,'scope':'Postprediction original human sentence alignment; no canonical English or mapping oracle input/correction'}
