import copy,sys,unittest
from pathlib import Path
from scripts.analyze_catalog_scaling import analyze
from scripts.catalog_fixture import COUNTS

def fixture():
 reports=[]
 for i in (1,2,3):
  for n in COUNTS:
   rows=[]
   for j in range(8):
    s,o=((True,False),(False,True),(True,False),(False,False))[j%4];rows.append({'query_index':j,'query':{'predicate':('reach','reach','edge','edge')[j%4],'arguments':(['a','c'],['c','b'],['a','b'],['c','a'])[j%4],'positive':True},'support_found':s,'opposite_found':o,'global_verdict':None,'selected_closure_complete':True,'producer_returned_bytes':100,'selected_payload_bytes':100,'auditor_returned_bytes':400,'constructor_observer':{'failed_constructor_calls':0,'constructor_calls':12,'constructor_wall_s':1.},'normalized_original_nodes_sha256':'owned'+str(j),'producer':{'wall_s':1.,'cpu_s':1.},'auditor':{'wall_s':1.,'cpu_s':1.},'canonical_certificate_bytes_excluding_newline':1000})
   reports.append({'round':i,'count':n,'rows':rows,'worker_wall_s':8,'worker_cpu_s':8,'peak_RSS_bytes':100,'generation':{},'ingest':{},'snapshot_manifest':{},'retained_bytes':100})
 return reports
class ScorerTests(unittest.TestCase):
 def test_allfixedworkers_and_queries_required(self):
  a=fixture()
  with self.assertRaises(ValueError):analyze(a[:-1])
  a[-1]=a[0]
  with self.assertRaises(ValueError):analyze(a)
  a=fixture();a[-1]['rows'].pop()
  with self.assertRaises(ValueError):analyze(a)
 def test_negative_and_round_denominators_no_best_round(self):
  a=fixture();self.assertTrue(analyze(a)['headline']['joint']);large=next(r for r in a if r['round']==2 and r['count']==4096)
  for x in large['rows']:x['producer']['wall_s']=10;x['canonical_certificate_bytes_excluding_newline']=4000
  h=analyze(a)['headline'];self.assertTrue(h['H1_fixed_payload_witness_invariance']);self.assertFalse(h['H2_4096_vs9_wall_and_CPU_at_most2x_eachround']);self.assertFalse(h['H3_4096_vs9_certificate_bytes_at_most2x_eachround'])
 def test_zero_CPU_base_is_null_not_free_speed(self):
  a=fixture()
  for r in a:
   if r['count']==9:
    for x in r['rows']:x['producer']['cpu_s']=0;x['auditor']['cpu_s']=0
  result=analyze(a);self.assertFalse(result['headline']['H2_4096_vs9_wall_and_CPU_at_most2x_eachround']);self.assertTrue(all(r['cpu_ratio_vs9'] is None for r in result['paired_ratios']))
 def test_payload_and_same_normalized_proof_are_quality_requirements(self):
  a=fixture();a[-1]['rows'][0]['normalized_original_nodes_sha256']='changed';self.assertFalse(analyze(a)['headline']['H1_fixed_payload_witness_invariance'])
 def test_wrong_query_even_same_flag_and_nodes_is_rejected(self):
  a=fixture();a[-1]['rows'][0]['query']['arguments']=['x','y'];self.assertFalse(analyze(a)['headline']['H1_fixed_payload_witness_invariance'])
if __name__=='__main__':unittest.main()
