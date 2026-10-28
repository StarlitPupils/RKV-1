import sys,copy,unittest
from pathlib import Path
from scripts.analyze_pinned_metadata import analyze
from scripts.catalog_fixture import COUNTS

def fixture():
 rs=[];ps={}
 for i in (1,2,3):
  for n in COUNTS:
   for m in ('fresh','pinned'):
    for t in ('off','on'):
     qs=[]
     for j in range(8):
      p,args=(('reach',['a','c']),('reach',['c','b']),('edge',['a','b']),('edge',['c','a']))[j%4];a,b=((True,False),(False,True),(True,False),(False,False))[j%4];qs.append({'query_index':j,'query':{'predicate':p,'arguments':args,'positive':True},'support':a,'opposite':b,'global_verdict':None,'certificate_sha256':'owned'+str(n)+str(j),'selected_payload_B':100,'auditor_API_reported_returned_B':300,'observed_source_calls':None if t=='off' else [{'path':'one.logic.jsonl','returned_bytes':400}]})
     r={'round':i,'count':n,'method':m,'meter':t,'queries':qs,'query_count':8,'tracked_pinned_metadata_B':100 if m=='pinned' else None,'observer':None if t=='off' else {'failed_constructor_calls':0,'constructor_calls':1 if m=='pinned' else 10},'batch':{'wall_s':1 if m=='fresh' else .5,'cpu_s':1 if m=='fresh' else .5},'peak_RSS_B':100};rs.append(r);ps[(i,n,m,t)]={'return_code':0,'error':None,'parent_full_process_wall_s':1 if m=='fresh' else .5}
 return rs,ps
class AnalysisTests(unittest.TestCase):
 def test_required48_and_all8(self):
  r,p=fixture()
  with self.assertRaises(ValueError):analyze(r[:-1],p)
  r[-1]['queries'].pop()
  with self.assertRaises(ValueError):analyze(r,p)
 def test_ON_speed_does_not_replace_OFF_primary_loss(self):
  r,p=fixture();self.assertTrue(analyze(r,p)['headline']['joint']);bad=next(x for x in r if x['round']==2 and x['count']==4096 and x['method']=='pinned' and x['meter']=='off');bad['batch']['wall_s']=2;self.assertFalse(analyze(r,p)['headline']['H2_primary4096_meterOFF_time'])
 def test_RSS_cap_zero_clock_and_OFF_null(self):
  r,p=fixture();bad=next(x for x in r if x['round']==1 and x['count']==4096 and x['method']=='pinned' and x['meter']=='off');bad['peak_RSS_B']=126;self.assertFalse(analyze(r,p)['headline']['H3_primary4096_meterOFF_RSS_atmost1_25']);bad['observer']={};self.assertFalse(analyze(r,p)['headline']['H1_identity_payload_lifecycle_measurement'])
  r,p=fixture();base=next(x for x in r if x['round']==1 and x['count']==4096 and x['method']=='fresh' and x['meter']=='off');base['batch']['cpu_s']=0;self.assertFalse(analyze(r,p)['headline']['H2_primary4096_meterOFF_time'])
 def test_byte_proof_and_callback_count_required(self):
  r,p=fixture();r[-1]['queries'][0]['certificate_sha256']='changed';self.assertFalse(analyze(r,p)['headline']['H1_identity_payload_lifecycle_measurement']);r,p=fixture();r[-1]['observer']['constructor_calls']=2;self.assertFalse(analyze(r,p)['headline']['H1_identity_payload_lifecycle_measurement'])
if __name__=='__main__':unittest.main()
