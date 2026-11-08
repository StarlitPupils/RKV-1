"""Portable CI entry: synthetic metadata plus optional Windows owned workers; NO quota RPC."""
import argparse
import hashlib
import itertools
import json
import sys
import sysconfig
import tempfile
from contextlib import contextmanager
from pathlib import Path
from version_cost_candidate_interface import compile_plan, require_formal_admission

def digest(raw): return hashlib.sha256(raw).hexdigest()

@contextmanager
def owned_fixture(prefix):
    parent = Path(__file__).resolve().parent / 'ci-owned-fixtures'
    parent.mkdir(exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=prefix, dir=parent)).resolve()
    if not folder.is_relative_to(parent.resolve()): raise ValueError('Fixture escaped owned workspace')
    # Preserve successful/failed evidence; CI runner lifecycle owns later workspace disposal.
    yield str(folder)

def fixture(input_root):
    versions = [{'version': f'v{i:03d}', 'original_commit': f'{i:040x}',
        'files': [{'path': name, 'bytes': len(raw), 'sha256': digest(raw), 'Git_blob_SHA1': 'a' * 40}
                  for name, raw in [('README.md', f'new CI fixture {i}'.encode()), ('docs/ROADMAP.md', b'')]]} for i in range(12)]
    catalog = {'pinned_input_commit': 'b' * 40, 'versions': versions}
    catalog_sha = digest(json.dumps(catalog).encode())
    libraries, tasks = [], []
    def add(row):
        row.update(sequence=len(tasks), requires_complete=[] if not tasks else [tasks[-1]['task_id']]); tasks.append(row)
    for order, roles in enumerate(itertools.permutations(('full', 'solid', 'rkv'))):
        for position, role in enumerate(roles):
            key = f'order{order:02d}-{role}'
            libraries.append({'library_key': key, 'role': role, 'order_index': order, 'position': position})
            for i, item in enumerate(versions):
                v = item['version']; prefix = [x['version'] for x in versions[:i + 1]]
                add({'task_id': f'{key}-u{i}', 'library_key': key, 'role': role, 'kind': 'update', 'version': v,
                    'input_version': v, 'create': i == 0, 'input_source_directory': str(input_root / v / 'originals'),
                    'input_files': item['files'], 'expected_visible_versions': prefix, 'metric_boundary': 'API_CALL_ONLY'})
                add({'task_id': f'{key}-h{i}', 'library_key': key, 'role': role, 'kind': 'validate_history', 'version': v,
                    'expected_visible_versions': prefix, 'whole_restore_calls': len(prefix), 'original_file_checks': 2 * len(prefix), 'metric_boundary': 'VALIDATION_ONLY'})
            for selector, i in [('v000', 0), ('v005', 5), ('current', 11)]:
                for j, operation in enumerate(['read_path', 'read_path', 'read_missing', 'restore']):
                    row = {'task_id': f'{key}-{selector}-{j}', 'library_key': key, 'role': role, 'kind': 'cold_read',
                        'selector': selector, 'expected_version': versions[i]['version'], 'operation': operation, 'metric_boundary': 'API_CALL_ONLY'}
                    if operation == 'restore': row['expected_files'] = versions[i]['files']
                    elif operation == 'read_missing': row.update(path='__rkv_cost_missing__.md', expected_files=[], expected_return='None_not_empty_bytes')
                    else: row.update(path=versions[i]['files'][j]['path'], expected_files=[versions[i]['files'][j]])
                    add(row)
    manifest = {'libraries': libraries, 'tasks': tasks,
        'versions': [{**v, 'source_directory': str(input_root / v['version'] / 'originals')} for v in versions],
        'source_input_manifest_sha256': catalog_sha, 'source_input_commit': catalog['pinned_input_commit'],
        'budgets': {'overall_wall_s': 1800}}
    return manifest, catalog, catalog_sha

