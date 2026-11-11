"""Synthetic regressions for per-task quota binding and formal result extraction."""
import json
import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from version_cost_candidate_ci_checks import fixture
from version_cost_candidate_engine import PreparedCoordinator, logical_budget_snapshot
from version_cost_candidate_interface import compile_plan
from version_cost_formal_results import audit, digest, score, verify_guard, verify_outputs, verify_task
from version_cost_official_guard_link import TRANSPORT_ERROR, check_row, permission_from_binding


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

    def simulate_guard(self, case, summaries, walls, *, cleanup=True):
        root = self.root / case
        reference = 1000
        plan_sha = 'c' * 64
        task_id = 'task-a'
        controller = SimpleNamespace(root=root, plan_sha=plan_sha, started=100,
                                     plan={'guard_cap_s': 10, 'budgets': {'global_wall_s': 3600},
                                           'preflight_mode': 'official', 'preflight_worker': 'synthetic',
                                           'quota_script': 'synthetic', 'preflight_freeze_path': 'synthetic',
                                           'preflight_freeze_sha256': 'a' * 64})
        now = 100.
        calls = []

        def observe(folder, spec, *, deadline, cleanup_s):
            nonlocal now
            index = len(calls)
            self.assertEqual(deadline, 110.)
            self.assertEqual(cleanup_s, 2.)
            calls.append(folder)
            summary = summaries[index]
            wall = walls[index]
            now += wall
            permit = (summary.get('ordinaryUsageAllowed') is True and
                      summary['primary']['usedPercent'] < 100 and summary['primary']['resetsAt'] == reference)
            spec_sha = write(folder / 'spec.json', spec)
            pid, helper = 40 + index * 2, 41 + index * 2
            result = {'pid': pid, 'spec_sha256': spec_sha, 'read_record': {
                'failure': None, 'summary': summary, 'official_RPC_source_unchanged': True,
                'RPC_retries': 0, 'owned_failure_before_RPC': False,
                'held_app_servers': [{'pid': helper, 'actual_exit_code': 1, 'pipes_closed': True,
                                      'cleanup_error': None}],
            }}
            footer = {'pid': pid, 'spec_sha256': spec_sha, 'success': True}
            record = {'mode': 'official', 'authorized_reference': reference,
                      'reason': None if permit else 'quota_or_evidence_denied',
                      'root_pid': pid, 'root_exit_code': 0, 'cleanup_confirmed': cleanup,
                      'job_final': {'active': 0}, 'spec_sha256': spec_sha, 'worker_result': result,
                      'worker_footer': footer, 'wall_s': wall, 'permission': permit,
                      'members': [{'pid': helper, 'actual_exit_code': 1, 'observation_error': None}]}
            write(folder / 'work/result.json', result)
            write(folder / 'work/finally.json', footer)
            write(folder / 'observation.json', record)
            return record

        with patch('version_cost_official_guard_link.run_bounded', side_effect=observe):
            with patch('version_cost_official_guard_link.time.perf_counter', side_effect=lambda: now):
                binding = check_row(controller, {'id': task_id}, reference)
        return root, reference, plan_sha, task_id, calls, binding

    def test_quota_transport_retry_keeps_both_witnesses_and_same_deadline(self):
        error = {'id': 2, 'error': {'code': -32603, 'message': TRANSPORT_ERROR}}
        ok = {'ordinaryUsageAllowed': True, 'primary': {'usedPercent': 74, 'resetsAt': 1000}}
        root, reference, plan_sha, task, calls, binding = self.simulate_guard('retry-ok', [error, ok], [6., 3.])
        self.assertEqual(calls, [root / 'preflights/task-a', root / 'preflights/task-a/retry-01'])
        self.assertTrue(permission_from_binding(binding, root, reference, task, plan_sha))
        guard = root / 'guards/task-a.json'
        event = {'allowed': True, 'guard_sha256': write(guard, binding)}
        self.assertEqual(verify_guard(root, plan_sha, reference, task, event), 9_000_000_000)

        retry_spec = calls[1] / 'spec.json'
        spec = json.loads(retry_spec.read_bytes())
        write(retry_spec, {**spec, 'task_id': 'task-b'})
        self.assertFalse(permission_from_binding(binding, root, reference, task, plan_sha))
        with self.assertRaises(ValueError):
            verify_guard(root, plan_sha, reference, task, event)

    def test_quota_retry_refuses_denial_unknown_late_and_unclean_cases(self):
        error = {'id': 2, 'error': {'code': -32603, 'message': TRANSPORT_ERROR}}
        other = {'id': 2, 'error': {'code': -32603, 'message': 'unclassified'}}
        ok = {'ordinaryUsageAllowed': True, 'primary': {'usedPercent': 74, 'resetsAt': 1000}}
        denied = {**ok, 'ordinaryUsageAllowed': False}
        exhausted = {**ok, 'primary': {'usedPercent': 100, 'resetsAt': 1000}}
        changed = {**ok, 'primary': {'usedPercent': 74, 'resetsAt': 1061}}
        cases = [
            ('initial-ok', [ok], [1.], True, 1, True),
            ('denied', [denied], [1.], True, 1, False),
            ('exhausted', [exhausted], [1.], True, 1, False),
            ('changed-window', [changed], [1.], True, 1, False),
            ('unknown', [other], [1.], True, 1, False),
            ('unclean', [error], [1.], False, 1, False),
            ('expired-first', [error], [10.], True, 1, False),
            ('expired-retry', [error, ok], [6., 4.], True, 2, False),
            ('repeated-error', [error, error], [1., 1.], True, 2, False),
            ('retry-denied', [error, denied], [1., 1.], True, 2, False),
            ('retry-changed-window', [error, changed], [1., 1.], True, 2, False),
        ]
        for case, summaries, walls, cleanup, attempts, permitted in cases:
            with self.subTest(case=case):
                root, reference, plan_sha, task, calls, binding = self.simulate_guard(
                    case, summaries, walls, cleanup=cleanup)
                self.assertEqual(len(calls), attempts)
                self.assertEqual(permission_from_binding(binding, root, reference, task, plan_sha), permitted)

    def test_budget_counts_one_root_scan_with_live_lock_and_bundle_removal(self):
        root = self.root / 'owned-budget'
        library = root / 'libraries' / 'solid'
        library.mkdir(parents=True)
        (library / 'stable').write_bytes(b's' * 96)
        (root / 'journal').write_bytes(b'j' * 32)
        gate = threading.Barrier(2)

        def writer():
            gate.wait(timeout=5)
            for i in range(128):
                lock = library / 'append.lock'
                lock.write_bytes(b'x' * 64)
                tmp = library / '.HEAD.tmp'
                tmp.write_bytes(b'h' * 16)
                os.replace(tmp, library / 'HEAD')
                bundle = library / f'bundle-{i}'
                bundle.write_bytes(b'b' * 256)
                bundle.unlink()
                lock.unlink()

        with ThreadPoolExecutor(max_workers=1) as pool:
            target = pool.submit(writer)
            gate.wait(timeout=5)
            for _ in range(128):
                size, libs, terms, _ = logical_budget_snapshot(root, ['solid', 'empty'])
                self.assertEqual(size - libs['solid'], 32)
                self.assertEqual(libs['empty'], 0)
                self.assertGreaterEqual(terms, 2)
                self.assertGreaterEqual(libs['solid'], 96)
            target.result(timeout=10)
        self.assertEqual(logical_budget_snapshot(root, ['solid', 'empty']), (144, {'solid': 112, 'empty': 0}, 3, 0))

    def test_budget_snapshot_discards_only_bounded_missing_entry_failures(self):
        root = self.root / 'synthetic-root'
        with patch('version_cost_candidate_engine.scan_logical_sizes',
                   side_effect=[FileNotFoundError(), (12, {'a': 5}, 2)]) as scan:
            self.assertEqual(logical_budget_snapshot(root, ['a']), (12, {'a': 5}, 2, 1))
            self.assertEqual(scan.call_count, 2)
        with patch('version_cost_candidate_engine.scan_logical_sizes', side_effect=FileNotFoundError()) as scan:
            with self.assertRaises(FileNotFoundError):
                logical_budget_snapshot(root, ['a'])
            self.assertEqual(scan.call_count, 3)
        with patch('version_cost_candidate_engine.scan_logical_sizes', side_effect=PermissionError()) as scan:
            with self.assertRaises(PermissionError):
                logical_budget_snapshot(root, ['a'])
            self.assertEqual(scan.call_count, 1)

    def test_observed_global_and_library_caps_remain_fail_closed(self):
        root = self.root / 'budget-caps'
        library = root / 'libraries' / 'a'
        library.mkdir(parents=True)
        (library / 'stored').write_bytes(b'x' * 20)
        (root / 'log').write_bytes(b'x' * 10)
        coordinator = PreparedCoordinator.__new__(PreparedCoordinator)
        coordinator.root = root
        coordinator.started = 0
        coordinator.budget_metrics = dict.fromkeys(
            ('calls', 'wall_ns', 'self_cpu_ns', 'logical_file_size_terms', 'discarded_snapshot_retries'), 0)
        limits = {'global_wall_s': 5, 'metadata_reserve_B': 2, 'global_output_B': 32, 'library_B': 20}
        coordinator.plan = {'libraries': [{'library_key': 'a'}], 'budgets': limits}
        with patch('version_cost_candidate_engine.time.perf_counter', return_value=1):
            self.assertIsNone(coordinator.budget()['reason'])
            limits['global_output_B'] = 31
            self.assertEqual(coordinator.budget()['reason'], 'global_output_limit')
            limits['global_output_B'] = 32
            limits['library_B'] = 19
            self.assertEqual(coordinator.budget()['reason'], 'library_output_limit')
        with patch('version_cost_candidate_engine.time.perf_counter', return_value=6):
            self.assertEqual(coordinator.budget()['reason'], 'global_wall_limit')

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
