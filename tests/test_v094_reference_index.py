import copy
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_v094_view_campaign as fixtures
from scripts.audit_evidence_view_index import ReferenceIndex
from scripts.view_slow_reference import rank_original


class ReferenceAuditIndexTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.OwnedModelCampaign(methodName='test_oracle_fields_and_normalized_duplicate_rejected_before_model_load')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.ref=ReferenceIndex(self.fixture.raw,expected_source_sha256=hashlib.sha256(self.fixture.raw).hexdigest())

    def test_cached_source_rank_and_all_three_packets_match_independent_slow_reference(self):
        for query in ('alpha beta','gamma alpha alpha','zzznomatch'):
            self.assertEqual(self.ref.rank(query),rank_original(self.fixture.raw,query))
        for method in ('whole_record','first_two','overlap_two'):
            out=self.fixture.root/('cached-'+method);self.fixture.call(method,out)
            for i in (0,1):
                row=json.loads((out/f'prediction-{i}.json').read_bytes())
                self.assertEqual(self.ref.verify_prediction(row,method,expected_sid=self.fixture.sid),row['result']['source_verification']['available_original_sentence_indices'])

    def test_wrong_source_binding_rank_and_body_refuse(self):
        with self.assertRaises(ValueError):ReferenceIndex(self.fixture.raw,expected_source_sha256='0'*64)
        out=self.fixture.root/'tamper';self.fixture.call('overlap_two',out)
        original=json.loads((out/'prediction-0.json').read_bytes())
        for kind in ('rank','range','body'):
            row=copy.deepcopy(original)
            if kind=='rank':row['result']['ordered_candidate_ids'].reverse()
            elif kind=='range':row['result']['trusted_records'][0]['binding']['record_offset']+=1
            else:row['result']['view']['encoded_hex']='7b7d'
            with self.assertRaises((ValueError,AssertionError)):self.ref.verify_prediction(row,'overlap_two',expected_sid=self.fixture.sid)
