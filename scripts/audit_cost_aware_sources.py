"""Independent comparison by integer cross products; no candidate order function imported."""
import json,hashlib,functools
from fractions import Fraction
from scripts.evidence_retrieval import lexical,admit

def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def reference_order(shared,question,method):
 ids,scores=lexical(shared,question)
 if method=='lexical':return ids
 if method=='length_only':return sorted(ids,key=lambda k:(shared['locators'][k]['length'],k))
 if method!='score_per_byte':raise ValueError('Unknown method')
 def compare(a,b):
  na,da=scores[a].as_integer_ratio();nb,db=scores[b].as_integer_ratio();left=na*db*shared['locators'][b]['length'];right=nb*da*shared['locators'][a]['length']
  return -1 if left>right else 1 if left<right else (a>b)-(a<b)
 return sorted(ids,key=functools.cmp_to_key(compare))
def audit_prediction(snapshot,model,question,method,row):
 ranked=reference_order(model['shared'],question,method);selected,used=admit(model,ranked,max_facts=12,max_source_bytes=4096);assert row['selected_ids']==selected and row['admitted_record_B']==used<=4096 and len(selected)<=12 and row['question_SHA']==sha(question.encode());assert [h['paper_id'] for h in row['source_proof']]==selected;returned=0
 for h in row['source_proof']:
  loc=h['locator'];expected=model['shared']['locators'][h['paper_id']];assert loc=={'snapshot_id':snapshot.snapshot_id,'path':'corpus.jsonl',**expected};raw=snapshot.read_range('corpus.jsonl',loc['offset'],loc['length']);assert sha(raw)==loc['sha256'];obj=json.loads(raw);assert 'doc:'+str(obj['doc_id'])==h['paper_id'] and sha(obj['title'].encode())==h['title_sha256'] and sha(canonical(obj['abstract']))==h['abstract_sha256'];returned+=len(raw)
 assert returned==used;return {'source_bindings':len(selected),'application_returned_B':returned}
def score_sources(gold,selected):
 targets={'doc:'+str(k) for k,v in gold['evidence'].items() if v}
 if not targets:return {'annotated':False,'gold_papers':0,'recall_fraction':None,'complete':None}
 recovered=len(targets&set(selected));r=Fraction(recovered,len(targets));return {'annotated':True,'gold_papers':len(targets),'recovered_papers':recovered,'recall_fraction':[r.numerator,r.denominator],'complete':recovered==len(targets)}
