"""Unauthenticated fixed-origin HEAD observability; no model endpoint, no key reads."""
import time
from urllib.request import Request,build_opener,ProxyHandler,getproxies
from urllib.error import HTTPError
from rkv1.memory_model import NoRedirect
ROOT='https://api.deepseek.com/'
def probe(mode):
 if mode not in ('system','direct'):raise ValueError('Unknown route')
 opener=build_opener(ProxyHandler({}) if mode=='direct' else ProxyHandler(),NoRedirect());started=time.perf_counter();result={'mode':mode,'method':'HEAD','origin':ROOT,'authorization_header_sent':False,'model_calls':0,'status':None,'error_type':None,'http_response_observed':False,'proxy_configured_for_https':bool(getproxies().get('https')) if mode=='system' else False,'response_body_read':False,'redirect_followed':False,'timeout_s':15,'transport_retries':0}
 try:
  with opener.open(Request(ROOT,method='HEAD'),timeout=15) as response:result['status']=response.status;result['http_response_observed']=True
 except HTTPError as e:result['status']=e.code;result['error_type']=type(e).__name__;result['http_response_observed']=True
 except Exception as e:result['error_type']=type(e).__name__
 result['wall_s']=time.perf_counter()-started;return result

ORDER=('system','direct','direct','system','system','direct')
def run(out,guard=None,transport=None):
 import json,os
 from pathlib import Path
 from rkv1.benchmark import peak_rss
 out=Path(out);out.mkdir(exist_ok=False);start=time.perf_counter();cpu=time.process_time();success=False;rows=[]
 def write(name,v):
  with (out/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 try:
  for index,mode in enumerate(ORDER):
   if guard:guard()
   row={'index':index,'round':index//2+1,**(probe(mode) if transport is None else transport(mode))};assert row['mode']==mode and row['origin']==ROOT and row['method']=='HEAD' and row['authorization_header_sent'] is False and row['model_calls']==0 and row['redirect_followed'] is False;write('request-'+str(index)+'.json',row);rows.append(row)
  result={'planned_requests':6,'attempted_requests':len(rows),'complete':len(rows)==6,'rows':rows,'new_model_API_calls':0,'no_causal_diagnosis_of_past_failure':True};write('worker.json',result);success=True;return result
 finally:write('worker-finally.json',{'success':success,'body_wall_s':time.perf_counter()-start,'body_CPU_s':time.process_time()-cpu,'peak_RSS_B':peak_rss()})
