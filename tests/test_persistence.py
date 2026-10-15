import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch,Mock

from rkv1 import persistence
from rkv1.core import Archive,MAGIC,pack,unpack,verify,assert_tree_equal
from rkv1.experiments.restore_faults import injected,killed


class PersistenceTests(unittest.TestCase):
    def test_flush_precedes_fsync_and_failures_propagate(self):
        stream=Mock();stream.fileno.return_value=19;order=[]
        stream.flush.side_effect=lambda:order.append("flush")
        with patch.object(persistence.os,"fsync",side_effect=lambda fd:order.append(("fsync",fd))):
            self.assertTrue(persistence.finish_file(stream,"files"))
        self.assertEqual(order,["flush",("fsync",19)])
        stream.flush.side_effect=OSError("flush failed")
        with patch.object(persistence.os,"fsync") as sync:
            with self.assertRaises(OSError):persistence.finish_file(stream,"files")
            sync.assert_not_called()
        with patch.object(persistence.os,"fsync") as sync:
            self.assertFalse(persistence.finish_file(stream,"close"));sync.assert_not_called()
        for invalid in (None,True,[],"unknown"):
            with self.assertRaises(ValueError):persistence.validate_policy(invalid)

    def test_all_exception_boundaries_and_empty_file_sync(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/"source";source.mkdir()
            (source/"0-empty").write_bytes(b"");(source/"1-data").write_bytes(b"precise"*1000)
            archive=root/"input.rkv";pack(source,archive)
            for case in ("normal-files","normal-close","write-first","flush-first","fsync-first","fsync-last","close-first","publish-before"):
                r=injected(archive,source,root/case,case)
                self.assertEqual(r["target_present"],case.startswith("normal-"))
            with patch.object(persistence.os,"fsync") as sync:
                verify(archive);sync.assert_not_called()
            with self.assertRaises(ValueError):unpack(archive,root/"bad",sync_policy="unknown")
            self.assertFalse((root/"bad").exists())

    def test_file_hash_must_pass_before_sync(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/"s";source.mkdir();(source/"a").write_bytes(b"abc"*1000)
            archive=root/"a.rkv";pack(source,archive)
            with Archive(archive) as r:h=copy.deepcopy(r.header);start=r.body_start
            payload=archive.read_bytes()[start:];h["files"][0]["sha256"]="0"*64
            encoded=json.dumps(h,separators=(",",":"),sort_keys=True).encode()
            archive.write_bytes(MAGIC+struct.pack("<Q",len(encoded))+hashlib.sha256(encoded).digest()+encoded+payload)
            with patch.object(persistence,"finish_file") as finish:
                with self.assertRaisesRegex(ValueError,"File SHA"):unpack(archive,root/"bad")
                finish.assert_not_called()
            self.assertFalse((root/"bad").exists())

    def test_real_process_kills_before_and_after_publish(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/"s";source.mkdir()
            (source/"a").write_bytes(b"a"*1000);(source/"b").write_bytes(b"b"*1000)
            archive=root/"a.rkv";pack(source,archive)
            for case in ("kill-after-sync","kill-before-publish","kill-after-publish"):
                result=killed(archive,source,root/case,case)
                self.assertEqual(result["target_present"],case=="kill-after-publish")

    def test_existing_target_preserved_and_sync_failure_not_downgraded(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);s=root/"s";s.mkdir();(s/"a").write_bytes(b"data")
            a=root/"a.rkv";pack(s,a);dest=root/"existing";dest.mkdir();(dest/"marker").write_bytes(b"keep")
            with self.assertRaises(FileExistsError):unpack(a,dest)
            self.assertEqual((dest/"marker").read_bytes(),b"keep")
            with patch.object(persistence.os,"fsync",side_effect=OSError("not supported")):
                with self.assertRaises(OSError):unpack(a,root/"failed")
                result=unpack(a,root/"explicit-close",sync_policy="close")
                self.assertEqual(result["files_synced"],0)
            self.assertFalse((root/"failed").exists())

    def test_segmented_work_ledger_matches_actual_decoded_blocks(self):
        from rkv1.read_benchmark import touched_bytes
        from test_layout import fits
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);s=root/"s";s.mkdir();(s/"a").write_bytes(fits()[0])
            a=root/"a.rkv";pack(s,a,4096,layout="fits-segments-v1",transform="fits-byte-shuffle-v1")
            with Archive(a) as r:
                for offset,length in ((2870,20),(2880,1),(4090,20),(6970,30),(80000,100),(0,0),(r.files["a"]["size"],0)):
                    decoded=[];original=r.block
                    def block(key):decoded.append(key);return original(key)
                    with patch.object(r,"block",block):r.read_range("a",offset,length)
                    work=touched_bytes(r.header,{"path":"a","offset":offset,"length":length},r)
                    self.assertEqual(work["chunk_decodes"],len(decoded))
                    self.assertEqual(work["decoded_raw_bytes"],sum(r.header["blocks"][k]["raw_size"] for k in decoded))
                    self.assertEqual(work["stored_payload_bytes"],sum(r.header["blocks"][k]["stored_size"] for k in decoded))

    def test_sync_benchmark_same_archive_and_policies(self):
        from contextlib import redirect_stdout
        from rkv1.sync_benchmark import measure
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);s=root/"s";s.mkdir();(s/"empty").write_bytes(b"");(s/"data").write_bytes(b"sample"*1000)
            with redirect_stdout(io.StringIO()):
                j=measure([{"name":"sample","source":str(s),"pack":{"compression":"zlib","chunk_size":4096}}],root/"scratch",rounds=1)
            trials=j["cases"][0]["trials"]
            self.assertEqual(len(trials),4);self.assertTrue(all(r["bytewise_verified"] for r in trials))
            self.assertEqual({r["stats"]["files_synced"] for r in trials},{0,2})
            self.assertEqual(len({r["archive_sha256"] for r in trials}),1)

    def test_fault_matrix_covers_all_formats(self):
        from rkv1.experiments.restore_faults import campaign
        import importlib.util
        if importlib.util.find_spec("blosc") is None:self.skipTest("Optional Blosc dependency")
        with tempfile.TemporaryDirectory() as t:
            fixture=json.loads((Path(__file__).parent/"fixtures/v1.json").read_text("utf-8"))
            result=campaign(Path(t)/"audit",fixture,repetitions=1)
            self.assertEqual(len(result["records"]),66)
            self.assertEqual({r["format"] for r in result["records"]},set(range(1,7)))
            self.assertTrue(result["all_expected_outcomes_verified"])

    def test_worker_failure_preserves_unicode_diagnostic(self):
        from rkv1.controlled import _child
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with self.assertRaises(ValueError) as failure:
                _child("decode",root,root/"不存在.rkv",root/"out",{"restore_sync":"files"})
            self.assertIn("不存在",str(failure.exception))

    def test_windows_publish_retries_are_bounded_and_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);stage=root/"stage";stage.mkdir();dest=root/"final";original=Path.rename;count=0
            def temporary(path,target):
                nonlocal count
                count+=1
                if count<=2:raise PermissionError("transient")
                return original(path,target)
            with patch.object(Path,"rename",temporary),patch.object(persistence,"_transient_windows_rename",return_value=True),patch.object(persistence.time,"sleep") as sleep:
                self.assertEqual(persistence.publish_directory(stage,dest),3)
                self.assertEqual([c.args[0] for c in sleep.call_args_list],[.01,.05])
            stage.mkdir()
            with patch.object(Path,"rename") as renamed:
                with self.assertRaises(FileExistsError):persistence.publish_directory(stage,dest)
                renamed.assert_not_called()
            dest.rmdir()
            with patch.object(Path,"rename",side_effect=PermissionError("persistent")) as renamed,patch.object(persistence,"_transient_windows_rename",return_value=True),patch.object(persistence.time,"sleep") as sleep:
                with self.assertRaises(PermissionError):persistence.publish_directory(stage,dest)
                self.assertEqual(renamed.call_count,4);self.assertEqual(sleep.call_count,3)
                self.assertFalse(dest.exists())
            with patch.object(Path,"rename",side_effect=OSError("other error")) as renamed,patch.object(persistence,"_transient_windows_rename",return_value=False):
                with self.assertRaises(OSError):persistence.publish_directory(stage,dest)
                self.assertEqual(renamed.call_count,1)

    def test_benchmark_retains_failed_job_without_retry(self):
        from contextlib import redirect_stdout
        from rkv1.sync_benchmark import measure,_child
        count=0
        def fail_once(*args,**kwargs):
            nonlocal count
            count+=1
            if count==3:raise ValueError("Injected worker failure")
            return _child(*args,**kwargs)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);s=root/"s";s.mkdir();(s/"data").write_bytes(b"value")
            with redirect_stdout(io.StringIO()),patch("rkv1.sync_benchmark._child",fail_once):
                report=measure([{"name":"x","source":s,"pack":{}}],root/"scratch",rounds=1)
            trials=report["cases"][0]["trials"]
            self.assertEqual(count,4);self.assertEqual(sum(not x["success"] for x in trials),1)
            failure=next(x for x in trials if not x["success"])
            self.assertFalse(failure["target_present"]);self.assertIn("Injected",failure["error"])
