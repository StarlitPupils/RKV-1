import json,os,sys,threading,tempfile,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
import scripts.api_intervention as a
from tests.test_api_intervention import payload
class HTTPTests(unittest.TestCase):
 def test_actual_local_transport_raw_bytes_key_header_redirect_never_forwarded(self):
  seen=[];redirect=False
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    seen.append({'path':self.path,'authorization_ok':self.headers.get('Authorization')=='Bearer OWNED-LOCAL-TEST-TOKEN','request':json.loads(self.rfile.read(int(self.headers['Content-Length'])))})
    if redirect:
     self.send_response(302);self.send_header('Location','http://127.0.0.1:'+str(self.server.server_port)+'/must-not-receive-key');self.end_headers();return
    raw=json.dumps(payload('INSUFFICIENT',False),indent=2).encode();self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with patch.object(a,'ENDPOINT','http://127.0.0.1:'+str(server.server_port)+'/chat/completions'),patch.dict(os.environ,{'RKV_LLM_API_KEY':'OWNED-LOCAL-TEST-TOKEN'}):
    raw=a.http_transport(a.request_body('Owned claim',[]));self.assertIs(type(raw),bytes);self.assertIn(b'\n',raw);self.assertEqual(json.loads(raw)['model'],'fixture');self.assertTrue(seen[0]['authorization_ok']);self.assertNotIn('OWNED-LOCAL-TEST-TOKEN',json.dumps(seen[0]['request']))
    redirect=True
    with self.assertRaises(a.TransportPolicyError):a.http_transport(a.request_body('Owned claim',[]))
    self.assertEqual(len(seen),2);self.assertTrue(all(x['path']=='/chat/completions' for x in seen))
  finally:server.shutdown();server.server_close();thread.join(timeout=2)
if __name__=='__main__':unittest.main()
