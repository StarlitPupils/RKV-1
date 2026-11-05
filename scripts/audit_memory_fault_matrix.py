"""Post-output original-source audit and separately copied corruption controls."""
import copy,hashlib,json,shutil
from pathlib import Path
from rkv1.memory import Memory
from scripts.execution_receipts import inspect
from scripts.memory_fault_fixture import file_ledger,audit_result

def audit(root,out,*,expected_originals):
 root,out=Path(root),Path(out);out.mkdir(exist_ok=False);before=file_ledger(root)
 summary=json.loads((root/'summary.json').read_bytes());rows=summary['rows'];n=summary['size']
 phases=('after_first_object','after_snapshot','after_index','before_HEAD','after_HEAD','success')
 if len(rows)!=6 or [r['phase'] for r in rows]!=list(phases):raise ValueError('Fixed case order differs')
 restores=queries=source_return=0;controls=[]
 for row in rows:
  folder=root/row['phase'];raws={}
  for epoch in (0,1):
   raw=(folder/'originals'/f'{epoch}.jsonl').read_bytes()
   if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=expected_originals[str(n)+':'+str(epoch)]:raise ValueError('External original fixture differs')
   raws[epoch]=raw
  memory=Memory(folder/'memory');epoch=1 if row['phase'] in ('after_HEAD','success') else 0
  if memory.current()!=row['visible_sid'] or row['visible_source_epoch']!=epoch:raise ValueError('Visible HEAD differs')
  for filename,sid,e in [('current-query.json',row['visible_sid'],epoch),('old-query.json',row['old_sid'],0)]+([('explicit-new-query.json',row['known_new_sid'],1)] if row['phase'] in ('after_index','before_HEAD','after_HEAD','success') else []):
   result=json.loads((folder/filename).read_bytes());v=audit_result(memory,result,raws[e],sid);source_return+=v['source_application_return_B'];restores+=1;queries+=1
  if row['phase']=='after_snapshot':
   with memory.store.snapshot(row['known_new_sid']) as snap:raw=snap.read_range('corpus.jsonl')
   if raw!=raws[1]:raise ValueError('Published new raw snapshot differs before index')
   source_return+=len(raw);restores+=1
   try:memory.search('RKV97PROBE',snapshot=row['known_new_sid'])
   except FileNotFoundError:pass
   else:raise ValueError('Unindexed source queried')
  parent=json.loads((root/(row['phase']+'-parent.json')).read_bytes())
  if parent!=row['parent']:raise ValueError('Parent receipt differs')
  witness=folder/'parent-witness.json';plan_sha=hashlib.sha256((folder/'receipts'/'plan.json').read_bytes()).hexdigest()
  w=json.loads(witness.read_bytes())
  if w['child_pid']!=parent['actual_producer_pid'] or w['observed_exit_code']!=parent['producer_observed_exit_code']:raise ValueError('Producer witness mismatch')
  receipt=inspect(folder/'receipts',plan_sha,witness_path=witness,expected_witness_SHA=hashlib.sha256(witness.read_bytes()).hexdigest())
  if receipt['campaign_complete']!=(row['phase']=='success') or row['operation_receipt_complete']!=receipt['campaign_complete']:raise ValueError('Operation completion conflates HEAD visibility')
  original=json.loads((root/(row['phase']+'-baseline-identities.json')).read_bytes());now=file_ledger(folder/'memory')
  for name,v in original.items():
   if name!='HEAD.json' and now[name]!=v:raise ValueError('Old immutable file changed')
  if epoch==0 and original['HEAD.json']!=now['HEAD.json']:raise ValueError('HEAD changed before publication')
 success=rows[-1];origin=root/'success';old_sid=success['old_sid'];original_raw=(origin/'originals'/'0.jsonl').read_bytes()
 corrupt=out/'bad-selected-CAS';shutil.copytree(origin/'memory',corrupt);m=Memory(corrupt)
 with m.store.snapshot(old_sid) as snap:key=snap.header['files'][0]['chunks'][0]['id']
 path=m.store.object_path(key);b=bytearray(path.read_bytes());b[-1]^=1;path.write_bytes(b)
 try:m.search('RKV97PROBE',snapshot=old_sid)
 except ValueError:controls.append('selected_original_CAS_corruption_refused')
 else:raise ValueError('Corrupt source accepted')
 p=out/'bad-HEAD';shutil.copytree(origin/'memory',p);(p/'HEAD.json').write_bytes(b'{"version":1,"snapshot_id":"'+b'0'*64+b'"}')
 try:Memory(p).search('RKV97PROBE')
 except FileNotFoundError:controls.append('missing_HEAD_manifest_query_refused')
 else:raise ValueError('Missing HEAD source substituted')
 result=json.loads((origin/'old-query.json').read_bytes());bad=copy.deepcopy(result);bad['hits'][0]['sentences'][0]='changed owned text'
 with (out/'bad-returned-query.json').open('x',encoding='utf-8') as stream:json.dump(bad,stream,ensure_ascii=False,indent=2)
 try:audit_result(Memory(origin/'memory'),bad,original_raw,old_sid)
 except ValueError:controls.append('literal_query_evidence_tamper_refused')
 else:raise ValueError('Query evidence tamper accepted')
 if file_ledger(root)!=before:raise ValueError('Original workload changed by audit')
 answer={'size':n,'cases':6,'queries_verified':queries,'whole_source_restores':restores,'source_application_return_B':source_return,'corruption_controls':controls,'control_whole_source_restores':1,'control_source_application_return_B':len(original_raw),'additional_source_query_refusal_attempts':3,'all_original_files_unchanged':True,'no_update_replay':True,'source_availability_not_entailment':True}
 with (out/'audit.json').open('x',encoding='utf-8') as f:json.dump(answer,f,indent=2)
 return answer
