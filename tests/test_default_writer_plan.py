import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.default_writer_plan import load_plan
from scripts.writer_scope_fixture import source, sha, ledger
from scripts.run_default_writer_plan import run
from scripts.audit_default_writer_plan import audit


class DefaultWriterPlanTests(unittest.TestCase):
    def plan(self):
        plan = json.loads(Path('docs/memory-default-writer-plan.json').read_bytes())
        plan['mode'] = 'owned-test'
        plan['schedule'] = [{'id':f'r1-n9-{p}', 'round':1, 'size':9, 'phase':p}
                            for p in ('before_HEAD', 'after_HEAD', 'clean_return')]
        plan['counts'] = {name:value//9 for name, value in plan['counts'].items()}
        plan['fixture_files'] = {f'9:{e}':{'bytes':len(source(9,e)), 'sha256':sha(source(9,e))}
                                 for e in (0,1,2)}
        return plan

    def test_real_cli_and_owner_exits_match_pinned_tiny_schedule(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'plan.json'
            path.write_text(json.dumps(self.plan()), encoding='utf-8')
            run(root/'run', path)
            before = ledger(root/'run')
            # Windows CI can spell TEMP with a short-name alias. Exercise an
            # equivalent noncanonical path on every OS before comparing argv.
            (root/'alias').mkdir()
            audit(root/'alias'/'..'/'run', path, root/'audit.json')
            result = json.loads((root/'audit.json').read_bytes())
            self.assertEqual(result['queries_verified'],18)
            self.assertEqual(result['cli_contention_refusals'],6)
            self.assertEqual(ledger(root/'run'),before)
            # A forged successful completion must not pass independent observation.
            receipt = root/'run/r1-n9-after_HEAD/writer-exit.json'
            value = json.loads(receipt.read_bytes())
            value['exit'] = 0
            receipt.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'exit witness'):
                audit(root/'run', path, root/'forged.json')
            self.assertFalse((root/'forged.json').exists())

    def test_changed_schedule_inputs_limits_and_denominators_refuse(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'bad-plan.json'
            for field in ('schedule','fixture_files','limits_s','counts','policy','expected','candidate_source_anchors'):
                bad = copy.deepcopy(plan)
                bad[field] = {}
                path.write_text(json.dumps(bad), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_plan(path)
            path.write_text(json.dumps(plan), encoding='utf-8')
            self.assertEqual(load_plan(path)['mode'],'owned-test')
            formal = Path('docs/memory-default-writer-plan.json')
            with self.assertRaisesRegex(ValueError,'external exact-CI'):
                run(Path(directory)/'unstarted-formal', formal)
            self.assertFalse((Path(directory)/'unstarted-formal').exists())
