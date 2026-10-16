"""Exact byte spans of QASPER paper members; only paper text is indexed.

A locator includes the original JSON key, colon and value, without surrounding
comma/braces. It can therefore recover its identity without a rewritten export.
"""
import json


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError("Duplicate QASPER JSON key")
        result[key]=value
    return result


def constant(value):raise ValueError("Nonfinite QASPER JSON constant")


def members(raw):
    text=raw.decode('utf-8',errors='strict');size=len(text)
    decoder=json.JSONDecoder(object_pairs_hook=unique,parse_constant=constant)
    def space(at):
        while at<size and text[at] in ' \t\r\n':at+=1
        return at
    at=space(0);whole=at<size and text[at]=='{';seen=set();previous=byte_at=0
    if whole:
        at=space(at+1)
        if at<size and text[at]=='}':
            if space(at+1)!=size:raise ValueError('Trailing QASPER JSON')
            return
    while at<size:
        begin=at;key,at=decoder.raw_decode(text,at)
        if not isinstance(key,str) or not 1<=len(key)<=256 or key in seen:
            raise ValueError('Invalid or duplicate QASPER paper ID')
        seen.add(key);at=space(at)
        if at>=size or text[at]!=':':raise ValueError('QASPER member requires colon')
        at=space(at+1);obj,end=decoder.raw_decode(text,at)
        # Encode only disjoint portions, keeping total offset work linear even
        # for literal UTF-8 and escaped JSON, rather than encoding every prefix.
        start_byte=byte_at+len(text[previous:begin].encode('utf-8'))
        end_byte=start_byte+len(text[begin:end].encode('utf-8'))
        yield key,obj,start_byte,raw[start_byte:end_byte]
        previous,byte_at=end,end_byte;at=space(end)
        if not whole:
            if at!=size:raise ValueError('Trailing QASPER member bytes')
            return
        if at<size and text[at]=='}':
            if space(at+1)!=size:raise ValueError('Trailing QASPER JSON')
            return
        if at>=size or text[at]!=',':raise ValueError('Unfinished QASPER object')
        at=space(at+1)
        if at>=size or text[at]=='}':raise ValueError('Trailing QASPER comma')
    raise ValueError('Unfinished QASPER object')


def records(raw,limit):
    for key,obj,offset,original in members(raw):
        if len(original)>limit:raise ValueError('Evidence record exceeds 1 MiB')
        if (not isinstance(obj,dict) or not isinstance(obj.get('title'),str)
                or not isinstance(obj.get('abstract'),str) or not isinstance(obj.get('full_text'),list)):
            raise ValueError('JSON evidence requires QASPER title/abstract/full_text')
        paragraphs=[obj['abstract']]
        for section in obj['full_text']:
            if (not isinstance(section,dict) or not isinstance(section.get('paragraphs'),list)
                    or not all(isinstance(p,str) for p in section['paragraphs'])):
                raise ValueError('Invalid QASPER paper paragraphs')
            paragraphs.extend(section['paragraphs'])
        # qas, answer spans, figures/tables and other metadata are not projected
        # into the FTS body or exposed as model evidence sentences.
        yield 'qasper:'+key,obj['title'],paragraphs,offset,original,'qasper-json-member-v1'
