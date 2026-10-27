import hashlib,json,struct,unittest
from scripts.postings_transform import canonical,forward,inverse,uvar,read_uvar,MAX_RAW,MAX_TF
from scripts.index_frame import encode,decode,HEADER,MAX_PAYLOAD

class IndexFrameTests(unittest.TestCase):
    def model(self):return {'shared':{'doc_lengths':{'a':3,'b':1},'postings':{'x':{'a':2,'b':1},'y':{'a':1}}},'sentinel':'β','opaque':{'float':1.25,'null':None,'boolean':True}}
    def test_unsigned_varints_golden_and_malformed(self):
        for value,raw in ((0,b'\x00'),(127,b'\x7f'),(128,b'\x80\x01'),(16383,b'\xff\x7f'),(16384,b'\x80\x80\x01'),((1<<64)-1,b'\xff'*9+b'\x01')):
            self.assertEqual(uvar(value),raw);self.assertEqual(read_uvar(raw,0),(value,len(raw)))
        for raw in (b'',b'\x80',b'\x80\x00',b'\xff'*10,b'\x80'*10+b'\x01'):
            with self.assertRaises(ValueError):read_uvar(raw,0)
        for value in (-1,True,1<<64,1.1):
            with self.assertRaises(ValueError):uvar(value)
    def test_typed_payload_literal_golden_and_exact_original(self):
        obj=self.model();raw=canonical(obj);meta={**obj,'shared':{**obj['shared'],'postings':{}}};meta_raw=canonical(meta)
        expected=uvar(len(meta_raw))+meta_raw+b'\x02\x02\x03'+b'\x01x\x02\x01\x02\x01\x01'+b'\x01y\x01\x01\x01'
        payload,stats=forward(raw);self.assertEqual(payload,expected);self.assertEqual(stats['posting_pairs'],3);self.assertEqual(inverse(payload,len(raw)),raw)
    def test_all_methods_codecs_unicode_and_empty_postings(self):
        models=(self.model(),{'shared':{'doc_lengths':{},'postings':{}},'other':['line\nquote "','汉字😀']},
            {'shared':{'doc_lengths':{'doc " β':1},'postings':{'token\\汉':{'doc " β':1}}}})
        for obj in models:
            raw=canonical(obj)
            for method in ('plain','typed'):
                for codec in ('raw','zlib','zstd','lzma'):
                    frame,stats=encode(raw,method=method,codec=codec);self.assertEqual(decode(frame),raw);self.assertEqual(stats['frame_bytes'],len(frame))
    def test_typed_rejects_noncanonical_bad_schema_duplicate_and_frequency(self):
        bad=[json.dumps(self.model(),indent=2).encode(),b'{"shared":{},"shared":{}}',b'{"v":NaN}',b'{"v":1e9999}',b'[]']
        for tf in (True,0,MAX_TF+1,1.5):bad.append(canonical({'shared':{'doc_lengths':{'a':1},'postings':{'x':{'a':tf}}}}))
        bad.append(canonical({'shared':{'doc_lengths':{},'postings':{'x':{'unknown':1}}}}))
        for raw in bad:
            with self.assertRaises(ValueError):forward(raw)
        raw=b' noncanonical arbitrary raw bytes '
        self.assertEqual(decode(encode(raw,method='plain',codec='zlib')[0]),raw)
    def test_header_lengths_three_SHA_trailing_and_corruption_refuse(self):
        frame,_=encode(canonical(self.model()),codec='zlib');h=list(HEADER.unpack_from(frame));stored=frame[HEADER.size:]
        for invalid in (frame[:-1],frame+b'X',frame[:HEADER.size-1],frame[:-1]+bytes([frame[-1]^1])):
            with self.assertRaises(ValueError):decode(invalid)
        for field,value in ((0,b'WRONG!!!'),(1,2),(2,255),(3,MAX_RAW+1),(4,MAX_PAYLOAD+1),(5,len(stored)+1),(6,b'\x00'*32),(7,b'\x00'*32),(8,b'\x00'*32)):
            changed=h.copy();changed[field]=value
            with self.assertRaises(ValueError):decode(HEADER.pack(*changed)+stored)
    def test_single_codec_frame_only_even_self_consistent_stored_hash(self):
        from scripts.index_frame import _compress
        for codec in ('zlib','zstd','lzma'):
            frame,_=encode(canonical(self.model()),codec=codec);h=list(HEADER.unpack_from(frame));stored=frame[HEADER.size:]+_compress(b'extra unwanted frame',codec)
            h[5]=len(stored);h[8]=hashlib.sha256(stored).digest()
            with self.assertRaises(ValueError):decode(HEADER.pack(*h)+stored)
    def test_original_size_bound_precedes_repeated_ID_expansion(self):
        meta={'shared':{'doc_lengths':{'a'*1000:1},'postings':{}}};metadata=canonical(meta)
        payload=uvar(len(metadata))+metadata+b'\x01\x01\x01'+b'\x01x\x01\x01\x01'
        with self.assertRaisesRegex(ValueError,'Restored JSON would exceed'):inverse(payload,len(metadata)+10)
    def test_typed_EOF_order_counts_and_zero_document_delta_refuse(self):
        raw=canonical(self.model());payload,_=forward(raw);meta_len,at=read_uvar(payload,0);header_end=at+meta_len
        variants=[payload+b'X',payload[:-1],payload[:header_end]+b'\x03'+payload[header_end+1:]]
        # Literal golden last posting doc delta 1 -> forbidden zero.
        variants.append(payload[:-2]+b'\x00'+payload[-1:])
        for bad in variants:
            with self.assertRaises(ValueError):inverse(bad,len(raw))
    def test_distinct_text_frame_and_existing_public_API_refuse(self):
        import tempfile
        from pathlib import Path
        from rkv1.text_frame import encode as old_encode,decode as old_decode
        from rkv1.experiments.paper_retriever import PaperRetriever
        raw=canonical(self.model());frame,_=encode(raw,codec='zlib');old,_=old_encode(raw,codec='zlib',mode='plain')
        with self.assertRaises(ValueError):old_decode(frame)
        with self.assertRaises(ValueError):decode(old)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'index.rkvpost';path.write_bytes(frame)
            with self.assertRaises(ValueError):PaperRetriever(root/'not-a-store','0'*64,path,model_sha256=hashlib.sha256(frame).hexdigest())

if __name__=='__main__':unittest.main()
