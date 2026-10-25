import hashlib
from pathlib import Path
import tempfile
import unittest

from rkv1.core import Archive
from rkv1.text_frame import encode,decode,HEADER,MAGIC,MAX_RAW,CODECS,_compress
from rkv1.text_lanes import forward,inverse,HEADER as LANES


class TextFrameTests(unittest.TestCase):
    def test_lanes_exact_spelling_comments_strings_unicode_all_bytes_and_boundaries(self):
        cases=[b'',b'a',b'0',bytes(range(256))*3,
            'x = -0.000e+03 # café\r\n\t"雪\\n"; \\alpha_{1.00}\r\n'.encode(),b'a'*16384,
            *[hashlib.shake_256(str(n).encode()).digest(n) for n in (1,2,127,128,255,8192)]]
        for raw in cases:
            payload,info=forward(raw);self.assertEqual(inverse(payload,len(raw)),raw)
            self.assertEqual(sum(info['pool_bytes']),len(raw));self.assertLessEqual(info['control_bytes'],2*len(raw))
            self.assertEqual(info['transformed_bytes'],40+info['control_bytes']+len(raw))

    def test_all_codecs_modes_deterministic_frames_and_bytewise_recovery(self):
        cases=[b'',bytes(range(256)),b'alpha = 1.250e-09\r\n'*100,'# 雪 café\r\n\\beta_{i}'.encode()]
        for codec in CODECS:
            for mode in ('plain','lanes','auto'):
                for raw in cases:
                    with self.subTest(codec=codec,mode=mode,size=len(raw)):
                        frame,info=encode(raw,codec=codec,mode=mode)
                        self.assertEqual(decode(frame),raw);self.assertEqual(encode(raw,codec=codec,mode=mode)[0],frame)
                        self.assertEqual(info['dictionary_bytes'],0);self.assertEqual(info['model_bytes'],0)

    def test_auto_attempts_both_and_never_selects_a_larger_frame(self):
        for codec in CODECS:
            for raw in (b'',b'x y = 314159;\r\n'*100,hashlib.shake_256(b'noise').digest(8192)):
                plain,_=encode(raw,codec=codec,mode='plain');frame,meta=encode(raw,codec=codec,mode='auto')
                self.assertEqual([a['mode'] for a in meta['attempts']],['plain','lanes'])
                self.assertLessEqual(len(frame),len(plain));self.assertEqual(decode(frame),raw)
                if meta['attempts'][0]['frame_bytes']==meta['attempts'][1]['frame_bytes']:self.assertEqual(meta['selected_mode'],'plain')

    def test_header_corruption_truncation_and_invalid_inputs_rejected(self):
        frame,_=encode(b'original',codec='zlib',mode='plain');values=list(HEADER.unpack_from(frame))
        for field,value in ((0,b'BADMAGIC'),(1,9),(2,99),(3,MAX_RAW+1),(4,9999),(5,0),(6,b'0'*32)):
            v=list(values);v[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):decode(HEADER.pack(*v)+frame[HEADER.size:])
        for broken in (b'',frame[:-1],frame+b'x'):
            with self.assertRaises(ValueError):decode(broken)
        for args in ({'raw':'not-bytes'},{'raw':b'x','codec':[]},{'raw':b'x','mode':'missing'}):
            with self.assertRaises(ValueError):encode(**args)

    def test_all_codecs_reject_extra_streams_even_if_outer_length_is_updated(self):
        for codec in CODECS:
            frame,_=encode(b'original',codec=codec,mode='plain');v=list(HEADER.unpack_from(frame))
            for extra in (b'garbage',_compress(b'second frame',codec)):
                values=list(v);values[5]+=len(extra)
                with self.subTest(codec=codec),self.assertRaises(ValueError):decode(HEADER.pack(*values)+frame[HEADER.size:]+extra)

    def test_lane_tags_lengths_canonical_varints_and_unused_data_rejected(self):
        raw=b'a 23';payload,_=forward(raw)
        bad_tag=bytearray(payload);bad_tag[40]=4
        bad_zero=bytearray(payload);bad_zero[41]=0
        wrong_size=bytearray(payload);wrong_size[:8]=(999).to_bytes(8,'little')
        for bad in (bytes(bad_tag),bytes(bad_zero),bytes(wrong_size),payload[:-1]):
            with self.assertRaises(ValueError):inverse(bad,len(raw))
        with self.assertRaisesRegex(ValueError,'Noncanonical'):
            inverse(LANES.pack(3,2,0,0,0)+b'\x00\x82\x00ab',2)
        with self.assertRaises(ValueError):inverse(LANES.pack(0,1,0,0,0)+b'a',1)

    def test_forged_small_decompressed_size_is_bounded_and_rejected(self):
        for codec,code in CODECS.items():
            payload=_compress(b'A'*(1<<20),codec)
            frame=HEADER.pack(MAGIC,0,code,1,1,len(payload),hashlib.sha256(b'A').digest())+payload
            with self.subTest(codec=codec),self.assertRaises(ValueError):decode(frame)

    def test_experimental_magic_cannot_be_opened_as_a_main_RKV_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'experimental.rkvtext';path.write_bytes(encode(b'Source spelling.',codec='zlib')[0])
            with self.assertRaises(ValueError):Archive(path)
