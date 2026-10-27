"""Private draft: exact raw JSON string spans, only abstract sentence units."""
import json
from json.decoder import scanstring
from rkv1.core import digest

def _constant(value):raise ValueError('Nonfinite original JSON value')

def abstract_units(raw,*,parent_offset=0):
    if type(raw) is not bytes or type(parent_offset) is not int or parent_offset<0:raise ValueError('Invalid original record range')
    text=raw.decode('utf-8');obj=json.loads(text,parse_constant=_constant)
    if type(obj) is not dict or type(obj.get('doc_id')) is not int or not isinstance(obj.get('title'),str) or type(obj.get('abstract')) is not list or any(not isinstance(s,str) for s in obj['abstract']):raise ValueError('Unsupported original scientific record')
    offsets=[0]
    for char in text:offsets.append(offsets[-1]+len(char.encode('utf-8')))
    decoder=json.JSONDecoder(parse_constant=_constant);i=0;seen=set();spans=[]
    def space(position):
        while position<len(text) and text[position] in ' \r\n\t':position+=1
        return position
    i=space(i)
    if text[i]!='{':raise ValueError('Original paper object required')
    i+=1
    while True:
        i=space(i)
        if text[i]=='}':i+=1;break
        if text[i]!='"':raise ValueError('Invalid original key')
        key,i=scanstring(text,i+1,True)
        if key in seen:raise ValueError('Duplicate original paper key')
        seen.add(key);i=space(i)
        if text[i]!=':':raise ValueError('Original key separator missing')
        i=space(i+1)
        if key=='abstract':
            if text[i]!='[':raise ValueError('Abstract array required')
            i=space(i+1)
            if text[i]!=']':
                while True:
                    start=i
                    if text[start]!='"':raise ValueError('Original sentence string required')
                    value,i=scanstring(text,start+1,True);spans.append((start,i,value));i=space(i)
                    if text[i]==']':break
                    if text[i]!=',':raise ValueError('Invalid abstract separator')
                    i=space(i+1)
            i+=1
        else:_,i=decoder.raw_decode(text,i)
        i=space(i)
        if text[i]=='}':i+=1;break
        if text[i]!=',':raise ValueError('Invalid original member separator')
        i+=1
    if space(i)!=len(text) or [s[2] for s in spans]!=obj['abstract']:raise ValueError('Original sentence span identity differs')
    parent_sha=digest(raw);paper='doc:'+str(obj['doc_id']);units=[]
    for index,(start,end,value) in enumerate(spans):
        a=offsets[start];b=offsets[end];original=raw[a:b]
        if json.loads(original)!=value:raise ValueError('Original UTF8/escaped string span differs')
        units.append({'unit_id':paper+':abstract:'+str(index),'paper_id':paper,'sentence_index':index,'text':value,
            'offset':parent_offset+a,'length':b-a,'sha256':digest(original),'decoded_text_sha256':digest(value.encode('utf-8')),
            'parent_offset':parent_offset,'parent_length':len(raw),'parent_sha256':parent_sha})
    return units
