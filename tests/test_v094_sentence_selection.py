import unittest
from scripts.view_sentence_choice import select_indices


class OwnedSelectionChecks(unittest.TestCase):
    def test_overlap_changes_selection_without_gold_and_keeps_source_order(self):
        rows=['unrelated owned line', 'beta result', 'alpha alpha result', 'alpha beta result']
        self.assertEqual(select_indices('alpha alpha beta',rows,method='first_two'),[0,1])
        self.assertEqual(select_indices('alpha alpha beta',rows,method='overlap_two'),[2,3])

    def test_duplicate_ties_zero_overlap_short_empty_are_deterministic(self):
        self.assertEqual(select_indices('alpha',['same','same','same'],method='overlap_two'),[0,1])
        self.assertEqual(select_indices('alpha',[],method='overlap_two'),[])
        self.assertEqual(select_indices('alpha',[''],method='overlap_two'),[0])

    def test_explicit_method_source_types_and_oracle_argument_refuse(self):
        for q,ss,m in [(None,[],'first_two'),(' ',[],'first_two'),('alpha',[1],'overlap_two'),('alpha',[],'oracle')]:
            with self.assertRaises(ValueError):select_indices(q,ss,method=m)
        with self.assertRaises(TypeError):select_indices('alpha',['a'],method='first_two',gold_indices=[0])


if __name__ == '__main__':unittest.main()
