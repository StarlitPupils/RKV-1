"""Experimental original-source evidence views; scientific outcomes require frozen evaluation."""
import json
import re
from rkv1.store import Store
from scripts.store_sentence_spans import _read
from scripts.sentence_spans import locate, recover, _pairs
from scripts.view_sentence_choice import select_indices
from scripts.view_admission import admit, canonical

METHODS = ('whole_record', 'first_two', 'overlap_two')


def _inputs(question, records, method, source_header=None):
    if type(question) is not str or not question.strip() or len(question.encode()) > 4096:
        raise ValueError('Bounded question required')
    if method not in METHODS or type(records) is not list or not 0 <= len(records) <= 12:
        raise ValueError('Explicit method and 0..12 trusted records required')
    for row in records:
        if type(row) is not dict or set(row) != {'id', 'binding'} or type(row['id']) is not str or type(row['binding']) is not dict:
            raise ValueError('Exact original record schema required')
        if row['binding'].get('field') != 'abstract':
            raise ValueError('Explicit original scientific abstract field required')
    if len({r['id'] for r in records}) != len(records):
        raise ValueError('Duplicate paper identity')
    if not records and source_header is None:
        raise ValueError('Empty candidate set still requires external source identity')
    first = records[0]['binding'] if records else source_header
    header = {key: first[key] for key in ('snapshot_id', 'path', 'source_sha256')}
    if header['path'] != 'corpus.jsonl' or any(type(header[k]) is not str or re.fullmatch('[0-9a-f]{64}',header[k]) is None for k in ('snapshot_id','source_sha256')):
        raise ValueError('Explicit bounded source identity required')
    if source_header is not None and source_header != header:
        raise ValueError('Caller source anchor and candidate source differ')
    for row in records:
        if any(row['binding'][key] != header[key] for key in header):
            raise ValueError('Mixed original source identities')
    return {**header, 'view_schema': 'original-evidence-draft-1', 'question': question}


def _empty_source(store, header):
    with Store(store,io_backend='bounded').snapshot(header['snapshot_id']) as snapshot:
        entry=snapshot.files.get(header['path'])
        if entry is None or entry['sha256']!=header['source_sha256']:
            raise ValueError('Empty view still requires original source metadata')


def _original(store, row):
    raw = _read(store, row['binding'])
    def invalid_constant(value):
        raise ValueError('Nonfinite original JSON value')
    obj = json.loads(raw,object_pairs_hook=_pairs,parse_constant=invalid_constant)
    if 'doc:'+str(obj.get('doc_id')) != row['id'] or type(obj.get('abstract')) is not list or any(type(s) is not str for s in obj['abstract']):
        raise ValueError('Original paper identity or sentence field differs')
    return raw, obj


def build_view(store, question, records, *, method, byte_cap=20000, source_header=None):
    header = _inputs(question, records, method, source_header)
    # Reject invalid cap/header before Store reads.
    admit(header, [], view_byte_cap=byte_cap, max_items=12)
    if not records:
        _empty_source(store,header)
    items, returned = [], 0
    for row in records:
        raw, obj = _original(store, row)
        returned += len(raw)
        if method == 'whole_record':
            item = {'id': row['id'], 'binding': row['binding'], 'record_hex': raw.hex()}
        else:
            indices = select_indices(question, obj['abstract'], method=method)
            spans = locate(raw, field='abstract')['sentences']
            chosen = [spans[i] for i in indices]
            tokens = [recover(raw, span, expected_record_sha256=row['binding']['record_sha256'], field='abstract') for span in chosen]
            item = {'id': row['id'], 'witness': {'schema': 'experimental-source-span-1', 'binding': row['binding'],
                    'sentences': chosen, 'application_record_return_B': len(raw)}, 'original_token_hex': [t.hex() for t in tokens]}
        items.append(item)
    result = admit(header, items, view_byte_cap=byte_cap, max_items=12)
    result.update(preparation_record_return_B=returned, prepared_record_count=len(records), method=method,
                  no_source_read_or_API_wire_budget_claim=True)
    return result


def verify_view(store, encoded, question, records, *, method, byte_cap=20000, source_header=None):
    header = _inputs(question, records, method, source_header)
    if type(encoded) is not bytes or type(byte_cap) is not int or byte_cap < 0 or len(encoded) > byte_cap:
        raise ValueError('Canonical original view bytes exceed cap')
    packet = json.loads(encoded)
    if canonical(packet) != encoded or type(packet) is not dict or set(packet) != {'header', 'items'} or canonical(packet['header']) != canonical(header):
        raise ValueError('Noncanonical or untrusted view header')
    if type(packet['items']) is not list or len(packet['items']) > 12:
        raise ValueError('Invalid view item count')
    if not records:
        _empty_source(store,header)
    approved = {r['id']: r for r in records}
    seen, sources, returned = set(), {}, 0
    order = {r['id']: i for i, r in enumerate(records)}
    previous = -1
    for item in packet['items']:
        if type(item) is not dict or type(item.get('id')) is not str or item['id'] not in approved or item['id'] in seen:
            raise ValueError('Duplicate or unknown paper')
        key = item['id']
        if order[key] <= previous:
            raise ValueError('Paper order differs')
        previous = order[key]
        seen.add(key)
        raw, obj = _original(store, approved[key])
        returned += len(raw)
        if method == 'whole_record':
            if canonical(item) != canonical({'id': key, 'binding': approved[key]['binding'], 'record_hex': raw.hex()}):
                raise ValueError('Whole original record differs')
            sources[key] = list(range(len(obj['abstract'])))
        else:
            indices = select_indices(question, obj['abstract'], method=method)
            spans = locate(raw, field='abstract')['sentences']
            rows = [spans[i] for i in indices]
            tokens = [recover(raw, span, expected_record_sha256=approved[key]['binding']['record_sha256'], field='abstract') for span in rows]
            expected = {'id': key, 'witness': {'schema': 'experimental-source-span-1', 'binding': approved[key]['binding'],
                        'sentences': rows, 'application_record_return_B': len(raw)}, 'original_token_hex': [t.hex() for t in tokens]}
            if canonical(item) != canonical(expected):
                raise ValueError('Original sentence index/token differs')
            sources[key] = indices
    return {'available_original_sentence_indices': sources, 'verification_record_return_B': returned,
            'greedy_admission_independently_verified': False, 'scientific_entailment_verified': False}
