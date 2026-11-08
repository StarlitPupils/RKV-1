"""Parent-side endpoint inventories; SHA binding needs an external trusted tip."""
import hashlib
import json
import os
import stat
import time
from pathlib import Path

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())

def identity(path):
    raw = Path(path).read_bytes()
    return {'bytes': len(raw), 'sha256': sha(raw)}

def _regular(path, directory):
    value = path.lstat()
    if stat.S_ISLNK(value.st_mode) or getattr(value, 'st_file_attributes', 0) & 0x400:
        raise ValueError('Symlink/reparse point refused')
    if directory != stat.S_ISDIR(value.st_mode) or (not directory and not stat.S_ISREG(value.st_mode)):
        raise ValueError('Unsupported inventory member')
    return value

def _fields(value):
    return {'bytes': value.st_size, 'mtime_ns': value.st_mtime_ns,
            'device': value.st_dev, 'file_id': value.st_ino, 'hardlinks': value.st_nlink}

def capture(root, binding, phase):
    start_ns, cpu_ns = time.perf_counter_ns(), time.process_time_ns()
    root = Path(root)
    entries, dirs, read_bytes, reads = {}, [], 0, 0
    if root.exists():
        _regular(root, True)
        for current, subdirs, files in os.walk(root, followlinks=False):
            current = Path(current)
            for name in sorted(subdirs):
                directory = current / name
                _regular(directory, True)
                dirs.append(directory.relative_to(root).as_posix())
            for name in sorted(files):
                path = current / name
                before = _regular(path, False)
                if before.st_size > 4 << 20 or len(entries) >= 512:
                    raise ValueError('Owned inventory bound')
                with path.open('rb') as stream:
                    opened_before = os.fstat(stream.fileno())
                    raw = stream.read((4 << 20) + 1)
                    opened_after = os.fstat(stream.fileno())
                after = _regular(path, False)
                if not (_fields(before) == _fields(opened_before) == _fields(opened_after) == _fields(after)) or len(raw) != before.st_size:
                    raise ValueError('Unstable inventory file')
                entries[path.relative_to(root).as_posix()] = {**_fields(after), 'sha256': sha(raw)}
                reads += 1
                read_bytes += len(raw)
                if read_bytes > 16 << 20:
                    raise ValueError('Owned inventory byte bound')
    result = {'schema': 'readonly-endpoint-inventory1', 'phase': phase,
              'binding': binding, 'library': str(root.resolve()), 'root_exists': root.exists(),
              'directories': sorted(dirs), 'files': dict(sorted(entries.items())),
              'raw_file_read_calls': reads, 'raw_file_read_B': read_bytes,
              'start_ns': start_ns, 'end_ns': time.perf_counter_ns(),
              'self_cpu_ns': time.process_time_ns() - cpu_ns,
              'physical_IO_B': None, 'whole_system_resources': None}
    result['wall_ns'] = result['end_ns'] - start_ns
    return result

def delta(before, after):
    a, b = before['files'], after['files']
    return {'added': sorted(set(b) - set(a)), 'removed': sorted(set(a) - set(b)),
            'changed': sorted(name for name in set(a) & set(b) if a[name] != b[name]),
            'directories_changed': before['directories'] != after['directories'],
            'root_existence_changed': before['root_exists'] != after['root_exists']}

def unchanged(change):
    return not any(change.values())
