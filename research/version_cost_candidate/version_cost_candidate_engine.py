"""Serial coordinator for a bound formal plan or the owned smoke."""
import json
import re
import time
from pathlib import Path
from version_cost_readonly_receipts import canonical, capture, delta, identity, save, sha, unchanged
from version_cost_task_monitor import run_task
from version_cost_official_guard_link import check_row, permission_from_binding

from version_cost_candidate_interface import validate_execution_plan as validate_plan, require_formal_admission

class PreparedCoordinator:
    def __init__(self, stage, plan_path, expected_plan_sha, guard, formal_admission=None, package_sha256=None):
        self.started, self.cpu = time.perf_counter(), time.process_time()
        self.stage = Path(stage).resolve()
        raw = Path(plan_path).read_bytes()
        if sha(raw) != expected_plan_sha:
            raise ValueError('External plan identity differs')
        self.plan, self.plan_sha = json.loads(raw), expected_plan_sha
        validate_plan(self.plan, self.stage)
        self.root = self.stage / 'runs' / self.plan['run_key']
        if not re.fullmatch('[a-z0-9-]+', self.plan['run_key']):
            raise ValueError('Unsafe run identity')
        self.guard = guard
        self.formal_admission = formal_admission
        self.package_sha256 = package_sha256
        self.prev, self.seq = None, 0
        self.budget_metrics = {'calls': 0, 'wall_ns': 0, 'self_cpu_ns': 0, 'logical_file_size_terms': 0}

    def journal(self, event, **fields):
        value = {'seq': self.seq, 'previous_line_sha256': self.prev,
                 'event': event, 'plan_sha256': self.plan_sha,
                 'elapsed_s': time.perf_counter() - self.started, **fields}
        raw = canonical(value) + b'\n'
        with (self.root / 'journal.jsonl').open('ab') as stream:
            stream.write(raw)
            stream.flush()
            import os
            os.fsync(stream.fileno())
        self.prev, self.seq = sha(raw), self.seq + 1

    def budget(self):
        start_ns, cpu_ns = time.perf_counter_ns(), time.process_time_ns()
        elapsed = time.perf_counter() - self.started
        root_files = [path for path in self.root.rglob('*') if path.is_file()]
        total = sum(path.stat().st_size for path in root_files)
        library_files = {lib['library_key']: [path for path in (self.root / 'libraries' / lib['library_key']).rglob('*') if path.is_file()] for lib in self.plan['libraries']}
        libraries = {key: sum(path.stat().st_size for path in paths) for key, paths in library_files.items()}
        limits = self.plan['budgets']
        reason = ('global_wall_limit' if elapsed > limits['global_wall_s'] else
                  'global_output_limit' if total + limits['metadata_reserve_B'] > limits['global_output_B'] else
                  'library_output_limit' if any(value > limits['library_B'] for value in libraries.values()) else None)
        self.budget_metrics['calls'] += 1
        self.budget_metrics['wall_ns'] += time.perf_counter_ns() - start_ns
        self.budget_metrics['self_cpu_ns'] += time.process_time_ns() - cpu_ns
        self.budget_metrics['logical_file_size_terms'] += len(root_files) + sum(len(paths) for paths in library_files.values())
        return {'reason': reason, 'elapsed_s': elapsed, 'root_logical_B': total,
                'all_library_logical_B': libraries, 'metadata_reserve_B': limits['metadata_reserve_B']}

    def run(self):
        if self.plan['mode'] == 'prepared-formal-version-cost-1':
            require_formal_admission(self.plan, self.formal_admission or {}, package_sha=self.package_sha256, authorized_reference=self.plan['authorized_reference'])
            if self.formal_admission.get('plan_file_sha256') != self.plan_sha:
                raise PermissionError('External grant does not bind this plan file')
        # Exclusive root allocation refuses a consumed run before any mutation.
        self.root.mkdir(parents=True, exist_ok=False)
        for name in ['libraries', 'cases', 'specs', 'inventories', 'receipts', 'guards', 'preflights']:
            (self.root / name).mkdir()
        save(self.root / 'attempted.json', {'plan_sha256': self.plan_sha, 'scope': self.plan['scope']})
        self.journal('run_reserved', planned=len(self.plan['tasks']))
        completed, launched, reason, error = [], [], None, None
        try:
            frozen_raw = (self.stage / 'runtime-freeze.json').read_bytes()
            if sha(frozen_raw) != self.plan['freeze_sha256']:
                raise ValueError('Freeze differs')
            freeze = json.loads(frozen_raw)
            for path, item in freeze['absolute_files'].items():
                if identity(path) != item:
                    raise ValueError('Frozen source differs: ' + path)
            for task in self.plan['tasks']:
                if self.budget()['reason']:
                    reason = self.budget()['reason']
                    break
                if task['requires'] and task['requires'][0] not in completed:
                    raise ValueError('Actual predecessor not complete')
                self.journal('task_reserved', task_id=task['id'], library_key=task['library_key'])
                reference = self.plan['authorized_reference']
                guard = (check_row(self, task, reference)
                         if self.plan['mode'] == 'prepared-formal-version-cost-1'
                         else self.guard(task, reference))
                save(self.root / 'guards' / (task['id'] + '.json'), guard)
                allowed = permission_from_binding(guard, self.root, reference, task['id'], self.plan_sha)
                self.journal('bounded_guard_checked', task_id=task['id'], allowed=allowed,
                             guard_sha256=identity(self.root / 'guards' / (task['id'] + '.json'))['sha256'])
                if not allowed:
                    reason = 'bounded_guard_refused'
                    break
                library = self.root / 'libraries' / task['library_key']
                binding = {'plan_sha256': self.plan_sha, 'task_id': task['id'], 'library_key': task['library_key']}
                before = capture(library, binding, 'before')
                before_path = self.root / 'inventories' / (task['id'] + '.before.json')
                save(before_path, before)
                spec = {**task, 'mode': self.plan['mode'], 'owned_root': str(self.stage),
                    'campaign_root': str(self.root), 'library': str(library), 'path_roots': freeze['path_roots'],
                    'freeze_path': str(self.stage / 'runtime-freeze.json'), 'freeze_sha256': self.plan['freeze_sha256'],
                    'before_sha256': identity(before_path)['sha256']}
                if self.plan['mode'] == 'prepared-formal-version-cost-1':
                    spec.update(formal_admission=self.formal_admission, package_sha256=self.package_sha256,
                        bound_plan_file_sha256=self.plan_sha, authorized_reference=self.plan['authorized_reference'])
                spec_path = self.root / 'specs' / (task['id'] + '.json')
                save(spec_path, spec)
                worker_name = ('version_cost_candidate_history_worker.py' if task['op'] == 'validate_history' else
                               'version_cost_candidate_api_worker.py')
                created = []
                def on_created(value):
                    created.append(value)
                    self.journal('task_started', task_id=task['id'], library_key=task['library_key'], **value)
                monitor = run_task(self.root / 'cases' / task['id'], self.stage.parent / worker_name, spec_path,
                    wall_s=self.plan['budgets']['task_wall_s'], rss_B=self.plan['budgets']['task_RSS_B'],
                    global_snapshot=self.budget, on_created=on_created)
                launched.append(task['id'])
                case, work = self.root / 'cases' / task['id'], self.root / 'cases' / task['id'] / 'work'
                after = capture(library, {**binding, 'before_sha256': identity(before_path)['sha256'],
                    'observed_pid': monitor['pid'], 'actual_exit_code': monitor['actual_exit_code'],
                    'monitor_sha256': identity(case / 'monitor.json')['sha256']}, 'after')
                after_path = self.root / 'inventories' / (task['id'] + '.after.json')
                save(after_path, after)
                change = delta(before, after)
                receipt = {'task_id': task['id'], 'library_key': task['library_key'], 'created': created,
                    'before_sha256': identity(before_path)['sha256'], 'after_sha256': identity(after_path)['sha256'],
                    'spec_sha256': identity(spec_path)['sha256'], 'monitor_sha256': identity(case / 'monitor.json')['sha256'],
                    'delta': change, 'pid': monitor['pid'], 'actual_exit_code': monitor['actual_exit_code'],
                    'status': monitor['status'], 'global_after': self.budget()}
                if monitor['status'] != 'completed':
                    save(self.root / 'receipts' / (task['id'] + '.json'), receipt)
                    reason = monitor['reason']
                    self.journal('task_stopped', task_id=task['id'], reason=reason,
                        receipt_sha256=identity(self.root / 'receipts' / (task['id'] + '.json'))['sha256'])
                    break
                entry, footer, result = [json.loads((work / name).read_bytes()) for name in ['entry.json', 'finally.json', 'result.json']]
                if not footer['success'] or not (entry['pid'] == footer['pid'] == result['pid'] == monitor['pid']) or monitor['job_accounting'] != {'total': 1, 'active': 0}:
                    raise ValueError('Actual exit/footer binding differs')
                if any(item['spec_sha256'] != identity(spec_path)['sha256'] for item in [entry, footer, result]):
                    raise ValueError('Specification identity differs')
                if task['op'] in ('validate_history', 'restore', 'read') and not unchanged(change):
                    raise ValueError('Readonly endpoint changed')
                if task['op'] == 'validate_history' and result['versions'] != task['versions']:
                    raise ValueError('Actual history prefix differs')
                if task['op'] == 'append' and result['receipt']['phase'] != 'stage_completed':
                    raise ValueError('Append completion missing')
                if task['op'] in ('append', 'restore', 'read'):
                    interval = result['api_intervals'][0]
                    if not (result['setup_end_ns'] <= interval['begin_ns'] <= interval['end_ns'] <= result['post_start_ns'] <= result['post_end_ns']) or not interval['returned_normally']:
                        raise ValueError('API boundary differs')
                receipt.update({name + '_sha256': identity(work / (name + '.json'))['sha256'] for name in ['entry', 'finally', 'result']})
                save(self.root / 'receipts' / (task['id'] + '.json'), receipt)
                completed.append(task['id'])
                self.journal('task_completed', task_id=task['id'], library_key=task['library_key'],
                    receipt_sha256=identity(self.root / 'receipts' / (task['id'] + '.json'))['sha256'])
                if self.budget()['reason']:
                    reason = self.budget()['reason']
                    break
        except BaseException as exc:
            reason = reason or 'identity_or_integration_failure'
            error = {'type': type(exc).__name__, 'message': str(exc)}
        last_budget = self.budget()
        reason = reason or last_budget['reason']
        status = 'complete' if reason is None and len(completed) == len(self.plan['tasks']) else 'stopped'
        self.journal('run_' + status, completed=len(completed), launched=len(launched), reason=reason)
        terminal = {'status': status, 'reason': reason, 'error': error, 'plan_sha256': self.plan_sha,
                    'planned_tasks': len(self.plan['tasks']), 'completed_task_ids': completed,
                    'launched_task_ids': launched, 'journal_tip_sha256': self.prev, 'journal_events': self.seq,
                    'parent_wall_s': time.perf_counter() - self.started, 'parent_self_CPU_s': time.process_time() - self.cpu,
                    'last_budget': last_budget, 'formal_ready': False,
                    'mode': self.plan['mode'],
                    'guard_mode': 'bounded-official-preflight'}
        terminal['budget_observer_metrics'] = dict(self.budget_metrics)
        save(self.root / 'terminal.json', terminal)
        return terminal
