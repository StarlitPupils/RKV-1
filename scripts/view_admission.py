"""Owned-fixture preparation: canonical evidence-view cap, not API request cap."""
import hashlib
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def admit(header, candidates, *, view_byte_cap, max_items):
    """Keep supplied order; count full canonical header/items and all metadata.

    Candidate identity/semantic/ranking verification belongs to the future caller.
    This function does not read sources, models, gold, or API credentials.
    """
    if type(header) is not dict or type(candidates) is not list:
        raise ValueError('Explicit header and ordered candidate list required')
    if type(view_byte_cap) is not int or view_byte_cap < 0 or type(max_items) is not int or max_items < 0:
        raise ValueError('Exact nonnegative integer bounds required')
    if any(type(item) is not dict or type(item.get('id')) is not str or not item['id'] for item in candidates):
        raise ValueError('Each prepared candidate needs an explicit unique ID')
    if len({item['id'] for item in candidates}) != len(candidates):
        raise ValueError('Duplicate candidate identity')
    # Canonical roundtrip is an explicit copy, with its CPU/RAM to be measured.
    packet = json.loads(canonical({'header': header, 'items': []}))
    if len(canonical(packet)) > view_byte_cap:
        raise ValueError('Even the empty evidence-view header does not fit')
    trace = []
    for item in candidates:
        copied = json.loads(canonical(item))
        proposed = {'header': packet['header'], 'items': packet['items'] + [copied]}
        cost = len(canonical(proposed))
        reason = 'accepted'
        if len(packet['items']) >= max_items:
            reason = 'count_stop'
        elif cost > view_byte_cap:
            reason = 'full_view_byte_rejected'
        else:
            packet = proposed
        trace.append({'id': item['id'], 'reason': reason, 'proposed_full_view_B': cost})
    encoded = canonical(packet)
    assert len(encoded) <= view_byte_cap
    return {'packet': packet, 'encoded_hex': encoded.hex(), 'encoded_B': len(encoded),
            'sha256': hashlib.sha256(encoded).hexdigest(), 'trace': trace,
            'view_cap_not_full_API_wire_or_source_read_budget': True}
