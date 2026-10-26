import hashlib
from pathlib import Path
import random
import struct
import tempfile
import unittest

from rkv1 import arithmetic
from rkv1.neural_small import Predictor,model_bytes,PARAMETERS
from rkv1.neural_frame import encode,decode,HEADER,MAX_RAW


class NeuralFrameTests(unittest.TestCase):
    def test_integer_CDF_all_contexts_and_skew_arithmetic_symbol_boundaries(self):
        params=[0]*PARAMETERS;params[-256]=1280;p=Predictor(model_bytes(params))
        for context in ([256]*4,[0,255,1,128],[255]*4):
            c=p.cdf(context);self.assertEqual((c[0],c[-1]),(0,32768));self.assertTrue(all(a<b for a,b in zip(c,c[1:])))
        raw=bytes(range(256))+b'\0'*128
        payload,bits=arithmetic.encode(raw,p.cdf);self.assertEqual(arithmetic.decode(payload,bits,len(raw),p.cdf),raw)
        rng=random.Random(361);p=Predictor(model_bytes([rng.randint(-12,12) for _ in range(PARAMETERS)]))
        payload,bits=arithmetic.encode(raw,p.cdf);self.assertEqual(arithmetic.decode(payload,bits,len(raw),p.cdf),raw)
        with self.assertRaises(ValueError):arithmetic.encode(b'x',lambda context:[0]*257)

    def test_exact_all_bytes_empty_unicode_CRLF_and_deterministic_three_codecs_and_neural(self):
        model=model_bytes([0]*PARAMETERS);rng=random.Random(20261026)
        for raw in (b'',bytes(range(256)),'snow\u96ea caf\u00e9\r\n'.encode(),rng.randbytes(127)):
            for method in ('neural','zlib','zstd','lzma'):
                args={'model':model} if method=='neural' else {}
                frame,info=encode(raw,method=method,**args);self.assertEqual(decode(frame),raw)
                self.assertEqual(frame,encode(raw,method=method,**args)[0]);self.assertEqual(info['frame_bytes'],len(frame))
                self.assertEqual(info['model_raw_bytes'],len(model) if method=='neural' else 0)

    def test_corruption_truncation_trailing_bad_lengths_and_model_are_rejected(self):
        model=model_bytes([0]*PARAMETERS);frame,_=encode(b'abc\r\n',model=model)
        for damaged in (frame[:-1],frame+b'x',b'',frame[:HEADER.size]):
            with self.assertRaises(ValueError):decode(damaged)
        for index in (0,HEADER.size, len(frame)-1):
            damaged=bytearray(frame);damaged[index]^=1
            with self.assertRaises(ValueError):decode(bytes(damaged))
        fields=list(HEADER.unpack_from(frame));fields[3]=MAX_RAW+1
        with self.assertRaises(ValueError):decode(HEADER.pack(*fields)+frame[HEADER.size:])
        for invalid in (b'',model+b'x',b'wrongfmt'+model[8:]):
            with self.assertRaises(ValueError):Predictor(invalid)
        with self.assertRaises(ValueError):model_bytes([1]*(PARAMETERS-1))

    def test_no_numpy_needed_and_main_archive_rejects_experimental_magic(self):
        from rkv1.core import Archive
        frame,_=encode(b'quantized evidence',model=model_bytes([0]*PARAMETERS))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'experimental.rkvnn';path.write_bytes(frame)
            with self.assertRaises(ValueError):Archive(path)
        # This complete test suite also runs in the scientific environment without NumPy.
        self.assertEqual(decode(frame),b'quantized evidence')
