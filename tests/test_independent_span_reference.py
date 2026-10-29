import json
import unittest
from scripts.independent_span_reference import original_record, reference_tokens, sha
from scripts.sentence_spans import locate


class OwnedIndependentReference(unittest.TestCase):
    def test_all_positions_match_independent_byte_parser(self):
        for field in ('abstract', 'sentences'):
            raw = json.dumps({'nested': {field: ['same']}, 'label': '\u4e2d', field: ['same', 'same', 'escape " \\ \n \u03b1', '']}, ensure_ascii=False, indent=1).encode()
            self.assertEqual(reference_tokens(raw, field=field), locate(raw, field=field)['sentences'])

    def test_complete_jsonl_bounds_and_subrecord_refusal(self):
        first = b'{"nested":{"abstract":["same"]}}\r\n'
        second = b'{"abstract":["same"]}'
        source = first + second
        self.assertEqual(original_record(source, expected_source_sha256=sha(source), record_offset=len(first), record_length=len(second)), second)
        inner = b'{"abstract":["same"]}'
        with self.assertRaises(ValueError):
            original_record(source, expected_source_sha256=sha(source), record_offset=first.index(inner), record_length=len(inner))
        for offset, length, source_sha in [(False, len(first), sha(source)), (0, len(first)-2, sha(source)), (len(first), len(second), '0'*64)]:
            with self.assertRaises(ValueError):
                original_record(source, expected_source_sha256=source_sha, record_offset=offset, record_length=length)


if __name__ == '__main__':
    unittest.main()
