import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rkv1.memory import Memory,records
from rkv1.core import digest


def article(i=1,title='Calibration café 雪',body='Rare variants beacon.',extra='',meta=''):
    return (f'<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE article SYSTEM "https://unreachable.invalid/jats.dtd">'
            f'<article article-type="research-article"><front><article-meta><article-id pub-id-type="publisher-id">{i}</article-id>'
            f'<article-id pub-id-type="doi">10.7554/eLife.{i}</article-id><title-group><article-title>{title}</article-title></title-group>'
            f'<abstract><p>Neutrino <italic>precision</italic> &amp; light.</p></abstract>{meta}</article-meta></front>'
            f'<body><sec><title>Heading not indexed</title><p>{body}</p>{extra}</sec></body>'
            f'<sub-article><body><p>REVIEWPRIVATEQ23</p></body></sub-article></article>').encode()


class JATSMemoryTests(unittest.TestCase):
    def test_exact_file_record_inline_projection_and_exclusions(self):
        raw=article(extra='<fig><caption><p>FIGPRIVATEQ23</p></caption></fig><table-wrap><p>TABLEPRIVATEQ23</p></table-wrap>')+b'\r\n'
        row,=records('article.xml',raw)
        self.assertEqual(row[0],'elife:1');self.assertEqual(row[2],['Neutrino precision & light.','Rare variants beacon.'])
        self.assertEqual(row[3:],(0,raw,'elife-jats-article-v1'))
        self.assertEqual(list(records('renamed.xml',row[4])),[row])

    def test_duplicate_identity_schema_truncation_entities_and_size_rejected(self):
        raw=article()
        bad=[raw[:-8],raw+b'x',raw.replace(b'10.7554/eLife.1',b'10.7554/eLife.2'),raw.replace(b'<body>',b'<body/><body>',1),
             raw.replace(b'</article-meta>',b'<article-id pub-id-type="publisher-id">1</article-id></article-meta>'),
             raw.replace(b'article-type="research-article"',b'article-type="review"'),
             b'<!DOCTYPE article [<!ENTITY test "EXPAND">]>'+raw[raw.index(b'<article '):],
             b'<!DOCTYPE article [<!ENTITY test SYSTEM "file:///secret">]>'+raw[raw.index(b'<article '):].replace(b'beacon.',b'&test;')]
        for value in bad:
            with self.subTest(value=value[:35]):
                with self.assertRaises(ValueError):list(records('a.xml',value))
        with self.assertRaisesRegex(ValueError,'1 MiB'):list(records('a.xml',b'x'*((1<<20)+1)))

    def test_real_text_update_metadata_rebind_renames_and_old_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir()
            for i in range(1,13):(source/f'{i}-v1.xml').write_bytes(article(i))
            full=Memory.create(root/'full',index_profile='compact-full-v2');m=Memory.create(root/'v4',index_profile='compact-projection-v4')
            full.add(source,label='first');first=m.add(source,label='first')['snapshot_id']
            for p in list(source.iterdir()):
                i=int(p.name.split('-')[0]);p.unlink();(source/f'{i}-v2.xml').write_bytes(article(i,meta='<custom-meta>METAPRIVATEQ23</custom-meta>'))
            full.add(source,label='meta');result=m.add(source,label='meta')
            self.assertEqual(result['overlay_rebindings'],12);self.assertEqual(result['replay_budget']['cas_bytes'],0)
            (source/'1-v2.xml').write_bytes(article(1,body='Rare variants TRUEBODYQ23.'))
            full.add(source,label='body');result=m.add(source,label='body');self.assertEqual(result['overlay_upserts'],1)
            for q in ('precision','rare variants','TRUEBODYQ23','METAPRIVATEQ23','REVIEWPRIVATEQ23'):
                self.assertEqual(full.search(q,top_k=20)['hits'],m.search(q,top_k=20)['hits'])
            self.assertFalse(m.search('TRUEBODYQ23',snapshot=first)['hits'])
            hit=m.search('TRUEBODYQ23')['hits'][0];loc=hit['locator'];self.assertEqual(loc['sha256'],digest((source/loc['path']).read_bytes()))
            self.assertEqual(loc['offset'],0)


if __name__=='__main__':unittest.main()
