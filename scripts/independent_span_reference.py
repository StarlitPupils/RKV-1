"""Independent owned-fixture JSONL/token reference; no candidate scanner import."""
import hashlib
import json
import re


_TOKEN = re.compile(rb'\s*("(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"|[{}\[\]:,]|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|true|false|null)')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def original_record(source, *, expected_source_sha256, record_offset, record_length):
    if type(source) is not bytes or sha(source) != expected_source_sha256:
        raise ValueError('External original source differs')
    if type(record_offset) is not int or type(record_length) is not int or record_offset < 0 or record_length < 1:
        raise ValueError('Invalid original JSONL range')
    cursor = 0
    for part in source.split(b'\n'):
        stop = cursor + len(part) + (1 if cursor + len(part) < len(source) else 0)
        if cursor == record_offset and stop - cursor == record_length:
            raw = source[cursor:stop]
            json.loads(raw)
            return raw
        cursor = stop
    raise ValueError('Locator is not one complete original JSONL record')


def reference_tokens(raw, *, field):
    # Validate syntax with standard JSON independently before byte-token walking.
    obj = json.loads(raw)
    if field not in ('abstract', 'sentences') or type(obj) is not dict or type(obj.get(field)) is not list:
        raise ValueError('Explicit original array field required')
    matches = []
    cursor = 0
    while cursor < len(raw):
        if raw[cursor:].strip() == b'':
            break
        match = _TOKEN.match(raw, cursor)
        if match is None:
            raise ValueError('Unrecognized original JSON token')
        matches.append((match.group(1), match.start(1), match.end(1)))
        cursor = match.end()
    position = 0
    strings = {}

    def consume(expected):
        nonlocal position
        if position >= len(matches) or matches[position][0] != expected:
            raise ValueError('Unexpected original punctuation')
        position += 1

    def value(path):
        nonlocal position
        token, start, end = matches[position]
        if token == b'{':
            consume(b'{')
            keys = set()
            while matches[position][0] != b'}':
                key = json.loads(matches[position][0])
                if type(key) is not str or key in keys:
                    raise ValueError('Duplicate or invalid original object member')
                keys.add(key)
                position += 1
                consume(b':')
                value(path + (key,))
                if matches[position][0] == b'}':
                    break
                consume(b',')
            consume(b'}')
        elif token == b'[':
            consume(b'[')
            index = 0
            while matches[position][0] != b']':
                value(path + (index,))
                index += 1
                if matches[position][0] == b']':
                    break
                consume(b',')
            consume(b']')
        else:
            decoded = json.loads(token)
            if type(decoded) is str:
                strings[path] = (start, end, decoded)
            position += 1
    value(())
    if position != len(matches):
        raise ValueError('Extra original tokens')
    result = []
    for index, sentence in enumerate(obj[field]):
        if type(sentence) is not str:
            raise ValueError('Original sentence is not a string')
        start, end, decoded = strings[(field, index)]
        result.append({'sentence_index': index, 'offset': start, 'length': end - start,
                       'token_sha256': sha(raw[start:end]), 'decoded_utf8_sha256': sha(decoded.encode('utf-8'))})
    return result
