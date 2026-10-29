import unittest,tempfile,sys
from pathlib import Path
from scripts.run_campaign_lifecycle import run_case
class Checks(unittest.TestCase):
 def test_one_owned_response_boundary_parent_complete_and_readonly(self):
  with tempfile.TemporaryDirectory() as t:
   result=run_case('after_response_persist',Path(t)/'case',sys.executable);self.assertEqual(result['before_inspection']['state'],'open_ambiguous');self.assertEqual(result['inspector_or_report_additional_sends'],0);self.assertFalse(result['child_finally_present']);self.assertTrue((Path(t)/'case/parent.json').exists())
