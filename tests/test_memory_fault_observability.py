import copy,json,tempfile,unittest
from pathlib import Path
from rkv1.memory import Memory
from scripts.memory_fault_fixture import source,audit_result,sha
from scripts.run_memory_fault_matrix import run,Producer
from scripts.audit_memory_fault_matrix import audit

class MemoryFaultObservabilityTests(unittest.TestCase):
 def test_six_real_memory_cases_and_three_source_controls(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);run(root/'matrix');v=json.loads((root/'matrix'/'summary.json').read_bytes())
   self.assertEqual([r['visible_source_epoch'] for r in v['rows']],[0,0,0,0,1,1])
   self.assertEqual([r['operation_receipt_complete'] for r in v['rows']],[False]*5+[True])
   expected={f'9:{e}':{'bytes':len(source(9,e)),'sha256':sha(source(9,e))} for e in (0,1)}
   checked=audit(root/'matrix',root/'audit',expected_originals=expected)
   self.assertEqual(checked['queries_verified'],16);self.assertEqual(checked['whole_source_restores'],17);self.assertEqual(len(checked['corruption_controls']),3)
 def test_external_fixture_wrong_sha_refuses(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'matrix';p.mkdir();(p/'after_first_object'/'originals').mkdir(parents=True)
   rows=[{'phase':x} for x in ('after_first_object','after_snapshot','after_index','before_HEAD','after_HEAD','success')]
   (p/'summary.json').write_text(json.dumps({'size':9,'rows':rows}),encoding='utf-8');(p/'after_first_object'/'originals'/'0.jsonl').write_bytes(source(9,0))
   with self.assertRaisesRegex(ValueError,'External original fixture'):audit(p,Path(td)/'audit',expected_originals={'9:0':{'bytes':len(source(9,0)),'sha256':'0'*64}})
 def test_literal_and_duplicate_hit_refuse(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'source').mkdir();raw=source(9,0);(p/'source'/'corpus.jsonl').write_bytes(raw);m=Memory.create(p/'memory');sid=m.add(p/'source')['snapshot_id'];r=m.search('RKV97PROBE',top_k=8)
   audit_result(m,r,raw,sid);bad=copy.deepcopy(r);bad['hits'][0]['sentences'][0]='changed'
   with self.assertRaises(ValueError):audit_result(m,bad,raw,sid)
   bad=copy.deepcopy(r);bad['hits'].append(bad['hits'][0])
   with self.assertRaises(ValueError):audit_result(m,bad,raw,sid)
 def test_kill_interface_refuses_parent_and_invalid_sizes(self):
  import os
  for pid in (0,False,os.getpid()):
   with self.assertRaises(ValueError):Producer(pid,None)
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(ValueError):run(Path(td)/'bad',True)
   self.assertFalse((Path(td)/'bad').exists())
