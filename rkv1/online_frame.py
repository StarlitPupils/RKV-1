"""Explicit online-statistics experimental frame, independent of Archive."""
import lzma
import struct
import zlib
from .neural_frame import HEADER,MAX_RAW,_sha,_restore

MAGIC=b'RKVONL01'
METHODS={'order0':0,'order1':1,'zlib':2,'zstd':3,'lzma':4}


def encode(raw,*,method='order1'):
    if not isinstance(raw,bytes) or len(raw)>MAX_RAW or method not in METHODS:
        raise ValueError('Invalid online frame input')
    code=METHODS[method];rule_sha=bytes(32);state={}
    if code in (0,1):
        from .online_counts import Predictor,RULE_SHA
        from .arithmetic import encode as arithmetic_encode
        predictor=Predictor(code);payload,bits=arithmetic_encode(raw,predictor.cdf)
        rule_sha=RULE_SHA;state=predictor.accounting()
    else:
        if code==2:payload=zlib.compress(raw,6)
        elif code==3:
            from .codecs import zstd_module
            payload=zstd_module().ZstdCompressor(level=3,write_content_size=True,write_checksum=True).compress(raw)
        else:payload=lzma.compress(raw,preset=6)
        bits=8*len(payload)
    frame=HEADER.pack(MAGIC,1,code,len(raw),0,len(payload),bits,_sha(raw),rule_sha,_sha(payload))+payload
    return frame,{'method':method,'raw_bytes':len(raw),'header_bytes':HEADER.size,
                  'payload_bytes':len(payload),'payload_bits':bits,'frame_bytes':len(frame),
                  'external_model_bytes':0,'embedded_model_bytes':0,'dictionary_bytes':0,
                  'rule_sha256':rule_sha.hex(),'state':state}


def decode(frame):
    try:
        if len(frame)<HEADER.size:raise ValueError('Short online frame')
        magic,version,method,n,model_n,pn,bits,rs,rule_sha,ps=HEADER.unpack_from(frame)
        if magic!=MAGIC or version!=1 or method not in METHODS.values() or n>MAX_RAW:
            raise ValueError('Invalid online frame header')
        if model_n or pn>2*MAX_RAW+8192 or len(frame)!=HEADER.size+pn:
            raise ValueError('Invalid online frame lengths')
        payload=frame[HEADER.size:]
        if _sha(payload)!=ps:raise ValueError('Online payload SHA mismatch')
        if method in (0,1):
            from .online_counts import Predictor,RULE_SHA
            from .arithmetic import decode as arithmetic_decode
            if rule_sha!=RULE_SHA:raise ValueError('Unknown online rule')
            raw=arithmetic_decode(payload,bits,n,Predictor(method).cdf)
        else:
            if rule_sha!=bytes(32) or bits!=8*pn:raise ValueError('Plain online frame contains model state')
            raw=_restore(method-1,payload,n)
        if _sha(raw)!=rs:raise ValueError('Online original SHA mismatch')
        return raw
    except (zlib.error,lzma.LZMAError,struct.error,OverflowError) as exc:
        raise ValueError('Invalid online frame') from exc
