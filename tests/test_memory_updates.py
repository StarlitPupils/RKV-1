from contextlib import closing
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from rkv1.memory import Memory,_json


class MemoryUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/"source";self.source.mkdir()
        rng=random.Random(17)
        self.docs=[{"doc_id":i,"title":f"beacon calibration {i}","abstract":["rare variants "*(i%3+1)+"".join(rng.choices("abcdefghijklmnopqrstuvwxyz ",k=600))]} for i in range(32)]
        self.write();self.original=(self.source/"corpus.jsonl").read_bytes()
        self.reference=Memory.create(self.root/"reference",index_profile="full-v1")
        self.candidate=Memory.create(self.root/"candidate")

    def write(self):
        (self.source/"corpus.jsonl").write_bytes(b"".join(json.dumps(d).encode()+b"\r\n" for d in self.docs))

    def both(self,label):
        a=self.reference.add(self.source,label=label);b=self.candidate.add(self.source,label=label)
        self.compare(a["snapshot_id"],b["snapshot_id"])
        return a,b

    def compare(self,a,b):
        for q in ("beacon calibration","rare variants","RKV17PROBE","absentword"):
            xs=self.reference.search(q,snapshot=a,top_k=20)["hits"];ys=self.candidate.search(q,snapshot=b,top_k=20)["hits"]
            self.assertEqual([h["key"] for h in xs],[h["key"] for h in ys])
            for x,y in zip(xs,ys):
                self.assertEqual(x["locator"],y["locator"]);self.assertEqual(x["sentences"],y["sentences"])
                self.assertAlmostEqual(x["rank"],y["rank"],places=12)

    def test_prefix_edit_keeps_base_index_and_verifies_old_and_current_offsets(self):
        _,first=self.both("base")
        self.docs[0]["abstract"][0]+=" RKV17PROBE";self.write();_,new=self.both("prefix")
        self.assertEqual(new["delta_depth"],1);self.assertEqual(new["relocation_ranges"],1)
        self.assertEqual(new["overlay_upserts"],1);self.assertLess(new["new_index_bytes"],2048)
        self.assertEqual(len(list((self.root/"candidate/indexes").glob("*.sqlite"))),1)
        self.compare(first["snapshot_id"],first["snapshot_id"])
        self.assertFalse(self.candidate.search("RKV17PROBE",snapshot=first["snapshot_id"])["hits"])

    def test_twelve_revisions_use_single_base_relative_overlay_not_a_chain(self):
        _,first=self.both("base");initial=self.docs[0]["abstract"][0]
        history=[]
        for i in range(12):
            self.docs[0]["abstract"][0]=initial+" RKV17PROBE "+str(i);self.write()
            _,result=self.both(f"revision-{i}");history.append(result["snapshot_id"])
            self.assertEqual(result["delta_depth"],1)
            manifest=self.candidate._manifest(result["snapshot_id"])
            self.assertEqual(manifest["deltas"][0]["parent_snapshot"],first["snapshot_id"])
        self.assertEqual(len(list((self.root/"candidate/indexes").glob("*.sqlite"))),1)
        for sid in history:self.compare(sid,sid)

    def test_two_shift_ranges_select_old_rows_before_any_move(self):
        self.both("base")
        self.docs[0]["abstract"][0]+=" RKV17PROBE"*1000
        self.docs[16]["abstract"][0]+=" another offset change"
        self.write();_,result=self.both("crossing-ranges")
        self.assertEqual(result["relocation_ranges"],2)
        self.assertEqual(result["overlay_upserts"],2)

    def test_deletion_relocates_and_many_changed_records_make_checkpoint(self):
        _,first=self.both("base");self.docs.pop(0);self.write();_,deleted=self.both("delete")
        self.assertEqual(deleted["delta_depth"],1)
        for d in self.docs[:9]:d["abstract"][0]+=" RKV17PROBE"
        self.write();_,checkpoint=self.both("checkpoint")
        self.assertEqual(checkpoint["delta_depth"],0)
        self.compare(first["snapshot_id"],first["snapshot_id"])

    def test_relocation_fragment_limit_can_checkpoint_without_losing_results(self):
        self.both("base");self.docs[0]["abstract"][0]+=" RKV17PROBE";self.docs[16]["abstract"][0]+=" RKV17PROBE";self.write()
        with patch("rkv1.memory_index.MAX_RELOCATIONS",1):_,result=self.both("fragment-checkpoint")
        self.assertEqual(result["delta_depth"],0)

    def test_whitespace_only_source_change_keeps_exact_bytes_and_both_formats(self):
        for profile in ("compact-delta-v2","compact-base-v3"):
            root=self.root/profile;m=Memory.create(root,index_profile=profile)
            m.add(self.source,label="before")
            raw=(self.source/"corpus.jsonl").read_bytes()+b"\r\n\n";(self.source/"corpus.jsonl").write_bytes(raw)
            added=m.add(self.source,label="blank-bytes")
            self.assertEqual(m.store.snapshot(added["snapshot_id"]).read_range("corpus.jsonl"),raw)
            self.assertTrue(m.search("beacon")["hits"])

    def test_gear_memory_cli_native_equivalence_and_cross_chunk_exact_reads(self):
        path=self.root/"gear";p=subprocess.run([sys.executable,"-m","rkv1","memory-init",str(path),str(self.source),"--chunker","gear-v1","--chunk-size","4096"],capture_output=True,text=True,encoding="utf-8")
        self.assertEqual(p.returncode,0,p.stderr);first=json.loads(p.stdout)
        m=Memory(path);self.docs[0]["abstract"][0]+=" RKV17PROBE";self.write();new=m.add(self.source,label="insert")
        raw=(self.source/"corpus.jsonl").read_bytes()
        with m.store.snapshot(new["snapshot_id"]) as snap:
            self.assertEqual(snap.read_range("corpus.jsonl"),raw)
            for offset in (0,4090,8190,len(raw)-32):self.assertEqual(snap.read_range("corpus.jsonl",offset,32),raw[offset:offset+32])
        library=os.environ.get("RKV_NATIVE_LIBRARY")
        if library:
            native=Memory.create(self.root/"native-gear",chunker="gear-v1",chunk_size=4096)
            added=native.add(self.source,label="insert",chunker_backend="rust",native_library=library)
            self.assertEqual(added["snapshot_id"],new["snapshot_id"])
            self.assertEqual(native.search("beacon")["hits"],m.search("beacon")["hits"])

    def test_corrupt_overlay_and_wrong_base_format_are_rejected(self):
        self.candidate.add(self.source);self.docs[0]["abstract"][0]+=" RKV17PROBE";self.write();new=self.candidate.add(self.source,label="insert")
        path=next((self.root/"candidate/indexes").glob("*.delta"));raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        with self.assertRaisesRegex(ValueError,"delta SHA"):self.candidate.search("beacon")
        path.write_bytes(raw)
        manifest_path=self.root/"candidate/manifests"/(new["snapshot_id"]+".json")
        value=json.loads(manifest_path.read_bytes());value["deltas"][0]["version"]=2;manifest_path.write_bytes(_json(value))
        with self.assertRaisesRegex(ValueError,"format/base"):self.candidate.search("beacon")


if __name__=="__main__":unittest.main()
