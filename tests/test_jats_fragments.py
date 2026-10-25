import copy
import unittest

from rkv1.core import digest
from rkv1.jats_fragments import fragments, verify
from tests.test_memory_jats import article


class JATSFragmentTests(unittest.TestCase):
    def test_byte_ranges_unicode_quotes_comments_cdata_and_empty(self):
        raw = b'\xef\xbb\xbf' + article(body='\u96ea &amp; caf\u00e9 <italic>inline</italic><!-- > --><![CDATA[ <x> ]]>',
            extra='<p id="a&gt;b" data-x="&quot; >">Second</p><p/><p id="empty" />') + b'\r\n'
        rows = fragments(raw)
        self.assertEqual([r['role'] for r in rows], ['title', 'abstract', 'body', 'body', 'body', 'body'])
        self.assertEqual(rows[2]['text'], '\u96ea & caf\u00e9 inline <x>')
        self.assertTrue(verify(raw, rows[2]).startswith('<p>\u96ea &amp; caf\u00e9'.encode()))
        for row in rows:
            original = verify(raw, row)
            self.assertEqual(digest(original), row['sha256'])
            self.assertEqual(row['parent_sha256'], digest(raw))
        self.assertEqual(verify(raw, rows[-2]), b'<p/>')
        self.assertEqual(verify(raw, rows[-1]), b'<p id="empty" />')
        self.assertTrue(rows[3]['key'].endswith('id:a%3Eb'))

    def test_exclusions_nested_paragraphs_and_same_lexical_projection(self):
        raw = article(extra='<fig><p>FIGSECRET</p></fig><table-wrap><p>TABLESECRET</p></table-wrap>'
            '<p id="outer">Outer <p>nested</p> tail</p><p>final</p>')
        rows = fragments(raw)
        self.assertEqual([r['text'] for r in rows[2:]], ['Rare variants beacon.', 'Outer nested tail', 'final'])
        self.assertNotIn('SECRET', ' '.join(r['text'] for r in rows))
        self.assertEqual(verify(raw, rows[3]), b'<p id="outer">Outer <p>nested</p> tail</p>')

    def test_parent_identity_range_and_projection_tampering_rejected(self):
        raw = article()
        original = fragments(raw)[2]
        for field, value in [('parent_key', 'elife:99'), ('parent_sha256', '0'*64), ('offset', 0),
                             ('length', 1), ('sha256', '0'*64), ('text', 'fabricated'),
                             ('role', 'title'), ('selector', 'pos:99'), ('key', 'unknown')]:
            altered = copy.deepcopy(original); altered[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify(raw, altered)
        with self.assertRaises(ValueError): verify(article(2), original)
        with self.assertRaises(ValueError): verify(raw+b'\n', original)

    def test_key_policies_insertions_duplicates_and_restrictions(self):
        before = article(extra='<p id="anchor">Stable anchor</p><p>Ordinal tail</p>')
        after = before.replace(b'<p id="anchor">', b'<p>Inserted</p><p id="anchor">')
        a = next(r for r in fragments(before) if r['text'] == 'Stable anchor')
        b = next(r for r in fragments(after) if r['text'] == 'Stable anchor')
        self.assertEqual(a['key'], b['key']); self.assertEqual(a['sha256'], b['sha256'])
        self.assertNotEqual(a['offset'], b['offset'])
        a = next(r for r in fragments(before, mode='position') if r['text'] == 'Stable anchor')
        b = next(r for r in fragments(after, mode='position') if r['text'] == 'Stable anchor')
        self.assertNotEqual(a['key'], b['key'])
        duplicate = article(extra='<p id="dup">One</p><p id="dup">Two</p>')
        with self.assertRaisesRegex(ValueError, 'Duplicate'): fragments(duplicate)
        self.assertEqual(len(fragments(duplicate, mode='position')), 5)
        for raw in (article().replace(b'UTF-8', b'ISO-8859-1'), article()[:-3], b'x'*((1<<20)+1),
                    article().replace(b'<body>', b'<body>&unbound;', 1)):
            with self.subTest(raw=raw[:60]), self.assertRaises((ValueError, UnicodeError)): fragments(raw)
        with self.assertRaises(ValueError): fragments(article(), mode='unknown')


if __name__ == '__main__': unittest.main()
