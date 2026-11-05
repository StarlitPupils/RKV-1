"""PRIVATE owned Memory update fault preparation; not a scientific corpus."""
import json,hashlib
from pathlib import Path
def source(n,epoch):
 if type(n) is not int or not 9<=n<=1024 or epoch not in (0,1):raise ValueError('Fixed bounded owned source')
 rows=[]
 for i in range(n):
  text=[f'RKV97PROBE epoch{epoch} original evidence {i}.','Escaped 雪; repeated duplicate.','Escaped 雪; repeated duplicate.'] if i<4 else [f'Background owned record {i}.']
  rows.append({'doc_id':i,'title':f'Owned {i}','abstract':text})
 return b''.join(json.dumps(r,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()+b'\r\n' for r in rows)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_ledger(root):return {p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in Path(root).rglob('*') if p.is_file()}
def audit_result(memory,result,original,sid):
 if result['snapshot_id']!=sid:raise ValueError('Wrong explicit/current SID')
 with memory.store.snapshot(sid) as snap:
  restored=snap.read_range('corpus.jsonl')
 if restored!=original:raise ValueError('Whole original source identity differs')
 expected={};offset=0
 for line in original.splitlines(keepends=True):
  obj=json.loads(line)
  if obj['doc_id']<4:expected['doc:'+str(obj['doc_id'])]=(offset,line,obj)
  offset+=len(line)
 if len(result['hits'])!=4 or {h['key'] for h in result['hits']}!=set(expected):raise ValueError('Sentinel set differs')
 for hit in result['hits']:
  offset,line,obj=expected[hit['key']]
  if hit['locator']!={'snapshot_id':sid,'path':'corpus.jsonl','offset':offset,'length':len(line),'sha256':sha(line)}:raise ValueError('Original locator differs')
  if hit['title']!=obj['title'] or hit['sentences']!=obj['abstract'] or hit['source_bytes_verified'] is not True:raise ValueError('Mixed/original text differs')
 return {'verified_original_records':4,'source_SHA':sha(restored),'source_application_return_B':len(restored),'source_application_bytes_not_physical_IO':True}
