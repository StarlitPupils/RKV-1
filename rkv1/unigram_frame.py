"""Static training unigram control using the same integer arithmetic coder."""
import struct
import zlib

from .arithmetic import encode as arithmetic_encode,decode as arithmetic_decode
from .neural_frame import HEADER,MAX_RAW,_sha,_restore

MAGIC=b'RKVUNI01'
MODEL_MAGIC=b'RKVUMD01'
MODEL_BYTES=520


def build_model(raws):
    counts=[0]*256
    for raw in raws:
        for symbol in raw:counts[symbol]+=1
    total=sum(counts)
    if not total:raise ValueError('Empty unigram training data')
    frequencies=[1+n*(32768-256)//total for n in counts]
    for i in range(32768-sum(frequencies)):frequencies[i]+=1
    return MODEL_MAGIC+struct.pack('<256H',*frequencies)


class Predictor:
    def __init__(self,model):
        if not isinstance(model,bytes) or len(model)!=MODEL_BYTES or model[:8]!=MODEL_MAGIC:raise ValueError('Invalid unigram model')
        frequencies=struct.unpack('<256H',model[8:])
        if not all(frequencies) or sum(frequencies)!=32768:raise ValueError('Invalid unigram frequencies')
        values=[0]
        for value in frequencies:values.append(values[-1]+value)
        self.values=tuple(values)

    def cdf(self,context):return self.values


def encode(raw,*,model):
    if not isinstance(raw,bytes) or len(raw)>MAX_RAW:raise ValueError('Invalid unigram input')
    predictor=Predictor(model);model_z=zlib.compress(model,6);payload,bits=arithmetic_encode(raw,predictor.cdf)
    header=HEADER.pack(MAGIC,1,4,len(raw),len(model_z),len(payload),bits,_sha(raw),_sha(model),_sha(payload))
    frame=header+model_z+payload
    return frame,{'method':'unigram','raw_bytes':len(raw),'header_bytes':HEADER.size,'model_raw_bytes':len(model),
                  'model_zlib_bytes':len(model_z),'payload_bytes':len(payload),'payload_bits':bits,'frame_bytes':len(frame),
                  'dictionary_bytes':0,'external_model_bytes':0}


def decode(frame):
    if len(frame)<HEADER.size:raise ValueError('Short unigram frame')
    magic,version,method,n,model_n,payload_n,bits,raw_sha,model_sha,payload_sha=HEADER.unpack_from(frame)
    if magic!=MAGIC or version!=1 or method!=4 or n>MAX_RAW:raise ValueError('Invalid unigram frame')
    if model_n>1024 or payload_n>2*MAX_RAW+8192 or len(frame)!=HEADER.size+model_n+payload_n:raise ValueError('Invalid unigram lengths')
    try:model=_restore(1,frame[HEADER.size:HEADER.size+model_n],MODEL_BYTES)
    except zlib.error as exc:raise ValueError('Invalid unigram model zlib stream') from exc
    payload=frame[HEADER.size+model_n:]
    if _sha(model)!=model_sha or _sha(payload)!=payload_sha:raise ValueError('Unigram model/payload SHA mismatch')
    raw=arithmetic_decode(payload,bits,n,Predictor(model).cdf)
    if _sha(raw)!=raw_sha:raise ValueError('Unigram original SHA mismatch')
    return raw
