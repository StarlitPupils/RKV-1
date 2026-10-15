import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch

from rkv1.memory import Memory
from rkv1.memory_model import answer,exposed_hits,validate_answer,configuration


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/"source";self.source.mkdir()
        docs=[{"doc_id":1,"title":"Calibration beacon","abstract":["The beacon calibration code is COBALT-7421.","A quote: \"café\" and snow 雪."]},
              {"doc_id":2,"title":"Different material","abstract":["The coating contains silver nanoparticles."]}]
        self.raw=b"".join(json.dumps(d,ensure_ascii=True).encode()+b"\r\n" for d in docs)
        (self.source/"corpus.jsonl").write_bytes(self.raw)
        self.memory=Memory.create(self.root/"memory");self.added=self.memory.add(self.source)

    def test_retrieval_reopens_and_binds_exact_escaped_original_record(self):
        m=Memory(self.root/"memory");j=m.search("beacon calibration code")
        h=j["hits"][0];self.assertEqual(h["key"],"doc:1");loc=h["locator"]
        expected=self.raw[loc["offset"]:loc["offset"]+loc["length"]]
        self.assertTrue(expected.endswith(b"\r\n"));self.assertIn(b"\\u96ea",expected)
        self.assertEqual(m.store.snapshot(j["snapshot_id"]).read_range(loc["path"],loc["offset"],loc["length"]),expected)
        self.assertIn("雪",h["sentences"][1]);self.assertTrue(h["source_bytes_verified"])

    def test_update_keeps_old_snapshot_and_reuses_unchanged_source(self):
        first=self.added["snapshot_id"]
        (self.source/"revision.txt").write_bytes("The beacon revision is JADE-8842.\r\n雪".encode())
        updated=self.memory.add(self.source,label="revision")
        self.assertGreater(updated["reused_references"],0);self.assertNotEqual(first,updated["snapshot_id"])
        self.assertTrue(any(h["key"]=="file:revision.txt" for h in self.memory.search("JADE revision")["hits"]))
        self.assertFalse(any(h["key"]=="file:revision.txt" for h in self.memory.search("JADE revision",snapshot=first)["hits"]))
        self.assertEqual(self.memory.stats()["cas"]["snapshot_count"],2)

    def test_index_corruption_is_not_served(self):
        p=self.root/"memory/indexes"/(self.added["snapshot_id"]+".sqlite")
        raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        with self.assertRaisesRegex(ValueError,"index SHA"):self.memory.search("beacon")

    def test_cas_corruption_is_not_served(self):
        snap=self.memory.store.snapshot(self.added["snapshot_id"])
        ref=snap.files["corpus.jsonl"]["chunks"][0];p=self.memory.store.object_path(ref["id"])
        raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        with self.assertRaises(ValueError):self.memory.search("beacon")

    def test_claim_labels_duplicate_keys_and_failed_index_keep_head(self):
        sid=self.memory.current();(self.source/"labels.jsonl").write_text('{"id":1,"claim":"x","evidence":{}}\n')
        with self.assertRaises(ValueError):self.memory.add(self.source,label="bad")
        self.assertEqual(self.memory.current(),sid)
        (self.source/"labels.jsonl").unlink();(self.source/"corpus.jsonl").write_bytes(self.raw+self.raw)
        with self.assertRaisesRegex(ValueError,"Duplicate"):self.memory.add(self.source,label="duplicates")
        self.assertEqual(self.memory.current(),sid)

    def test_derived_answers_cannot_self_promote_or_be_implicitly_searched(self):
        a=self.memory.remember({"question":"secret beacon","primary_evidence":True,"record_type":"primary","text":"violet answer"})
        stored=json.loads((self.root/"memory/answers"/(a["answer_id"]+".json")).read_bytes())
        self.assertFalse(stored["primary_evidence"]);self.assertEqual(stored["record_type"],"derived-model-answer")
        self.assertEqual(self.memory.search("violet")["hits"],[])
        with self.assertRaisesRegex(ValueError,"overlap"):self.memory.add(self.root/"memory/answers")

    def test_citation_binding_and_insufficient_abstention(self):
        hits=self.memory.search("beacon")["hits"]
        good={"verdict":"SUPPORT","evidence":[{"citation_id":"D0","sentence":0}],"explanation":"Exact calibration is documented."}
        result=validate_answer(json.dumps(good),hits);self.assertTrue(result["citation_binding_valid"]);self.assertFalse(result["scientific_entailment_verified"])
        for citation in ({"citation_id":"D99","sentence":0},{"citation_id":"D0","sentence":99},{"citation_id":"D0","sentence":True}):
            with self.assertRaises(ValueError):validate_answer(json.dumps({**good,"evidence":[citation]}),hits)
        with self.assertRaises(ValueError):validate_answer(json.dumps({**good,"evidence":[]}),hits)
        self.assertEqual(validate_answer(json.dumps({**good,"verdict":"INSUFFICIENT","evidence":[]}),[])["verdict"],"INSUFFICIENT")

    def test_context_budget_prevents_citing_omitted_sentences(self):
        h=self.memory.search("beacon")["hits"][0];limited=exposed_hits([h],budget=len(h["sentences"][0].encode()))
        self.assertEqual(limited[0]["visible_sentence_ids"],[0])
        with self.assertRaises(ValueError):validate_answer('{"verdict":"SUPPORT","evidence":[{"citation_id":"D0","sentence":1}],"explanation":"x"}',limited)

    def api(self,status=200,content=None):
        seen=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers["Content-Length"])));seen.append(body)
                response={"model":"contract-test-only","choices":[{"message":{"content":json.dumps(content or {"verdict":"SUPPORT","evidence":[{"citation_id":"D0","sentence":0}],"explanation":"Documented code."})},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":20}}
                raw=json.dumps(response).encode();self.send_response(status);self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        return {"base_url":f"http://127.0.0.1:{server.server_port}","model":"contract-test-only","max_tokens":256,"timeout_s":3},seen

    def test_http_contract_and_key_is_not_in_persisted_record(self):
        config,seen=self.api()
        with patch.dict(os.environ,{"RKV_LLM_API_KEY":"fake-contract-secret"}):r=answer(self.memory,"beacon calibration",config=config)
        self.assertTrue(r["accepted"]);self.assertEqual(len(seen),1)
        raw=(self.root/"memory/answers"/(r["writeback"]["answer_id"]+".json")).read_bytes()
        self.assertNotIn(b"fake-contract-secret",raw);self.assertFalse(json.loads(raw)["primary_evidence"])
        self.assertEqual(seen[0]["model"],"contract-test-only")

    def test_http_and_invalid_citations_are_retained_without_retry(self):
        config,seen=self.api(status=503);r=answer(self.memory,"beacon",config=config)
        self.assertFalse(r["accepted"]);self.assertEqual(r["http_status"],503);self.assertEqual(len(seen),1)
        config,seen=self.api(content={"verdict":"SUPPORT","evidence":[{"citation_id":"D77","sentence":0}],"explanation":"bad"})
        r=answer(self.memory,"beacon",config=config);self.assertFalse(r["accepted"]);self.assertEqual(len(seen),1)
        self.assertIn("raw_model_content",r)

    def test_cli_outside_api_and_configuration_validation(self):
        p=subprocess.run([sys.executable,"-m","rkv1","memory-search",str(self.root/"memory"),"beacon"],capture_output=True,text=True,encoding="utf-8")
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)["hits"][0]["key"],"doc:1")
        with patch.dict(os.environ,{"RKV_LLM_BASE_URL":"https://user:password@example.com/v1","RKV_LLM_MODEL":"x"}):
            with self.assertRaises(ValueError):configuration()

    def test_input_query_bounds_and_plain_text_byte_identity(self):
        raw="雪 café\r\nUTF8 note".encode();(self.source/"note.md").write_bytes(raw)
        r=self.memory.add(self.source,label="note");self.assertEqual(self.memory.store.snapshot(r["snapshot_id"]).read_range("note.md"),raw)
        for q,k in (("",5),("x",True),("x",21)):
            with self.assertRaises(ValueError):self.memory.search(q,top_k=k)
