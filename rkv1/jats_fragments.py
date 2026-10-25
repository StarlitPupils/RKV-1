"""Experimental exact JATS ranges; deliberately separate from Memory readers.

Text is a reproducible lexical projection. A range is original contiguous XML,
not standalone XML: its parent SHA and article identity are mandatory context.
"""
from collections import Counter
from urllib.parse import quote
import xml.etree.ElementTree as ET
from xml.parsers import expat

from .core import digest
from .memory_jats import EXCLUDE, parse, reject

MAX_SOURCE = 1 << 20
MAX_UNITS = 16384
MODES = ('position', 'xml-id')


def _tag_end(raw, start):
    """Find the original tag end, respecting > inside quoted attributes."""
    quoted = None
    for i in range(start, len(raw)):
        byte = raw[i]
        if quoted is not None:
            if byte == quoted:
                quoted = None
        elif byte in (34, 39):
            quoted = byte
        elif byte == 62:
            return i + 1
    raise ValueError('Unterminated original XML tag')


def fragments(raw, *, mode='xml-id'):
    """Return exact-range descriptors, including empty projected paragraphs.

position keys explicitly mean ordinal position within abstract/body. xml-id
keys prefer a unique projected element id, falling back to that same ordinal;
neither scheme asserts semantic equivalence across a changed record.
"""
    if mode not in MODES:
        raise ValueError('Unknown JATS fragment key mode')
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_SOURCE:
        raise ValueError('JATS fragment source must be bytes of at most 1 MiB')
    raw.decode('utf-8-sig', errors='strict')
    parent_key, title, paragraphs = parse(raw)
    builder = ET.TreeBuilder()
    parser = expat.ParserCreate()
    bounds = {}
    stack = []

    def declaration(version, encoding, standalone):
        if encoding and encoding.lower().replace('-', '') != 'utf8':
            raise ValueError('JATS fragment ranges require UTF-8 XML')

    def start(name, attrs):
        el = builder.start(name, attrs)
        offset = parser.CurrentByteIndex
        end = _tag_end(raw, offset)
        stack.append((el, offset, end, raw[end-2:end] == b'/>'))

    def end(name):
        el, offset, opening_end, empty = stack.pop()
        finish = opening_end if empty else _tag_end(raw, parser.CurrentByteIndex)
        assert builder.end(name) is el
        bounds[el] = (offset, finish)

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = builder.data
    parser.XmlDeclHandler = declaration
    parser.EntityDeclHandler = reject
    parser.ExternalEntityRefHandler = reject
    parser.SkippedEntityHandler = reject
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    try:
        parser.Parse(raw, True)
        root = builder.close()
    except (expat.ExpatError, ET.ParseError) as exc:
        raise ValueError('Invalid JATS fragment XML') from exc
    meta = root.find('front/article-meta')
    units = [('title', meta.find('title-group/article-title'))]

    def visit(el, role):
        if el.tag in EXCLUDE:
            return
        if el.tag == 'p':
            units.append((role, el))
            return
        for child in el:
            visit(child, role)

    for abstract in meta.findall('abstract'):
        if not abstract.get('abstract-type'):
            visit(abstract, 'abstract')
    visit(root.find('body'), 'body')
    if len(units) > MAX_UNITS:
        raise ValueError('Too many JATS fragment units')
    ids = Counter(el.get('id') for _, el in units if el.get('id'))
    if mode == 'xml-id' and any(n != 1 for n in ids.values()):
        raise ValueError('Duplicate projected JATS element id')
    counts = Counter()
    result = []
    parent_sha = digest(raw)
    for role, el in units:
        counts[role] += 1
        selector = ('id:' + quote(el.get('id'), safe='')) if mode == 'xml-id' and el.get('id') else 'pos:' + str(counts[role])
        offset, finish = bounds[el]
        original = raw[offset:finish]
        result.append({'key': parent_key + ':' + role + ':' + selector,
                       'parent_key': parent_key, 'parent_sha256': parent_sha,
                       'role': role, 'selector': selector,
                       'offset': offset, 'length': len(original),
                       'sha256': digest(original), 'text': ''.join(el.itertext()).strip()})
    assert [f['text'] for f in result] == [title, *paragraphs]
    assert len({f['key'] for f in result}) == len(result)
    previous = -1
    for f in result:
        assert previous <= f['offset'] and f['length'] > 0
        previous = f['offset'] + f['length']
    return result


def verify(raw, descriptor, *, mode='xml-id'):
    """Audit full parent context and exact range, rather than trusting a label.

This intentionally re-parses the whole source. It is an audit primitive, not a
claim of bounded-cost range-only Memory decoding.
"""
    if not isinstance(descriptor, dict):
        raise ValueError('JATS fragment descriptor must be a mapping')
    found = next((f for f in fragments(raw, mode=mode) if f['key'] == descriptor.get('key')), None)
    if found is None or found != descriptor:
        raise ValueError('JATS fragment differs from its original parent source')
    return raw[found['offset']:found['offset'] + found['length']]
