import copy
import json
from pathlib import Path
import tempfile
import unittest
from rkv1.core import digest
from rkv1.memory import Memory
from rkv1.store import Store
from rkv1.evidence_path import trace
from scripts.cas_traffic import CASTraffic
from scripts.evidence_path_fixture import audit


class CASTrafficTests(unittest.TestCase):
    def test_real_object_bytes_decode_and_restore_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();raw=b'ABC'*300
            (src/'a.bin').write_bytes(raw);(src/'raw.bin').write_bytes(b'\x00\xff\x1a')
            store=Store.create(root/'store',compression='zlib',io_backend='bounded')
            sid=store.add(src)['snapshot_id'];ref=store.snapshot(sid).files['a.bin']['chunks'][0]
            raw_ref=store.snapshot(sid).files['raw.bin']['chunks'][0]
            size=store.object_path(ref['id']).stat().st_size+store.object_path(raw_ref['id']).stat().st_size
            meter=CASTraffic(store)
            with meter:
                self.assertEqual(store.block(ref['id'],len(raw)),raw)
                self.assertEqual(store.block(raw_ref['id'],3),b'\x00\xff\x1a')
            data=meter.result();self.assertEqual(data['application_CAS_file_bytes'],size)
            self.assertEqual(data['CAS_decoded_output_bytes'],len(raw)+3);self.assertEqual(data['decode_successes'],2)
            self.assertEqual(data['raw_codec_output_bytes'],3)
            self.assertEqual(data['compressed_decode_output_bytes'],len(raw))
            before=copy.deepcopy(data);store.block(ref['id'],len(raw))
            self.assertEqual(meter.result(),before)

    def test_corruption_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();(src/'a.bin').write_bytes(b'abc'*300)
            store=Store.create(root/'store',compression='zlib');sid=store.add(src)['snapshot_id']
            ref=store.snapshot(sid).files['a.bin']['chunks'][0];path=store.object_path(ref['id'])
            raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
            meter=CASTraffic(store)
            with meter,self.assertRaises(ValueError):store.block(ref['id'],ref['size'])
            self.assertGreater(meter.data['application_CAS_file_bytes'],0)
            self.assertEqual(meter.data['decode_successes'],0)

    def test_trace_identity_and_independent_audit_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir()
            doc={'doc_id':0,'title':'Synthetic','abstract':['RKVVALUE old']}
            (src/'records.jsonl').write_bytes(json.dumps(doc).encode()+b'\r\n')
            memory=Memory.create(root/'memory');sid=memory.add(src)['snapshot_id']
            before=trace(memory,'doc:0',snapshot=sid);meter=CASTraffic(memory.store)
            with meter:after=trace(memory,'doc:0',snapshot=sid)
            self.assertEqual(before,after)
            measured=meter.result();audit(memory,after,snapshot=sid,root_key='doc:0')
            self.assertEqual(meter.result(),measured)
            self.assertGreater(measured['CAS_decoded_output_bytes'],0)
