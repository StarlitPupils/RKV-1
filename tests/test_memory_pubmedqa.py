import json
from pathlib import Path
import tempfile
import unittest

from rkv1.core import digest
from rkv1.memory import Memory, _json, records
from rkv1.memory_model import context_payload, exposed_hits
from rkv1.memory_paragraph import ParagraphIndex
from rkv1.memory_pubmedqa import records as pubmed_records


def document(i):
    return {'QUESTION':'QUESTIONONLYQ31','CONTEXTS':[f'Bodybeacon token{i:03d} café 雪.','Exact \"quotes\" and lines\r\nare retained.'],
            'LONG_ANSWER':'ANSWERONLYQ31','LABELS':['SECTIONONLYQ31'],'MESHES':['MESHONLYQ31'],
            'YEAR':'YEARONLYQ31','final_decision':'DECISIONONLYQ31','reasoning_required_pred':'PREDICTIONONLYQ31'}


class PubMedQAMemoryTests(unittest.TestCase):
    def test_original_members_unicode_escaping_offsets_and_projection_whitelist(self):
        docs={'11':document(11),'22':document(22)}
        for escaped in (False,True):
            raw=(json.dumps(docs,ensure_ascii=escaped,indent=2)+'\r\n').encode()
            rows=list(records('original.pubmedqa.json',raw));self.assertEqual(len(rows),2)
            for key,title,body,offset,member,kind in rows:
                self.assertEqual(raw[offset:offset+len(member)],member)
                parsed,=list(pubmed_records(member,1<<20));self.assertEqual(parsed[:3],(key,title,body))
                pmid=key.split(':')[1];self.assertEqual(title,'PMID '+pmid)
                self.assertEqual(body,docs[pmid]['CONTEXTS']);self.assertEqual(kind,'pubmedqa-json-member-v1')
                self.assertNotIn('QUESTIONONLYQ31',title+' '.join(body))
            with self.assertRaises(ValueError):list(records('ambiguous.json',raw))

    def test_all_metadata_excluded_from_both_retrievers_and_model_context(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();(src/'original.pubmedqa.json').write_bytes(_json({'11':document(11)}))
            m=Memory.create(root/'memory');m.add(src);side=ParagraphIndex.create(m,root/'sidecar')['index']
            for marker in ('QUESTIONONLYQ31','ANSWERONLYQ31','SECTIONONLYQ31','MESHONLYQ31','YEARONLYQ31','DECISIONONLYQ31','PREDICTIONONLYQ31'):
                self.assertEqual(m.search(marker)['hits'],[]);self.assertEqual(side.search(m,marker)['hits'],[])
            for found in (m.search('Bodybeacon'),side.search(m,'Bodybeacon')):
                h,=found['hits'];self.assertEqual(h['sentences'],document(11)['CONTEXTS'])
                payload=json.dumps(context_payload(exposed_hits(found['hits'],budget=48000)))
                self.assertNotIn('QUESTIONONLYQ31',payload);self.assertNotIn('ANSWERONLYQ31',payload)
                loc=h['locator'];member=m.store.snapshot(m.current()).read_range(loc['path'],loc['offset'],loc['length'])
                self.assertEqual(digest(member),loc['sha256']);self.assertIn(b'ANSWERONLYQ31',member)

    def test_v3_and_v4_history_renames_question_rebinding_and_true_body_edit(self):
        for profile in ('compact-budget-v3','compact-projection-v4'):
            with self.subTest(profile=profile),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);src=root/'source';src.mkdir();path=src/'first.pubmedqa.json';docs={str(100+i):document(i) for i in range(20)}
                path.write_bytes(_json(docs));m=Memory.create(root/'memory',index_profile=profile);old=m.add(src)['snapshot_id']
                first=m.lookup('pubmedqa:100')['hits'][0]
                for d in docs.values():d['QUESTION']+=' changed annotation';d['LONG_ANSWER']+=' longer ignored annotation'
                path.unlink();path=src/'renamed.pubmedqa.json';path.write_text(json.dumps(dict(reversed(list(docs.items()))),ensure_ascii=True,indent=3),encoding='utf-8')
                added=m.add(src,label='metadata')
                if profile=='compact-projection-v4':self.assertEqual(added['overlay_rebindings'],20);self.assertEqual(added['overlay_upserts'],0)
                h=m.lookup('pubmedqa:100')['hits'][0];self.assertEqual(h['sentences'],first['sentences']);self.assertEqual(h['locator']['path'],path.name)
                self.assertEqual(m.lookup('pubmedqa:100',snapshot=old)['hits'][0],first)
                docs['100']['CONTEXTS'][0]+=' FUTUREBODYQ31';path.write_bytes(_json(docs));m.add(src,label='body')
                self.assertTrue(m.search('FUTUREBODYQ31')['hits']);self.assertFalse(m.search('FUTUREBODYQ31',snapshot=old)['hits'])
                self.assertFalse(m.search('QUESTIONONLYQ31')['hits']);self.assertFalse(m.search('ANSWERONLYQ31')['hits'])

    def test_duplicate_nonfinite_schema_invalid_ids_and_large_member_rejected(self):
        invalid=(b'{"11":{"CONTEXTS":[]},"11":{"CONTEXTS":[]}}',b'{"11":{"CONTEXTS":[],"x":NaN}}',
                 b'{"0":{"CONTEXTS":[]}}',b'{"01":{"CONTEXTS":[]}}',b'{"-1":{"CONTEXTS":[]}}',
                 b'{"x":{"CONTEXTS":[]}}',b'{"11":{"CONTEXTS":"bad"}}',b'{"11":{"CONTEXTS":[1]}}',b'{"11":{}}')
        for raw in invalid:
            with self.subTest(raw=raw),self.assertRaises(ValueError):list(pubmed_records(raw,1<<20))
        with self.assertRaisesRegex(ValueError,'exceeds'):list(pubmed_records(_json({'11':{'CONTEXTS':[],'LONG_ANSWER':'x'*(1<<20)}}),1<<20))
        key,title,body,*_=next(pubmed_records(b'{"11":{"CONTEXTS":[]}}',1<<20));self.assertEqual((key,title,body),('pubmedqa:11','PMID 11',[]))

    def test_corrupted_original_cas_cannot_be_served(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();(src/'original.pubmedqa.json').write_bytes(_json({'11':document(11)}))
            m=Memory.create(root/'memory');sid=m.add(src)['snapshot_id'];side=ParagraphIndex.create(m,root/'sidecar')['index']
            ref=m.store.snapshot(sid).files['original.pubmedqa.json']['chunks'][0];path=m.store.object_path(ref['id'])
            raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
            with self.assertRaises(ValueError):m.search('Bodybeacon')
            with self.assertRaises(ValueError):side.search(m,'Bodybeacon')
