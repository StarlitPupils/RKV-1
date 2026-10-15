import json
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rkv1.memory import Memory


class MemoryIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/"source";self.source.mkdir()
        self.docs=[{"doc_id":i,"title":f"Calibration {i}","abstract":["silver beacon "*(i%3+1)+("rare variants" if i%2 else "common variants"),"café 雪"]} for i in range(16)]
        self.write()
        self.reference=Memory.create(self.root/"reference",index_profile="full-v1")
        self.candidate=Memory.create(self.root/"candidate",index_profile="compact-delta-v2")

    def write(self):
        (self.source/"corpus.jsonl").write_bytes(b"".join(json.dumps(d,ensure_ascii=True).encode()+b"\r\n" for d in self.docs))

    def compare(self,a,b):
        for question in ("calibration silver beacon","rare variants","common variants","café","replacement","futuremarker","absentword"):
            x=self.reference.search(question,snapshot=a,top_k=20);y=self.candidate.search(question,snapshot=b,top_k=20)
            self.assertEqual([h["key"] for h in x["hits"]],[h["key"] for h in y["hits"]])
            for old,new in zip(x["hits"],y["hits"]):
                self.assertEqual(old["title"],new["title"]);self.assertEqual(old["sentences"],new["sentences"])
                self.assertEqual(old["locator"],new["locator"])
                self.assertAlmostEqual(old["rank"],new["rank"],places=12)

    def add_both(self,label):
        a=self.reference.add(self.source,label=label);b=self.candidate.add(self.source,label=label)
        self.assertEqual(a["snapshot_id"],b["snapshot_id"])
        self.compare(a["snapshot_id"],b["snapshot_id"])
        return a,b

    def test_global_bm25_survives_add_edit_delete_and_record_relocation(self):
        _,first=self.add_both("initial")
        self.docs[-1]["abstract"][0]="replacement rare variants beacon "*8
        self.write();_,edited=self.add_both("edit")
        self.assertEqual(edited["delta_depth"],1)
        self.docs.pop(3);self.write();self.add_both("delete")
        (self.source/"future.txt").write_text("futuremarker silver rare variants",encoding="utf-8")
        _,last=self.add_both("append")
        self.assertEqual(len(list((self.root/"candidate/indexes").glob("*.sqlite"))),2)
        self.compare(first["snapshot_id"],first["snapshot_id"])
        self.assertFalse(self.candidate.search("futuremarker",snapshot=first["snapshot_id"])["hits"])
        self.assertTrue(Memory(self.root/"candidate").search("futuremarker",snapshot=last["snapshot_id"])["hits"])

    def test_checkpoint_bounds_chain_and_old_snapshots_still_work(self):
        _,first=self.add_both("base")
        for i in range(9):
            (self.source/f"note-{i}.txt").write_text(f"futuremarker {i}",encoding="utf-8")
            _,latest=self.add_both(f"revision-{i}")
        self.assertEqual(latest["delta_depth"],0)
        self.assertEqual(len(list((self.root/"candidate/indexes").glob("*.sqlite"))),2)
        self.compare(first["snapshot_id"],first["snapshot_id"])

    def test_compact_index_does_not_store_title_or_body_copy(self):
        import sqlite3
        added=self.candidate.add(self.source)
        with closing(sqlite3.connect(self.root/"candidate/indexes"/(added["snapshot_id"]+".sqlite"))) as db:
            self.assertEqual(db.execute("SELECT title,body FROM evidence LIMIT 1").fetchone(),(None,None))
            self.assertEqual(db.execute("SELECT count(*) FROM locators").fetchone()[0],16)

    def test_many_relocated_records_trigger_checkpoint_and_preserve_rankings(self):
        _,first=self.add_both("base")
        self.docs[0]["abstract"][0]+=" replacement"
        self.write();_,result=self.add_both("relocation")
        self.assertEqual(result["delta_depth"],0)
        self.assertGreater(result["new_index_bytes"],0)
        self.compare(first["snapshot_id"],first["snapshot_id"])

    def test_delta_corruption_is_rejected_before_results(self):
        self.candidate.add(self.source);(self.source/"note.txt").write_text("futuremarker")
        self.candidate.add(self.source,label="update")
        path=next((self.root/"candidate/indexes").glob("*.delta"));raw=path.read_bytes()
        path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        with self.assertRaisesRegex(ValueError,"delta SHA"):self.candidate.search("futuremarker")

    def test_failed_manifest_publication_does_not_advance_head(self):
        first=self.candidate.add(self.source);(self.source/"note.txt").write_text("futuremarker")
        from rkv1 import memory_index
        publish=memory_index._publish
        def fail(path,data):
            if path.parent.name=="manifests":raise OSError("injected manifest failure")
            return publish(path,data)
        with patch.object(memory_index,"_publish",side_effect=fail):
            with self.assertRaises(OSError):self.candidate.add(self.source,label="failure")
        self.assertEqual(self.candidate.current(),first["snapshot_id"])
        self.assertFalse(self.candidate.search("futuremarker")["hits"])
        self.assertGreater(self.candidate.stats()["by_directory_bytes"]["indexes"],0)

    def test_label_only_alias_and_readding_old_snapshot_reuse_index(self):
        first=self.candidate.add(self.source,label="first")
        alias=self.candidate.add(self.source,label="alias")
        self.assertEqual(alias["new_index_bytes"],0)
        (self.source/"note.txt").write_text("futuremarker")
        self.candidate.add(self.source,label="future")
        (self.source/"note.txt").unlink()
        old=self.candidate.add(self.source,label="first")
        self.assertEqual(old["snapshot_id"],first["snapshot_id"])
        self.assertTrue(old["index_reused"])
        self.assertFalse(self.candidate.search("futuremarker")["hits"])

    def test_first_publication_failure_can_reuse_verified_orphan_base(self):
        from rkv1 import memory_index
        publish=memory_index._publish
        def fail(path,data):
            if path.parent.name=="manifests":raise OSError("injected first publication failure")
            return publish(path,data)
        with patch.object(memory_index,"_publish",side_effect=fail):
            with self.assertRaises(OSError):self.candidate.add(self.source)
        self.assertFalse((self.root/"candidate/HEAD.json").exists())
        self.candidate.add(self.source)
        self.assertTrue(self.candidate.search("beacon")["hits"])

    def test_legacy_memory_remains_readable_and_keeps_legacy_profile(self):
        first=self.reference.add(self.source)
        self.assertEqual(self.reference._manifest(first["snapshot_id"])["version"],1)
        (self.source/"note.txt").write_text("futuremarker")
        result=Memory(self.root/"reference").add(self.source,label="legacy-update")
        self.assertEqual(self.reference._manifest(result["snapshot_id"])["version"],1)
        self.assertTrue(self.reference.search("futuremarker")["hits"])


if __name__=="__main__":unittest.main()
