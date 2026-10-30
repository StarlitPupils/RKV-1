import hashlib,json,unittest
from pathlib import Path
import test_v094_view_campaign as fixtures
from scripts.run_evidence_view_plan import run_plan,ORDER
from scripts.audit_evidence_view_index import ReferenceIndex
from scripts.score_evidence_view_cohort import score_completed


class OwnedFreshProcessPlan(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.OwnedModelCampaign(methodName='test_oracle_fields_and_normalized_duplicate_rejected_before_model_load')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        f=self.fixture;q=f.root/'questions.json';q.write_text(json.dumps([{'claim_id':x['id'],'claim':x['question']} for x in f.questions]))
        self.config=f.root/'config.json';self.config.write_text(json.dumps({'store_root':str(f.store.root),'sid':f.sid,'model_path':str(f.model),'model_sha':f.sha,'questions_path':str(q),'questions_sha':hashlib.sha256(q.read_bytes()).hexdigest(),'expected_questions':2,'owned_fixture':True,'deadline':None}))

    def test_nine_fresh_children_original_rank_views_and_gold_after_complete(self):
        f=self.fixture;out=f.root/'fresh-plan';rows=run_plan(self.config,out)
        self.assertEqual([r['method'] for r in rows],[m for group in ORDER for m in group])
        self.assertTrue(all(r['exit_code']==0 and r['parent_full_wall_s']>0 for r in rows))
        ref=ReferenceIndex(f.raw,expected_source_sha256=hashlib.sha256(f.raw).hexdigest())
        gold_calls=[]
        def gold():gold_calls.append(1);return {'owned-1':{'0':[{'sentences':[1]}]},'owned-empty':{}}
        result=score_completed([out/r['case'] for r in rows],f.questions,gold,lambda row,method:ref.verify_prediction(row,method,expected_sid=f.sid))
        self.assertEqual(len(result),18);self.assertEqual(gold_calls,[1])
        with self.assertRaises(FileExistsError):run_plan(self.config,out)

    def test_parent_quota_failure_stops_unstarted_workers_and_keeps_planned_denominator(self):
        count=0
        def guard():
            nonlocal count
            count+=1
            if count==2:raise RuntimeError('Owned stop before second child')
        out=self.fixture.root/'partial-plan'
        with self.assertRaises(RuntimeError):run_plan(self.config,out,guard=guard)
        final=json.loads((out/'plan-finally.json').read_bytes())
        self.assertEqual((final['completed_workers'],final['planned_workers'],final['planned_predictions']),(1,9,18));self.assertFalse(final['success'])
        self.assertFalse((out/'round-1-first_two').exists())
