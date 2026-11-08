"""Read-only official app-server account/rateLimits/read; no model requests."""
import json
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time

def read():
    p=subprocess.Popen([shutil.which('codex'),'app-server','--stdio'],stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8')
    lines=queue.Queue()
    def reader():
        for line in p.stdout: lines.put(line)
    threading.Thread(target=reader,daemon=True).start()
    def send(obj):
        p.stdin.write(json.dumps(obj)+'\n');p.stdin.flush()
    def response(i):
        end=time.monotonic()+35
        while time.monotonic()<end:
            try: obj=json.loads(lines.get(timeout=max(.1,end-time.monotonic())))
            except queue.Empty: break
            if obj.get('id')==i:return obj
        raise TimeoutError('Read-only app-server quota response unavailable')
    try:
        send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'rkv_quota_reader','version':'1.0'}}})
        first=response(1)
        if 'error' in first:raise RuntimeError(first['error'])
        send({'method':'initialized','params':{}})
        send({'id':2,'method':'account/rateLimits/read'})
        result=response(2)
        Path('.tools/last-quota-read.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        if 'result' in result:
            value=result['result'];primary=value.get('rateLimitsByLimitId',{}).get('codex',value.get('rateLimits',{})).get('primary')
            print(json.dumps({'ordinaryUsageAllowed':value.get('ordinaryUsageAllowed'),'primary':primary}))
        else:
            print(json.dumps(result))
    finally:
        p.terminate()
        try:p.wait(timeout=3)
        except subprocess.TimeoutExpired:p.kill()

if __name__=='__main__':read()
