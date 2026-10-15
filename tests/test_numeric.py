import copy
import hashlib
import json
from pathlib import Path
import random
import struct
import tempfile
import unittest
from unittest.mock import patch

from rkv1.core import Archive, MAGIC, assert_tree_equal, pack, unpack, validate_manifest, verify
from rkv1.numeric import POLICIES, decode, encode
from rkv1.numeric_benchmark import numeric_benchmark
from rkv1.numeric_data import SPECS, fetch, noise


class NumericTests(unittest.TestCase):
    def test_byte_exact_all_words_tails_and_float_bit_patterns(self):
        # NaN payloads, signed zero, infinities, subnormals, both byte orders:
        # these are input bit patterns, never Python floating-point values.
        bits = bytes.fromhex("00000080000000000100c07f4523a17f0000807f01000000")
        rng = random.Random(19)
        for policy, (_, width) in POLICIES.items():
            for raw in (bits, bits[::-1], b"\0" * 193, b"\xff" * 201, rng.randbytes(65539)):
                for tail in range(width):
                    sample = raw + bytes(range(tail))
                    coded = encode(sample, policy)
                    self.assertEqual(len(coded), len(sample))
                    self.assertEqual(decode(coded, len(sample), policy), sample)
            for size in range(2 * width):
                self.assertIsNone(encode(bytes(size), policy))
                with self.assertRaises(ValueError):
                    decode(bytes(size), size, policy)
            with self.assertRaises(ValueError):
                decode(bytes(32), 33, policy)
            with self.assertRaises(ValueError):
                decode(bytes(32), True, policy)

    def test_golden_lane_order_and_independent_xor_reference(self):
        raw = bytes(range(17))
        self.assertEqual(encode(raw, "byte-shuffle-2-v1"), raw[:16:2] + raw[1:16:2] + raw[16:])
        for policy, (kind, width) in POLICIES.items():
            end = len(raw) // width * width
            if end < width * 2:
                continue
            words = [raw[i:i+width] for i in range(0, end, width)]
            expected = words
            if kind == "xor-shuffle":
                expected = [words[0]] + [bytes(x ^ y for x,y in zip(a,b)) for a,b in zip(words[1:],words)]
            expected = bytes(word[lane] for lane in range(width) for word in expected) + raw[end:]
            self.assertEqual(encode(raw, policy), expected)

    def test_archive_restore_ranges_dedup_and_unaligned_chunks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source"; source.mkdir()
            raw = b"".join(i.to_bytes(8, "little") for i in range(2000)) + b"tail!"
            (source / "array.bin").write_bytes(raw)
            (source / "copy.bin").write_bytes(raw)
            (source / "empty").write_bytes(b"")
            for index, policy in enumerate(POLICIES):
                for dedup in (False, True):
                    archive = root / f"{index}-{dedup}.rkv"
                    stats = pack(source, archive, 4093, compression="zlib", transform=policy, deduplicate=dedup)
                    self.assertGreater(stats["transformed_chunks"], 0)
                    with Archive(archive) as reader:
                        self.assertEqual(reader.header["version"], 4)
                        for offset,length in ((0,0),(1,57),(4088,30),(len(raw)-9,9)):
                            self.assertEqual(reader.read_range("array.bin",offset,length), raw[offset:offset+length])
                    dest = root / f"out-{index}-{dedup}"
                    unpack(archive, dest)
                    assert_tree_equal(source,dest)
                    self.assertEqual(verify(archive)["verified_files"],3)

    def test_format_gates_and_none_v2_v4_cost_control(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source"; source.mkdir()
            (source / "a").write_bytes(bytes(range(256))*19)
            a,b=root/"a.rkv",root/"b.rkv"
            pack(source,a); pack(source,b,format_version=4)
            with Archive(a) as old, Archive(b) as new:
                self.assertEqual(old.header["version"],2)
                changed=copy.deepcopy(new.header);changed["version"]=2
                self.assertEqual(changed,old.header)
                self.assertEqual(a.stat().st_size,b.stat().st_size)
                self.assertEqual(a.read_bytes()[old.body_start:],b.read_bytes()[new.body_start:])
            for kwargs in ({"format_version":True},{"format_version":3},
                {"transform":"byte-shuffle-2-v1","format_version":2},
                {"transform":"byte-shuffle-2-v1","unit_size":4096},
                {"transform":"csv-columns-v1","format_version":4}):
                target=root/"bad.rkv"
                with self.assertRaises(ValueError):pack(source,target,**kwargs)
                self.assertFalse(target.exists())

    def test_v4_integrity_and_invalid_recipe(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/"source";source.mkdir()
            raw=b"".join(i.to_bytes(2,"little") for i in range(10000))
            (source/"a").write_bytes(raw);archive=root/"data.rkv"
            pack(source,archive,compression="zlib",transform="byte-shuffle-2-v1")
            with Archive(archive) as reader:
                header=copy.deepcopy(reader.header); body=archive.read_bytes()[reader.body_start:]
            for field,value in (("coded_size",len(raw)-1),("transform","unknown"),("raw_size",3)):
                changed=copy.deepcopy(header);next(iter(changed["blocks"].values()))[field]=value
                with self.assertRaises(ValueError):validate_manifest(changed,len(body))
            # A valid but wrong global+block recipe must fail the original-byte SHA.
            changed=copy.deepcopy(header);changed["transform"]="xor-shuffle-2-v1"
            for meta in changed["blocks"].values():meta["transform"]="xor-shuffle-2-v1"
            encoded=json.dumps(changed,sort_keys=True,separators=(",",":")).encode()
            archive.write_bytes(MAGIC+struct.pack("<Q",len(encoded))+hashlib.sha256(encoded).digest()+encoded+body)
            with self.assertRaises(ValueError):verify(archive)
            with self.assertRaises(ValueError):unpack(archive,root/"failed")
            self.assertFalse((root/"failed").exists())

    def test_incremental_reuse_checks_original_bytes_and_bad_base(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/"source";source.mkdir()
            raw=b"".join(i.to_bytes(2,"little") for i in range(8000))
            (source/"a").write_bytes(raw);base=root/"base.rkv"
            pack(source,base,4096,transform="xor-shuffle-2-v1")
            result=pack(source,root/"next.rkv",4096,transform="xor-shuffle-2-v1",base=base)
            self.assertGreater(result["reused_chunks"],0)
            broken=bytearray(base.read_bytes());broken[-1]^=1;base.write_bytes(broken)
            with self.assertRaises(ValueError):pack(source,root/"bad.rkv",4096,transform="xor-shuffle-2-v1",base=base)
            self.assertFalse((root/"bad.rkv").exists())

    def test_noise_fallback_and_source_pins(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);record=noise(root)
            none=pack(record["source"],root/"none.rkv",65536,format_version=4)
            for policy in ("byte-shuffle-2-v1","xor-shuffle-2-v1"):
                result=pack(record["source"],root/(policy+".rkv"),65536,transform=policy)
                self.assertEqual(result["transformed_chunks"],0)
                self.assertGreater(result["stored_bytes"],none["stored_bytes"])
            self.assertEqual(len(SPECS["eeg"]["files"]),1)
            self.assertEqual(len(SPECS["ecg"]["files"]),3)
            with patch("rkv1.numeric_data.urlopen") as open_url:
                open_url.return_value.__enter__.return_value.read.return_value=b"wrong original bytes"
                with self.assertRaises(ValueError):fetch(root,"eeg")
                self.assertFalse((root/"eeg").exists())

    def test_matched_numeric_campaign_subprocess_smoke(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/"source";source.mkdir()
            (source/"a").write_bytes(b"".join(i.to_bytes(2,"little") for i in range(5000)))
            common={"chunk_size":4096,"unit_size":None,"compression":"zlib","deduplicate":True,"format_version":4}
            configs=[{**common,"layout":"smoke","transform":name} for name in ("none","byte-shuffle-2-v1")]
            result=numeric_benchmark(source,configs=configs,rounds=1,queries=2,warmup_queries=1)
            self.assertEqual(result["schema_version"],10)
            self.assertTrue(all(r["verified_measured_roundtrips"]==1 for r in result["results"]))
