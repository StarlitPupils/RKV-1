import copy
import io
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from rkv1.core import Archive,pack,unpack,verify,assert_tree_equal,validate_manifest
from rkv1.layouts import FITS_POLICY, fits_image, HEADER_LIMIT


def fits(width=4, count=20000):
    cards=["SIMPLE  =                    T",f"BITPIX  = {-8*width:20d}","NAXIS   =                    2",
           f"NAXIS1  = {count:20d}","NAXIS2  =                    1","END"]
    head=b"".join(c.ljust(80).encode() for c in cards).ljust(2880,b" ")
    # Special values and byte-distinct NaN payloads, in big-endian byte order.
    word=(bytes.fromhex("7fc12345 ff800000 80000000 00000001") if width==4 else
          bytes.fromhex("7ff8123456789012 fff0000000000000 8000000000000000 0000000000000001"))
    image=(word*((count*width+len(word)-1)//len(word)))[:count*width]
    return head+image+b"~"*((-len(image))%2880),len(head),len(head)+len(image)


class LayoutTests(unittest.TestCase):
    def test_bounded_detection_whitelist_and_position(self):
        raw,start,end=fits()
        stream=io.BytesIO(raw);stream.seek(7)
        self.assertEqual((fits_image(stream,len(raw)).start,fits_image(stream,len(raw)).end),(start,end))
        self.assertEqual(stream.tell(),7)
        for changed in (raw+b" ",raw[:-2880],raw.replace(b"                 -32",b"                  16",1),
                        raw.replace(b"NAXIS2  =                    1",b"NAXIS2  =                    0",1),
                        raw.replace(b"END     ",b"MISSING ",1),raw.replace(b"NAXIS2  ",b"NAXIS1  ",1)):
            self.assertIsNone(fits_image(io.BytesIO(changed),len(changed)))
        # Extension bytes are not silently excluded.
        self.assertIsNone(fits_image(io.BytesIO(raw+bytes(2880)),len(raw)+2880))
        class Counting(io.BytesIO):
            consumed=0
            def read(self,n=-1):
                b=super().read(n);self.consumed+=len(b);return b
        huge=(b"SIMPLE  =                    T".ljust(80)+b" "*(2880-80))*400
        stream=Counting(huge)
        self.assertIsNone(fits_image(stream,len(huge)))
        self.assertLessEqual(stream.consumed,HEADER_LIMIT)

    def test_regions_exact_roundtrip_and_ranges(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/"source";source.mkdir()
            originals={}
            for w in (4,8):
                raw,start,end=fits(w);name=f"bits{w}.dat";originals[name]=raw
                (source/name).write_bytes(raw)
            (source/"unknown.fits").write_bytes(b"not a FITS"*40);(source/"empty").write_bytes(b"")
            for layout in ("fixed","fits-segments-v1"):
                path=root/(layout+".rkv");stats=pack(source,path,4093,layout=layout,transform=FITS_POLICY)
                with Archive(path) as r:
                    self.assertEqual(r.header["version"],6)
                    self.assertEqual(r.layout_offset_bytes>0,layout!="fixed")
                    for name,raw in originals.items():
                        self.assertEqual(r.read_range(name),raw)
                        _,start,end=fits(int(name[4]))
                        for offset in [0,1,2879,2880,4092,4093,end-2,end,len(raw)]+[random.Random(i).randrange(len(raw)) for i in range(20)]:
                            length=min(37,len(raw)-offset)
                            self.assertEqual(r.read_range(name,offset,length),raw[offset:offset+length])
                        cursor=0
                        for key in r.files[name]["chunks"]:
                            m=r.header["blocks"][key]
                            if m["transform"]!="none":
                                self.assertGreaterEqual(cursor,start);self.assertLessEqual(cursor+m["raw_size"],end)
                            cursor+=m["raw_size"]
                        if layout!="fixed":
                            offsets=list(r._file_offsets[name]);self.assertIn(start,offsets);self.assertIn(end,offsets)
                    self.assertEqual(r.read_range("empty",0,0),b"")
                    self.assertTrue(all(r.header["blocks"][k]["transform"]=="none" for k in r.files["unknown.fits"]["chunks"]))
                out=root/(layout+"-out");unpack(path,out);assert_tree_equal(source,out);verify(path)
                if layout!="fixed":
                    with Archive(path) as r:h=copy.deepcopy(r.header)
                    h["layout"]="fixed"
                    with self.assertRaises(ValueError):validate_manifest(h,stats["payload_bytes"])

    def test_manifest_rejects_invalid_routing_and_lengths(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);s=root/"s";s.mkdir();(s/"a").write_bytes(fits()[0]);p=root/"a.rkv"
            stats=pack(s,p,4096,layout="fits-segments-v1",transform=FITS_POLICY)
            with Archive(p) as r:original=copy.deepcopy(r.header)
            for edit in (lambda h:h.update(layout="unknown"), lambda h:h.update(version=5),
                         lambda h:h["files"][0].update(size=h["files"][0]["size"]+1),
                         lambda h:next(iter(h["blocks"].values())).update(transform=FITS_POLICY),
                         lambda h:next(iter(h["blocks"].values())).update(raw_size=0)):
                h=copy.deepcopy(original);edit(h)
                with self.assertRaises(ValueError):validate_manifest(h,stats["payload_bytes"])
            for kwargs in ({"layout":"fits-segments-v1","format_version":5},
                           {"format_version":6,"unit_size":4096},
                           {"format_version":6,"transform":"csv-columns-v1"},
                           {"format_version":6,"compression":"blosc-zstd-shuffle-4"}):
                with self.assertRaises(ValueError):pack(s,root/"bad.rkv",**kwargs)
                self.assertFalse((root/"bad.rkv").exists())

    def test_v6_base_reuse_and_layout_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);s=root/"s";s.mkdir();(s/"a").write_bytes(fits()[0])
            base=root/"base.rkv";pack(s,base,4096,layout="fits-segments-v1",transform=FITS_POLICY)
            result=pack(s,root/"new.rkv",4096,base=base,layout="fits-segments-v1",transform=FITS_POLICY)
            self.assertEqual(result["new_chunks"],0);verify(root/"new.rkv")
            with self.assertRaises(ValueError):pack(s,root/"bad.rkv",4096,base=base,transform=FITS_POLICY)

    def test_payload_damage_does_not_publish_restored_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);s=root/"s";s.mkdir();(s/"a").write_bytes(fits()[0]);p=root/"a.rkv"
            pack(s,p,4096,layout="fits-segments-v1",transform=FITS_POLICY)
            blob=bytearray(p.read_bytes());blob[-1]^=1;p.write_bytes(blob)
            with self.assertRaises(ValueError):verify(p)
            with self.assertRaises(ValueError):unpack(p,root/"bad")
            self.assertFalse((root/"bad").exists())

    def test_reference_limit_applies_before_duplicate_payload_expansion(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);s=root/"s";s.mkdir();(s/"a").write_bytes(b"x"*20)
            with patch("rkv1.core.MAX_BLOCKS",5):
                with self.assertRaisesRegex(ValueError,"references"):
                    pack(s,root/"bad.rkv",1,format_version=6)
            self.assertFalse((root/"bad.rkv").exists())

    def test_fresh_process_benchmark(self):
        from rkv1.numeric_benchmark import numeric_benchmark
        from rkv1.layout_benchmark import matrix
        self.assertEqual(len(matrix(4)),20)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/"a").write_bytes(fits(count=2000)[0])
            report=numeric_benchmark(p,configs=[matrix(4)[0],matrix(4)[4]],rounds=1,queries=2,warmup_queries=1)
            for r in report["results"]:
                self.assertTrue(r["bytewise_verified"])
                self.assertTrue(all(t["blosc_loaded"] is False for t in r["encode_trials"]+r["decode_trials"]))
