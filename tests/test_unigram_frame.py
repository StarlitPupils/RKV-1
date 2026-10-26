import struct
import tempfile
from pathlib import Path
import unittest
from rkv1.unigram_frame import build_model,Predictor,encode,decode
from rkv1.neural_frame import decode as old_neural_decode
from rkv1.core import Archive

class UnigramFrameTests(unittest.TestCase):
 def test_count_model_positive_normalized_and_no_test_updates(self):
  model=build_model([b'AAAAAB',bytes(range(256))]);p=Predictor(model)
  self.assertEqual(len(model),520);self.assertEqual(p.cdf([0]*4)[-1],32768)
  self.assertTrue(all(a<b for a,b in zip(p.values,p.values[1:])))
  self.assertEqual(p.cdf([255]*4),p.cdf([256]*4));self.assertEqual(model,build_model([b'AAAAAB',bytes(range(256))]))
  with self.assertRaises(ValueError):build_model([])
 def test_original_bytes_and_experimental_format_boundaries(self):
  model=build_model([b'AB'*32,bytes(range(256))])
  for raw in (b'',bytes(range(256)),('snow'+chr(38634)).encode()+bytes([13,10])):
   frame,info=encode(raw,model=model);self.assertEqual(decode(frame),raw);self.assertEqual(frame,encode(raw,model=model)[0]);self.assertEqual(info['model_raw_bytes'],520)
   with self.assertRaises(ValueError):old_neural_decode(frame)
   with tempfile.TemporaryDirectory() as temp:
    path=Path(temp)/'unigram.rkvnn';path.write_bytes(frame)
    with self.assertRaises(ValueError):Archive(path)
 def test_corruption_and_invalid_frequency_table_fail_closed(self):
  model=build_model([b'AB'*32]);frame,_=encode(b'AAB',model=model)
  for bad in (frame[:-1],frame+b'x',b''):
   with self.assertRaises(ValueError):decode(bad)
  for i in (0,134,len(frame)-1):
   bad=bytearray(frame);bad[i]^=1
   with self.assertRaises(ValueError):decode(bytes(bad))
  with self.assertRaises(ValueError):Predictor(model[:8]+struct.pack('<256H',*([0]*256)))
