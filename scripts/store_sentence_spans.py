"""Explicit source binding for tiny owned Store fixtures; no retrieval or API."""
import re
from rkv1.store import Store
from scripts.sentence_spans import locate, recover, digest


def _hash(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _read(root, binding):
    if type(binding) is not dict or set(binding) != {'snapshot_id', 'path', 'source_sha256', 'record_offset', 'record_length', 'record_sha256', 'field'}:
        raise ValueError('Exact source binding required')
    for key in ('snapshot_id', 'source_sha256', 'record_sha256'):
        if not _hash(binding[key]):
            raise ValueError('Explicit original hash required')
    if binding['path'] != 'corpus.jsonl' or binding['field'] not in ('abstract', 'sentences'):
        raise ValueError('Unsupported explicit source path or field')
    for key in ('record_offset', 'record_length'):
        if type(binding[key]) is not int or binding[key] < 0:
            raise ValueError('Invalid original record range')
    if binding['record_length'] == 0:
        raise ValueError('Empty record range')
    store = Store(root, io_backend='bounded')
    with store.snapshot(binding['snapshot_id']) as snapshot:
        entry = snapshot.files.get(binding['path'])
        if entry is None or entry['sha256'] != binding['source_sha256']:
            raise ValueError('Original source identity differs')
        if binding['record_offset'] + binding['record_length'] > entry['size']:
            raise ValueError('Record range outside original source')
        raw = snapshot.read_range(binding['path'], binding['record_offset'], binding['record_length'])
    if digest(raw) != binding['record_sha256']:
        raise ValueError('Original record SHA differs')
    return raw


def make_witness(root, binding, indices):
    if type(indices) is not list or any(type(i) is not int or i < 0 for i in indices) or len(set(indices)) != len(indices):
        raise ValueError('Distinct explicit sentence indices required')
    raw = _read(root, binding)
    rows = locate(raw, field=binding['field'])['sentences']
    if any(i >= len(rows) for i in indices):
        raise ValueError('Sentence index outside source')
    return {'schema': 'experimental-source-span-1', 'binding': dict(binding),
            'sentences': [rows[i] for i in indices],
            'application_record_return_B': len(raw)}


def recover_witness(root, witness, *, expected_binding):
    # This external expected binding is not inferred from the witness itself.
    if type(witness) is not dict or set(witness) != {'schema', 'binding', 'sentences', 'application_record_return_B'}:
        raise ValueError('Unexpected witness schema')
    if type(witness['binding']) is not dict or type(expected_binding) is not dict:
        raise ValueError('Explicit binding dictionaries required')
    if witness['schema'] != 'experimental-source-span-1' or witness['binding'] != expected_binding or any(type(witness['binding'][key]) is not type(value) for key, value in expected_binding.items()):
        raise ValueError('Independently trusted source binding differs')
    if type(witness['sentences']) is not list or type(witness['application_record_return_B']) is not int:
        raise ValueError('Invalid witness accounting or sentence list')
    raw = _read(root, expected_binding)
    if witness['application_record_return_B'] != len(raw):
        raise ValueError('Original record accounting differs')
    indices = [row.get('sentence_index') if type(row) is dict else None for row in witness['sentences']]
    if any(type(i) is not int for i in indices) or len(set(indices)) != len(indices):
        raise ValueError('Duplicate or invalid sentence indices')
    return [recover(raw, row, expected_record_sha256=expected_binding['record_sha256'], field=expected_binding['field']) for row in witness['sentences']]