def offline():
    with owned_fixture('rkv-candidate-ci-') as directory:
        root = Path(directory); m, c, cs = fixture(root / 'inputs')
        plan = compile_plan(m, c, manifest_sha='c' * 64, catalog_sha=cs,
            input_root=root / 'inputs', run_root=root / 'run-not-created', budget_s=1800)
        assert len(plan['tasks']) == 648 and len(plan['libraries']) == 18
        current = [r for r in plan['tasks'] if r.get('selected_version') == 'v011']
        assert len(current) == 72 and all(r['version'] is None for r in current)
        for package in [None, '', '0' * 63, '0' * 64]:
            try: require_formal_admission(plan, {}, package_sha=package, authorized_reference=1)
            except PermissionError: pass
            else: raise AssertionError('Unknown admission passed')
        assert not (root / 'run-not-created').exists()
    print(json.dumps({'offline_CI_checks': True, 'synthetic_rows': 648, 'official_calls': 0, 'formal_runs': 0}))

def worker_smoke():
    if sys.platform != 'win32': raise RuntimeError('Native worker CI requires Windows; do not silently skip')
    from version_cost_readonly_receipts import identity, save
    from version_cost_task_monitor import run_task
    modules = Path(__file__).resolve().parent
    with owned_fixture('rkv-owned-worker-ci-') as directory:
        stage = Path(directory) / 'version-cost-final-candidate-01'; root = stage / 'runs/owned-smoke'
        source = stage / 'owned-inputs/v000'; (source / 'docs').mkdir(parents=True)
        (source / 'README.md').write_bytes(b'NEW isolated CI\r\n\xff'); (source / 'docs/ROADMAP.md').write_bytes(b'')
        truth = {name: identity(source / name) for name in ['README.md', 'docs/ROADMAP.md']}
        files = {str(p): identity(p) for p in modules.glob('version_cost_*.py')}
        paths = [str(modules), sysconfig.get_path('purelib'), str(Path(sys._base_executable).parent / 'Lib'), str(Path(sys._base_executable).parent / 'DLLs')]
        save(stage / 'runtime-freeze.json', {'absolute_files': files, 'path_roots': paths})
        for name in ['libraries', 'specs', 'cases']: (root / name).mkdir(parents=True, exist_ok=True)
        tasks = [{'id': 'add', 'op': 'append', 'version': 'v000', 'create': True, 'source': str(source), 'expected_files': truth},
                 {'id': 'history', 'op': 'validate_history', 'versions': ['v000'], 'expected_history': {'v000': truth}},
                 {'id': 'current', 'op': 'restore', 'version': None, 'selected_version': 'v000', 'operation': 'restore', 'expected_files': truth}]
        for task in tasks:
            spec = {**task, 'mode': 'candidate-owned-smoke-1', 'owned_root': str(stage), 'campaign_root': str(root),
                'library_key': 'owned-full', 'kind': 'full', 'library': str(root / 'libraries/owned-full'),
                'freeze_path': str(stage / 'runtime-freeze.json'), 'freeze_sha256': identity(stage / 'runtime-freeze.json')['sha256'], 'path_roots': paths}
            p = root / 'specs' / (task['id'] + '.json'); save(p, spec)
            worker = modules / ('version_cost_candidate_history_worker.py' if task['op'] == 'validate_history' else 'version_cost_candidate_api_worker.py')
            observed = run_task(root / 'cases' / task['id'], worker, p, wall_s=10, rss_B=128 << 20,
                global_snapshot=lambda: {'reason': None}, on_created=lambda event: None)
            assert observed['status'] == 'completed' and observed['job_accounting'] == {'total': 1, 'active': 0}
        for prefix in ['cases/history/work/v000/outputs', 'cases/current/work/outputs']:
            for name in truth: assert (root / prefix / name).read_bytes() == (source / name).read_bytes()
    print(json.dumps({'native_owned_CI_smoke': True, 'task_processes': 3, 'official_calls': 0, 'formal_runs': 0}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--offline', action='store_true'); parser.add_argument('--worker-smoke', action='store_true')
    args = parser.parse_args()
    if args.offline: offline()
    if args.worker_smoke: worker_smoke()
    if not (args.offline or args.worker_smoke): parser.error('Select offline and/or owned worker CI checks; no formal execution option')
