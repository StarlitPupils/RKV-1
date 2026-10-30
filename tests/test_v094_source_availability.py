import unittest
from scripts.source_availability_metrics import score


class PostpredictionSourceMetrics(unittest.TestCase):
    def test_partial_paper_coverage_and_complete_alternative_are_separate(self):
        gold={'1':[{'sentences':[0,1]},{'sentences':[2]}],'2':[{'sentences':[0]}]}
        a=score({'doc:1':[0]},gold)
        self.assertEqual(a['paper_recall'],.5);self.assertFalse(a['complete_rationale_available'])
        b=score({'doc:1':[2]},gold)
        self.assertEqual(b['paper_recall'],.5);self.assertTrue(b['complete_rationale_available'])
        self.assertFalse(score({},gold)['complete_rationale_available'])

    def test_unannotated_quality_null_not_false_and_bad_indices_refuse(self):
        self.assertIsNone(score({'doc:1':[0]}, {})['complete_rationale_available'])
        self.assertIsNone(score({}, {})['paper_recall'])
        for available,gold in [({'doc:1':[True]},{}),({'doc:1':[0,0]},{}),({}, {'1':[{'sentences':[]}]}),({}, {'1':[{'sentences':[False]}]})]:
            with self.assertRaises(ValueError):score(available,gold)
