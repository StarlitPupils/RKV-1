import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from rkv1.crossdomain_benchmark import crossdomain_benchmark
from rkv1.crossdomain_data import diagnostics,fetch,SPECS,word_census
from rkv1.numeric_benchmark import numeric_benchmark


class CrossDomainTests(unittest.TestCase):
    def test_structural_diagnostics_preserve_header_discrepancy_and_bits(self):
        payload=bytes.fromhex("00000000 00000080 0000807f 0100c07f")
        self.assertEqual(word_census(payload),{"words":4,"nan_words":1,"infinity_words":1,"positive_zero_words":1,"negative_zero_words":1})
        header=bytearray(632);struct.pack_into("<i",header,304,6);struct.pack_into("<i",header,316,4)
        self.assertEqual(diagnostics("seismic",bytes(header)+payload)["stored_samples"],4)
        with self.assertRaises(ValueError):diagnostics("seismic",bytes(header)+payload[:-1])
        def rec(raw):return struct.pack("<I",len(raw))+raw+struct.pack("<I",len(raw))
        h=b"CORD"+struct.pack("<I",500)+bytes(76)
        dcd=rec(h)+rec(b"test")+rec(struct.pack("<I",4))+rec(payload)*6
        d=diagnostics("molecular",dcd)
        self.assertEqual((d["header_declared_frames"],d["stored_complete_frames"]),(500,2))
        self.assertEqual(d["payload_float32_census"]["nan_words"],6)
        with self.assertRaises(ValueError):diagnostics("molecular",dcd[:-1]+b"x")

    def test_download_pins_and_existing_corruption_reject_without_refetch(self):
        raw=b"original text\r\n"
        spec={**SPECS["python"],"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
        with tempfile.TemporaryDirectory() as temp,patch.dict(SPECS,{"python":spec}),patch("rkv1.crossdomain_data.urlopen") as url:
            url.return_value.__enter__.return_value.read.return_value=b"wrong"
            with self.assertRaises(ValueError):fetch(temp,"python")
            self.assertFalse((Path(temp)/"python").exists())
            url.return_value.__enter__.return_value.read.return_value=raw
            d=fetch(temp,"python");self.assertEqual(d["files"][0]["sha256"],spec["sha256"])
            path=Path(d["source"])/spec["path"];path.write_bytes(raw+b"x");calls=url.call_count
            with self.assertRaises(ValueError):fetch(temp,"python")
            self.assertEqual(url.call_count,calls)

    def test_completed_journal_real_process_sync_and_matched_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/"source";source.mkdir();(source/"a").write_bytes(bytes(range(256))*32)
            # Small real campaign through the same fresh-process implementation.
            common={"chunk_size":4096,"unit_size":None,"compression":"zlib","format_version":4,"restore_sync":"files","deduplicate":True}
            configs=[{**common,"layout":"test","transform":name} for name in ("none","byte-shuffle-4-v1")]
            journal=root/"events.jsonl"
            j=numeric_benchmark(source,configs=configs,rounds=1,queries=2,warmup_queries=1,scratch=root/"scratch",journal=journal)
            records=[json.loads(line) for line in journal.read_text("utf-8").splitlines()]
            self.assertEqual(records[-1]["event"],"completed")
            returned=[r for r in records if r["event"]=="worker_returned"]
            self.assertEqual(len(returned),8)
            self.assertTrue(all(r["result"]["stats"]["files_synced"]==1 for r in returned if r["phase"]=="decode"))
            self.assertEqual(sum(r["event"]=="roundtrip_verified" for r in records),4)
            self.assertEqual(sum(r["event"]=="range_returned" for r in records),4)
            self.assertTrue(all(r["bytewise_verified"] for r in j["results"]))

    def test_failed_worker_retained_once_after_successful_prior_phase(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/"source";source.mkdir();(source/"a").write_bytes(b"truth")
            journal=root/"events.jsonl"
            with patch("rkv1.numeric_benchmark._child",side_effect=[{"stats":{},"wall_s":.1},ValueError("injected restore failure")]) as child:
                with self.assertRaisesRegex(ValueError,"injected restore failure"):
                    numeric_benchmark(source,configs=[{"transform":"none"}],rounds=1,journal=journal)
                self.assertEqual(child.call_count,2)
            records=[json.loads(line) for line in journal.read_text("utf-8").splitlines()]
            self.assertEqual([r["event"] for r in records],["started","worker_returned","worker_failed"])
            self.assertEqual(records[-1]["phase"],"decode")

    def test_existing_evidence_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/"source";source.mkdir();(source/"a").write_bytes(b"truth")
            journal=root/"events.jsonl";journal.write_bytes(b"retained\n")
            with patch("rkv1.numeric_benchmark._child") as child:
                with self.assertRaises(FileExistsError):numeric_benchmark(source,journal=journal)
                child.assert_not_called()
            self.assertEqual(journal.read_bytes(),b"retained\n")
