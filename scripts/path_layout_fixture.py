"""Layout-only synthetic control: same original JSONL records, different files."""
import json
from collections import Counter
from rkv1.core import digest
from scripts.evidence_path_fixture import corpus

LAYOUTS=('clustered','separated')


def sources(epoch,layout):
    raw=corpus(epoch)
    if layout=='clustered':return {'records.jsonl':raw}
    if layout!='separated':raise ValueError('Unknown fixed layout')
    groups={f'step-{i}.jsonl':[] for i in range(3)}
    for line in raw.splitlines(keepends=True):
        key=json.loads(line)['doc_id']
        step=key%3 if key<96 else (key-10000)%3
        groups[f'step-{step}.jsonl'].append(line)
    return {name:b''.join(lines) for name,lines in groups.items()}


def identity(epoch,layout):
    files=sources(epoch,layout)
    lines=[line for raw in files.values() for line in raw.splitlines(keepends=True)]
    assert Counter(lines)==Counter(corpus(epoch).splitlines(keepends=True))
    return {'epoch':epoch,'files':{name:{'bytes':len(raw),'sha256':digest(raw),
             'records':len(raw.splitlines())} for name,raw in files.items()},
            'total_source_bytes':sum(map(len,files.values())),
            'original_corpus_sha256':digest(corpus(epoch)),
            'record_multiset_sha256':digest(b''.join(sorted(lines)))}


def manifest():
    return {'schema':'rkv-layout-control-1','synthetic_only':True,
            'layouts':{layout:{'epochs':[identity(e,layout) for e in range(13)]} for layout in LAYOUTS},
            'scope':'Same byte records incl CRLF, no added padding; paths/SIDs/offsets and compression/index costs may change'}
