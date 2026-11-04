"""Private single-writer receipt preparation. No execution or replay interface.

Trust external plan/witness SHA anchors supplied by the caller. Hashes do not
authenticate a controller. No claim of directory-sync or power-loss safety.
"""
import hashlib,json,os,re,stat
from pathlib import Path
MAX_PLAN=32768
MAX_LOG=524288
MAX_ARTIFACT=1048576
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(v):
 if type(v) is not str or re.fullmatch('[0-9a-f]{64}',v) is None:raise ValueError('SHA256 required')
 return v
def regular(path):
 p=Path(path)
 for x in [p,*p.parents]:
  if x.exists() or x.is_symlink():
   s=x.lstat()
   if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024):raise ValueError('Linked/reparse paths refused')
 if not p.is_file():raise ValueError('Regular file required')
 return p
def loadraw(path,limit,meter):
 p=regular(path)
 with p.open('rb') as f:raw=f.read(limit+1)
 meter['application_read_B']+=len(raw)
 if len(raw)>limit:raise ValueError('Bounded file limit exceeded')
 return raw
def decode(raw):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('Duplicate JSON member')
   d[k]=v
  return d
 def reject(v):raise ValueError('Nonfinite JSON')
 value=json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)
 if encoded(value)!=raw:raise ValueError('Canonical JSON required')
 return value
def keys(v,expected):
 if type(v) is not dict or set(v)!=set(expected):raise ValueError('Exact schema required')
def plan_decode(raw):
 v=decode(raw);keys(v,('schema','run_id','stages','automatic_replay'))
 if type(v['schema']) is not int or v['schema']!=1 or v['automatic_replay'] is not False:raise ValueError('Plan schema differs')
 if type(v['run_id']) is not str or re.fullmatch('[a-zA-Z0-9_]{1,64}',v['run_id']) is None:raise ValueError('Safe run identity required')
 ids=v['stages']
 if type(ids) is not list or not 1<=len(ids)<=64 or any(type(i) is not str or re.fullmatch('[a-zA-Z][a-zA-Z0-9_]{0,31}',i) is None for i in ids) or len(set(ids))!=len(ids):raise ValueError('Bounded unique fixed stages required')
 return v
def exclusive(path,raw):
 with Path(path).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def create(folder,run_id,ids):
 raw=encoded({'schema':1,'run_id':run_id,'stages':ids,'automatic_replay':False});plan_decode(raw)
 if len(raw)>MAX_PLAN:raise ValueError('Plan too large')
 folder=Path(folder);folder.mkdir(exist_ok=False);(folder/'artifacts').mkdir()
 exclusive(folder/'plan.json',raw);exclusive(folder/'events.jsonl',b'');return sha(raw)
def scan(folder,plan_sha,extra=None):
 digest(plan_sha);folder=Path(folder);meter={'application_read_B':0}
 raw=loadraw(folder/'plan.json',MAX_PLAN,meter)
 if sha(raw)!=plan_sha:raise ValueError('External plan anchor differs')
 plan=plan_decode(raw);log=loadraw(folder/'events.jsonl',MAX_LOG,meter)
 if extra is not None:log+=extra
 if len(log)>MAX_LOG or log and not log.endswith(b'\n'):raise ValueError('Oversize or torn log; no completion inference')
 states={i:'unreserved' for i in plan['stages']};prev=plan_sha;records=[]
 for n,line in enumerate(log.splitlines()):
  if n>=4*len(states):raise ValueError('Too many events')
  e=decode(line);event=e.get('event') if type(e) is dict else None
  keys(e,('seq','prev','stage','event','artifact') if event=='artifact_verified' else ('seq','prev','stage','event'))
  if type(e['seq']) is not int or e['seq']!=n or digest(e['prev'])!=prev or type(e['stage']) is not str or e['stage'] not in states:raise ValueError('Invalid event binding')
  i=e['stage'];old=states[i]
  order={'reserved':'unreserved','started':'reserved','artifact_verified':'started','stage_completed':'artifact_verified'}
  if type(event) is not str or event not in order or order[event]!=old:raise ValueError('Invalid transition')
  if event=='reserved' and any(states[j]!='stage_completed' for j in plan['stages'][:plan['stages'].index(i)]):raise ValueError('Earlier stage incomplete')
  if event=='artifact_verified':
   a=e['artifact'];keys(a,('bytes','sha256'))
   if type(a['bytes']) is not int or not 0<=a['bytes']<=MAX_ARTIFACT:raise ValueError('Invalid artifact byte count')
   digest(a['sha256']);b=loadraw(folder/'artifacts'/(i+'.bin'),MAX_ARTIFACT,meter)
   if len(b)!=a['bytes'] or sha(b)!=a['sha256']:raise ValueError('Artifact identity differs')
  states[i]=event;prev=sha(line);records.append(e)
 return {'plan':plan,'plan_SHA':plan_sha,'events_SHA':sha(log),'tip_SHA':prev,'states':states,'records':records,**meter}
def inspect(folder,plan_sha,*,witness_path=None,expected_witness_SHA=None):
 if (witness_path is None)!=(expected_witness_SHA is None):raise ValueError('Both external witness path and SHA required')
 r=scan(folder,plan_sha);code=None
 if witness_path is not None:
  digest(expected_witness_SHA);meter={'application_read_B':0};raw=loadraw(witness_path,MAX_PLAN,meter);r['application_read_B']+=meter['application_read_B']
  if sha(raw)!=expected_witness_SHA:raise ValueError('External witness anchor differs')
  w=decode(raw);keys(w,('schema','run_id','plan_SHA','events_SHA','child_pid','observed_exit_code'))
  if type(w['schema']) is not int or w['schema']!=1 or w['run_id']!=r['plan']['run_id'] or w['plan_SHA']!=plan_sha or w['events_SHA']!=r['events_SHA']:raise ValueError('Witness bound to different run/plan/log')
  if type(w['child_pid']) is not int or w['child_pid']<=0 or type(w['observed_exit_code']) is not int:raise ValueError('Actual PID and integer exit required')
  code=w['observed_exit_code']
 all_stages=all(v=='stage_completed' for v in r['states'].values());locked=(Path(folder)/'writer.lock').exists()
 r.update(all_stage_footers_present=all_stages,externally_observed_exit=code,writer_lock_present=locked,campaign_complete=all_stages and code==0 and not locked,automatic_replay_permitted=False,unreserved_implies_unattempted=False,local_hash_chain_authenticates_controller=False)
 return r
def append(folder,plan_sha,stage,event,**values):
 folder=Path(folder);lock=folder/'writer.lock'
 fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);success=False
 try:
  old=scan(folder,plan_sha);e={'seq':len(old['records']),'prev':old['tip_SHA'],'stage':stage,'event':event,**values};raw=encoded(e)+b'\n'
  scan(folder,plan_sha,extra=raw)
  with (folder/'events.jsonl').open('ab') as f:
   if f.write(raw)!=len(raw):raise OSError('Partial append')
   f.flush();os.fsync(f.fileno())
  success=True
 finally:
  if success:lock.unlink()
 # Failure deliberately leaves lock and any bytes as evidence. No stale-lock recovery.
