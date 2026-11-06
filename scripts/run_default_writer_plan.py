"""Bounded default writer acceptance from an externally fixed plan. Use a new output directory for each execution."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from rkv1.benchmark import peak_rss
from rkv1.memory import Memory
from scripts.run_memory_fault_matrix import Producer
from scripts.default_writer_plan import load_plan
from scripts.writer_scope_fixture import ledger, meta, publish, source, verify

PHASES = ('before_HEAD', 'after_HEAD', 'clean_return')



def load(path):
    return json.loads(path.read_bytes())


def worker(folder, phase):
    limits = load(folder / "case-plan.json")["limits_s"]
    from rkv1 import memory as implementation

    wall, cpu = time.perf_counter(), time.process_time()
    memory = Memory(folder / 'memory')
    publish(folder / 'started.json', {'pid': os.getpid()})
    original_head = implementation._head
    success = False

    def publish_head(path, value):
        if Path(path) != memory.root / 'HEAD.json':
            return original_head(path, value)
        if phase == 'after_HEAD':
            original_head(path, value)
        publish(folder / 'ready.json', {'pid': os.getpid(), 'new_sid': value['snapshot_id'],
                                        'observed_ns': time.perf_counter_ns()})
        deadline = time.monotonic() + limits["owner_barrier"]
        while not (folder / 'allow-return.json').exists():
            if time.monotonic() >= deadline:
                raise TimeoutError('Parent did not release writer')
            time.sleep(.01)
        if phase != 'after_HEAD':
            original_head(path, value)

    try:
        implementation._head = publish_head
        result = memory.add(folder / 'intent-A', label='default-A')
        publish(folder / 'returned.json', result)
        success = True
    finally:
        implementation._head = original_head
        publish(folder / 'worker-finally.json', {'pid': os.getpid(), 'success': success,
                                                'wall_s': time.perf_counter() - wall,
                                                'self_cpu_s': time.process_time() - cpu,
                                                'peak_rss_B': peak_rss()})


def cli(folder, label, command, *args):
    limits = load(folder / "case-plan.json")["limits_s"]
    argv = [sys.executable, '-m', 'rkv1', command, str(folder / 'memory'), *map(str, args)]
    publish(folder / f'{label}-reserved.json', {'argv': argv})
    started = time.perf_counter_ns()
    with (folder / f'{label}.stdout').open('xb') as stdout, (folder / f'{label}.stderr').open('xb') as stderr:
        process = subprocess.Popen(argv, stdout=stdout, stderr=stderr)
        try:
            code = process.wait(timeout=limits["cli"])
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=limits["cli"])
            publish(folder / f'{label}-exit.json', {'launcher_pid': process.pid,
                                                    'exit': process.returncode,
                                                    'started_ns': started,
                                                    'observed_ns': time.perf_counter_ns()})
    return code


def query(folder, label, memory, pin, old_sid, epoch, expected_sid):
    for name in ('current', 'pin', 'explicit'):
        if name == 'current':
            result, expected, sid = memory.search('RKV99PROBE', top_k=8), epoch, expected_sid
        elif name == 'pin':
            result, expected, sid = pin.search('RKV99PROBE', top_k=8), 0, old_sid
        else:
            result, expected, sid = memory.search('RKV99PROBE', top_k=8, snapshot=old_sid), 0, old_sid
        original = (folder / ('source-old' if expected == 0 else 'intent-A' if expected == 1 else 'intent-B') / 'corpus.jsonl').read_bytes()
        proof = verify(memory, result, original, sid)
        publish(folder / f'{label}-{name}.json', {'result': result, 'epoch': expected, 'proof': proof})


def run_case(folder, case, plan, guard):
    phase, size = case['phase'], case['size']
    limits = plan['limits_s']
    wall, cpu = time.perf_counter(), time.process_time()
    deadline = time.monotonic() + limits['case']
    def check():
        guard()
        if time.monotonic() >= deadline:
            raise TimeoutError('Case time limit reached')
    def wait_file(path, process):
        end = min(deadline, time.monotonic() + limits['owner_start_or_ready'])
        while not path.exists():
            check()
            if process.poll() is not None or time.monotonic() >= end:
                raise RuntimeError('Writer ended or marker timed out: ' + path.name)
            time.sleep(.01)
    folder.mkdir()
    publish(folder / 'case-plan.json', {'case':case, 'limits_s':plan['limits_s']})
    for epoch, name in enumerate(('source-old', 'intent-A', 'intent-B')):
        path = folder / name / 'corpus.jsonl'
        path.parent.mkdir()
        with path.open('xb') as stream:
            stream.write(source(size, epoch))
        if meta(path) != plan['fixture_files'][f'{size}:{epoch}']:
            raise ValueError('Fixture differs from plan')
    memory = Memory.create(folder / 'memory', chunk_size=4096)
    old_sid = memory.add(folder / 'source-old', label='owned-baseline')['snapshot_id']
    publish(folder / 'baseline.json', {'sid': old_sid, 'files': ledger(memory.root)})
    with memory.pin() as pin, (folder / 'writer.log').open('xb') as log:
        publish(folder / 'writer-reserved.json', {'before_spawn': True})
        start = time.perf_counter_ns()
        process = subprocess.Popen([sys.executable, '-m', 'scripts.run_default_writer_plan', str(folder), '--worker', phase],
                                   stdout=log, stderr=subprocess.STDOUT)
        owner = None
        completed = False
        try:
            wait_file(folder / 'started.json', process)
            owner = Producer(load(folder / 'started.json')['pid'], process)
            wait_file(folder / 'ready.json', process)
            ready = load(folder / 'ready.json')
            if ready['pid'] != owner.pid:
                raise ValueError('Barrier producer differs')
            publish(folder / 'held-before.json', ledger(memory.root, held=True))
            check()
            if cli(folder, 'blocked-add', 'memory-add', folder / 'intent-B') != 2:
                raise ValueError('CLI writer did not refuse competition')
            check()
            if cli(folder, 'blocked-budget', 'memory-budget') != 2:
                raise ValueError('CLI configuration did not refuse competition')
            after = ledger(memory.root, held=True)
            publish(folder / 'held-after.json', after)
            if after != load(folder / 'held-before.json'):
                raise ValueError('Blocked CLI changed files')
            epoch = int(phase == 'after_HEAD')
            check()
            query(folder, 'held', memory, pin, old_sid, epoch, ready['new_sid'] if epoch else old_sid)
            check()
            if phase == 'clean_return':
                publish(folder / 'allow-return.json', {'allow': True})
            else:
                owner.kill()
            actual_exit = owner.exit()
            launcher_exit = process.wait(timeout=limits["cli"])
            publish(folder / 'writer-exit.json', {'pid': owner.pid, 'launcher_pid': process.pid,
                                                  'exit': actual_exit, 'launcher_exit': launcher_exit,
                                                  'started_ns': start, 'observed_ns': time.perf_counter_ns()})
            completed = True
            if (actual_exit == launcher_exit == 0) != (phase == 'clean_return'):
                raise ValueError('Writer exit differs from boundary')
            publish(folder / 'head-after-exit.json', {'sid': memory.current()})
            check()
            if cli(folder, 'new-intent', 'memory-add', folder / 'intent-B', '--label', 'independent-B') != 0:
                raise ValueError('New intent failed after observed exit')
            check()
            if cli(folder, 'configure', 'memory-budget') != 0:
                raise ValueError('Configuration failed after observed exit')
            sid = load(folder / 'new-intent.stdout')['snapshot_id']
            check()
            query(folder, 'new', memory, pin, old_sid, 2, sid)
            check()
        finally:
            cleanup = process.poll() is None
            try:
                if cleanup:
                    owner_exited = (owner is not None and owner.handle is not None
                                    and owner.dll.WaitForSingleObject(owner.handle, 0) == 0)
                    if not owner_exited:
                        owner.kill() if owner is not None else process.kill()
                    process.wait(timeout=30)
            finally:
                if owner is not None:
                    owner.close()
                publish(folder / 'case-resources.json', {'wall_s':time.perf_counter()-wall, 'self_cpu_s':time.process_time()-cpu, 'peak_rss_B':peak_rss(), 'full_tree_cpu_rss':None})
                publish(folder / 'writer-cleanup.json', {'terminated_by_cleanup': cleanup,
                                                         'normal_observation_saved': completed})


def run(root, anchor, guard=None):
    plan = load_plan(anchor)
    if plan['mode'] == 'formal' and guard is None:
        raise ValueError('Formal run requires external exact-CI and quota guard')
    root = Path(root).resolve()
    root.mkdir()
    publish(root / 'plan.json', plan)
    wall, cpu = time.perf_counter(), time.process_time()
    completed = 0
    failure = None
    deadline = time.monotonic() + plan['limits_s']['whole_run']
    def check():
        if guard is not None:
            guard()
        if time.monotonic() >= deadline:
            raise TimeoutError('Whole plan time limit reached')
    try:
        for case in plan['schedule']:
            check()
            publish(root / (case['id'] + '-reserved.json'), {'case':case, 'before_start':True})
            run_case(root / case['id'], case, plan, check)
            completed += 1
        if load_plan(anchor) != plan:
            raise ValueError('Plan or source changed during execution')
    except BaseException as error:
        failure = type(error).__name__
        raise
    finally:
        publish(root / 'parent-finally.json', {'planned':len(plan['schedule']), 'completed':completed,
            'failure':failure, 'missing_execution_and_extra_cost':None,
            'wall_s':time.perf_counter()-wall, 'self_cpu_s':time.process_time()-cpu,
            'peak_rss_B':peak_rss(), 'full_tree_cpu_rss':None})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--worker', choices=PHASES)
    parser.add_argument('--plan', type=Path)
    args = parser.parse_args()
    if args.worker:
        worker(args.root, args.worker)
    else:
        run(args.root, args.plan)
