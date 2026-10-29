"""Fixed owned records for representation mechanics; no scientific inputs."""
import json

COUNTS = (3, 17, 65)
MODES = ('utf8_compact', 'escaped_pretty')


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def fixture(count, mode):
    if type(count) is not int or count not in COUNTS or mode not in MODES:
        raise ValueError('Frozen fixture count and encoding required')
    records = []
    for i in range(count):
        field = 'abstract' if i % 2 == 0 else 'sentences'
        value = {'doc_id': i, 'title': 'Owned record ' + str(i),
                 'nested': {field: ['decoy']},
                 field: ['Repeated owned statement.', 'Repeated owned statement.',
                         'UTF-8 \u4e2d\u6587 / \u03b1; quote " slash \\ newline\n' + str(i), '']}
        record = json.dumps(value, ensure_ascii=mode == 'escaped_pretty',
                            separators=(',', ':') if mode == 'utf8_compact' else (', ', ': ')).encode('utf-8') + (b'\n' if mode == 'utf8_compact' else b'\r\n')
        records.append((record, field))
    # Pretty means spaced JSON with escaped Unicode, still one JSON object per line.
    return b''.join(r for r, _ in records), records
