import unittest
from scripts.api_replication_plan import select_replication
from scripts.api_campaign import validate_inputs

def fixture():
    return [{'id': i, 'claim': 'Owned claim ' + str(i),
             'evidence': {} if i >= 20 else {'1': [{'label': 'SUPPORT' if i < 10 else 'CONTRADICT', 'sentences': [0]}]}}
            for i in range(30)]

class ReplicationPlanTests(unittest.TestCase):
    def test_exclusions_and_reordered_input(self):
        rows = fixture()
        a = select_replication(rows, ['0'], ['Owned claim 1'])
        self.assertEqual(a, select_replication(list(reversed(rows)), ['0'], ['Owned claim 1']))
        self.assertFalse({'0', '1'} & set(a['selected_claim_ids']))

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            select_replication(fixture() + [fixture()[0]])

    def test_insufficient_stratum_rejected(self):
        with self.assertRaises(ValueError):
            select_replication(fixture(), range(6))

    def test_normalized_question_exclusion(self):
        p = select_replication(fixture(), (), ['  OWNED  claim 0 '])
        self.assertNotIn('0', p['selected_claim_ids'])

    def test_all_conditions_and_donor_validation(self):
        rows = fixture(); p = select_replication(rows)
        q = {str(c['id']): c['claim'] for c in rows if str(c['id']) in p['selected_claim_ids']}
        validate_inputs(p, q)
        self.assertEqual(len(p['jobs']), 48)
        p['jobs'][0] = p['jobs'][1].copy()
        with self.assertRaises(ValueError):
            validate_inputs(p, q)
