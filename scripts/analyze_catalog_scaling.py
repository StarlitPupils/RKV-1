"""Fixed diagnostics for catalogue amplification; no best-round selection."""
import statistics
from scripts.catalog_fixture import COUNTS

def ratio(value,base):return value/base if base>0 else None

def analyze(reports):
 if len(reports)!=12 or {(r['round'],r['count']) for r in reports}!={(i,n) for i in (1,2,3) for n in COUNTS}:raise ValueError('Exactly12fixed unique workers required')
 summaries=[];identities={};H1=True
 for r in reports:
  if len(r['rows'])!=8 or [x['query_index'] for x in r['rows']]!=list(range(8)):raise ValueError('All eight queries retained')
  for x in r['rows']:
   expected=((True,False),(False,True),(True,False),(False,False))[x['query_index']%4]
   p,args=(('reach',['a','c']),('reach',['c','b']),('edge',['a','b']),('edge',['c','a']))[x['query_index']%4]
   H1 &= x['query']=={'predicate':p,'arguments':args,'positive':True}
   H1 &= (x['support_found'],x['opposite_found'])==expected and x['global_verdict'] is None and x['selected_closure_complete'] is True and x['producer_returned_bytes']==x['selected_payload_bytes'] and x['constructor_observer']['failed_constructor_calls']==0
   identity=(x['normalized_original_nodes_sha256'],x['selected_payload_bytes'],x['producer_returned_bytes'],x['auditor_returned_bytes'])
   if x['query_index'] not in identities:identities[x['query_index']]=identity
   else:H1 &= identities[x['query_index']]==identity
  summaries.append({'round':r['round'],'count':r['count'],'median_query_producer_plus_auditor_wall_s':statistics.median(x['producer']['wall_s']+x['auditor']['wall_s'] for x in r['rows']),'median_query_producer_plus_auditor_cpu_s':statistics.median(x['producer']['cpu_s']+x['auditor']['cpu_s'] for x in r['rows']),'median_certificate_bytes':statistics.median(x['canonical_certificate_bytes_excluding_newline'] for x in r['rows']),'median_constructor_calls':statistics.median(x['constructor_observer']['constructor_calls'] for x in r['rows']),'median_constructor_wall_s':statistics.median(x['constructor_observer']['constructor_wall_s'] for x in r['rows']),'worker_wall_s':r['worker_wall_s'],'worker_cpu_s':r['worker_cpu_s'],'peak_RSS_bytes':r['peak_RSS_bytes'],'generation':r['generation'],'ingest':r['ingest'],'snapshot_manifest':r['snapshot_manifest'],'retained_bytes':r['retained_bytes']})
 pairs=[]
 for i in (1,2,3):
  base=next(x for x in summaries if x['round']==i and x['count']==9)
  for row in [x for x in summaries if x['round']==i]:
   pairs.append({'round':i,'count':row['count'],'wall_ratio_vs9':ratio(row['median_query_producer_plus_auditor_wall_s'],base['median_query_producer_plus_auditor_wall_s']),'cpu_ratio_vs9':ratio(row['median_query_producer_plus_auditor_cpu_s'],base['median_query_producer_plus_auditor_cpu_s']),'certificate_ratio_vs9':ratio(row['median_certificate_bytes'],base['median_certificate_bytes'])})
 large=[x for x in pairs if x['count']==4096]
 H2=all(x['wall_ratio_vs9'] is not None and x['cpu_ratio_vs9'] is not None and x['wall_ratio_vs9']<=2 and x['cpu_ratio_vs9']<=2 for x in large);H3=all(x['certificate_ratio_vs9'] is not None and x['certificate_ratio_vs9']<=2 for x in large)
 return {'headline':{'H1_fixed_payload_witness_invariance':bool(H1),'H2_4096_vs9_wall_and_CPU_at_most2x_eachround':H2,'H3_4096_vs9_certificate_bytes_at_most2x_eachround':H3,'joint':bool(H1 and H2 and H3),'workers':12,'queries':96,'new_remote_model_calls':0,'new_training_runs':0,'not_acceleration_or_science_claim':True},'summaries':summaries,'paired_ratios':pairs,'CPU_zero_base_yields_null_and_gate_false':True}
