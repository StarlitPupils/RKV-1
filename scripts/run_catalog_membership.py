"""Experimental fixed known-owned membership component worker, no science or standalone SID claim."""
import argparse,atexit,copy,json,time,sys
from pathlib import Path
from rkv1.store import Store
from rkv1.core import digest
from rkv1.benchmark import peak_rss
from scripts.postings_transform import canonical
from scripts.catalog_fixture import sources,COUNTS,PATHS
from scripts.selected_witness import catalog
from scripts.catalog_commitment import from_store
from scripts.audit_catalog_commitment import verify

def size(value,seen=None):
 seen=set() if seen is None else seen
 if id(value) in seen:return 0
 seen.add(id(value));n=sys.getsizeof(value)
 if isinstance(value,dict):return n+sum(size(k,seen)+size(v,seen) for k,v in value.items())
 if isinstance(value,(list,tuple)):return n+sum(size(v,seen) for v in value)
 return n

def run(work,count,round_number):
 if type(count) is not int or count not in COUNTS or type(round_number) is not int or round_number not in (1,2,3):raise ValueError('Fixed geometry required')
 start=time.perf_counter();cpu=time.process_time();work.mkdir(exist_ok=False);status={'success':False}
 def done():
  with (work/'finally-timing.json').open('x',encoding='utf-8') as f:json.dump({**status,'worker_full_wall_s':time.perf_counter()-start,'worker_full_cpu_s':time.process_time()-cpu,'peak_RSS_B':peak_rss()},f,indent=2);f.write('\n')
 atexit.register(done);src=work/'source';src.mkdir();expected=sources(count)
 for n,b in expected.items():(src/n).write_bytes(b)
 store=Store.create(work/'store',compression='zlib');sid=store.add(src)['snapshot_id'];t=time.perf_counter();c=time.process_time();tree=from_store(store,sid);build={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c}
 anchor=copy.deepcopy(tree.anchor);trusted=tree.anchor_sha256;proofs={p:tree.proof(p) for p in PATHS};records=[];application_B=0;t=time.perf_counter();c=time.process_time()
 with store.snapshot(sid) as snap:
  for path in PATHS:
   raw=snap.read_range(path);result=verify(anchor,proofs[path],raw,expected_anchor_sha256=trusted,expected_snapshot_id=sid,expected_path=path,source_byte_budget=1048576);assert result['original_selected_bytes_membership_verified'] and not result['full_eligible_coverage_verified'];application_B+=len(raw);records.append({'path':path,'bytes':len(raw),'sha256':digest(raw),'proof_sha256':digest(canonical(proofs[path]))})
 validation={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c};path=PATHS[0];base=proofs[path];raw=expected[path];controls=[]
 changes=[('wrong_index',lambda p:p.update(leaf_index=(p['leaf_index']+1)%count)),('wrong_entry_SHA',lambda p:p['entry'].update(sha256='0'*64)),('truncated_path',lambda p:p['siblings'].pop()),('trailing_path',lambda p:p['siblings'].append('0'*64)),('bool_index',lambda p:p.update(leaf_index=True)),('wrong_SID',lambda p:p.update(snapshot_id='0'*64))]
 for name,mutate in changes:
  bad=copy.deepcopy(base);mutate(bad)
  try:verify(anchor,bad,raw,expected_anchor_sha256=trusted,expected_snapshot_id=sid,expected_path=path)
  except ValueError:controls.append(name)
  else:raise AssertionError('Accepted '+name)
 for name,payload,budget in (('wrong_original_bytes',raw+b'!',1048576),('zero_payload_budget',raw,0)):
  try:verify(anchor,base,payload,expected_anchor_sha256=trusted,expected_snapshot_id=sid,expected_path=path,source_byte_budget=budget)
  except ValueError:controls.append(name)
  else:raise AssertionError('Accepted '+name)
 (src/'notes.txt').write_bytes(b'Owned new HEAD notes; eligible payload is unchanged')
 new_sid=store.add(src)['snapshot_id'];new_tree=from_store(store,new_sid);assert new_sid!=sid and new_tree.anchor['root_sha256']==anchor['root_sha256'] and new_tree.anchor_sha256!=trusted
 assert verify(anchor,base,raw,expected_anchor_sha256=trusted,expected_snapshot_id=sid,expected_path=path)['original_selected_bytes_membership_verified']
 try:verify(new_tree.anchor,base,raw,expected_anchor_sha256=new_tree.anchor_sha256,expected_snapshot_id=new_sid,expected_path=path)
 except ValueError:pass
 else:raise AssertionError('Old proof rebound to new HEAD')
 old=catalog(store,sid,PATHS,1048576);packet={'anchor':anchor,'members':[proofs[p] for p in PATHS]};index={'anchor':anchor,'records':tree.records,'nodes':[[lo,n,v.hex()] for (lo,n),v in sorted(tree._nodes.items())]}
 batch={'anchor':anchor,'messages':[{'query_index':j,'anchor_sha256':trusted,'members':[proofs[p] for p in PATHS]} for j in range(8)]};baseline_batch={'messages':[{'query_index':j,'catalogue':old} for j in range(8)]}
 for name,value in (('packet.json',packet),('index.json',index),('baseline-catalogue.json',old),('candidate-batch.json',batch),('baseline-batch.json',baseline_batch)):
  with (work/name).open('xb') as f:f.write(canonical(value)+b'\n')
 for i,path in enumerate(PATHS):
  with (work/('member-'+str(i)+'.json')).open('xb') as f:f.write(canonical(proofs[path])+b'\n')
 assert len(records)==2 and len(controls)==8
 allfiles={p.relative_to(work).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in work.rglob('*') if p.is_file()};status['success']=True
 return {'round':round_number,'count':count,'snapshot_id':sid,'new_HEAD_snapshot_id':new_sid,'trusted_anchor_sha256':trusted,'records':records,'controls':controls,'oldSID_preserved_newHEAD_rebinding_rejected':True,'build_full_metadata_and_tree':build,'selected_verify':validation,'selected_source_application_returned_B':application_B,'one_packet_B':len(canonical(packet)),'one_baseline_catalogue_B':len(canonical(old)),'anchor_once_B':len(canonical(anchor)),'two_member_proofs_B':sum(len(canonical(p)) for p in proofs.values()),'retained_index_file_B':len(canonical(index))+1,'fixed8_candidate_metadata_batch_B':len(canonical(batch)),'fixed8_baseline_metadata_batch_B':len(canonical(baseline_batch)),'tracked_extra_tree_metadata_B':size((tree.records,tree._nodes,tree._positions,tree.anchor)),'peak_RSS_B':peak_rss(),'all_worker_files_before_finally':allfiles,'retained_B_before_finally':sum(e['bytes'] for e in allfiles.values()),'retries':0,'logic_DAG_or_science_verified':False,'new_model_calls':0}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--count',type=int,required=True);p.add_argument('--round',type=int,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=run(a.work,a.count,a.round)
 with a.report.open('xb') as f:f.write(canonical(r)+b'\n')
