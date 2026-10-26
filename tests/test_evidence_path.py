import json
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rkv1.memory import Memory
from rkv1.evidence_path import trace
from scripts.evidence_path_fixture import audit


class EvidencePathTests(unittest.TestCase):
    def test_independent_original_record_audit_rejects_rehashed_quote(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir()
            doc={'doc_id':0,'title':'Synthetic','abstract':['RKVVALUE caf'+chr(233)+' '+chr(38634)]}
            raw=json.dumps(doc,ensure_ascii=True).encode()+b'\r\n'
            (src/'records.jsonl').write_bytes(raw)
            memory=Memory.create(root/'memory');sid=memory.add(src)['snapshot_id']
            proof=trace(memory,'doc:0',snapshot=sid)
            self.assertEqual(audit(memory,proof,snapshot=sid,root_key='doc:0')['bindings'],1)
            self.assertNotIn(proof['evidence'][0]['quote'].encode('utf-8'),raw)
            bad=copy.deepcopy(proof);hop=bad['evidence'][0];hop['quote']+=' changed'
            from rkv1.core import digest
            hop['quote_utf8_sha256']=digest(hop['quote'].encode())
            with self.assertRaises(ValueError):audit(memory,bad,snapshot=sid,root_key='doc:0')
    def test_snapshot_bound_path_and_missing_current_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();path=src/'records.jsonl'
            docs=[{'doc_id':i,'title':'Synthetic experiment','abstract':[line]}
                  for i,line in enumerate(('RKVNEXT doc:1','RKVNEXT doc:2','RKVVALUE old café 雪'))]
            def write():path.write_bytes(b''.join(json.dumps(d,ensure_ascii=True).encode()+b'\r\n' for d in docs))
            write();memory=Memory.create(root/'memory');old=memory.add(src)['snapshot_id']
            result=trace(memory,'doc:0',snapshot=old)
            self.assertEqual((result['status'],result['value']),('complete','old café 雪'))
            self.assertEqual(len(result['evidence']),3)
            self.assertTrue(all(h['locator']['snapshot_id']==old for h in result['evidence']))
            docs[2]['abstract']=['RKVVALUE new'];write();new=memory.add(src)['snapshot_id']
            self.assertEqual(trace(memory,'doc:0',snapshot=new)['value'],'new')
            self.assertEqual(trace(memory,'doc:0',snapshot=old)['value'],'old café 雪')
            docs.pop();write();deleted=memory.add(src)['snapshot_id']
            result=trace(memory,'doc:0',snapshot=deleted)
            self.assertEqual(result['status'],'missing');self.assertIsNone(result['value'])
            self.assertEqual(trace(memory,'doc:0',snapshot=old)['status'],'complete')

    def test_explicit_limits_cycles_and_wrong_binding(self):
        class Fixture:
            def lookup(self,key,*,snapshot):
                quote='RKVNEXT doc:0'
                return {'snapshot_id':snapshot,'hits':[{'key':key,'sentences':[quote],
                     'source_bytes_verified':True,'locator':{'snapshot_id':snapshot,'length':100}}]}
        sid='a'*64;m=Fixture()
        self.assertEqual(trace(m,'doc:0',snapshot=sid)['status'],'cycle')
        result=trace(m,'doc:0',snapshot=sid,max_evidence_bytes=99)
        self.assertEqual(result['status'],'budget');self.assertEqual(result['evidence'],[])
        self.assertEqual((result['verified_record_bytes'],result['admitted_record_bytes']),(100,0))
        self.assertEqual(trace(m,'doc:0',snapshot=sid,max_hops=1)['status'],'hop-limit')
        bad=m.lookup('doc:0',snapshot=sid);bad['hits'][0]['locator']['snapshot_id']='b'*64
        with patch.object(m,'lookup',return_value=bad),self.assertRaises(ValueError):trace(m,'doc:0',snapshot=sid)
        for kwargs in ({'snapshot':None},{'snapshot':sid,'max_hops':True},{'snapshot':sid,'max_evidence_bytes':0}):
            with self.assertRaises(ValueError):trace(m,'doc:0',**kwargs)
