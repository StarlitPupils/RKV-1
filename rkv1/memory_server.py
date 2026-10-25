"""Loopback-only evidence demo; model credentials stay in the server environment."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import threading

from .memory import Memory
from .memory_model import answer,configuration
from .context_selection import SELECTORS,BODY_BUDGETS


def serve(root,port=8765):
    if type(port) is not int or not 1024<=port<=65535:raise ValueError("Invalid demo port")
    Memory(root);lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,code,value,content="application/json; charset=utf-8"):
            raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
            self.send_response(code);self.send_header("Content-Type",content)
            self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff");self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            try:
                if self.path=="/":self.send(200,Path(__file__).with_name("memory_demo.html").read_bytes(),"text/html; charset=utf-8")
                elif self.path=="/api/status":
                    try:c=configuration();model=c["model"]
                    except ValueError:model=None
                    self.send(200,{"memory":Memory(root).stats(),"model":model,'context_api_version':2,
                        'supported_clients':['memory-v1','memory-v2'],'context_selectors':list(SELECTORS),
                        'context_body_budgets':list(BODY_BUDGETS),'default_context_selector':'source-order','default_context_body_budget':24000})
                else:self.send(404,{"error":"Unknown resource"})
            except Exception:self.send(500,{"error":"Memory status unavailable"})
        def do_POST(self):
            origin=self.headers.get("Origin")
            client=self.headers.get('X-RKV-Client')
            if (origin and origin!=f"http://127.0.0.1:{port}") or client not in ('memory-v1','memory-v2'):
                self.send(403,{"error":"Use this loopback demo page"});return
            if self.headers.get("Content-Type","").split(";")[0]!="application/json":
                self.send(415,{"error":"JSON required"});return
            try:length=int(self.headers.get("Content-Length","0"))
            except ValueError:self.send(400,{"error":"Invalid request length"});return
            if not 0<length<=16384:self.send(413,{"error":"Request too large"});return
            try:
                value=json.loads(self.rfile.read(length));q=value["question"];m=Memory(root)
                if self.path=="/api/search":self.send(200,m.search(q))
                elif self.path=="/api/answer":
                    if client!='memory-v2' and ('context_selector' in value or 'context_body_budget' in value):
                        self.send(400,{'error':'Context controls require the memory-v2 client protocol'});return
                    if not lock.acquire(blocking=False):self.send(409,{"error":"One model request is already running"});return
                    try:self.send(200,answer(m,q,context_selector=value.get('context_selector','source-order'),context_body_budget=value.get('context_body_budget',24000)))
                    finally:lock.release()
                else:self.send(404,{"error":"Unknown action"})
            except (ValueError,KeyError,TypeError):self.send(400,{"error":"Invalid query or missing model configuration"})
            except Exception:self.send(500,{"error":"Evidence verification or service request failed"})
    server=ThreadingHTTPServer(("127.0.0.1",port),Handler)
    print(f"RKV evidence demo: http://127.0.0.1:{port}",flush=True)
    try:server.serve_forever()
    finally:server.server_close()
