"""Fixed bookkeeping gates for seen proof transport, no favorable reruns."""
def ratio(a,b):return a/b if b>0 else None
def analyze(reports,parents,outer_bytes,dedicated_source_B,common_B):
 keys={(i,m,c) for i in (1,2,3) for m in ('plain','compact') for c in ('zstd','zlib')}
 mapping={(r['round'],r['method'],r['codec']):r for r in reports}
 if len(reports)!=12 or set(mapping)!=keys or set(parents)!=keys or set(outer_bytes)!=keys or type(dedicated_source_B) is not int or dedicated_source_B<0:raise ValueError('Exactly12workers and nonnegative full source premium required')
 identity=None;H0=True;pairs=[]
 for key,r in mapping.items():
  if r['case_count']!=96 or len(r['cases'])!=96:raise ValueError('All96roots must be retained')
  actual=[(x['id'],x['source_snapshot_id'],x['source_sha256'],x['source_bytes']) for x in r['cases']]
  if len({x[0] for x in actual})!=96:raise ValueError('Distinct case IDs required despite duplicate original bytes')
  if identity is None:identity=actual
  elif actual!=identity:raise ValueError('Same root ordering/SID/SHA required allmethods')
  H0 &= parents[key]['return_code']==0 and parents[key]['error'] is None and all(x['restored_sha256']==x['source_sha256'] and x['independent_header_catalog_mapping_and_original_DAG']['independent_header_and_catalog_mapping_verified'] and x['independent_header_catalog_mapping_and_original_DAG']['original_selected_DAG_verified'] and x['independent_header_catalog_mapping_and_original_DAG']['global_verdict'] is None for x in r['cases'])
  if r['retained_bytes']!=r['total_frame_bytes']+r['total_original_bytes']:raise ValueError('All frame+restored files must reconcile')
 for i in (1,2,3):
  for codec in ('zstd','zlib'):
   a=mapping[(i,'plain',codec)];b=mapping[(i,'compact',codec)];ka=(i,'plain',codec);kb=(i,'compact',codec);frame_delta=b['total_frame_bytes']-a['total_frame_bytes'];full_delta=b['retained_bytes']+outer_bytes[kb]-a['retained_bytes']-outer_bytes[ka]+dedicated_source_B
   pairs.append({'round':i,'codec':codec,'frame_delta_B':frame_delta,'full_conservative_listed_file_delta_B':full_delta,'candidate_dedicated_source_premium_B':dedicated_source_B,'plain_complete_listed_B':common_B+a['retained_bytes']+outer_bytes[ka],'compact_complete_listed_B':common_B+b['retained_bytes']+outer_bytes[kb]+dedicated_source_B,'worker_wall_ratio':ratio(b['worker_wall_s'],a['worker_wall_s']),'worker_CPU_ratio':ratio(b['worker_cpu_s'],a['worker_cpu_s']),'parent_wall_ratio':ratio(parents[kb]['parent_full_process_wall_s'],parents[ka]['parent_full_process_wall_s'])})
 primary=[p for p in pairs if p['codec']=='zstd'];H1=all(x['full_conservative_listed_file_delta_B']<0 for x in primary);H2=all(all(x[k] is not None and x[k]<=1. for k in ('worker_wall_ratio','worker_CPU_ratio','parent_wall_ratio')) for x in primary)
 return {'headline':{'H0_all1152_exact_original_and_independent_DAG':bool(H0),'H1_primary_Zstd_full_conservative_listed_file_B':H1,'H2_primary_workerwall_CPU_parentwall':H2,'joint':bool(H0 and H1 and H2),'formal_workers':12,'restored_roots':1152,'seen_representation_only_no_new_science':True},'pairs':pairs,'common_listed_source_context_input_B':common_B,'all_dedicated_new_source_premium_B':dedicated_source_B,'unallocated_OS_allocator_directory_metadata_not_zero':True}
