import unittest
from fractions import Fraction
from scripts.query_similarity import best_training_match,classify

class SimilarityAuditTests(unittest.TestCase):
    def test_exact_fraction_threshold_order_and_duplicates(self):
        q='alpha beta gamma delta';a='alpha beta gamma delta epsilon';b='alpha beta gamma omega';r=best_training_match(q,[b,a,a])
        self.assertEqual((r['max_jaccard_numerator'],r['max_jaccard_denominator']),(4,5));self.assertTrue(r['near_at_least_four_fifths']);self.assertEqual(len(r['best_train_question_sha256']),1);self.assertFalse(r['is_exact_normalized_question'])
        self.assertEqual(r,best_training_match(q,[a,b]));self.assertFalse(best_training_match(q,[b])['near_at_least_four_fifths'])
    def test_empty_or_disjoint_not_invented_identical_and_normalized_exact(self):
        for q,t in (('',[]),('the and',['the and']),('alpha',['beta'])):
            r=best_training_match(q,t);self.assertFalse(r['near_at_least_four_fifths']);self.assertEqual(r['best_train_question_sha256'],[]);self.assertEqual(r['max_jaccard_numerator'],0)
        self.assertTrue(best_training_match(' Alpha  beta ',['alpha beta'])['is_exact_normalized_question'])
    def test_all_wins_losses_ties_and_complete_transitions_preserved(self):
        base={'a':Fraction(0),'b':Fraction(1),'c':Fraction(1,2)};candidate={'a':Fraction(1),'b':Fraction(0),'c':Fraction(1,2)};near={'a':True,'b':False,'c':False};r=classify(base,candidate,near)
        self.assertEqual([x['direction'] for x in r],['win','loss','tie']);self.assertEqual(sum(Fraction(x['delta_numerator'],x['delta_denominator']) for x in r),0);self.assertTrue(r[0]['candidate_complete']);self.assertTrue(r[1]['base_complete'])
    def test_denominator_or_type_mismatch_refused(self):
        with self.assertRaises(ValueError):classify({'a':Fraction(0)},{},{'a':False})
        with self.assertRaises(ValueError):classify({'a':0.0},{'a':Fraction(0)},{'a':False})
        with self.assertRaises(ValueError):best_training_match({'claim':'alpha'},['alpha'])

if __name__=='__main__':unittest.main()
