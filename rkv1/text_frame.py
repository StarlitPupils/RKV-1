"""Experimental whole-object text frames, distinct from RKV archives v1-v6."""
import hashlib
import struct

MAGIC=b'RKVTEXT1'
HEADER=struct.Struct('<8sBBQQQ32s')
CODECS={'zlib':1,'zstd':2,'lzma':3}
MODES=('plain','lanes','auto')
MAX_RAW=64<<20
MAX_TRANSFORMED=3*MAX_RAW+40


def _compress(raw,codec):
    if codec=='zlib':
        import zlib
        return zlib.compress(raw,6)
    if codec=='zstd':
        import zstandard as zstd
        return zstd.ZstdCompressor(level=3,write_content_size=True,write_checksum=True).compress(raw)
    import lzma
    return lzma.compress(raw,preset=6)


def _inflate(payload,codec,size):
    if codec==1:
        import zlib
        try:
            d=zlib.decompressobj();raw=d.decompress(payload,size+1)
            if not d.eof or d.unused_data or d.unconsumed_tail:raise ValueError('Incomplete or trailing Zlib data')
        except zlib.error as e:raise ValueError('Invalid Zlib payload') from e
    elif codec==2:
        import zstandard as zstd
        try:
            params=zstd.get_frame_parameters(payload)
            if params.content_size!=size or params.window_size>MAX_TRANSFORMED or params.dict_id!=0:
                raise ValueError('Zstandard frame size/window/dictionary does not bind the declared payload')
            raw=zstd.ZstdDecompressor().decompress(payload,max_output_size=size,allow_extra_data=False)
        except zstd.ZstdError as e:raise ValueError('Invalid Zstandard payload') from e
    else:
        import lzma
        try:
            d=lzma.LZMADecompressor(memlimit=256<<20);raw=d.decompress(payload,max_length=size+1)
            if not d.eof or d.unused_data:raise ValueError('Incomplete or trailing LZMA data')
        except lzma.LZMAError as e:raise ValueError('Invalid LZMA payload') from e
    if len(raw)!=size:raise ValueError('Text frame decompressed length mismatch')
    return raw


def encode(raw,*,codec='zstd',mode='auto'):
    if (type(raw) is not bytes or len(raw)>MAX_RAW or type(codec) is not str or type(mode) is not str
            or codec not in CODECS or mode not in MODES):
        raise ValueError('Invalid experimental text frame input/codec/mode')
    sha=hashlib.sha256(raw).digest();attempts=[];frames=[]
    for selected in (('plain','lanes') if mode=='auto' else (mode,)):
        stats=None;transformed=raw
        if selected=='lanes':
            from .text_lanes import forward
            transformed,stats=forward(raw)
        compressed=_compress(transformed,codec);method=int(selected=='lanes')
        frame=HEADER.pack(MAGIC,method,CODECS[codec],len(raw),len(transformed),len(compressed),sha)+compressed
        frames.append(frame);attempts.append({'mode':selected,'frame_bytes':len(frame),'compressed_payload_bytes':len(compressed),'transformed_bytes':len(transformed),'lanes':stats})
    chosen=min(range(len(frames)),key=lambda i:len(frames[i]))
    return frames[chosen],{'codec':codec,'requested_mode':mode,'selected_mode':attempts[chosen]['mode'],
        'original_bytes':len(raw),'frame_header_bytes':HEADER.size,'attempts':attempts,'dictionary_bytes':0,'model_bytes':0}


def decode(frame):
    if type(frame) is not bytes or len(frame)<HEADER.size or len(frame)>MAX_TRANSFORMED+HEADER.size+1048576:
        raise ValueError('Invalid experimental text frame size/type')
    magic,method,codec,raw_size,transformed_size,compressed_size,sha=HEADER.unpack_from(frame)
    if (magic!=MAGIC or method not in (0,1) or codec not in CODECS.values() or raw_size>MAX_RAW
            or transformed_size>3*raw_size+40 or transformed_size>MAX_TRANSFORMED
            or compressed_size!=len(frame)-HEADER.size or (method==0 and transformed_size!=raw_size)):
        raise ValueError('Invalid experimental text frame header')
    raw=_inflate(frame[HEADER.size:],codec,transformed_size)
    if method:
        from .text_lanes import inverse
        raw=inverse(raw,raw_size)
    if len(raw)!=raw_size or hashlib.sha256(raw).digest()!=sha:raise ValueError('Text frame original SHA/size mismatch')
    return raw
