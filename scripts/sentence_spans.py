"""Owned-fixture prototype: exact UTF-8 JSON sentence token spans, no ranking."""
import hashlib
import json


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate JSON member')
        result[key] = value
    return result


def locate(raw, *, field='sentences'):
    if field not in ('sentences', 'abstract') or type(field) is not str:
        raise ValueError('Explicit supported sentence array field required')
    if type(raw) is not bytes:
        raise ValueError('Original bytes required')
    text = raw.decode('utf-8')
    obj = json.loads(text, object_pairs_hook=_pairs,
                     parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Non-JSON number')))
    if type(obj) is not dict or type(obj.get(field)) is not list:
        raise ValueError('Top-level sentences array required')
    if any(type(x) is not str for x in obj[field]):
        raise ValueError('Sentence strings required')
    # Explicit O(N) offset map; its allocation is not a constant-memory claim.
    offsets = [0]
    for char in text:
        offsets.append(offsets[-1] + len(char.encode('utf-8')))
    decoder = json.JSONDecoder()

    def whitespace(i):
        while i < len(text) and text[i] in ' \r\n\t':
            i += 1
        return i

    pos = whitespace(0)
    assert text[pos] == '{'
    pos = whitespace(pos + 1)
    rows = []
    while text[pos] != '}':
        key, end = decoder.raw_decode(text, pos)
        pos = whitespace(end)
        assert text[pos] == ':'
        pos = whitespace(pos + 1)
        if key == field:
            assert text[pos] == '['
            cursor = whitespace(pos + 1)
            for index, sentence in enumerate(obj[field]):
                value, finish = decoder.raw_decode(text, cursor)
                assert value == sentence
                start, stop = offsets[cursor], offsets[finish]
                token = raw[start:stop]
                assert json.loads(token) == sentence
                rows.append({'sentence_index': index, 'offset': start,
                             'length': stop - start, 'token_sha256': digest(token),
                             'decoded_utf8_sha256': digest(sentence.encode('utf-8'))})
                cursor = whitespace(finish)
                if index + 1 < len(obj[field]):
                    assert text[cursor] == ','
                    cursor = whitespace(cursor + 1)
            assert text[cursor] == ']'
        _, pos = decoder.raw_decode(text, pos)
        pos = whitespace(pos)
        if text[pos] == ',':
            pos = whitespace(pos + 1)
        else:
            assert text[pos] == '}'
    return {'record_sha256': digest(raw), 'record_B': len(raw), 'field': field, 'sentences': rows}


def recover(raw, witness, *, expected_record_sha256, field='sentences'):
    """Bind the full record and exact token; this still reads the entire record."""
    if digest(raw) != expected_record_sha256:
        raise ValueError('External record identity mismatch')
    if set(witness) != {'sentence_index', 'offset', 'length', 'token_sha256', 'decoded_utf8_sha256'}:
        raise ValueError('Unexpected witness fields')
    for number_field in ('sentence_index', 'offset', 'length'):
        if type(witness[number_field]) is not int or witness[number_field] < 0:
            raise ValueError('Invalid index or range')
    start, length = witness['offset'], witness['length']
    if length == 0 or start + length > len(raw):
        raise ValueError('Range outside record')
    original = locate(raw, field=field)['sentences']
    index = witness['sentence_index']
    if index >= len(original) or witness != original[index]:
        raise ValueError('Sentence position or original token mismatch')
    return raw[start:start + length]
