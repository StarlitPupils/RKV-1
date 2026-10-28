"""Preregistered OFF timing/RAM gates; ON only validates observer conservation."""
def ratio(a,b):return a/b if b>0 else None

def analyze(reports,parents):
 from scripts.catalog_fixture import COUNTS
 keys={(i,n,m,t) for i in (1,2,3) for n in COUNTS for m in ('fresh','pinned') for t in ('off','on')};table={(r['round'],r['count'],r['method'],r['meter']):r for r in reports}
 if len(reports)!=48 or set(table)!=keys or set(parents)!=keys:raise ValueError('Exactly48unique workers/parents required')
 same={};H1=True
 for key,r in table.items():
  if r['query_count']!=8 or [q['query_index'] for q in r['queries']]!=list(range(8)):raise ValueError('All8queries retained')
  assert parents[key]['return_code']==0 and parents[key]['error'] is None
  if r['method']=='pinned':H1 &= type(r['tracked_pinned_metadata_B']) is int and 0<r['tracked_pinned_metadata_B']<=16777216
  elif r['tracked_pinned_metadata_B'] is not None:H1=False
  if r['meter']=='off':H1 &= r['observer'] is None and all(q['observed_source_calls'] is None for q in r['queries'])
  else:
   H1 &= r['observer']['failed_constructor_calls']==0
   if r['method']=='pinned':H1 &= r['observer']['constructor_calls']==1
  for q in r['queries']:
   index=q['query_index'];support,opposite=((True,False),(False,True),(True,False),(False,False))[index%4];p,args=(('reach',['a','c']),('reach',['c','b']),('edge',['a','b']),('edge',['c','a']))[index%4]
   H1 &= q['support'] is support and q['opposite'] is opposite and q['query']=={'predicate':p,'arguments':args,'positive':True} and q['global_verdict'] is None
   identity=(q['certificate_sha256'],q['selected_payload_B'],q['auditor_API_reported_returned_B']);k=(r['count'],index)
   if k not in same:same[k]=identity
   else:H1 &= same[k]==identity
   if r['meter']=='on':H1 &= all(c['path'] in ('one.logic.jsonl','two.logic.jsonl') for c in q['observed_source_calls']) and sum(c['returned_bytes'] for c in q['observed_source_calls'])==q['selected_payload_B']+q['auditor_API_reported_returned_B']
 pairs=[];observer=[]
 for i in (1,2,3):
  for n in COUNTS:
   for t in ('off','on'):
    a=table[(i,n,'fresh',t)];b=table[(i,n,'pinned',t)];pairs.append({'round':i,'count':n,'meter':t,'batch_wall_ratio':ratio(b['batch']['wall_s'],a['batch']['wall_s']),'batch_CPU_ratio':ratio(b['batch']['cpu_s'],a['batch']['cpu_s']),'parent_wall_ratio':ratio(parents[(i,n,'pinned',t)]['parent_full_process_wall_s'],parents[(i,n,'fresh',t)]['parent_full_process_wall_s']),'peak_RSS_ratio':ratio(b['peak_RSS_B'],a['peak_RSS_B']),'pinned_tracked_metadata_B':b['tracked_pinned_metadata_B']})
   for method in ('fresh','pinned'):
    a=table[(i,n,method,'off')];b=table[(i,n,method,'on')];observer.append({'round':i,'count':n,'method':method,'ON_OFF_batchwall_ratio':ratio(b['batch']['wall_s'],a['batch']['wall_s']),'ON_OFF_batchCPU_ratio':ratio(b['batch']['cpu_s'],a['batch']['cpu_s'])})
 primary=[p for p in pairs if p['count']==4096 and p['meter']=='off'];H2=all(all(p[k] is not None and p[k]<=1 for k in ('batch_wall_ratio','batch_CPU_ratio','parent_wall_ratio')) for p in primary);H3=all(p['peak_RSS_ratio'] is not None and p['peak_RSS_ratio']<=1.25 for p in primary)
 return {'headline':{'H1_identity_payload_lifecycle_measurement':bool(H1),'H2_primary4096_meterOFF_time':H2,'H3_primary4096_meterOFF_RSS_atmost1_25':H3,'joint':bool(H1 and H2 and H3),'formal_workers':48,'queries':384,'no_compression_or_source_payload_gain':True},'pairs':pairs,'observer_ON_OFF':observer,'primary_uses_meterOFF_only':True}
