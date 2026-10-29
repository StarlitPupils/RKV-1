import json,sys,tempfile,unittest
from pathlib import Path
from scripts.api_intervention import plan,request_body,strict_content,run_slot,score,canonical

def claim(i,label):return {'id':i,'claim':'Owned distinct statement '+str(i),'evidence':{} if label=='INSUFFICIENT' else {'7':[{'label':label,'sentences':[0]}]}}
def hits():return [{'citation_id':'D0','key':'doc:7','title':'Owned title','sentences':['Owned evidence.'],'source_bytes_verified':True,'locator':{'snapshot_id':'a'*64,'path':'corpus.jsonl','offset':0,'length':100,'sha256':'b'*64}}]
def payload(verdict='SUPPORT',citation=True):return {'model':'fixture','usage':{'prompt_tokens':1,'completion_tokens':2},'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'verdict':verdict,'evidence':[{'citation_id':'D0','sentence':0}] if citation else [],'explanation':'Owned explanation.'})}}]}
class APITests(unittest.TestCase):
 def test_disjoint48job_plan_fixed_classes_donors_and_order(self):
  claims=[claim(i+100*j,l) for j,l in enumerate(('SUPPORT','CONTRADICT','INSUFFICIENT')) for i in range(1,25)];a=plan(claims);b=plan(list(reversed(claims)));self.assertEqual(a,b);self.assertEqual(len(a['jobs']),48);self.assertEqual(len(a['selected_claim_ids']),16);self.assertFalse(set(a['selected_claim_ids'])&set(a['excluded_prior_API_ids']))
  for j in a['jobs']:
   if j['condition']=='rotated':self.assertNotEqual(j['donor_claim_id'],j['claim_id'])
  selected=a['selected_claim_ids'][0];excluded=next(c for c in claims if str(c['id'])==selected);new=plan(claims,[excluded]);self.assertNotIn(selected,new['selected_claim_ids'])
 def test_bad_plan_and_wire_source_and_byte_limits(self):
  with self.assertRaises(ValueError):plan([claim(1,'SUPPORT')]*2)
  with self.assertRaises(ValueError):plan([claim(1,'SUPPORT')])
  body=request_body('Owned claim',hits());self.assertEqual(body['max_tokens'],512);self.assertEqual(body['thinking'],{'type':'disabled'})
  h=hits();h[0]['source_bytes_verified']=False
  with self.assertRaises(ValueError):request_body('Owned claim',h)
  h=hits();h[0]['locator']['length']=4097
  with self.assertRaises(ValueError):request_body('Owned claim',h)
  with self.assertRaises(ValueError):request_body('x'*4097,hits())
  h=hits();h[0]['sentences']=['x'*20000]
  with self.assertRaises(ValueError):request_body('Owned claim',h)
 def test_strict_schema_unknown_citation_bool_and_json_duplicates_reject(self):
  good=json.loads(payload()['choices'][0]['message']['content']);self.assertTrue(strict_content(json.dumps(good),hits())['citation_binding_valid'])
  variants=[{**good,'extra':1},{**good,'explanation':' '.join(['word']*36)},{**good,'evidence':[{'citation_id':'D1','sentence':0}]},{**good,'evidence':[{'citation_id':'D0','sentence':True}]},{**good,'evidence':[]}]
  for v in variants:
   with self.assertRaises(ValueError):strict_content(json.dumps(v),hits())
  with self.assertRaises(ValueError):strict_content('{"verdict":"SUPPORT","verdict":"CONTRADICT"}',hits())
  with self.assertRaises(ValueError):strict_content('{"verdict":NaN}',hits())
 def test_durable_slot_exactly_one_transport_and_key_never_persisted(self):
  with tempfile.TemporaryDirectory() as tmp:
   calls=[];transport=lambda body:(calls.append(body) or payload());body=request_body('Owned claim',hits());job={'claim_id':'owned','condition':'retrieved','donor_claim_id':'owned'};r=run_slot(tmp,0,job,body,hits(),transport=transport);self.assertTrue(r['accepted']);self.assertEqual(len(calls),1)
   with self.assertRaises(FileExistsError):run_slot(tmp,0,job,body,hits(),transport=transport)
   with self.assertRaises(ValueError):run_slot(tmp,48,job,body,hits(),transport=transport)
   self.assertEqual(len(calls),1);self.assertFalse(any('Authorization' in p.read_text() or 'API_KEY' in p.read_text() for p in Path(tmp).iterdir()))
 def test_failures_reserved_once_truncation_rejected_no_fallback(self):
  with tempfile.TemporaryDirectory() as tmp:
   def broken(body):raise TimeoutError('private transport diagnostic must not persist')
   body=request_body('Owned claim',hits());r=run_slot(tmp,0,{},body,hits(),transport=broken);self.assertFalse(r['accepted']);self.assertEqual(r['error']['type'],'TimeoutError');self.assertNotIn('private transport',canonical(r).decode())
   p=payload();p['choices'][0]['finish_reason']='length';r=run_slot(tmp,1,{},body,hits(),transport=lambda b:p);self.assertFalse(r['accepted'])
 def test_interrupted_reservation_is_not_retried(self):
  with tempfile.TemporaryDirectory() as tmp:
   (Path(tmp)/'slot-00.reserved.json').write_text('{}');calls=[]
   with self.assertRaises(FileExistsError):run_slot(tmp,0,{},request_body('Owned claim',[]),[],transport=lambda b:calls.append(b))
   self.assertFalse(calls)
 def test_citation_binding_versus_gold_and_missing_denominator(self):
  answer=strict_content(payload()['choices'][0]['message']['content'],hits());r={'accepted':True,'answer':answer};self.assertTrue(score(claim(1,'SUPPORT'),r)['verdict_and_rationale']);self.assertFalse(score(claim(1,'CONTRADICT'),r)['verdict_correct']);self.assertFalse(score(claim(1,'SUPPORT'),{'accepted':False,'answer':None})['verdict_correct']);self.assertIsNone(score(claim(1,'INSUFFICIENT'),r)['verdict_and_rationale'])
 def test_empty_evidence_noninsufficient_cannot_pass(self):
  with self.assertRaises(ValueError):strict_content(payload()['choices'][0]['message']['content'],[])
  self.assertEqual(strict_content(payload('INSUFFICIENT',False)['choices'][0]['message']['content'],[])['verdict'],'INSUFFICIENT')
if __name__=='__main__':unittest.main()
