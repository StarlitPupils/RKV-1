"""Experimental index frame, distinct magic from all RKV archives/text frames."""
import hashlib,struct
from rkv1.codecs import compressor,decompress

MAGIC=b'RKVPOST1'
HEADER=struct.Struct('<8sBBQQQ32s32s32s')
METHODS={'plain':0,'typed':1}
CODECS={'raw':0,'zlib':1,'zstd':2,'lzma':3}
MAX_RAW=64<<20
MAX_PAYLOAD=MAX_RAW+(1<<20)
MAX_FRAME=MAX_PAYLOAD+(1<<20)+HEADER.size

def _compress(raw,codec):
    if codec=='lzma':
        import lzma
        return lzma.compress(raw,preset=6)
    return compressor(codec)(raw)

def _inflate(stored,codec,size):
    if codec=='lzma':
        import lzma
        try:
            d=lzma.LZMADecompressor(memlimit=256<<20);raw=d.decompress(stored,max_length=size+1)
            if not d.eof or d.unused_data:raise ValueError('Incomplete or trailing LZMA index payload')
        except lzma.LZMAError as exc:raise ValueError('Invalid LZMA index payload') from exc
        if len(raw)!=size:raise ValueError('Decoded index payload length differs')
        return raw
    return decompress(stored,codec,size)

def encode(raw,*,method='typed',codec='zstd'):
    if type(raw) is not bytes or len(raw)>MAX_RAW or type(method) is not str or method not in METHODS or type(codec) is not str or codec not in CODECS:raise ValueError('Invalid index frame input/method/codec')
    typed=None;payload=raw
    if method=='typed':
        from scripts.postings_transform import forward
        payload,typed=forward(raw)
    stored=_compress(payload,codec)
    frame=HEADER.pack(MAGIC,METHODS[method],CODECS[codec],len(raw),len(payload),len(stored),hashlib.sha256(raw).digest(),hashlib.sha256(payload).digest(),hashlib.sha256(stored).digest())+stored
    if len(frame)>MAX_FRAME:raise ValueError('Index frame exceeds bound')
    return frame,{'method':method,'codec':codec,'original_bytes':len(raw),'payload_raw_bytes':len(payload),'payload_stored_bytes':len(stored),'frame_header_bytes':HEADER.size,'frame_bytes':len(frame),'typed_details':typed}

def decode(frame):
    if type(frame) is not bytes or not HEADER.size<=len(frame)<=MAX_FRAME:raise ValueError('Invalid index frame size/type')
    magic,method,codec,source_size,payload_size,stored_size,source_sha,payload_sha,stored_sha=HEADER.unpack_from(frame)
    if magic!=MAGIC or method not in METHODS.values() or codec not in CODECS.values() or source_size>MAX_RAW or payload_size>MAX_PAYLOAD or stored_size!=len(frame)-HEADER.size or (method==0 and payload_size!=source_size):raise ValueError('Invalid index frame header')
    stored=frame[HEADER.size:]
    if hashlib.sha256(stored).digest()!=stored_sha:raise ValueError('Index stored payload SHA differs')
    name=next(k for k,v in CODECS.items() if v==codec);payload=_inflate(stored,name,payload_size)
    if hashlib.sha256(payload).digest()!=payload_sha:raise ValueError('Index typed payload SHA differs')
    raw=payload
    if method:
        from scripts.postings_transform import inverse
        raw=inverse(payload,source_size)
    if len(raw)!=source_size or hashlib.sha256(raw).digest()!=source_sha:raise ValueError('Original index SHA/size differs')
    return raw

def main():
    import argparse,json,os
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    pack=sub.add_parser('pack');pack.add_argument('source');pack.add_argument('output');pack.add_argument('--method',choices=METHODS,default='typed');pack.add_argument('--codec',choices=CODECS,default='zstd')
    unpack=sub.add_parser('unpack');unpack.add_argument('source');unpack.add_argument('output');args=p.parse_args()
    limit=MAX_RAW if args.command=='pack' else MAX_FRAME
    with Path(args.source).open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('Input exceeds experimental frame size bound')
    if args.command=='pack':result,stats=encode(raw,method=args.method,codec=args.codec)
    else:result=decode(raw);stats={'restored_bytes':len(result),'restored_sha256':hashlib.sha256(result).hexdigest()}
    with Path(args.output).open('xb') as stream:stream.write(result);stream.flush();os.fsync(stream.fileno())
    print(json.dumps(stats))

if __name__=='__main__':main()
