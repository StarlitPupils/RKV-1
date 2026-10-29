import copy
import json
import unittest
from scripts.sentence_spans import locate, recover, digest


class OwnedSentenceSpans(unittest.TestCase):
    def test_utf8_escaped_and_duplicate_text_positions(self):
        raw = b'{"nested":{"sentences":["decoy"]},"sentences":["same","same","\\u4e2d\\n"],"tail":true}'
        result = locate(raw)
        self.assertNotEqual(result['sentences'][0]['offset'], result['sentences'][1]['offset'])
        for row in result['sentences']:
            self.assertEqual(json.loads(recover(raw, row, expected_record_sha256=digest(raw))), ['same', 'same', '\u4e2d\n'][row['sentence_index']])
        raw = json.dumps({'title': '\u4e2d\u6587', 'sentences': ['\u03b1', 'quote " and slash \\']}, ensure_ascii=False, indent=2).encode()
        result = locate(raw)
        self.assertEqual(json.loads(recover(raw, result['sentences'][0], expected_record_sha256=digest(raw))), '\u03b1')

    def test_no_sentence_and_empty_sentence_are_distinct(self):
        self.assertEqual(locate(b'{"sentences": []}')['sentences'], [])
        raw = b'{"sentences":[""]}'
        row = locate(raw)['sentences'][0]
        self.assertEqual(recover(raw, row, expected_record_sha256=digest(raw)), b'""')

    def test_wrong_external_identity_wrong_position_and_token_rejected(self):
        raw = b'{"sentences":["same","same"]}'
        row = locate(raw)['sentences'][0]
        with self.assertRaises(ValueError):
            recover(raw, row, expected_record_sha256='0' * 64)
        for field, value in [('sentence_index', 1), ('offset', row['offset'] + 1), ('length', 1000), ('token_sha256', '0' * 64), ('offset', True)]:
            damaged = copy.deepcopy(row)
            damaged[field] = value
            with self.assertRaises(ValueError):
                recover(raw, damaged, expected_record_sha256=digest(raw))

    def test_malformed_duplicate_members_nontext_and_nonfinite_rejected(self):
        for raw in [b'{"sentences":[],"sentences":[]}', b'{"nested":{"a":1,"a":2},"sentences":[]}', b'{"sentences":[1]}', b'{"sentences":null}', b'{"sentences":[],"bad":NaN}', b'{"sentences":[]} trailing']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                locate(raw)


if __name__ == '__main__':
    unittest.main()
