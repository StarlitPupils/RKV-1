"""Post-prediction alignment audit using supplied formal references only as oracle."""
from rkv1.core import digest
from scripts.postings_transform import canonical,parse
from scripts.audit_proofwriter_representation import single,rule

def audit_English_compilation(store,sid,source_mapping,source_paths,*,world):
 if world!='OWA':raise ValueError('Explicit OWA policy required')
 with store.snapshot(sid) as snap:
  original=snap.read_range('original.json');row=parse(original);expected_sources={};expected_bindings=[];returned=len(original)
  for kind,field,path,prefix in (('fact','triples','facts.logic.jsonl','f'),('rule','rules','rules.logic.jsonl','r')):
   lines=[];offset=0
   for i,key in enumerate(sorted(row[field])):
    entry=row[field][key];formal=entry['representation'];record={'id':prefix+str(i),'kind':kind}
    if kind=='fact':record['atom']=single(formal)
    else:record['head'],record['premises']=rule(formal)
    raw=canonical(record)+b'\n';lines.append(raw);expected_bindings.append({'path':path,'compiled_record_id':record['id'],'offset':offset,'length':len(raw),'compiled_record_sha256':digest(raw),'original_JSON_pointer':[field,key,'text'],'original_English_sentence_sha256':digest(entry['text'].encode('utf-8'))});offset+=len(raw)
   if lines:expected_sources[path]=b''.join(lines)
  if source_mapping!=expected_bindings or sorted(source_paths)!=sorted(expected_sources):raise ValueError('English-derived compilation differs from supplied formal reference oracle')
  for path,expected in expected_sources.items():
   raw=snap.read_range(path);returned+=len(raw)
   if raw!=expected:raise ValueError('English-derived source byte differs from supplied formal semantics')
 return {'original_file_sha256':digest(original),'original_file_bytes':len(original),'derived_files':{p:{'bytes':len(raw),'sha256':digest(raw)} for p,raw in expected_sources.items()},'original_English_bindings':len(expected_bindings),'controlled_English_alignment_with_supplied_reference_verified':True,'formal_reference_used_only_after_predictions':True,'application_returned_bytes':returned,'scientific_entailment_verified':False,'unrestricted_English_NLI_verified':False,'scope':'Postprediction audit of bounded English parse against supplied formal reference, not oracle input to prediction or general semantic understanding'}
