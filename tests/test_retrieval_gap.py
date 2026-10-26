import itertools
import random
import unittest
from scripts.retrieval_gap import oracle,partition,CATEGORIES


class RetrievalGapTests(unittest.TestCase):
    def test_shortest_gold_oracle_matches_exhaustive_unit_value_bound(self):
        rng=random.Random(52027)
        for _ in range(32):
            loc={str(i):{'length':rng.randrange(1,40)} for i in range(8)};gold=set(loc)|{'unresolved'};budget=rng.randrange(0,120);cap=rng.randrange(1,9)
            expected=max(len(combo) for size in range(9) for combo in itertools.combinations(loc,size) if len(combo)<=cap and sum(loc[k]['length'] for k in combo)<=budget)
            result=oracle(loc,gold,max_facts=cap,max_source_bytes=budget)
            self.assertEqual(result['recovered_groups'],expected);self.assertFalse(result['complete_possible'])
            self.assertLessEqual(result['selected_bytes'],budget)
        self.assertEqual(oracle({'a':{'length':4}},{'a'},max_source_bytes=4)['recovered_groups'],1)
        self.assertEqual(oracle({'a':{'length':4}},{'a'},max_source_bytes=3)['recovered_groups'],0)
        self.assertEqual(oracle({'a':{'length':4}},{'a'},candidates=[])['recovered_groups'],0)

    def test_partition_exhaustive_ordered_cases_and_no_causal_claim(self):
        loc={k:{'length':1} for k in ('hit','too-late','budget','absent')}
        r=partition(loc,['hit','budget','too-late'],['hit'],{'hit','too-late','budget','absent','unresolved'},max_facts=2)
        self.assertEqual(r['categories_by_group'],{'hit':'recovered','too-late':'below_count_prefix','budget':'byte_budget_excluded','absent':'no_candidate','unresolved':'unresolved_source'})
        self.assertEqual(set(r['counts']),set(CATEGORIES));self.assertEqual(sum(r['counts'].values()),5)
        with self.assertRaises(ValueError):partition(loc,['hit'],['absent'],{'hit'})
