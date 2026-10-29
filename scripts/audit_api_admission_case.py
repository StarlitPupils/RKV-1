"""Private owned-tested source fidelity for the next diagnostic, no real API cases opened."""
import hashlib,json
from scripts.api_admission_audit import independent_order,trace
from scripts.evidence_retrieval import lexical
from scripts.paper_gap import admission_trace

def audit_case(snapshot,shared,question,gold_ids,prior_hits):
 ordered,scores=independent_order(shared,question);old,old_scores=lexical(shared,question);assert ordered==old and set(scores)==set(old_scores) and all(abs(scores[k]-old_scores[k])<=1e-12 for k in scores)
 result=trace(shared['locators'],ordered,gold_ids);reference=admission_trace(shared['locators'],old,gold_ids);assert result['selected_ids']==reference['selected_ids']==[h['key'] for h in prior_hits] and result['admitted_B']==reference['admitted_bytes']==sum(h['locator']['length'] for h in prior_hits)
 for key,event in result['gold_events'].items():assert event['category']==reference['gold_categories'][key]
 checked=returned=0;bykey={h['key']:h for h in prior_hits}
 for key in sorted(set(result['selected_ids'])|set(gold_ids)):
  loc=shared['locators'][key];raw=snapshot.read_range('corpus.jsonl',loc['offset'],loc['length']);assert hashlib.sha256(raw).hexdigest()==loc['sha256'];obj=json.loads(raw);assert 'doc:'+str(obj['doc_id'])==key;checked+=1;returned+=len(raw)
  if key in bykey:
   h=bykey[key];assert h['locator']=={'snapshot_id':snapshot.snapshot_id,'path':'corpus.jsonl',**loc} and h['title']==obj['title'] and h['sentences']==obj['abstract'] and h['source_bytes_verified'] is True
 return {**result,'ranking_SHA256':hashlib.sha256(json.dumps(ordered,separators=(',',':')).encode()).hexdigest(),'lexical_candidates':len(ordered),'original_record_checks':checked,'application_returned_B':returned,'source_identity_only_not_semantic':True}
