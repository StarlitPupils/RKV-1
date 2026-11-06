"""Strict schedule validation for owned default-writer process checks."""
import hashlib
import json
from pathlib import Path

from scripts.writer_scope_fixture import source, sha

PHASES = ('before_HEAD', 'after_HEAD', 'clean_return')


def text_identity(path):
    raw = Path(path).read_bytes().replace(b'\r\n', b'\n')
    return {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def load_plan(path):
    plan = json.loads(Path(path).read_bytes())
    if plan.get('schema') != 'rkv1-memory-default-writer-plan-v1':
        raise ValueError('Unknown default writer plan schema')
    mode = plan.get('mode')
    if mode == 'formal':
        sizes, rounds = (17, 129, 513), (1, 2, 3)
    elif mode == 'owned-test':
        sizes, rounds = (9,), (1,)
    else:
        raise ValueError('Unknown default writer plan mode')
    schedule = [{'id':f'r{r}-n{n}-{phase}', 'round':r, 'size':n, 'phase':phase}
                for r in rounds for n in sizes for phase in PHASES]
    count = len(schedule)
    if plan.get('schedule') != schedule:
        raise ValueError('Default writer schedule differs')
    counts = {'cases':count, 'default_api_processes':count, 'terminations':count*2//3,
              'normal_returns':count//3, 'cli_attempts':count*4, 'cli_contention_refusals':count*2,
              'cli_successes_after_exit':count*2, 'primary_queries':count*6, 'independent_queries':count*6}
    if plan.get('counts') != counts:
        raise ValueError('Default writer denominator differs')
    fixtures = {f'{n}:{epoch}':{'bytes':len(source(n, epoch)), 'sha256':sha(source(n, epoch))}
                for n in sizes for epoch in (0, 1, 2)}
    if plan.get('fixture_files') != fixtures:
        raise ValueError('Default writer input identity differs')
    limits = {'cli':15, 'owner_start_or_ready':30, 'owner_barrier':75,
              'case':150, 'whole_run':1800, 'independent_audit':300}
    if plan.get('limits_s') != limits:
        raise ValueError('Default writer time limits differ')
    if plan.get('policy') != {'retry':0, 'require_exact_source_ci_success':True,
                              'stop_on_failed_gate_or_quota_unavailable':True,
                              'missing_execution_and_extra_cost':None, 'external_model_calls':0}:
        raise ValueError('Default writer execution policy differs')
    if plan.get('per_case_cli') != [
        {'point':'while_held', 'command':'memory-add', 'exit':2},
        {'point':'while_held', 'command':'memory-budget', 'exit':2},
        {'point':'after_owner_exit', 'command':'memory-add', 'intent':'epoch_2_independent_B', 'exit':0},
        {'point':'after_owner_exit', 'command':'memory-budget', 'exit':0}]:
        raise ValueError('Default writer CLI schedule differs')
    if plan.get('expected') != {
        'before_HEAD':{'held_current_epoch':0, 'after_exit_epoch':0, 'owner_completed':None},
        'after_HEAD':{'held_current_epoch':1, 'after_exit_epoch':1, 'owner_completed':None},
        'clean_return':{'held_current_epoch':0, 'after_exit_epoch':1, 'owner_completed':True},
        'after_new_intent_epoch':2, 'pinned_and_explicit_epoch':0}:
        raise ValueError('Default writer expected outcomes differ')
    if plan.get('source_identity_encoding') != 'UTF-8 text with CRLF normalized to LF':
        raise ValueError('Missing source encoding rule')
    anchors = plan.get('candidate_source_anchors', {})
    if set(anchors) != {'rkv1/memory.py', 'rkv1/memory_writer.py', 'rkv1/cli.py',
                        'scripts/writer_scope_fixture.py', 'scripts/audit_read_view_plan.py',
                        'scripts/default_writer_plan.py', 'scripts/run_default_writer_plan.py',
                        'scripts/audit_default_writer_plan.py', 'scripts/run_memory_fault_matrix.py'}:
        raise ValueError('Default writer source set differs')
    for name, identity in anchors.items():
        if text_identity(name) != identity:
            raise ValueError('Default writer source identity differs: ' + name)
    return plan
