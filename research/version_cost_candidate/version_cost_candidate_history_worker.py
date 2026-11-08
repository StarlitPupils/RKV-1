"""Prepared independent prefix validator; never imports the API/mutation worker."""
import sys
sys.dont_write_bytecode = True
import time
START, CPU = time.perf_counter_ns(), time.process_time_ns()
import os
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from version_cost_candidate_worker_common import admit, save, sha, copy_outputs
work, spec_path = Path(sys.argv[1]), Path(sys.argv[2]); digest = sha(spec_path.read_bytes()); success = False
save(work / 'entry.json', {'pid': os.getpid(), 'spec_sha256': digest, 'entry_ns': START})
try:
    spec, digest, limit = admit(spec_path, work)
    versions = spec['versions']
    if spec['op'] != 'validate_history' or not 1 <= len(versions) <= 12 or versions != [f'v{i:03d}' for i in range(len(versions))] or set(spec['expected_history']) != set(versions):
        raise ValueError('Complete committed history prefix required')
    from version_cost_archive_only import ArchiveOnly
    archive = ArchiveOnly(spec['library'])
    if archive.current() != versions[-1]: raise ValueError('HEAD differs from expected validation prefix')
    outputs = {v: copy_outputs(work / v, archive.restore(v), spec['expected_history'][v]) for v in versions}
    save(work / 'result.json', {'pid': os.getpid(), 'spec_sha256': digest, 'versions': versions,
        'outputs': outputs, 'update_API_timing': None, 'performance_sample': False}); success = True
except BaseException:
    save(work / 'error.json', {'pid': os.getpid(), 'spec_sha256': digest, 'traceback': traceback.format_exc()}); raise
finally:
    save(work / 'finally.json', {'success': success, 'pid': os.getpid(), 'spec_sha256': digest,
        'entry_wall_ns': time.perf_counter_ns() - START, 'entry_self_cpu_ns': time.process_time_ns() - CPU})
