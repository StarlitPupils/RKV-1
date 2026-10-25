import json
import unittest

from rkv1.qasper_audit import cases, score


def source(evidence=('gold',), unanswerable=False):
    return json.dumps({'p1': {'title': 'A', 'abstract': 'abstract', 'full_text': [{'paragraphs':['gold','tail']}],
        'qas': [{'question_id':'q1','question':'Where is the evidence?', 'answers':[{'answer':{'unanswerable':unanswerable,'evidence':list(evidence)}}]}]}}).encode()


def hit(key='qasper:p1', body=None):
    return {'key':key,'citation_id':'D0','title':'A','sentences':body or ['abstract','gold','tail'],'source_bytes_verified':True}


class QASPERAuditTests(unittest.TestCase):
    def test_exact_gold_parent_and_unmapped_evidence_remain_in_denominator(self):
        c,=cases(source());self.assertTrue(c['fully_text_mapped_reference'])
        self.assertTrue(score(c,[hit()])['complete_reference_exposed'])
        self.assertFalse(score(c,[hit(key='qasper:wrong')])['complete_reference_exposed'])
        c,=cases(source(('gold','FLOAT SELECTED Table 1')))
        s=score(c,[hit()]);self.assertFalse(c['fully_text_mapped_reference'])
        self.assertFalse(s['complete_reference_exposed']);self.assertEqual(s['best_reference_paragraph_recall'],.5)
        self.assertEqual(s['failure_or_success_reason'],'no-fully-text-mapped-reference')

    def test_unanswerable_and_empty_references_are_not_awarded_success(self):
        for raw in (source(unanswerable=True),source(())):
            c,=cases(raw);s=score(c,[hit()])
            self.assertIsNone(s['complete_reference_exposed']);self.assertIsNone(s['best_reference_paragraph_recall'])
            self.assertEqual(s['failure_or_success_reason'],'no-nonempty-answerable-reference')

    def test_existing_greedy_budget_can_have_nonmonotonic_gold_coverage(self):
        c,=cases(source());h=hit(body=['x'*8,'gold'])
        self.assertTrue(score(c,[h],budget=4)['complete_reference_exposed'])
        self.assertFalse(score(c,[h],budget=8)['complete_reference_exposed'])
        self.assertEqual(score(c,[h],budget=8)['failure_or_success_reason'],'budget-omitted-reference')
        self.assertGreater(score(c,[h],budget=8)['serialized_context_json_bytes'],8)

    def test_label_schema_and_unverified_hit_rejected(self):
        obj=json.loads(source());obj['p1']['qas'][0]['answers'][0]['answer']['unanswerable']='False'
        with self.assertRaises(ValueError):cases(json.dumps(obj).encode())
        obj=json.loads(source());obj['p1']['qas']*=2
        with self.assertRaises(ValueError):cases(json.dumps(obj).encode())
        c,=cases(source());h=hit();h['source_bytes_verified']=False
        with self.assertRaises(ValueError):score(c,[h])
        with self.assertRaises(ValueError):score(c,[hit()],budget=-1)


if __name__=='__main__':unittest.main()
