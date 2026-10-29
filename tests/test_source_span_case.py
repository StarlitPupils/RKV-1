import tempfile
from pathlib import Path
import unittest
from scripts.run_source_spans import run_case
from scripts.source_span_fixture import fixture
from scripts.independent_span_reference import original_record, reference_tokens


class OwnedSpanCase(unittest.TestCase):
    def test_one_tiny_store_case_and_independent_original_boundaries(self):
        # Only smallest fixture, not any formal 17/65-record performance pretest.
        with tempfile.TemporaryDirectory() as tmp:
            case = run_case(Path(tmp)/'case', 3, 'utf8_compact')
            source, _ = fixture(3, 'utf8_compact')
            self.assertEqual(len(case['rows']), 3)
            self.assertEqual(len(case['controls']), 6)
            for row in case['rows']:
                b = row['binding']
                raw = original_record(source, expected_source_sha256=b['source_sha256'], record_offset=b['record_offset'], record_length=b['record_length'])
                ref = reference_tokens(raw, field=b['field'])
                self.assertEqual(row['witness']['sentences'], [ref[0], ref[2]])
                self.assertEqual(row['application_record_return_B'], 2*len(raw))
            self.assertTrue(all(c['refused'] for c in case['controls']))


if __name__ == '__main__':
    unittest.main()
