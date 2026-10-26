import json
from pathlib import Path
import tempfile
import unittest
from rkv1.core import digest
from rkv1.store import Store
from scripts.source_alignment import corpus_records,alignments,verify_binding


class SourceAlignmentTests(unittest.TestCase):
    def test_original_member_offsets_aliases_unicode_and_rejections(self):
        raw=b'{\r\n"z": "\\u96ea",\r\n"a": "'+ '\u96ea'.encode() +b'",\r\n"b": "other"\r\n}'
        facts,aliases=corpus_records(raw);self.assertEqual(aliases,{'z':'a','a':'a','b':'b'})
        self.assertEqual(set(facts),{'a','b'})
        for key,rec in facts.items():
            original=raw[rec['offset']:rec['offset']+rec['length']]
            self.assertEqual(digest(original),rec['sha256']);self.assertEqual(json.loads(b'{'+original+b'}'),{key:rec['text']})
        for bad in (b'{"a":"x","a":"y"}',b'{"a":1}',b'"a":"x"',b'{}',raw+b'trailing'):
            with self.assertRaises(ValueError):corpus_records(bad)

    def test_uuid_precedence_literal_fallback_and_unresolved_are_distinct(self):
        facts,aliases=corpus_records(b'{"a":"Original fact.","alias":"Original fact.","b":"Exact annotation."}')
        row={'proof':'sent1 & sent2 -> int1: fixture; int1 & sent3 -> hypothesis;','meta':{
            'triples':{'sent1':'Paraphrased annotation.','sent2':'Exact annotation.','sent3':'exact annotation.'},
            'worldtree_provenance':{'sent1':{'uuid':'alias'},'sent2':{'uuid':''},'sent3':{'uuid':''}}}}
        r=alignments(row,facts,aliases)
        self.assertEqual([x['resolution'] for x in r],['provided_UUID','exact_decoded_text','unresolved'])
        self.assertEqual([x['fact_id'] for x in r],['a','b',None]);self.assertEqual([x['annotation_exact'] for x in r],[False,True,None])
        with self.assertRaises(ValueError):alignments({**row,'proof':''},facts,aliases)

    def test_actual_store_original_range_and_damage_rejection(self):
        raw=json.dumps({'a':'Synthetic '+ '\u96ea'*24000,'b':'Fixture.'},ensure_ascii=False).encode()
        facts,aliases=corpus_records(raw)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();(src/'corpus.json').write_bytes(raw)
            store=Store.create(root/'store',compression='zlib',chunk_size=65536,io_backend='bounded');sid=store.add(src)['snapshot_id']
            with store.snapshot(sid) as snap:
                loc=verify_binding(snap,facts,'a');self.assertEqual(loc['snapshot_id'],sid)
                self.assertEqual(snap.read_range('corpus.json'),raw)
                ref=snap.files['corpus.json']['chunks'][0]
            path=store.object_path(ref['id']);broken=bytearray(path.read_bytes());broken[-1]^=1;path.write_bytes(broken)
            with self.assertRaises(ValueError),store.snapshot(sid) as snap:verify_binding(snap,facts,'a')
