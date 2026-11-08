"""Prepared generic update/cold API worker; external copying stays outside its timer."""
import sys
sys.dont_write_bytecode = True
import time
START, CPU = time.perf_counter_ns(), time.process_time_ns()
import os
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from version_cost_candidate_worker_common import admit, source_for, save, sha, copy_outputs
work, spec_path = Path(sys.argv[1]), Path(sys.argv[2]); digest = sha(spec_path.read_bytes())
success, intervals = False, []
save(work / 'entry.json', {'pid': os.getpid(), 'spec_sha256': digest, 'entry_ns': START})
try:
    spec, digest, limit = admit(spec_path, work)
    from version_cost_archive_only import ArchiveOnly
    op = spec['op']; source = source_for(spec, limit) if op == 'append' else None
    def operation():
        if op == 'append':
            archive = ArchiveOnly.create(spec['library'], spec['kind']) if spec['create'] else ArchiveOnly(spec['library'])
            return archive.append(spec['version'], source)
        archive = ArchiveOnly(spec['library'])
        if op == 'restore': return archive.restore(spec['version'])
        if op == 'read': return archive.read(spec['path'], spec['version'])
        raise ValueError('Unknown API operation')
    setup_end = time.perf_counter_ns(); begin, cpu_begin = time.perf_counter_ns(), time.process_time_ns(); normal = False
    try: value = operation(); normal = True
    finally:
        end, cpu_end = time.perf_counter_ns(), time.process_time_ns()
        intervals.append({'begin_ns': begin, 'end_ns': end, 'wall_ns': end - begin,
                          'self_cpu_ns': cpu_end - cpu_begin, 'returned_normally': normal})
    post_start = time.perf_counter_ns()
    result = {'pid': os.getpid(), 'spec_sha256': digest, 'op': op, 'api_intervals': intervals,
              'setup_end_ns': setup_end, 'post_start_ns': post_start,
              'selected_version': spec.get('selected_version'),
              'formal_performance_sample': spec['mode'] == 'prepared-formal-version-cost-1'}
    if op == 'append': result['receipt'] = value
    elif op == 'read' and spec['operation'] == 'read_missing':
        if value is not None: raise ValueError('Missing is not None')
        result['missing'] = True
    else:
        values = value if op == 'restore' else {spec['path']: value}
        result['outputs'] = copy_outputs(work, values, spec['expected_files'])
    result['post_end_ns'] = time.perf_counter_ns(); save(work / 'result.json', result); success = True
except BaseException:
    save(work / 'error.json', {'pid': os.getpid(), 'spec_sha256': digest, 'traceback': traceback.format_exc()}); raise
finally:
    save(work / 'finally.json', {'success': success, 'pid': os.getpid(), 'spec_sha256': digest,
        'api_intervals': intervals, 'entry_wall_ns': time.perf_counter_ns() - START,
        'entry_self_cpu_ns': time.process_time_ns() - CPU})
