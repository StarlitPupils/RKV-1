import copy
import importlib.util
from pathlib import Path
import random
import struct
import tempfile
import unittest
from unittest.mock import patch

from rkv1.blosc_codec import HEADER,PROFILES,compressor,decompress,preflight
from rkv1.core import Archive,assert_tree_equal,pack,unpack,validate_manifest,verify
from rkv1.scientific_data import primary_layout,SPECS
from rkv1.scientific_benchmark import scientific_benchmark

AVAILABLE=importlib.util.find_spec("blosc") is not None


class ScientificTests(unittest.TestCase):
    def test_fits_layout_inspection_preserves_special_bits(self):
        for bitpix,fmt,width in ((-32,">IIII",4),(-64,">QQQQ",8)):
            cards=["SIMPLE  =                    T",f"BITPIX  = {bitpix:20d}","NAXIS   =                    2",
                   "NAXIS1  =                    2","NAXIS2  =                    2","END"]
            header=b"".join(c.ljust(80).encode() for c in cards).ljust(2880,b" ")
            bits=(0,1<<(width*8-1),0x7fc12345 if width==4 else 0x7ff8123456789012,
                  0x7f800000 if width==4 else 0x7ff0000000000000)
            body=struct.pack(fmt,*bits);raw=header+body+bytes(2880-len(body))
            layout=primary_layout(raw)
            self.assertEqual((layout["bitpix"],layout["image_words"]),(bitpix,4))
            for key in ("positive_zero_words","negative_zero_words","nan_words","infinite_words"):
                self.assertEqual(layout[key],1)
            with self.assertRaises(ValueError):primary_layout(raw+b" ")
            with self.assertRaises(ValueError):primary_layout(raw.replace(b"END     ",b"MISSING ",1))
        self.assertEqual({s[3] for s in SPECS.values()},{-32,-64})

    def test_invalid_blosc_headers_rejected_before_native_import(self):
        raw=HEADER.pack(2,1,0x91,4,1024,1024,32)+bytes(16)
        for offset,value in ((0,3),(1,2),(2,0x94),(3,8),(4,255),(12,31)):
            changed=bytearray(raw);changed[offset]=value
            with patch("rkv1.blosc_codec.configured") as load:
                with self.assertRaises(ValueError):decompress(bytes(changed),1024,"blosc-zstd-shuffle-4")
                load.assert_not_called()
        for size in (0,True,9<<20):
            with self.assertRaises(ValueError):preflight(raw,size,"blosc-zstd-shuffle-4")
        with self.assertRaises(ValueError):preflight(b"short",1024,"blosc-zstd-shuffle-4")

    @unittest.skipUnless(AVAILABLE,"Optional Blosc dependency")
    def test_all_blosc_filters_widths_and_literal_tails(self):
        bits=bytes.fromhex("00000080 4523c17f 010000000000f87f 0000000000000080")
        for profile in PROFILES:
            for length in (4093,65536,100000):
                raw=(bits*((length+len(bits)-1)//len(bits)))[:length]
                coded=compressor(profile)(raw)
                self.assertLess(len(coded),len(raw))
                self.assertEqual(decompress(coded,len(raw),profile),raw)
                with self.assertRaises(ValueError):decompress(coded+b"x",len(raw),profile)
                with self.assertRaises(ValueError):decompress(coded,len(raw)+1,profile)

    @unittest.skipUnless(AVAILABLE,"Optional Blosc dependency")
    def test_v5_roundtrip_ranges_noise_and_versions(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/"source";source.mkdir()
            raw=b"".join(i.to_bytes(8,"big") for i in range(3000))+b"tail!"
            (source/"array").write_bytes(raw);(source/"noise").write_bytes(random.Random(3).randbytes(4099))
            for i,profile in enumerate(PROFILES):
                archive=root/f"{i}.rkv"
                stats=pack(source,archive,4093,compression=profile)
                with Archive(archive) as reader:
                    self.assertEqual(reader.header["version"],5)
                    self.assertTrue(any(m["codec"]==profile for m in reader.header["blocks"].values()))
                    self.assertEqual(reader.read_range("array",4088,32),raw[4088:4120])
                    changed=copy.deepcopy(reader.header);changed["version"]=4
                    with self.assertRaises(ValueError):validate_manifest(changed,stats["payload_bytes"])
                out=root/f"out{i}";unpack(archive,out);assert_tree_equal(source,out)
                verify(archive)
            for kwargs in ({"compression":"blosc-zstd-shuffle-4","format_version":4},
                {"compression":"blosc-zstd-shuffle-4","transform":"byte-shuffle-4-v1"},
                {"format_version":5,"unit_size":4096}, {"format_version":5,"transform":"csv-columns-v1"}):
                with self.assertRaises(ValueError):pack(source,root/"bad.rkv",**kwargs)
                self.assertFalse((root/"bad.rkv").exists())

    @unittest.skipUnless(AVAILABLE,"Optional Blosc dependency")
    def test_blosc_damage_fails_original_sha_or_native_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/"source";source.mkdir()
            (source/"a").write_bytes(bytes(range(256))*1000)
            path=root/"a.rkv";pack(source,path,compression="blosc-zstd-bitshuffle-4")
            blob=bytearray(path.read_bytes());blob[-1]^=0x80;path.write_bytes(blob)
            with self.assertRaises(ValueError):verify(path)
            with self.assertRaises(ValueError):unpack(path,root/"failed")
            self.assertFalse((root/"failed").exists())

    @unittest.skipUnless(AVAILABLE,"Optional Blosc dependency")
    def test_environment_overrides_rejected(self):
        with patch.dict("os.environ",{"BLOSC_NTHREADS":"2"}):
            with self.assertRaises(ValueError):compressor("blosc-zstd-shuffle-4")

    @unittest.skipUnless(AVAILABLE,"Optional Blosc dependency")
    def test_scientific_subprocess_campaign_smoke(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/"bits").write_bytes(bytes(range(128))*64)
            from rkv1.scientific_benchmark import matrix
            self.assertEqual(len(matrix(4)),18)
            # Use the ordinary + professional configurations without the full matrix.
            from rkv1.numeric_benchmark import numeric_benchmark
            configs=[matrix(4)[0],matrix(4)[7]]
            report=numeric_benchmark(root,configs=configs,rounds=1,queries=2,warmup_queries=1)
            self.assertTrue(all(r["bytewise_verified"] for r in report["results"]))
