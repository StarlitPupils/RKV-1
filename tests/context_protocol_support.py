"""Synthetic loopback contract service. It is deliberately not an answer model."""
import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import os
import socket
import subprocess
import sys
import threading
import time
from urllib.request import urlopen


def corpus():
    paragraphs=[('neutral '*2000)[:7990],('general '*3000)[:15990],
                'rareanchor protocol fixture: "quoted" snow \u96ea and caf\u00e9.']
    rows=[{'doc_id':1,'title':'Protocol fixture','abstract':paragraphs},
          {'doc_id':2,'title':'Unrelated control','abstract':['different control material.']}]
    return b''.join(json.dumps(r,ensure_ascii=False).encode()+b'\r\n' for r in rows)


class FixtureService:
    def __init__(self):self.requests=[];self.reply_mode='echo-visible'

    def __enter__(self):
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                raw=self.rfile.read(int(self.headers['Content-Length']));body=json.loads(raw)
                context=json.loads(body['messages'][1]['content'])['evidence']
                owner.requests.append({'raw':raw,'body':body,'context':context,'authorization_present':bool(self.headers.get('Authorization'))})
                citations=[]
                if context:
                    h=context[0];visible=h['sentences']
                    chosen=next((s for s in visible if 'rareanchor' in s['text']),visible[0])
                    i=99999 if owner.reply_mode=='omitted' else chosen['sentence']
                    citations=[{'citation_id':h['citation_id'],'sentence':i}]
                answer={'verdict':'SUPPORT' if citations else 'INSUFFICIENT','evidence':citations,
                        'explanation':'Synthetic protocol fixture only; no scientific answer.'}
                response={'model':'rkv-local-protocol-fixture','choices':[{'message':{'content':json.dumps(answer)},'finish_reason':'stop'}]}
                encoded=json.dumps(response).encode();self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(encoded)));self.end_headers();self.wfile.write(encoded)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.config={'base_url':self.url,'model':'rkv-local-protocol-fixture','max_tokens':256,'timeout_s':3}
        return self

    def __exit__(self,*args):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)


@contextmanager
def demo_service(memory,model_url,*,env=None,cwd=None):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    selected={k:v for k,v in (os.environ if env is None else env).items() if not k.startswith('RKV_LLM_')}
    selected.update({'RKV_LLM_BASE_URL':model_url,'RKV_LLM_MODEL':'rkv-local-protocol-fixture'})
    process=subprocess.Popen([sys.executable,'-m','rkv1','memory-serve',str(memory),'--port',str(port)],env=selected,cwd=cwd,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    base=f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            if process.poll() is not None:raise RuntimeError('Demo startup failed: '+process.stderr.read())
            try:
                with urlopen(base+'/api/status',timeout=.2) as response:status=json.load(response)
                break
            except OSError:time.sleep(.05)
        else:raise RuntimeError('Demo startup timed out')
        yield base,status
    finally:
        if process.poll() is None:process.terminate()
        try:process.communicate(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.communicate()
