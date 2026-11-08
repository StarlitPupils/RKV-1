"""Bind a fresh held-Job official observation to each tiny-owned coordinator row."""
import json
import time
from pathlib import Path
from version_cost_readonly_receipts import identity
from version_cost_bounded_preflight import run_bounded, allowed

def permission_from_binding(binding, root, reference):
    if binding.get('origin') != 'bounded-official-preflight':
        return False
    try:
        path = Path(binding['observation_path']).resolve()
        if not path.is_relative_to(Path(root).resolve() / 'preflights'):
            return False
        if identity(path)['sha256'] != binding['observation_sha256']:
            return False
        record = json.loads(path.read_bytes())
        # Re-evaluate the actual observation. A callback boolean or stale summary is insufficient.
        return record['authorized_reference'] == reference and allowed(record)
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
            'freeze_sha256': plan['preflight_freeze_sha256']}
    folder = controller.root / 'preflights' / task['id']
    record = run_bounded(folder, spec, deadline=deadline, cleanup_s=cleanup_s)
    path = folder / 'observation.json'
    return {'origin': 'bounded-official-preflight', 'observation_path': str(path),
            'observation_sha256': identity(path)['sha256'],
            'observed_mode': record['mode'], 'observation_reason': record['reason'],
            'callback_permission_for_diagnostics_only': record['permission'],
            'fresh_run_for_task': task['id'], 'cache_reused': False}
