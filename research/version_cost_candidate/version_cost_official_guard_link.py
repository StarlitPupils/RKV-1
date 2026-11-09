"""Bind a fresh held-Job official observation to each tiny-owned coordinator row."""
import json
import time
from pathlib import Path
from version_cost_readonly_receipts import identity, sha
from version_cost_bounded_preflight import run_bounded, allowed

def permission_from_binding(binding, root, reference, task_id, plan_sha):
    if (binding.get('origin') != 'bounded-official-preflight' or
            binding.get('fresh_run_for_task') != task_id or binding.get('cache_reused') is not False):
        return False
    try:
        path = Path(binding['observation_path']).resolve()
        expected = Path(root).resolve() / 'preflights' / task_id / 'observation.json'
        if path != expected or not expected.resolve().is_relative_to(Path(root).resolve()):
            return False
        raw = path.read_bytes()
        if sha(raw) != binding['observation_sha256']:
            return False
        record = json.loads(raw)
        spec_raw = (path.parent / 'spec.json').read_bytes()
        spec = json.loads(spec_raw)
        return (spec['mode'] == 'official' and spec['authorized_reference'] == reference and
                spec['task_id'] == task_id and spec['plan_sha256'] == plan_sha and
                record['spec_sha256'] == sha(spec_raw) and
                record['authorized_reference'] == reference and allowed(record))
    except (OSError, KeyError, TypeError, ValueError):
        return False

def check_row(controller, task, reference):
    plan = controller.plan
    cleanup_s = 2.
    deadline = min(time.perf_counter() + plan['guard_cap_s'],
                   controller.started + plan['budgets']['global_wall_s'] - cleanup_s)
    spec = {'mode': plan['preflight_mode'], 'authorized_reference': reference,
            'worker': plan['preflight_worker'], 'quota_script': plan['quota_script'],
            'freeze_path': plan['preflight_freeze_path'],
            'freeze_sha256': plan['preflight_freeze_sha256'],
            'task_id': task['id'], 'plan_sha256': controller.plan_sha}
    folder = controller.root / 'preflights' / task['id']
    record = run_bounded(folder, spec, deadline=deadline, cleanup_s=cleanup_s)
    path = folder / 'observation.json'
    return {'origin': 'bounded-official-preflight', 'observation_path': str(path),
            'observation_sha256': identity(path)['sha256'],
            'observed_mode': record['mode'], 'observation_reason': record['reason'],
            'callback_permission_for_diagnostics_only': record['permission'],
            'fresh_run_for_task': task['id'], 'cache_reused': False}
