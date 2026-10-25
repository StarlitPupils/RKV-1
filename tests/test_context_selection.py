import copy
import unittest

from rkv1.context_selection import choose, lexical_order
from rkv1.qasper_audit import score_selected


def hit(key='qasper:p1',citation='D0',body=None):
    return {'key':key,'citation_id':citation,'title':'Title','sentences':body or ['generic introduction','Neutrino calibration rarevariant'],
            'source_bytes_verified':True,'locator':{'snapshot_id':'a'*64,'path':'papers.json','offset':17,'length':80,'sha256':'b'*64}}


class ContextSelectionTests(unittest.TestCase):
    def test_query_lexical_priority_and_source_sentence_ids(self):
        hits=[hit(body=['x'*30,'Neutrino calibration'])]
        order=lexical_order('neutrino calibration',hits)
        self.assertEqual(order[0],(0,1))
        visible=choose(hits,order,budget=20)
        self.assertEqual(visible[0]['visible_sentence_ids'],[1]);self.assertEqual(visible[0]['locator'],hits[0]['locator'])
        c={'paper_key':'qasper:p1','gold_sets':[['Neutrino calibration']],'fully_text_mapped_reference':True}
        self.assertTrue(score_selected(c,hits,visible,budget=20)['complete_reference_exposed'])

    def test_unicode_cost_ties_fallback_and_every_position_once(self):
        hits=[hit(body=['\u96ea','abc']),hit(key='qasper:p2',citation='D1',body=['def'])]
        self.assertEqual(lexical_order('the and',hits),[(0,0),(0,1),(1,0)])
        self.assertEqual(lexical_order('unmatchedtoken',hits),[(0,0),(0,1),(1,0)])
        self.assertEqual(choose(hits,[(0,0),(0,1),(1,0)],budget=3)[0]['visible_sentence_ids'],[0])
        self.assertEqual(choose(hits,[(0,0),(0,1),(1,0)],budget=0),[])
        with self.assertRaises(ValueError):choose(hits,[(0,0),(0,1),(0,1)])
        with self.assertRaises(ValueError):choose(hits,[(0,0),(0,1),(1,99)])

    def test_forged_selection_paragraph_ids_and_wire_identity_rejected(self):
        hits=[hit()];visible=choose(hits,lexical_order('neutrino',hits),budget=100)
        c={'paper_key':'qasper:p1','gold_sets':[['Neutrino calibration rarevariant']],'fully_text_mapped_reference':True}
        for kind in ('text','locator','id','duplicate'):
            altered=copy.deepcopy(visible)
            if kind=='text':altered[0]['sentences'][0]='fabricated'
            elif kind=='locator':altered[0]['locator']['offset']=0
            elif kind=='id':altered[0]['visible_sentence_ids']=[999]
            else:altered[0]['visible_sentence_ids']=[0,0]
            with self.subTest(kind=kind),self.assertRaises(ValueError):score_selected(c,hits,altered,budget=100)
        with self.assertRaises(ValueError):score_selected(c,hits,visible,budget=1)
        hits[0]['source_bytes_verified']=False
        with self.assertRaises(ValueError):lexical_order('neutrino',hits)


if __name__=='__main__':unittest.main()
