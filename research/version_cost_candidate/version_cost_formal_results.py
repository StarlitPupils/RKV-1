"""Read-only audit and scoring for a complete, externally bound formal run."""
import argparse
import hashlib
import json
import math
from collections import Counter
from decimal import Decimal
from pathlib import Path

from version_cost_candidate_decisions import joint, median, rss, space, wall


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path, expected=None):
    raw = path.read_bytes()
    if expected is not None:
        require(digest(raw) == expected, f'Digest mismatch: {path.name}')
    return json.loads(raw)


def inventory_view(record):
    return record['root_exists'], record['directories'], record['files']


def file_identity(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': digest(raw)}


def ns(seconds):
    require(type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0,
            'Invalid whole-process wall interval')
    return round(Decimal(str(seconds)) * 1_000_000_000)


def verify_outputs(work, task, result):
    if task['op'] == 'append':
        require(result['receipt']['phase'] == 'stage_completed', 'Update lacks completion receipt')
        return 0
    if task['op'] == 'validate_history':
        require(result['versions'] == task['versions'] and result['update_API_timing'] is None,
                'Independent history prefix or metric differs')
        require(result['outputs'] == task['expected_history'], 'History output metadata differs')
        expected = {f'{version}/outputs/{name}': item
                    for version, files in task['expected_history'].items()
                    for name, item in files.items()}
        folders = [work / version / 'outputs' for version in task['versions']]
    else:
        require(result['selected_version'] == task['selected_version'], 'Selected version differs')
        if task['operation'] == 'read_missing':
            require(result.get('missing') is True and not (work / 'outputs').exists(),
                    'Missing result differs from None')
            return 0
        require(result['outputs'] == task['expected_files'], 'Read output metadata differs')
        expected = {f'outputs/{name}': item for name, item in task['expected_files'].items()}
        folders = [work / 'outputs']
    actual = {p.relative_to(work).as_posix(): file_identity(p)
              for folder in folders for p in folder.rglob('*') if p.is_file()}
    require(actual == expected, 'Saved original output differs')
    return len(actual)


def verify_guard(root, plan_sha, reference, task_id, event):
    path = root / 'preflights' / task_id
    binding = read(root / 'guards' / f'{task_id}.json', event['guard_sha256'])
    require(binding['origin'] == 'bounded-official-preflight' and
            binding['fresh_run_for_task'] == task_id and binding['cache_reused'] is False and
            Path(binding['observation_path']) == path / 'observation.json' and event['allowed'] is True,
            'Guard path or task differs')
    observation = read(path / 'observation.json', binding['observation_sha256'])
    spec = read(path / 'spec.json', observation['spec_sha256'])
    require(spec['task_id'] == task_id and spec['plan_sha256'] == plan_sha and
            spec['mode'] == observation['mode'] == 'official' and
            spec['authorized_reference'] == observation['authorized_reference'] == reference and
            observation['root_exit_code'] == 0 and observation['reason'] is None and
            observation['cleanup_confirmed'] is True and observation['job_final']['active'] == 0,
            'Official observation does not grant permission')
    result = read(path / 'work/result.json')
    footer = read(path / 'work/finally.json')
    require(result == observation['worker_result'] and footer == observation['worker_footer'] and
            result['pid'] == footer['pid'] == observation['root_pid'] and footer['success'] is True and
            result['spec_sha256'] == footer['spec_sha256'] == observation['spec_sha256'],
            'Preflight PID, spec or footer differs')
    report = result['read_record']
    helpers = report['held_app_servers']
    summary, primary = report['summary'], report['summary']['primary']
    require(report['failure'] is None and len(helpers) == 1 and
            helpers[0]['pipes_closed'] is True and type(helpers[0]['actual_exit_code']) is int and
            summary['ordinaryUsageAllowed'] is True and
            type(primary['usedPercent']) in (int, float) and 0 <= primary['usedPercent'] < 100 and
            type(primary['resetsAt']) is int and abs(primary['resetsAt'] - reference) <= 60,
            'Official quota or helper cleanup evidence differs')
    return ns(observation['wall_s'])


def verify_task(root, plan_sha, task, events, prior):
    task_id, key = task['id'], task['library_key']
    started, completed = events[2], events[3]
    receipt = read(root / 'receipts' / f'{task_id}.json', completed['receipt_sha256'])
    case = root / 'cases' / task_id
    work = case / 'work'
    monitor = read(case / 'monitor.json', receipt['monitor_sha256'])
    spec = read(root / 'specs' / f'{task_id}.json', receipt['spec_sha256'])
    pid = monitor['pid']
    require(type(pid) is int and pid > 0 and
            receipt['task_id'] == task_id and receipt['library_key'] == key and
            pid == receipt['pid'] == started['pid'] and
            monitor['status'] == receipt['status'] == 'completed' and
            monitor['actual_exit_code'] == receipt['actual_exit_code'] == 0 and
            monitor['job_accounting'] == {'total': 1, 'active': 0} and monitor['resumed'] is True and
            receipt['spec_sha256'] == started['spec_sha256'] and
            all(spec.get(name) == value for name, value in task.items()) and
            spec['library'] == str(root / 'libraries' / key), 'Task, process or spec differs')
    result, entry, footer = [read(work / f'{name}.json', receipt[f'{name}_sha256'])
                             for name in ('result', 'entry', 'finally')]
    require(footer['success'] is True and all(item['pid'] == pid and
            item['spec_sha256'] == receipt['spec_sha256'] for item in (result, entry, footer)),
            'Worker result is not bound to the observed process')
    before, after = [read(root / 'inventories' / f'{task_id}.{phase}.json',
                          receipt[f'{phase}_sha256']) for phase in ('before', 'after')]
    binding = {'plan_sha256': plan_sha, 'task_id': task_id, 'library_key': key}
    require(before['phase'] == 'before' and after['phase'] == 'after' and
            before['binding'] == binding and after['binding'] == {
                **binding, 'before_sha256': receipt['before_sha256'], 'observed_pid': pid,
                'actual_exit_code': 0, 'monitor_sha256': receipt['monitor_sha256']} and
            before['library'] == after['library'] == spec['library'] and
            spec['before_sha256'] == receipt['before_sha256'] and
            before['end_ns'] <= entry['entry_ns'] <= entry['entry_ns'] + footer['entry_wall_ns'] <= after['start_ns'],
            'Endpoint inventory binding or chronology differs')
    require(inventory_view(before) == prior, 'Library changed between tasks')
    final_view = inventory_view(after)
    require(task['op'] == 'append' or final_view == prior, 'Read-only operation changed the library')
    rss_B = monitor['final_process_metrics']['peak_rss_B']
    require(type(rss_B) is int and rss_B > 0, 'Peak process RSS is unavailable')
    api_ns = None
    if task['op'] != 'validate_history':
        interval, = result['api_intervals']
        require(result['formal_performance_sample'] is True and
                result['api_intervals'] == footer['api_intervals'] and interval['returned_normally'] is True and
                result['setup_end_ns'] <= interval['begin_ns'] <= interval['end_ns'] <=
                result['post_start_ns'] <= result['post_end_ns'] and
                interval['wall_ns'] == interval['end_ns'] - interval['begin_ns'], 'API timer differs')
        api_ns = interval['wall_ns']
    measurement = {'task_id': task_id, 'API_wall_ns': api_ns,
                   'whole_process_wall_ns': ns(monitor['parent_wall_s']), 'peak_RSS_B': rss_B,
                   'observed_worker_user_CPU_s': monitor['final_process_metrics']['user_cpu_s'],
                   'observed_worker_kernel_CPU_s': monitor['final_process_metrics']['kernel_cpu_s'],
                   'original_outputs_verified': verify_outputs(work, task, result),
                   'retained_library_B': sum(item['bytes'] for item in after['files'].values())}
    return measurement, final_view


def score(plan, measurements, deployment_B):
    by_role = {role: {} for role in ('rkv', 'full', 'solid')}
    per_library = {lib['library_key']: [] for lib in plan['libraries']}
    for task, measurement in zip(plan['tasks'], measurements, strict=True):
        per_library[task['library_key']].append(measurement)
    for lib in plan['libraries']:
        by_role[lib['role']][lib['order_index']] = per_library[lib['library_key']]
    comparisons, primary = {}, []
    for baseline in ('full', 'solid'):
        candidate = [by_role['rkv'][i] for i in range(6)]
        control = [by_role[baseline][i] for i in range(6)]
        pairs = []
        for c, b in zip(candidate, control, strict=True):
            cb, bb = c[-1]['retained_library_B'], b[-1]['retained_library_B']
            cd, bd = cb + deployment_B['rkv'], bb + deployment_B[baseline]
            pairs.append({'candidate_library_B': cb, 'baseline_library_B': bb,
                          'candidate_source_mode_B': cd, 'baseline_source_mode_B': bd,
                          'library_only_decision': space(cb, bb), 'source_mode_decision': space(cd, bd)})
        decisions = [pair['source_mode_decision'] for pair in pairs]
        operations = {}
        for offset in [*range(0, 24, 2), *range(24, 36), 'all_updates']:
            def values(rows, field):
                if offset == 'all_updates':
                    return [sum(trace[i][field] for i in range(0, 24, 2)) for trace in rows]
                return [trace[offset][field] for trace in rows]
            for field in ('API_wall_ns', 'whole_process_wall_ns', 'peak_RSS_B'):
                if offset == 'all_updates' and field == 'peak_RSS_B':
                    continue
                left, right = values(candidate, field), values(control, field)
                is_rss = field == 'peak_RSS_B'
                decision = (rss if is_rss else wall)(left, right)
                left_stat, right_stat = (max(left), max(right)) if is_rss else (median(left), median(right))
                operations[f'{offset}/{field}'] = {
                    'candidate': left, 'baseline': right, 'decision': decision,
                    'candidate_max': max(left), 'baseline_max': max(right),
                    'compared_statistic': 'max' if is_rss else 'median',
                    'candidate_statistic': str(left_stat), 'baseline_statistic': str(right_stat),
                    'candidate_minus_baseline': str(left_stat - right_stat),
                }
                decisions.append(decision)
        comparisons[baseline] = {'space_pairs_in_order': pairs, 'operations': operations,
                                 'decision': joint(decisions)}
        primary.extend(decisions)
    return {'comparisons': comparisons, 'joint_decision': joint(primary),
            'deployment_logical_B': deployment_B, 'whole_system_CPU_RSS_IO': None}


def audit(plan_path, plan_sha, terminal_sha, deployment_path, deployment_sha):
    plan = read(plan_path, plan_sha)
    require(plan['mode'] == 'prepared-formal-version-cost-1', 'Expected formal plan')
    root = Path(plan['run_root'])
    terminal = read(root / 'terminal.json', terminal_sha)
    tasks = plan['tasks']
    require(terminal['plan_sha256'] == plan_sha and terminal['mode'] == plan['mode'] and
            len(tasks) == terminal['planned_tasks'] == 648 and len(plan['libraries']) == 18,
            'Formal denominator or plan binding differs')
    if terminal['status'] == 'stopped':
        return {'audit_status': 'incomplete', 'planned_tasks': 648,
                'controller_reported_completed': len(terminal['completed_task_ids']),
                'stop_reason': terminal['reason'], 'score': None}
    ids = [task['id'] for task in tasks]
    require(terminal['status'] == 'complete' and terminal['reason'] is None and
            terminal['completed_task_ids'] == terminal['launched_task_ids'] == ids and len(set(ids)) == 648,
            'Complete task witnesses are required before scoring')
    lines = (root / 'journal.jsonl').read_bytes().splitlines(keepends=True)
    require(len(lines) == terminal['journal_events'] == 2 + 4 * len(tasks), 'Journal denominator differs')
    previous, events = None, []
    for i, line in enumerate(lines):
        event = json.loads(line)
        require(line.endswith(b'\n') and event['seq'] == i and event['previous_line_sha256'] == previous and
                event['plan_sha256'] == plan_sha, 'Journal chain differs')
        previous = digest(line)
        events.append(event)
    require(previous == terminal['journal_tip_sha256'] and events[0]['event'] == 'run_reserved' and
            events[-1]['event'] == 'run_complete' and events[-1]['completed'] == len(tasks),
            'External terminal and journal differ')
    latest, measurements = {}, []
    for i, task in enumerate(tasks):
        row = events[1 + i * 4:5 + i * 4]
        require([x['event'] for x in row] ==
                ['task_reserved', 'bounded_guard_checked', 'task_started', 'task_completed'] and
                all(x['task_id'] == task['id'] for x in row), 'Task journal sequence differs')
        key = task['library_key']
        measurement, latest[key] = verify_task(root, plan_sha, task, row, latest.get(key, (False, [], {})))
        measurement['preflight_wall_ns'] = verify_guard(root, plan_sha, plan['authorized_reference'], task['id'], row[1])
        measurements.append(measurement)
    require(Counter(task['op'] for task in tasks) ==
            {'append': 216, 'validate_history': 216, 'read': 162, 'restore': 54}, 'Unexpected operation counts')
    require(sum(row['original_outputs_verified'] for row in measurements) == 3024, 'Original output denominator differs')
    require(set(latest) == {lib['library_key'] for lib in plan['libraries']}, 'Library coverage differs')
    for key, (exists, directories, files) in latest.items():
        lib = root / 'libraries' / key
        require(exists and lib.is_dir(), 'Final library is missing')
        actual = {p.relative_to(lib).as_posix(): file_identity(p) for p in lib.rglob('*') if p.is_file()}
        expected = {name: {'bytes': value['bytes'], 'sha256': value['sha256']} for name, value in files.items()}
        actual_dirs = sorted(p.relative_to(lib).as_posix() for p in lib.rglob('*') if p.is_dir())
        require(actual == expected and actual_dirs == directories, 'Final library inventory differs')
    deployment = read(deployment_path, deployment_sha)
    role_bytes = {}
    for role in ('full', 'solid', 'rkv'):
        paths = deployment['role_sets'][role]['required_file_paths']
        require(len(paths) == len(set(paths)) > 0, 'Deployment membership differs')
        for path in paths:
            identity = deployment['files'][path]
            require(file_identity(Path(path)) == {'bytes': identity['bytes'], 'sha256': identity['sha256']},
                    'Deployment file identity differs')
        role_bytes[role] = sum(deployment['files'][path]['bytes'] for path in paths)
        require(role_bytes[role] == deployment['role_sets'][role]['source_mode_incremental_payload_logical_B_from_existing_Python'],
                'Deployment total differs')
    root_logical_B = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    require(root_logical_B <= plan['budgets']['global_output_B'] and
            terminal['last_budget']['reason'] is None and
            terminal['parent_wall_s'] <= plan['budgets']['overall_wall_s'], 'Terminal budget exceeded')
    return {'audit_status': 'complete', 'planned_tasks': 648, 'audited_tasks': len(measurements),
            'terminal_sha256': terminal_sha, 'plan_sha256': plan_sha, 'deployment_sha256': deployment_sha,
            'measurements': measurements, 'score': score(plan, measurements, role_bytes),
            'costs': {'run_root_logical_B': root_logical_B,
                      'libraries_logical_B': sum(sum(item['bytes'] for item in view[2].values())
                                                 for view in latest.values()),
                      'controller_wall_s': terminal['parent_wall_s'],
                      'controller_self_CPU_s': terminal['parent_self_CPU_s'],
                      'budget_observer_metrics': terminal['budget_observer_metrics'],
                      'physical_IO_B': None, 'whole_system_CPU_RSS': None}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha', required=True)
    parser.add_argument('--terminal-sha', required=True)
    parser.add_argument('--deployment', type=Path, required=True)
    parser.add_argument('--deployment-sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.plan, args.plan_sha, args.terminal_sha, args.deployment, args.deployment_sha)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
