"""Strict member and source-byte audit for a version-scoped source distribution."""
import hashlib
from pathlib import PurePosixPath
import re
import tarfile


def audit_archive(path, version, expected):
    if re.fullmatch(r'\d+\.\d+\.\d+', version) is None:
        raise ValueError('Explicit version required')
    prefix = 'rkv1-' + version
    seen, hashed, total = set(), {}, 0
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts
            if not parts or parts[0] != prefix or '..' in parts or member.name.startswith('/') or '\\' in member.name:
                raise ValueError('Unsafe or wrong-version archive path')
            if member.name in seen:
                raise ValueError('Duplicate archive member')
            seen.add(member.name)
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError('Archive links or special files refused')
            rel = '/'.join(parts[1:])
            if rel.startswith(('results/', '.tools/', '.research/', 'data/')) and not rel.startswith('results/v'+version+'/'):
                raise ValueError('Historical or private payload in scoped source archive')
            if not rel or not (rel in expected or rel in ('PKG-INFO', 'setup.cfg') or rel.startswith('rkv1.egg-info/')):
                raise ValueError('Unexpected source archive payload: '+rel)
            with archive.extractfile(member) as stream:
                sha = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1 << 20), b''):
                    sha.update(chunk)
            hashed[rel] = sha.hexdigest()
            total += member.size
    if not set(expected) <= set(hashed):
        raise ValueError('Required source or current report missing')
    if any(hashed[rel] != sha for rel, sha in expected.items()):
        raise ValueError('Required source bytes changed')
    return {'required_files': len(expected), 'actual_files': len(hashed), 'uncompressed_B': total,
            'required_source_SHA_equal': True, 'historical_results_in_sdist': False}
