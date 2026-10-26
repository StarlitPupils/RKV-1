import unittest
import tempfile
from pathlib import Path
from rkv1.core import Archive
from rkv1.online_counts import Predictor,RULE_SHA
from rkv1.online_frame import encode,decode,HEADER
from rkv1.neural_frame import decode as previous_decode


class OnlineTests(unittest.TestCase):
    def test_past_update_timing_and_counts(self):
        p=Predictor(1)
        self.assertEqual(p.cdf([256]*4),list(range(0,32769,128)))
        p.cdf([256,256,256,65])
        self.assertEqual(p.counts[256][65],3)
        self.assertEqual(p.counts[65][65],1)
        p.cdf([256,256,65,65])
        self.assertEqual(p.counts[65][65],3)
        self.assertEqual(p.accounting()['logical_state_bytes'],132612)
        self.assertEqual(Predictor(0).accounting()['logical_state_bytes'],516)

    def test_bounded_state_rescale_and_exact_stream(self):
        p=Predictor(0)
        p.cdf([256]*4)
        for _ in range(16257):p.cdf([0]*4)
        self.assertEqual(p.rescales,1)
        self.assertEqual(p.totals[0],sum(p.counts[0]))
        self.assertLessEqual(p.totals[0],32768)
        q=Predictor(1)
        q.cdf([256]*4)
        for _ in range(16257):q.cdf([0]*4)
        self.assertEqual(q.rescales,1)
        self.assertEqual(q.totals[0],sum(q.counts[0]))
        frame,_=encode(b'\0'*16400,method='order0')
        self.assertEqual(decode(frame),b'\0'*16400)

    def test_all_methods_independent_recovery_determinism_and_old_rejection(self):
        for method in ('order0','order1','zlib','zstd','lzma'):
            for raw in (b'',bytes(range(256))*2,b'ABABAB\r\n'):
                frame,info=encode(raw,method=method)
                self.assertEqual(decode(frame),raw)
                self.assertEqual(encode(raw,method=method)[0],frame)
                self.assertEqual(info['embedded_model_bytes'],0)
                with self.assertRaises(ValueError):previous_decode(frame)
                with tempfile.TemporaryDirectory() as temp:
                    path=Path(temp)/'frame.rkvonline';path.write_bytes(frame)
                    with self.assertRaises(ValueError):Archive(path)

    def test_corruption_wrong_rules_and_trailing_rejected(self):
        frame,_=encode(b'ABAB')
        for bad in (b'',frame[:-1],frame+b'x'):
            with self.assertRaises(ValueError):decode(bad)
        for offset in (0,50,len(frame)-1):
            bad=bytearray(frame);bad[offset]^=1
            with self.assertRaises(ValueError):decode(bytes(bad))
        fields=list(HEADER.unpack_from(frame));fields[-2]=bytes(32)
        self.assertNotEqual(fields[-2],RULE_SHA)
        with self.assertRaises(ValueError):decode(HEADER.pack(*fields)+frame[HEADER.size:])
        with self.assertRaises(ValueError):Predictor(2)
        with self.assertRaises(ValueError):Predictor(1).cdf([256,256,-1,0])
