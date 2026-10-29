import unittest,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from unittest.mock import patch
from scripts import transport_probe as p
class Checks(unittest.TestCase):
 def test_unknown_mode_refuses_before_network(self):
  with self.assertRaises(ValueError):p.probe('unsafe')
 def test_owned_HEAD_no_auth_no_body_and_redirect_not_followed(self):
  received=[]
  class Handler(BaseHTTPRequestHandler):
   def do_HEAD(self):
    received.append((self.command,self.path,self.headers.get('Authorization'),self.headers.get('Content-Length')));self.send_response(302 if self.path=='/redirect' else 204);self.send_header('Location','/target');self.end_headers()
   def log_message(self,*a):pass
  server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever);thread.start()
  try:
   for path in ('/','/redirect'):
    with patch.object(p,'ROOT','http://127.0.0.1:'+str(server.server_port)+path),patch.dict('os.environ',{'RKV_LLM_API_KEY':'owned-not-used'}):r=p.probe('direct')
    self.assertEqual(r['model_calls'],0);self.assertFalse(r['authorization_header_sent'])
    if path=='/':self.assertTrue(r['http_response_observed']);self.assertEqual(r['status'],204)
    else:self.assertEqual(r['error_type'],'ValueError');self.assertIsNone(r['status'])
   self.assertEqual(len(received),2);self.assertFalse(any(x[1]=='/target' for x in received));self.assertTrue(all(x[0]=='HEAD' and x[2] is None and x[3] is None for x in received))
  finally:server.shutdown();server.server_close();thread.join()

 def test_fixed_six_schedule_durable_outputs_and_guard_stop(self):
  import tempfile,json
  from pathlib import Path
  calls=[]
  def fake(mode):
   calls.append(mode);return {'mode':mode,'method':'HEAD','origin':p.ROOT,'authorization_header_sent':False,'model_calls':0,'status':204,'error_type':None,'http_response_observed':True,'redirect_followed':False,'response_body_read':False,'timeout_s':15,'transport_retries':0,'wall_s':.1,'proxy_configured_for_https':False}
  with tempfile.TemporaryDirectory() as t:
   result=p.run(Path(t)/'out',transport=fake);self.assertEqual(calls,list(p.ORDER));self.assertEqual(len(result['rows']),6);self.assertEqual(len(list((Path(t)/'out').glob('request-*.json'))),6)
   def stop():raise RuntimeError('Owned quota unavailable')
   with self.assertRaises(RuntimeError):p.run(Path(t)/'stopped',guard=stop,transport=fake)
   self.assertEqual(len(calls),6);self.assertFalse(json.loads((Path(t)/'stopped/worker-finally.json').read_bytes())['success'])
