"""Experimental ASCII lexical byte lanes; no parsing or semantic rewriting."""
import re
import struct

HEADER=struct.Struct('<5Q')
TOKENS=re.compile(rb'([A-Za-z_][A-Za-z_0-9]*)|([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)|([ \t\r\n\v\f]+)|([^A-Za-z_0-9 \t\r\n\v\f]+)')


def varint(n):
    out=bytearray()
    while n>127:out.append((n&127)|128);n>>=7
    out.append(n);return bytes(out)


def forward(raw):
    if type(raw) is not bytes:raise ValueError('Byte lanes require bytes')
    pools=[bytearray() for _ in range(4)];control=bytearray();offset=count=0
    for m in TOKENS.finditer(raw):
        if m.start()!=offset:raise ValueError('Byte lanes did not partition the input')
        kind=m.lastindex-1;token=m.group();control.append(kind);control.extend(varint(len(token)));pools[kind].extend(token)
        offset=m.end();count+=1
    if offset!=len(raw):raise ValueError('Uncovered input bytes')
    sizes=[len(p) for p in pools]
    payload=HEADER.pack(len(control),*sizes)+control+b''.join(pools)
    return bytes(payload),{'tokens':count,'control_bytes':len(control),'pool_bytes':sizes,'transform_header_bytes':HEADER.size,'transformed_bytes':len(payload)}


def inverse(payload,raw_size):
    if type(payload) is not bytes or type(raw_size) is not int or raw_size<0 or len(payload)<HEADER.size:
        raise ValueError('Invalid byte lane payload')
    control_size,*sizes=HEADER.unpack_from(payload)
    if sum(sizes)!=raw_size or control_size>2*raw_size or HEADER.size+control_size+sum(sizes)!=len(payload):
        raise ValueError('Byte lane lengths do not bind the original size')
    control=payload[HEADER.size:HEADER.size+control_size];at=HEADER.size+control_size;pools=[]
    for size in sizes:pools.append(payload[at:at+size]);at+=size
    used=[0]*4;out=bytearray();at=0
    while at<len(control):
        kind=control[at];at+=1
        if kind>3:raise ValueError('Invalid byte lane tag')
        start=at;n=0
        for shift in range(0,35,7):
            if at>=len(control):raise ValueError('Truncated byte lane length')
            b=control[at];at+=1;n|=(b&127)<<shift
            if b<128:break
        else:raise ValueError('Oversized byte lane length')
        if n<1 or control[start:at]!=varint(n) or used[kind]+n>sizes[kind]:raise ValueError('Noncanonical or out-of-bounds byte lane length')
        out.extend(pools[kind][used[kind]:used[kind]+n]);used[kind]+=n
    if used!=sizes or len(out)!=raw_size:raise ValueError('Unused or missing byte lane data')
    return bytes(out)
