"""Read back persisted CLI/exit receipts and original source, without rerunning writers."""
import argparse
import json
import os
from pathlib import Path
import time

from rkv1.benchmark import peak_rss
from scripts.default_writer_plan import load_plan
from rkv1.memory import Memory
from scripts.audit_read_view_plan import verify
from scripts.writer_scope_fixture import ledger, meta, publish


def audit(root, plan_path, out):
    root = Path(root).resolve()
    def load(path):
        return json.loads(path.read_bytes())

    wall, cpu = time.perf_counter(), time.process_time()
    before = ledger(root)
    plan = load_plan(plan_path)
    deadline = time.monotonic() + plan["limits_s"]["independent_audit"]
    count = len(plan["schedule"])
    phases = ('before_HEAD', 'after_HEAD', 'clean_return')
    parent = load(root / 'parent-finally.json')
    if (plan != load(root / 'plan.json') or parent['planned'] != count or parent['completed'] != count or parent['failure'] is not None):
        raise ValueError('Plan and completed case denominators differ')
    results, returned_bytes = [], 0
    for entry in plan['schedule']:
        if time.monotonic() >= deadline:
            raise TimeoutError('Independent audit time limit reached')
        phase, size = entry['phase'], entry['size']
        case = root / entry['id']
        if load(case / 'case-plan.json') != {'case':entry, 'limits_s':plan['limits_s']}:
            raise ValueError('Case schedule differs')
        originals = []
        for epoch, name in enumerate(('source-old', 'intent-A', 'intent-B')):
            path = case / name / 'corpus.jsonl'
            if meta(path) != plan['fixture_files'][f'{size}:{epoch}']:
                raise ValueError('Original differs from independent plan')
            originals.append(path.read_bytes())
        ready, owner = load(case / 'ready.json'), load(case / 'writer-exit.json')
        clean = phase == 'clean_return'
        expected_exit = 0 if clean else 77 if os.name == 'nt' else -9
        if (owner['pid'] != ready['pid'] or owner['pid'] != load(case / 'started.json')['pid']
                or owner['exit'] != expected_exit or owner['launcher_exit'] != expected_exit
                or load(case / 'writer-cleanup.json') != {'terminated_by_cleanup': False, 'normal_observation_saved': True}):
            raise ValueError('Process exit witness differs')
        for name in ('returned.json', 'worker-finally.json', 'allow-return.json'):
            if (case / name).exists() != clean:
                raise ValueError('Completion evidence inconsistent with actual exit')
        if clean:
            footer = load(case / 'worker-finally.json')
            if not footer['success'] or footer['pid'] != owner['pid'] or load(case / 'returned.json')['snapshot_id'] != ready['new_sid']:
                raise ValueError('Successful operation footer differs')
        last = ready['observed_ns']
        for label, command, code in (('blocked-add', 'memory-add', 2), ('blocked-budget', 'memory-budget', 2),
                                     ('new-intent', 'memory-add', 0), ('configure', 'memory-budget', 0)):
            receipt = load(case / f'{label}-exit.json')
            argv = load(case / f'{label}-reserved.json')['argv']
            if label == 'new-intent':
                if not last < owner['observed_ns'] or argv[5:] != [str(case / 'intent-B'), '--label', 'independent-B']:
                    raise ValueError('New intent was not separated from owner exit')
                last = owner['observed_ns']
            if argv[1:5] != ['-m', 'rkv1', command, str(case / 'memory')] or receipt['exit'] != code or not last <= receipt['started_ns'] <= receipt['observed_ns']:
                raise ValueError('CLI receipt differs from plan or event order')
            last = receipt['observed_ns']
            if code:
                error = (case / f'{label}.stderr').read_bytes()
                if (case / f'{label}.stdout').stat().st_size or not error.startswith(b'ERROR: '):
                    raise ValueError('CLI rejection evidence absent')
                if os.name == 'nt' and b'Another cooperative Memory writer holds this scope' not in error:
                    raise ValueError('CLI failed for an unexpected reason')
        baseline = load(case / 'baseline.json')
        sids = [baseline['sid'], ready['new_sid'], load(case / 'new-intent.stdout')['snapshot_id']]
        visible = int(phase == 'after_HEAD')
        if len(set(sids)) != 3 or load(case / 'head-after-exit.json')['sid'] != sids[int(phase != 'before_HEAD')]:
            raise ValueError('Visibility or distinct update identity differs')
        if load(case / 'configure.stdout')['snapshot_id'] != sids[2]:
            raise ValueError('Configuration changed current snapshot')
        if load(case / 'held-before.json') != load(case / 'held-after.json'):
            raise ValueError('Contention changed repository')
        memory = Memory(case / 'memory')
        current = ledger(memory.root)
        if memory.current() != sids[2] or any(current.get(name) != value for name, value in baseline['files'].items()
              if name != 'HEAD.json'):
            raise ValueError('Old immutable files or final HEAD differ')
        for checkpoint, epoch in (('held', visible), ('new', 2)):
            for reader in ('current', 'pin', 'explicit'):
                proof = load(case / f'{checkpoint}-{reader}.json')
                expected = epoch if reader == 'current' else 0
                if proof['epoch'] != expected:
                    raise ValueError('Source version schedule differs')
                if proof['proof']['whole_source_application_return_B'] != len(originals[expected]):
                    raise ValueError('Primary whole-source charge differs')
                returned_bytes += verify(memory, proof['result'], originals[expected], sids[expected], 'search')
        results.append({'case_id':entry['id'], 'phase': phase, 'owner_exit': owner['exit'], 'owner_completed': True if clean else None,
                        'visible_epoch_after_exit': int(phase != 'before_HEAD'), 'query_count': 6})
    if ledger(root) != before:
        raise ValueError('Audit mutated original run')
    if load_plan(plan_path) != plan:
        raise ValueError('Plan or source changed during independent audit')
    publish(out, {'cases': results, 'queries_verified':count*6, 'cli_contention_refusals':count*2,
                  'cli_successes_after_owner_exit':count*2, 'whole_source_application_return_B': returned_bytes,
                  'wall_s': time.perf_counter() - wall, 'self_cpu_s': time.process_time() - cpu,
                  'peak_rss_B': peak_rss(), 'full_tree_cpu_rss': None})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('plan', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    audit(args.root, args.plan, args.output)
