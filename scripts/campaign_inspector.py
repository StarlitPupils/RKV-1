"""Private candidate: inspect-only; never imports or calls a model transport."""
import json,hashlib,re
from pathlib import Path

def digest(b):return hashlib.sha256(b).hexdigest()
def read(p):
 def unique(pairs):
  out={}
  for k,v in pairs:
   if k in out:raise ValueError('Duplicate field')
   out[k]=v
  return out
 return json.loads(p.read_bytes(),object_pairs_hook=unique)
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def inspect(folder,planned=48):
 folder=Path(folder)
 if planned!=48:raise ValueError('Fixed48planned slots required')
 if not folder.is_dir():return {'state':'no_campaign','model_send_allowed':False,'reserved':0,'results':0,'responses':0}
 for p in folder.iterdir():
  if p.name.startswith('slot-'):
   m=re.fullmatch(r'slot-([0-9]{2})\.(reserved\.json|request-private\.json|response-private\.bin|result\.json)',p.name)
   if not m or int(m[1])>=48 or not p.is_file() or p.is_symlink():raise ValueError('Unknown or unsafe slot file')
 files={p.name:{'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in folder.iterdir() if p.is_file()};reserved=results=responses=0;ambiguous=[]
 for i in range(48):
  stem='slot-'+str(i).zfill(2);reservation=folder/(stem+'.reserved.json');result=folder/(stem+'.result.json');response=folder/(stem+'.response-private.bin');request=folder/(stem+'.request-private.json')
  if not reservation.exists():
   if result.exists() or response.exists():raise ValueError('Output without reservation')
   continue
  reserved+=1;r=read(reservation)
  if type(r['index'])is not int or r['index']!=i or type(r['reserved_UTC_ns'])is not int or r['reserved_UTC_ns']<=0 or len(canonical(read(request)))!=r['request_B'] or digest(canonical(read(request)))!=r['request_sha256']:raise ValueError('Reservation/request identity mismatch')
  if response.exists():responses+=1
  if result.exists():
   v=read(result);results+=1
   if type(v['accepted'])is not bool or type(v['index'])is not int or v['index']!=i or v['request_sha256']!=r['request_sha256'] or v['job']!=r['job']:raise ValueError('Result identity mismatch')
   if response.exists() and (digest(response.read_bytes())!=v.get('response_SHA') or response.stat().st_size!=v.get('response_B')):raise ValueError('Response identity mismatch')
   if v['accepted'] and not response.exists():raise ValueError('Accepted without raw response')
  else:ambiguous.append(i)
 final=folder/'campaign-final.json';state='open_no_reservations' if not reserved else ('open_ambiguous' if ambiguous else 'open_outputs_no_final')
 if final.exists():
  f=read(final)
  if type(f['planned_calls'])is not int or type(f['attempted_calls'])is not int or type(f['missing_planned_calls'])is not int or f['planned_calls']!=48 or f['attempted_calls']!=reserved or f['missing_planned_calls']!=48-reserved or type(f['complete'])is not bool or f['complete']!=(reserved==48):raise ValueError('Final denominator mismatch')
  if results!=reserved or ambiguous:raise ValueError('Closed final lacks complete results')
  state='closed_complete' if f['complete'] else 'closed_incomplete'
 identity=digest(canonical({k:v for k,v in files.items() if k!='report-identity.json'}));report=folder/'report-identity.json';report_bound=False
 if report.exists():
  marker=read(report)
  if not final.exists() or set(marker)!={'campaign_identity_sha256','mechanical_marker_not_scientific_audit'} or marker['mechanical_marker_not_scientific_audit'] is not True or marker['campaign_identity_sha256']!=identity:raise ValueError('Report marker identity mismatch')
  report_bound=True;state+='_report_bound'
 return {'campaign_identity_sha256':identity,'report_identity_verified':report_bound,'state':state,'planned':48,'reserved':reserved,'results':results,'responses':responses,'ambiguous':ambiguous,'unreserved':48-reserved,'model_send_allowed':False,'file_ledger':files}


def write_report_marker(folder):
 folder=Path(folder);state=inspect(folder)
 if not state['state'].startswith('closed_'):raise ValueError('No report-only closure before campaign final')
 if state['report_identity_verified']:return {'already_bound':True,'model_send_allowed':False}
 marker={'campaign_identity_sha256':state['campaign_identity_sha256'],'mechanical_marker_not_scientific_audit':True}
 import os
 with (folder/'report-identity.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(marker,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 assert inspect(folder)['report_identity_verified'];return {'already_bound':False,'model_send_allowed':False}
