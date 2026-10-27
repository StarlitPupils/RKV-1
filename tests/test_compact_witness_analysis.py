import sys,copy,unittest
from pathlib import Path
from scripts.analyze_compact_witness import analyze

def fixture():
 reports=[];parents={};outer={}
 for i in (1,2,3):
  for m in ('plain','compact'):
   for c in ('zstd','zlib'):
    records=[{'id':'case'+str(j),'source_snapshot_id':'owned','source_sha256':'root'+str(j),'source_bytes':100,'restored_sha256':'root'+str(j),'independent_header_catalog_mapping_and_original_DAG':{'independent_header_and_catalog_mapping_verified':True,'original_selected_DAG_verified':True,'global_verdict':None}} for j in range(96)];frame=1000 if m=='plain' else 900;reports.append({'round':i,'method':m,'codec':c,'case_count':96,'cases':records,'total_frame_bytes':frame,'total_original_bytes':9600,'retained_bytes':frame+9600,'worker_wall_s':1.,'worker_cpu_s':1.});key=(i,m,c);parents[key]={'return_code':0,'error':None,'parent_full_process_wall_s':1.};outer[key]=100
 return reports,parents,outer
class ScorerTests(unittest.TestCase):
 def test_payload_win_cannot_hide_all_source_premium(self):
  args=fixture();r=analyze(*args,1000,5000);self.assertFalse(r['headline']['H1_primary_Zstd_full_conservative_listed_file_B']);self.assertTrue(all(x['frame_delta_B']<0 for x in r['pairs']));self.assertTrue(analyze(*args,0,5000)['headline']['joint'])
 def test_all_workers_cases_root_order_and_file_conservation_required(self):
  r,p,o=fixture()
  with self.assertRaises(ValueError):analyze(r[:-1],p,o,0,0)
  r[-1]['cases'][0]['source_sha256']='different'
  with self.assertRaises(ValueError):analyze(r,p,o,0,0)
  r,p,o=fixture();r[-1]['retained_bytes']+=1
  with self.assertRaises(ValueError):analyze(r,p,o,0,0)
 def test_one_round_cpu_or_parent_loss_is_not_best_round_win(self):
  r,p,o=fixture();next(x for x in r if x['round']==2 and x['method']=='compact' and x['codec']=='zstd')['worker_cpu_s']=1.1;self.assertFalse(analyze(r,p,o,0,0)['headline']['H2_primary_workerwall_CPU_parentwall'])
  r,p,o=fixture();p[(3,'compact','zstd')]['parent_full_process_wall_s']=1.1;self.assertFalse(analyze(r,p,o,0,0)['headline']['H2_primary_workerwall_CPU_parentwall'])
 def test_zero_clock_and_one_wrong_audit_stay_negative(self):
  r,p,o=fixture();next(x for x in r if x['round']==1 and x['method']=='plain' and x['codec']=='zstd')['worker_cpu_s']=0;z=analyze(r,p,o,0,0);self.assertFalse(z['headline']['H2_primary_workerwall_CPU_parentwall']);self.assertIsNone(next(x for x in z['pairs'] if x['round']==1 and x['codec']=='zstd')['worker_CPU_ratio'])
  r,p,o=fixture();r[-1]['cases'][-1]['independent_header_catalog_mapping_and_original_DAG']['original_selected_DAG_verified']=False;self.assertFalse(analyze(r,p,o,0,0)['headline']['H0_all1152_exact_original_and_independent_DAG'])
if __name__=='__main__':unittest.main()
