"""Self-contained experimental neural frame; independent of RKV archive versions."""
import hashlib
import lzma
import struct
import zlib

MAGIC=b'RKVNN001'
HEADER=struct.Struct('<8sBBIQQQ32s32s32s')
MAX_RAW=1<<20
METHODS={'neural':0,'zlib':1,'zstd':2,'lzma':3}


def _sha(raw):return hashlib.sha256(raw).digest()


def _restore(codec,payload,size):
    if codec==1:
        d=zlib.decompressobj();raw=d.decompress(payload,size+1)
        if not d.eof or d.unused_data or d.unconsumed_tail:raise ValueError('Invalid single zlib stream')
    elif codec==2:
        from .codecs import zstd_module
        zstd=zstd_module()
        try:
            params=zstd.get_frame_parameters(payload)
            if params.content_size!=size or params.window_size>MAX_RAW or params.dict_id:raise ValueError('Invalid zstd parameters')
            raw=zstd.ZstdDecompressor().decompress(payload,max_output_size=size+1,allow_extra_data=False)
        except zstd.ZstdError as exc:raise ValueError('Invalid zstd neural frame') from exc
    elif codec==3:
        d=lzma.LZMADecompressor(memlimit=256<<20);raw=d.decompress(payload,max_length=size+1)
        if not d.eof or d.unused_data:raise ValueError('Invalid single LZMA stream')
    else:raise ValueError('Unknown neural frame codec')
    if len(raw)!=size:raise ValueError('Decoded length differs')
    return raw


def encode(raw,*,method='neural',model=None):
    if not isinstance(raw,bytes) or len(raw)>MAX_RAW or method not in METHODS:raise ValueError('Invalid neural frame input')
    code=METHODS[method];model_z=b'';model_sha=bytes(32);model_len=0
    if code==0:
        from .neural_small import Predictor
        from .arithmetic import encode as arithmetic_encode
        predictor=Predictor(model);model_len=len(model);model_z=zlib.compress(model,6);model_sha=_sha(model)
        payload,bits=arithmetic_encode(raw,predictor.cdf)
    else:
        if model is not None:raise ValueError('Plain frame has no model')
        if code==1:payload=zlib.compress(raw,6)
        elif code==2:
            from .codecs import zstd_module
            payload=zstd_module().ZstdCompressor(level=3,write_content_size=True,write_checksum=True).compress(raw)
        else:payload=lzma.compress(raw,preset=6)
        bits=8*len(payload)
    header=HEADER.pack(MAGIC,1,code,len(raw),len(model_z),len(payload),bits,_sha(raw),model_sha,_sha(payload))
    frame=header+model_z+payload
    return frame,{'method':method,'raw_bytes':len(raw),'header_bytes':HEADER.size,'model_raw_bytes':model_len,
                  'model_zlib_bytes':len(model_z),'payload_bytes':len(payload),'payload_bits':bits,'frame_bytes':len(frame),
                  'dictionary_bytes':0,'external_model_bytes':0}


def decode(frame):
    try:
        if len(frame)<HEADER.size:raise ValueError('Short neural frame')
        magic,version,method,n,model_n,payload_n,bits,raw_sha,model_sha,payload_sha=HEADER.unpack_from(frame)
        if magic!=MAGIC or version!=1 or method not in METHODS.values() or n>MAX_RAW:raise ValueError('Invalid neural frame header')
        if model_n>8192 or payload_n>2*MAX_RAW+8192 or len(frame)!=HEADER.size+model_n+payload_n:raise ValueError('Invalid neural frame lengths')
        model_z=frame[HEADER.size:HEADER.size+model_n];payload=frame[HEADER.size+model_n:]
        if _sha(payload)!=payload_sha:raise ValueError('Neural payload SHA mismatch')
        if method==0:
            from .neural_small import Predictor,MODEL_BYTES
            from .arithmetic import decode as arithmetic_decode
            model=_restore(1,model_z,MODEL_BYTES)
            if _sha(model)!=model_sha:raise ValueError('Neural model SHA mismatch')
            raw=arithmetic_decode(payload,bits,n,Predictor(model).cdf)
        else:
            if model_n or model_sha!=bytes(32) or bits!=payload_n*8:raise ValueError('Plain frame contains neural state')
            raw=_restore(method,payload,n)
        if _sha(raw)!=raw_sha:raise ValueError('Neural frame original SHA mismatch')
        return raw
    except (zlib.error,lzma.LZMAError,struct.error,OverflowError) as exc:raise ValueError('Invalid neural frame') from exc
