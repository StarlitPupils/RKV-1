import json
from pathlib import Path
import tempfile
import unittest

from rkv1.memory import Memory,records
from rkv1.memory_qasper import members


def paper(title='Silver calibration'):
    return {'title':title,'abstract':'Neutrino precision café 雪.',
            'full_text':[{'section_name':None,'paragraphs':['Rare variants confirm beacon.']}],
            'qas':[{'question':'ANNOTATIONONLYQ9','answers':[{'answer':'PRIVATEANSWERQ9'}]}]}


class QasperMemoryTests(unittest.TestCase):
    def test_exact_unicode_and_escape_offsets_and_individual_member_reparse(self):
        for ascii_only in (True,False):
            raw=(json.dumps({'é雪':paper(),'second':paper('Second title')},ensure_ascii=ascii_only,indent=2)+'\r\n').encode()
            parsed=list(records('papers.json',raw));self.assertEqual(len(parsed),2)
            for key,title,body,offset,original,kind in parsed:
                self.assertEqual(original,raw[offset:offset+len(original)])
                one=list(records('papers.json',original));self.assertEqual(one,[(key,title,body,0,original,kind)])
                self.assertNotIn('ANNOTATIONONLYQ9',' '.join(body))
                self.assertNotIn('PRIVATEANSWERQ9',' '.join(body))

    def test_duplicate_keys_truncation_trailing_data_and_wrong_schema_rejected(self):
        value=json.dumps(paper()).encode();member=b'"paper":'+value
        bad=[b'{'+member+b','+member+b'}',b'{'+member+b',}',b'{'+member,
             b'{'+member+b'}garbage',member+b',',b'{"paper":{"title":"x","title":"y"}}',
             b'{"paper":{"title":"x","abstract":"y","full_text":[{"paragraphs":[17]}]}}',
             b'{"paper":{"title":"x","abstract":"y","full_text":[],"other":NaN}}',b'{}x']
        for raw in bad:
            with self.subTest(raw=raw[:40]):
                with self.assertRaises((ValueError,UnicodeError)):list(records('paper.json',raw))

    def test_empty_and_oversized_members_and_literal_punctuation(self):
        self.assertEqual(list(members(b'{}')),[])
        obj=paper('Quotes " } ] : , \\ are text');raw=json.dumps({'id':obj}).encode()
        self.assertEqual(list(records('paper.json',raw))[0][1],obj['title'])
        obj['abstract']='x'*(1<<20)
        with self.assertRaisesRegex(ValueError,'1 MiB'):list(records('paper.json',json.dumps({'id':obj}).encode()))

    def test_full_and_incremental_indexes_match_and_annotations_stay_unsearchable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();path=source/'qasper-dev-v0.1.json'
            docs={str(i):paper(f'Silver calibration {i}') for i in range(12)}
            path.write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf-8')
            full=Memory.create(root/'full',index_profile='compact-full-v2');incremental=Memory.create(root/'delta')
            first=[]
            for m in (full,incremental):
                first.append(m.add(source,label='original')['snapshot_id'])
                self.assertFalse(m.search('ANNOTATIONONLYQ9')['hits']);self.assertFalse(m.search('PRIVATEANSWERQ9')['hits'])
            docs['0']['full_text'][0]['paragraphs'][0]+=' QASPERUPDATEQ9'
            path.write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf-8')
            for m in (full,incremental):m.add(source,label='edit')
            for q in ('calibration','rare variants','QASPERUPDATEQ9'):
                xs=full.search(q,top_k=10)['hits'];ys=incremental.search(q,top_k=10)['hits']
                self.assertEqual(xs,ys)
            self.assertFalse(incremental.search('QASPERUPDATEQ9',snapshot=first[1])['hits'])
            hit=incremental.search('QASPERUPDATEQ9')['hits'][0];loc=hit['locator']
            original=path.read_bytes()[loc['offset']:loc['offset']+loc['length']]
            self.assertEqual(list(records(path.name,original))[0][0],hit['key'])
            # Real releases keep their versioned filenames, making a path-only
            # update count as an upsert rather than silently aliasing paths.
            target=source/'qasper-dev-v0.2.json';path.rename(target)
            result=incremental.add(source,label='renamed-release')
            self.assertEqual(result['delta_depth'],0)
            self.assertEqual(incremental.search('QASPERUPDATEQ9')['hits'][0]['locator']['path'],target.name)


if __name__=='__main__':unittest.main()
