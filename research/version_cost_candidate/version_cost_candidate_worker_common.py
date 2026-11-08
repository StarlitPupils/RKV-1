"""Prepared final worker admission/output helpers; only bounded owned smoke is open."""
import hashlib
import json
import os
import sys
from pathlib import Path

PATHS = ('README.md', 'docs/ROADMAP.md')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.flush(); os.fsync(stream.fileno())

def admit(spec_path, work):
    raw = Path(spec_path).read_bytes(); spec = json.loads(raw)
    stage, root, library = [Path(spec[name]).resolve() for name in ['owned_root', 'campaign_root', 'library']]
    if stage.name != 'version-cost-final-candidate-01' or root.parent != stage / 'runs' or library != root / 'libraries' / spec['library_key']:
        raise ValueError('Wrong prepared root/library binding')
    if spec['mode'] == 'candidate-owned-smoke-1':
        if root.name != 'owned-smoke' or spec['library_key'] != 'owned-full' or spec['kind'] != 'full':
            raise ValueError('Only the declared tiny smoke scope is open')
        max_file = 256
    elif spec['mode'] == 'prepared-formal-version-cost-1':
        grant = spec.get('formal_admission') or {}
        if not (grant.get('execution_authorized') is True and grant.get('real12_execution_human_authorized') is True and
                grant.get('plan_file_sha256') == spec.get('bound_plan_file_sha256') and
                grant.get('authorized_reference') == spec.get('authorized_reference') and
                grant.get('package_sha256') == spec.get('package_sha256') and
                (grant.get('exact_new_harness_CI') or {}).get('conclusion') == 'success'):
            raise PermissionError('Formal worker admission missing')
        max_file = 512 << 10
    else: raise ValueError('Unknown candidate worker scope')
    freeze_raw = Path(spec['freeze_path']).read_bytes()
    if sha(freeze_raw) != spec['freeze_sha256']: raise ValueError('Framework freeze differs')
    freeze = json.loads(freeze_raw)
    for name, expected in freeze['absolute_files'].items():
        data = Path(name).read_bytes()
        if len(data) != expected['bytes'] or sha(data) != expected['sha256']: raise ValueError('Framework identity differs')
    if spec['path_roots'] != freeze['path_roots']: raise ValueError('Package paths differ')
    for truth in [spec.get('expected_files', {})] + list(spec.get('expected_history', {}).values()):
        if not set(truth) <= set(PATHS) or any(type(v['bytes']) is not int or not 0 <= v['bytes'] <= max_file for v in truth.values()):
            raise ValueError('Expected original bound')
    if spec['mode'] == 'candidate-owned-smoke-1' and (spec.get('version') not in (None, 'v000') or any(v != 'v000' for v in spec.get('versions', []))):
        raise ValueError('Owned smoke admits only its single new version')
    sys.path = list(freeze['path_roots']); sys.pycache_prefix = str(Path(work) / 'unused-pycache-prefix')
    return spec, sha(raw), max_file

def source_for(spec, limit):
    source = Path(spec['source']).resolve(); library = Path(spec['library']).resolve()
    if source.is_relative_to(library) or library.is_relative_to(source): raise ValueError('Input/store overlap')
    if spec['mode'] == 'candidate-owned-smoke-1' and not source.is_relative_to(Path(spec['owned_root']) / 'owned-inputs'):
        raise ValueError('Owned source outside declared fresh input')
    found = {p.relative_to(source).as_posix(): p for p in source.rglob('*') if p.is_file()}
    if set(found) != set(PATHS): raise ValueError('Exact original source membership')
    for name, path in found.items():
        if path.is_symlink(): raise ValueError('Source symlink')
        raw = path.read_bytes()
        if len(raw) > limit or {'bytes': len(raw), 'sha256': sha(raw)} != spec['expected_files'][name]:
            raise ValueError('Original source differs')
    return source

def copy_outputs(work, values, truth):
    if set(values) != set(truth): raise ValueError('Original output membership differs')
    outputs = {}
    for name, raw in values.items():
        item = {'bytes': len(raw), 'sha256': sha(raw)}
        if item != truth[name]: raise ValueError('Original output bytes differ')
        dest = Path(work) / 'outputs' / name; dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        outputs[name] = item
    return outputs
