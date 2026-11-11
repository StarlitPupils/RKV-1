"""Bind a fresh held-Job official observation to each tiny-owned coordinator row."""
import json
import math
import time
from pathlib import Path
from version_cost_readonly_receipts import identity, sha
from version_cost_bounded_preflight import run_bounded, allowed

RETRY_DIR = 'retry-01'
TRANSPORT_ERROR = ('failed to fetch codex rate limits: error sending request for url '
                   '(https://chatgpt.com/backend-api/wham/usage)')


def retryable_transport_error(record):
    """Only classify the bound account/rateLimits/read transport error."""
    try:
        result, footer = record['worker_result'], record['worker_footer']
        read = result['read_record']
        helper, = read['held_app_servers']
        summary = read['summary']
        error = summary['error']
        pid, spec_sha = record['root_pid'], record['spec_sha256']
        return (
            record['mode'] == 'official' and record['reason'] == 'quota_or_evidence_denied' and
            record['permission'] is False and record['root_exit_code'] == 0 and
            record['cleanup_confirmed'] is True and record['job_final']['active'] == 0 and
            result['pid'] == footer['pid'] == pid and
            result['spec_sha256'] == footer['spec_sha256'] == spec_sha and footer['success'] is True and
            read['failure'] is None and read['official_RPC_source_unchanged'] is True and
            read['RPC_retries'] == 0 and read['owned_failure_before_RPC'] is False and
            helper['pipes_closed'] is True and helper['cleanup_error'] is None and
            type(helper['actual_exit_code']) is int and
            any(member['pid'] == helper['pid'] and member['actual_exit_code'] == helper['actual_exit_code']
                and member['observation_error'] is None for member in record['members']) and
            set(summary) == {'id', 'error'} and summary['id'] == 2 and
            error['code'] == -32603 and error['message'] == TRANSPORT_ERROR
        )
    except (KeyError, TypeError, ValueError):
        return False


def retry_timing_valid(retry, first, second):
    elapsed, budget = retry['elapsed_s'], retry['budget_s']
    return (type(elapsed) in (int, float) and type(budget) in (int, float) and
            math.isfinite(elapsed) and math.isfinite(budget) and
            0 <= first['wall_s'] + second['wall_s'] <= elapsed < budget <= 10)


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
        if not (spec['mode'] == 'official' and spec['authorized_reference'] == reference and
                spec['task_id'] == task_id and spec['plan_sha256'] == plan_sha and
                record['spec_sha256'] == sha(spec_raw) and record['authorized_reference'] == reference):
            return False
        if 'retry' not in binding:
            return allowed(record)
        if not retryable_transport_error(record):
            return False
        retry = binding['retry']
        retry_root = expected.parent / RETRY_DIR
        retry_path = retry_root / 'observation.json'
        if (retry_path.resolve() != retry_path or (retry_root / 'spec.json').read_bytes() != spec_raw):
            return False
        retry_raw = retry_path.read_bytes()
        if sha(retry_raw) != retry['observation_sha256']:
            return False
        second = json.loads(retry_raw)
        return (second['spec_sha256'] == record['spec_sha256'] and
                second['authorized_reference'] == reference and second['permission'] is True and
                retry_timing_valid(retry, record, second) and allowed(second))
    except (OSError, KeyError, TypeError, ValueError):
        return False

def check_row(controller, task, reference):
    plan = controller.plan
    cleanup_s = 2.
    started = time.perf_counter()
    deadline = min(started + plan['guard_cap_s'],
                   controller.started + plan['budgets']['global_wall_s'] - cleanup_s)
    spec = {'mode': plan['preflight_mode'], 'authorized_reference': reference,
            'worker': plan['preflight_worker'], 'quota_script': plan['quota_script'],
            'freeze_path': plan['preflight_freeze_path'],
            'freeze_sha256': plan['preflight_freeze_sha256'],
            'task_id': task['id'], 'plan_sha256': controller.plan_sha}
    folder = controller.root / 'preflights' / task['id']
    record = run_bounded(folder, spec, deadline=deadline, cleanup_s=cleanup_s)
    path = folder / 'observation.json'
    binding = {'origin': 'bounded-official-preflight', 'observation_path': str(path),
            'observation_sha256': identity(path)['sha256'],
            'observed_mode': record['mode'], 'observation_reason': record['reason'],
            'callback_permission_for_diagnostics_only': record['permission'],
            'fresh_run_for_task': task['id'], 'cache_reused': False}
    if retryable_transport_error(record) and time.perf_counter() < deadline:
        retry_folder = folder / RETRY_DIR
        second = run_bounded(retry_folder, spec, deadline=deadline, cleanup_s=cleanup_s)
        binding['retry'] = {'observation_sha256': identity(retry_folder / 'observation.json')['sha256'],
                            'elapsed_s': time.perf_counter() - started,
                            'budget_s': min(plan['guard_cap_s'], deadline - started)}
        binding['callback_permission_for_diagnostics_only'] = (
            second['permission'] and retry_timing_valid(binding['retry'], record, second))
    return binding
