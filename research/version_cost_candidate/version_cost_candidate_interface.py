"""Strict prepared interface and admission barrier. No process or archive imports."""
import hashlib
import json
import re
import itertools
from pathlib import Path

PATHS = ('README.md', 'docs/ROADMAP.md')

def sha(raw): return hashlib.sha256(raw).hexdigest()
def read_bound(path, expected):
    raw = Path(path).read_bytes()
    if sha(raw) != expected: raise ValueError('External object digest differs')
    return json.loads(raw)

def oracle(files):
    result = {}
    for item in files:
        name = item['path']
        if name not in PATHS or name in result or type(item['bytes']) is not int or not 0 <= item['bytes'] <= 512 << 10 or not re.fullmatch('[0-9a-f]{64}', item['sha256']):
            raise ValueError('Invalid original file oracle')
        result[name] = {'bytes': item['bytes'], 'sha256': item['sha256']}
    return result

def compile_plan(manifest, catalog, *, manifest_sha, catalog_sha, input_root, run_root, budget_s):
    if len(manifest['libraries']) != 18 or len(manifest['tasks']) != 648 or [v['version'] for v in manifest['versions']] != [f'v{i:03d}' for i in range(12)]:
        raise ValueError('Expected the complete fixed18/648 candidate')
    if manifest['source_input_manifest_sha256'] != catalog_sha or manifest['source_input_commit'] != catalog['pinned_input_commit']:
        raise ValueError('Catalog/candidate identity differs')
    if budget_s not in (1800, 3600): raise ValueError('Unreviewed wall budget')
    versions = catalog['versions']
    if [row['version'] for row in versions] != [f'v{i:03d}' for i in range(12)]:
        raise ValueError('Complete chronological input catalog required')
    if any(left['original_commit'] != right['original_commit'] or left['files'] != right['files'] for left, right in zip(manifest['versions'], versions)):
        raise ValueError('Manifest/catalog provenance differs')
    truth = {row['version']: oracle(row['files']) for row in versions}
    if any(set(value) != set(PATHS) for value in truth.values()): raise ValueError('Two exact original paths required')
    input_root, run_root = Path(input_root).resolve(), Path(run_root).resolve()
    if run_root.is_relative_to(input_root) or input_root.is_relative_to(run_root): raise ValueError('Input/output roots overlap')
    libraries = manifest['libraries']
    keys = [row['library_key'] for row in libraries]
    expected_libraries = [(i, position, role) for i, order in enumerate(itertools.permutations(('full', 'solid', 'rkv'))) for position, role in enumerate(order)]
    if len(set(keys)) != 18 or any(not re.fullmatch('order0[0-5]-(full|solid|rkv)', key) for key in keys):
        raise ValueError('Unique safe library identities required')
    if [(row['order_index'], row['position'], row['role']) for row in libraries] != expected_libraries or any(row['library_key'] != f"order{row['order_index']:02d}-{row['role']}" for row in libraries):
        raise ValueError('Frozen six-order library layout differs')
    roles = {row['library_key']: row['role'] for row in libraries}
    heads, validated = {key: -1 for key in keys}, {key: -1 for key in keys}
    tasks = []
    for index, row in enumerate(manifest['tasks']):
        key = row['library_key']
        offset = index % 36
        expected_kind = ('update' if offset % 2 == 0 else 'validate_history') if offset < 24 else 'cold_read'
        if key != libraries[index // 36]['library_key'] or row['kind'] != expected_kind:
            raise ValueError('Each library requires its fixed36-step trace')
        if row['sequence'] != index or row['requires_complete'] != ([] if index == 0 else [manifest['tasks'][index - 1]['task_id']]):
            raise ValueError('Global dependency differs')
        if key not in roles or row['role'] != roles[key]: raise ValueError('Library role differs')
        if row['metric_boundary'] != ('VALIDATION_ONLY' if row['kind'] == 'validate_history' else 'API_CALL_ONLY'):
            raise ValueError('Measurement scope differs')
        task = {'seq': index, 'id': row['task_id'], 'requires': list(row['requires_complete']),
                'library_key': key, 'kind': row['role'], 'metric_boundary': row['metric_boundary']}
        if row['kind'] == 'update':
            number = heads[key] + 1; version = f'v{number:03d}'
            if number >= 12 or validated[key] != heads[key] or row['version'] != version or row['input_version'] != version or type(row['create']) is not bool or row['create'] != (number == 0) or row['expected_visible_versions'] != [f'v{i:03d}' for i in range(number + 1)]:
                raise ValueError('Unverified/future update input')
            folder = input_root / version / 'originals'
            if Path(row['input_source_directory']).resolve() != folder or oracle(row['input_files']) != truth[version]:
                raise ValueError('Update source identity differs')
            task.update(op='append', version=version, create=number == 0, source=str(folder),
                        expected_files=truth[version], expected_visible_versions=[f'v{i:03d}' for i in range(number + 1)])
            heads[key] = number
        elif row['kind'] == 'validate_history':
            number = heads[key]; prefix = [f'v{i:03d}' for i in range(number + 1)]
            if number < 0 or row['version'] != prefix[-1] or row['expected_visible_versions'] != prefix or row['whole_restore_calls'] != len(prefix) or row['original_file_checks'] != 2 * len(prefix):
                raise ValueError('Missing/future history prefix')
            task.update(op='validate_history', versions=prefix, expected_history={v: truth[v] for v in prefix})
            validated[key] = number
        elif row['kind'] == 'cold_read':
            if heads[key] != 11 or validated[key] != 11: raise ValueError('Read before final validated HEAD')
            cold_index = offset - 24
            expected_selector = ('v000', 'v005', 'current')[cold_index // 4]
            expected_operation = ('read_path', 'read_path', 'read_missing', 'restore')[cold_index % 4]
            expected_path = ('README.md', 'docs/ROADMAP.md', '__rkv_cost_missing__.md', None)[cold_index % 4]
            if row['selector'] != expected_selector or row['operation'] != expected_operation or row.get('path') != expected_path:
                raise ValueError('Fixed cold-read selectors/order differ')
            selected = 'v011' if row['selector'] == 'current' else row['selector']
            if selected not in ('v000', 'v005', 'v011') or row['expected_version'] != selected:
                raise ValueError('Selected current/history identity differs')
            expected_files = oracle(row['expected_files'])
            operation = row['operation']
            if operation == 'restore':
                if expected_files != truth[selected]: raise ValueError('Restore oracle differs')
            elif operation == 'read_path':
                if row['path'] not in PATHS or expected_files != {row['path']: truth[selected][row['path']]}:
                    raise ValueError('Path oracle differs')
            elif operation == 'read_missing':
                if row['path'] != '__rkv_cost_missing__.md' or expected_files or row['expected_return'] != 'None_not_empty_bytes':
                    raise ValueError('Missing/empty contract differs')
            else: raise ValueError('Unknown cold operation')
            task.update(op='restore' if operation == 'restore' else 'read', operation=operation,
                        version=None if row['selector'] == 'current' else selected,
                        selected_version=selected, expected_files=expected_files)
            if 'path' in row: task['path'] = row['path']
        else: raise ValueError('Unknown task type')
        tasks.append(task)
    if any(value != 11 for value in validated.values()): raise ValueError('Incomplete library prefixes')
    if len({task['id'] for task in tasks}) != 648: raise ValueError('Duplicate task identity')
    return {'schema': 'prepared-final-version-cost-plan1', 'mode': 'prepared-formal-version-cost-1',
        'manifest_sha256': manifest_sha, 'catalog_sha256': catalog_sha,
        'input_root': str(input_root), 'run_root': str(run_root), 'libraries': libraries, 'tasks': tasks,
        'budgets': {**manifest['budgets'], 'overall_wall_s': budget_s},
        'budget_revision': 'original1800' if budget_s == 1800 else 'review_only3600_not_accepted',
        'formal_ready': False, 'execution_authorized': False}

def request_for(plan, task, *, framework_freeze_path, framework_freeze_sha, admission_path, admission_sha):
    root = Path(plan['run_root']).resolve()
    if task not in plan['tasks']: raise ValueError('Task is not in the bound plan')
    request = {**task, 'mode': plan['mode'], 'run_root': str(root),
        'library': str(root / 'libraries' / task['library_key']),
        'framework_freeze_path': str(framework_freeze_path), 'framework_freeze_sha256': framework_freeze_sha,
        'admission_path': str(admission_path), 'admission_sha256': admission_sha}
    return request

def require_formal_admission(plan, admission, *, package_sha, authorized_reference):
    # A missing condition stops BEFORE run-root allocation or process creation.
    if type(package_sha) is not str or not re.fullmatch('[0-9a-f]{64}', package_sha):
        raise PermissionError('A nonempty exact package SHA256 is required before formal admission')
    ci = admission.get('exact_new_harness_CI') or {}
    freeze = admission.get('final_freeze') or {}
    if not (admission.get('execution_authorized') is True and
            admission.get('authorized_reference') == authorized_reference and
            admission.get('package_sha256') == package_sha and
            admission.get('plan_content_sha256') == sha(json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()) and
            admission.get('accepted_budget_s') == plan['budgets']['overall_wall_s'] and
            ci.get('conclusion') == 'success' and type(ci.get('run_id')) is int and ci['run_id'] > 0 and
            re.fullmatch('[0-9a-f]{40}', ci.get('source_commit', '')) and
            freeze.get('source_commit') == ci.get('source_commit') and
            freeze.get('package_sha256') == package_sha and
            admission.get('real12_execution_human_authorized') is True):
        raise PermissionError('Formal admission incomplete; do not allocate a root or launch any worker')

def decorate_plan(base, *, manifest_path, catalog_path, freeze_sha, reference, run_key):
    result = dict(base)
    b = base['budgets']
    result.update(run_key=run_key, authorized_reference=reference, scope='prepared_formal',
        freeze_sha256=freeze_sha,
        manifest_path=str(manifest_path), catalog_path=str(catalog_path),
        guard_cap_s=b['quota_preflight_cap_s'],
        preflight_mode='official', preflight_worker=str(Path(manifest_path).resolve().parents[1] / 'version_cost_preflight_worker.py'))
    result['budgets'] = {**b, 'global_wall_s': b['overall_wall_s'], 'global_output_B': b['run_root_observed_logical_B'],
        'library_B': b['per_library_observed_logical_B'], 'metadata_reserve_B': 16 << 10,
        'task_wall_s': b['per_controlled_process_wall_s'], 'task_RSS_B': b['process_peak_RSS_B']}
    return result

def validate_execution_plan(plan, stage):
    stage = Path(stage).resolve()
    if stage.name != 'version-cost-final-candidate-01': raise ValueError('Wrong prepared package')
    if plan['mode'] == 'candidate-owned-smoke-1':
        if plan['run_key'] != 'owned-smoke' or plan['libraries'] != [{'library_key': 'owned-full', 'role': 'full'}] or len(plan['tasks']) != 3:
            raise ValueError('Only fixed new owned smoke admitted')
        for i, (task, op) in enumerate(zip(plan['tasks'], ['append', 'validate_history', 'restore'])):
            if task['seq'] != i or task['op'] != op or task['library_key'] != 'owned-full' or task['kind'] != 'full' or task['requires'] != ([] if i == 0 else [plan['tasks'][i - 1]['id']]):
                raise ValueError('Owned smoke trace differs')
        return
    if plan['mode'] != 'prepared-formal-version-cost-1': raise ValueError('Unknown prepared plan mode')
    manifest = read_bound(plan['manifest_path'], plan['manifest_sha256'])
    catalog = read_bound(plan['catalog_path'], plan['catalog_sha256'])
    base = compile_plan(manifest, catalog, manifest_sha=plan['manifest_sha256'], catalog_sha=plan['catalog_sha256'],
        input_root=plan['input_root'], run_root=plan['run_root'], budget_s=plan['budgets']['overall_wall_s'])
    expected = decorate_plan(base, manifest_path=plan['manifest_path'], catalog_path=plan['catalog_path'],
        freeze_sha=plan['freeze_sha256'], reference=plan['authorized_reference'], run_key=plan['run_key'])
    for key in ['quota_script', 'preflight_freeze_path', 'preflight_freeze_sha256']:
        expected[key] = plan[key]
    if expected != plan or Path(plan['run_root']).resolve() != stage / 'runs' / plan['run_key']:
        raise ValueError('Prepared plan differs from deterministic translation')
