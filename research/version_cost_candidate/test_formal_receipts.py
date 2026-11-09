"""Synthetic regressions for per-task quota binding and formal result extraction."""
import json
import tempfile
import unittest
from pathlib import Path

from version_cost_candidate_ci_checks import fixture
from version_cost_candidate_interface import compile_plan
from version_cost_formal_results import audit, digest, score, verify_guard, verify_outputs, verify_task
from version_cost_official_guard_link import permission_from_binding


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, sort_keys=True).encode()
    path.write_bytes(raw)
    return digest(raw)


class FormalReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = Path(__file__).resolve().parent / 'ci-owned-fixtures'
        parent.mkdir(exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(prefix='formal-receipts-', dir=parent))

    def test_same_run_quota_cannot_move_between_tasks_or_plans(self):
        task = 'task-a'
        plan_sha = 'c' * 64
        reference = 1000
        folder = self.root / 'preflights' / task
        spec_sha = write(folder / 'spec.json', {
            'mode': 'official', 'authorized_reference': reference, 'task_id': task, 'plan_sha256': plan_sha,
        })
        result = {'pid': 35, 'spec_sha256': spec_sha, 'read_record': {
            'failure': None, 'held_app_servers': [{'actual_exit_code': 0, 'pipes_closed': True}],
            'summary': {'ordinaryUsageAllowed': True, 'primary': {'usedPercent': 5, 'resetsAt': reference}},
        }}
        footer = {'pid': 35, 'spec_sha256': spec_sha, 'success': True}
        write(folder / 'work/result.json', result)
        write(folder / 'work/finally.json', footer)
        observation_path = folder / 'observation.json'
        observation_sha = write(observation_path, {
            'mode': 'official', 'authorized_reference': reference, 'reason': None, 'root_pid': 35,
            'root_exit_code': 0, 'cleanup_confirmed': True, 'job_final': {'active': 0},
            'spec_sha256': spec_sha, 'worker_result': result, 'worker_footer': footer, 'wall_s': 0.25,
        })
        binding = {'origin': 'bounded-official-preflight', 'fresh_run_for_task': task,
                   'cache_reused': False, 'observation_path': str(observation_path),
                   'observation_sha256': observation_sha}
        event = {'allowed': True, 'guard_sha256': write(self.root / 'guards/task-a.json', binding)}
        self.assertTrue(permission_from_binding(binding, self.root, reference, task, plan_sha))
        self.assertEqual(verify_guard(self.root, plan_sha, reference, task, event), 250_000_000)
        relabeled = {**binding, 'fresh_run_for_task': 'task-b'}
        self.assertFalse(permission_from_binding(relabeled, self.root, reference, 'task-b', plan_sha))
        copied = self.root / 'preflights/task-b'
        copied.mkdir()
        for name in ('spec.json', 'observation.json'):
            (copied / name).write_bytes((folder / name).read_bytes())
        relabeled['observation_path'] = str(copied / 'observation.json')
        self.assertFalse(permission_from_binding(relabeled, self.root, reference, 'task-b', plan_sha))
        self.assertFalse(permission_from_binding(binding, self.root, reference, task, 'd' * 64))
        with self.assertRaises(ValueError):
            verify_guard(self.root, 'd' * 64, reference, task, event)

    def test_fixed_workload_scoring_includes_both_controls_and_total_update_wall(self):
        inputs = self.root / 'synthetic-inputs'
        manifest, catalog, catalog_sha = fixture(inputs)
        plan = compile_plan(manifest, catalog, manifest_sha='c' * 64, catalog_sha=catalog_sha,
                            input_root=inputs, run_root=self.root / 'synthetic-run', budget_s=1800)
        values = [{'API_wall_ns': 10_000_000, 'whole_process_wall_ns': 20_000_000,
                   'peak_RSS_B': 100_000_000, 'retained_library_B': 800_000 if task['kind'] == 'rkv' else 1_000_000}
                  for task in plan['tasks']]
        deployment = {'rkv': 10_000, 'full': 10_000, 'solid': 10_000}
        passed = score(plan, values, deployment)
        self.assertEqual(passed['joint_decision'], 'candidate_for_limited_source_mode_adoption')
        for comparison in passed['comparisons'].values():
            self.assertEqual(len(comparison['space_pairs_in_order']), 6)
            self.assertEqual(len(comparison['operations']), 74)
            self.assertEqual(comparison['operations']['all_updates/API_wall_ns']['candidate_statistic'], '120000000')
        failed = score(plan, values, {**deployment, 'rkv': 300_000})
        self.assertEqual(failed['joint_decision'], 'does_not_meet_frozen_targets')
        for task, value in zip(plan['tasks'], values):
            if task['kind'] == 'rkv' and task['op'] == 'append':
                value['API_wall_ns'] = 18_000_000
        slowed = score(plan, values, deployment)
        self.assertEqual(slowed['comparisons']['full']['operations']['0/API_wall_ns']['decision'], 'pass')
        self.assertEqual(slowed['comparisons']['full']['operations']['all_updates/API_wall_ns']['decision'], 'fail')

    def test_output_digest_detects_same_length_tampering_and_missing_is_distinct(self):
        folder = self.root / 'output-test'
        path = folder / 'outputs/docs/ROADMAP.md'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'')
        item = {'docs/ROADMAP.md': {'bytes': 0, 'sha256': digest(b'')}}
        task = {'op': 'read', 'operation': 'read_path', 'selected_version': 'v000', 'expected_files': item}
        result = {'selected_version': 'v000', 'outputs': item}
        self.assertEqual(verify_outputs(folder, task, result), 1)
        with self.assertRaises(ValueError):
            verify_outputs(folder, {**task, 'operation': 'read_missing'}, {**result, 'missing': True})
        path.write_bytes(b'A')
        item['docs/ROADMAP.md'] = {'bytes': 1, 'sha256': digest(b'A')}
        path.write_bytes(b'B')
        with self.assertRaises(ValueError):
            verify_outputs(folder, task, result)

    def test_task_receipt_binds_times_pid_and_endpoints(self):
        root = self.root / 'receipt-run'
        task_id, key, plan_sha, pid = 'read-zero', 'order00-full', 'a' * 64, 123
        case = root / 'cases' / task_id
        work = case / 'work'
        files = {'docs/ROADMAP.md': {'bytes': 0, 'sha256': digest(b'')}}
        task = {'id': task_id, 'library_key': key, 'op': 'read', 'operation': 'read_path',
                'selected_version': 'v000', 'expected_files': files}
        binding = {'plan_sha256': plan_sha, 'task_id': task_id, 'library_key': key}
        library = str(root / 'libraries' / key)
        before = {'phase': 'before', 'binding': binding, 'library': library, 'end_ns': 10,
                  'root_exists': True, 'directories': ['docs'], 'files': files}
        before_sha = write(root / 'inventories' / f'{task_id}.before.json', before)
        spec_sha = write(root / 'specs' / f'{task_id}.json',
                         {**task, 'library': library, 'before_sha256': before_sha})
        monitor_sha = write(case / 'monitor.json', {
            'pid': pid, 'status': 'completed', 'resumed': True, 'actual_exit_code': 0,
            'job_accounting': {'total': 1, 'active': 0}, 'parent_wall_s': 0.1,
            'final_process_metrics': {'peak_rss_B': 42, 'user_cpu_s': 0, 'kernel_cpu_s': 0},
        })
        after = {**before, 'phase': 'after', 'start_ns': 91, 'binding': {
            **binding, 'before_sha256': before_sha, 'observed_pid': pid, 'actual_exit_code': 0,
            'monitor_sha256': monitor_sha}}
        after_sha = write(root / 'inventories' / f'{task_id}.after.json', after)
        common = {'pid': pid, 'spec_sha256': spec_sha}
        intervals = [{'begin_ns': 30, 'end_ns': 50, 'wall_ns': 20, 'returned_normally': True}]
        receipt = {'task_id': task_id, 'library_key': key, 'pid': pid, 'status': 'completed',
                   'actual_exit_code': 0, 'monitor_sha256': monitor_sha, 'spec_sha256': spec_sha,
                   'before_sha256': before_sha, 'after_sha256': after_sha}
        receipt['entry_sha256'] = write(work / 'entry.json', {**common, 'entry_ns': 11})
        receipt['finally_sha256'] = write(work / 'finally.json', {
            **common, 'entry_wall_ns': 79, 'success': True, 'api_intervals': intervals})
        receipt['result_sha256'] = write(work / 'result.json', {
            **common, 'api_intervals': intervals, 'setup_end_ns': 20, 'post_start_ns': 51,
            'post_end_ns': 70, 'formal_performance_sample': True, 'selected_version': 'v000',
            'outputs': files})
        output = work / 'outputs/docs/ROADMAP.md'
        output.parent.mkdir(parents=True)
        output.write_bytes(b'')
        receipt_path = root / 'receipts' / f'{task_id}.json'
        events = [{}, {}, {'pid': pid, 'spec_sha256': spec_sha},
                  {'receipt_sha256': write(receipt_path, receipt)}]
        prior = (True, ['docs'], files)
        metrics, final = verify_task(root, plan_sha, task, events, prior)
        self.assertEqual(final, prior)
        self.assertEqual(metrics['API_wall_ns'], 20)
        self.assertEqual(metrics['whole_process_wall_ns'], 100_000_000)
        after['start_ns'] = 12
        receipt['after_sha256'] = write(root / 'inventories' / f'{task_id}.after.json', after)
        events[-1]['receipt_sha256'] = write(receipt_path, receipt)
        with self.assertRaisesRegex(ValueError, 'chronology'):
            verify_task(root, plan_sha, task, events, prior)

    def test_stopped_run_keeps_denominator_without_opening_scoring_inputs(self):
        root = self.root / 'stopped'
        mode = 'prepared-formal-version-cost-1'
        plan_path = root / 'plan.json'
        plan_sha = write(plan_path, {'mode': mode, 'run_root': str(root),
                                    'tasks': [None] * 648, 'libraries': [None] * 18})
        terminal_sha = write(root / 'terminal.json', {
            'plan_sha256': plan_sha, 'mode': mode, 'planned_tasks': 648,
            'status': 'stopped', 'reason': 'bounded_guard_refused', 'completed_task_ids': ['task-0'],
        })
        report = audit(plan_path, plan_sha, terminal_sha, root / 'unavailable-deployment.json', '0' * 64)
        self.assertEqual(report['audit_status'], 'incomplete')
        self.assertEqual(report['planned_tasks'], 648)
        self.assertIsNone(report['score'])
        with self.assertRaises(ValueError):
            audit(plan_path, plan_sha, '0' * 64, root / 'unavailable-deployment.json', '0' * 64)


if __name__ == '__main__':
    unittest.main()
