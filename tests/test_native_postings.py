import ctypes,hashlib,os,random,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.index_frame import encode,decode
from scripts.native_postings import PairReader,decode_native
from scripts.postings_transform import canonical,uvar

class NativePostingsSelectionTests(unittest.TestCase):
    def test_explicit_sha_refusal_before_library_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'not-a-library';path.write_bytes(b'owned fixture')
            with patch('scripts.native_postings.ctypes.CDLL') as loader:
                for sha in (None,'x','0'*64):
                    with self.assertRaises(ValueError):PairReader(b'abc',path,sha)
                loader.assert_not_called()
    def test_explicit_abi_refusal_without_fallback(self):
        class ABI:
            def __call__(self):return 99
        class Library:rkv_postings_abi=ABI()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'not-a-library';path.write_bytes(b'owned fixture');sha=hashlib.sha256(path.read_bytes()).hexdigest()
            with patch('scripts.native_postings.ctypes.CDLL',return_value=Library()):
                with self.assertRaisesRegex(ValueError,'ABI'):PairReader(b'abc',path,sha)

@unittest.skipUnless(os.environ.get('RKV_POSTINGS_LIBRARY'),'Explicit experimental postings native library not selected')
class NativePostingsBinaryTests(unittest.TestCase):
    def library(self):
        path=Path(os.environ['RKV_POSTINGS_LIBRARY']).resolve();return path,hashlib.sha256(path.read_bytes()).hexdigest()
    def test_fixed_goldens_maximum_u64_and_random_canonical_batches(self):
        path,sha=self.library();rng=random.Random(20261027);values=[0,1,127,128,16383,(1<<64)-1]+[rng.getrandbits(64) for _ in range(2000)];raw=b'prefix'+b''.join(uvar(v) for v in values)+b'trailing'
        reader=PairReader(raw,path,sha);got,end=reader.pairs(6,len(values)//2);self.assertEqual(list(got)[:len(values)],values);self.assertEqual(end,len(raw)-8)
        first,at=reader.pairs(6,1);self.assertEqual(list(first)[:2],values[:2]);self.assertEqual(at,8)
    def test_noncanonical_truncated_overflow_and_input_bounds(self):
        path,sha=self.library()
        for raw in (b'\x80',b'\x80\x00\x01',b'\xff'*10,b'\xff'*9+b'\x02',b'\x01'):
            with self.assertRaises(ValueError):PairReader(raw,path,sha).pairs(0,1)
        reader=PairReader(b'\x01\x02',path,sha)
        for at,count in ((-1,1),(3,1),(0,0),(0,True),(0,1000001)):
            with self.assertRaises(ValueError):reader.pairs(at,count)
    def test_all_codecs_exact_frame_identity_empty_unicode_and_plain_refusal(self):
        path,sha=self.library()
        for model in ({'shared':{'doc_lengths':{},'postings':{}}},{'shared':{'doc_lengths':{'a':3,'β':1},'postings':{'alpha':{'a':2,'β':1},'beta':{'a':1}}},'opaque':['quote " and newline\n',True,None,1.25]}):
            raw=canonical(model)
            for codec in ('raw','zlib','zstd','lzma'):
                frame,_=encode(raw,codec=codec);self.assertEqual(decode_native(frame,path,sha),decode(frame));self.assertEqual(decode_native(frame,path,sha),raw)
            with tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp);source=folder/'input.rkvpost';source.write_bytes(frame);output=folder/'restored.json';args=[sys.executable,'-m','scripts.native_postings',str(source),str(output),'--library',str(path),'--library-sha256',sha]
                result=subprocess.run(args,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(output.read_bytes(),raw)
                result=subprocess.run(args,capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertEqual(output.read_bytes(),raw)
            frame,_=encode(raw,method='plain',codec='lzma')
            with self.assertRaises(ValueError):decode_native(frame,path,sha)
    def test_corrupt_header_stored_source_sha_and_reconstruction_budget_refusal(self):
        from scripts.index_frame import HEADER,MAGIC
        path,sha=self.library();raw=canonical({'shared':{'doc_lengths':{'a'*100:1},'postings':{'alpha':{'a'*100:1}}}});frame,_=encode(raw,codec='raw')
        bad=[frame[:-1],frame+b'x',b'OTHER000'+frame[8:],frame[:-1]+bytes([frame[-1]^1])]
        header=list(HEADER.unpack_from(frame));header[3]=len(raw)-1;bad.append(HEADER.pack(*header)+frame[HEADER.size:]);header=list(HEADER.unpack_from(frame));header[6]=bytes(32);bad.append(HEADER.pack(*header)+frame[HEADER.size:])
        for value in bad:
            with self.assertRaises(ValueError):decode_native(value,path,sha)

if __name__=='__main__':unittest.main()
