"""Explicit experimental native batch varints; original frame/validation retained."""
import ctypes,hashlib,re
from pathlib import Path
from scripts.postings_transform import MAX_RAW,MAX_PAYLOAD,MAX_DOCS,MAX_TOKENS,MAX_PAIRS,MAX_TF,read_uvar,parse,canonical,_schema
from scripts.index_frame import HEADER,MAGIC,METHODS,CODECS,MAX_FRAME,_inflate

class PairReader:
    def __init__(self,payload,library,expected_sha256):
        if type(payload) is not bytes or len(payload)>MAX_PAYLOAD:raise ValueError('Invalid native payload bound')
        if type(expected_sha256) is not str or re.fullmatch('[0-9a-f]{64}',expected_sha256) is None:raise ValueError('Explicit binary SHA required')
        path=Path(library).resolve()
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_sha256:raise ValueError('Native library SHA differs')
        self.library=ctypes.CDLL(str(path));abi=self.library.rkv_postings_abi;abi.argtypes=[];abi.restype=ctypes.c_uint32
        if abi()!=1:raise ValueError('Unsupported postings native ABI')
        self.function=self.library.rkv_postings_decode;self.function.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t,ctypes.POINTER(ctypes.c_uint64),ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];self.function.restype=ctypes.c_uint32
        self.payload=payload;self.source=ctypes.c_char_p(payload);self.address=ctypes.cast(self.source,ctypes.c_void_p).value;self.capacity=0;self.output=None
    def pairs(self,at,count):
        if type(at) is not int or not 0<=at<=len(self.payload) or type(count) is not int or not 1<=count<=MAX_DOCS:raise ValueError('Invalid batch count/offset')
        size=2*count
        if size>self.capacity:self.output=(ctypes.c_uint64*size)();self.capacity=size
        used=ctypes.c_size_t();code=self.function(self.address+at,len(self.payload)-at,size,self.output,self.capacity,ctypes.byref(used))
        if code!=0 or not 0<used.value<=len(self.payload)-at:raise ValueError('Invalid native canonical varint batch: '+str(code))
        return self.output,at+used.value

def inverse_native(payload,expected_size,reader):
    if type(payload) is not bytes or len(payload)>MAX_PAYLOAD or type(expected_size) is not int or not 0<=expected_size<=MAX_RAW:raise ValueError('Invalid typed payload bound')
    meta_len,at=read_uvar(payload,0)
    if meta_len>expected_size or meta_len>len(payload)-at:raise ValueError('Invalid canonical metadata size')
    meta_raw=payload[at:at+meta_len];at+=meta_len;model=parse(meta_raw)
    if canonical(model)!=meta_raw:raise ValueError('Noncanonical metadata JSON')
    placeholder,ids=_schema(model)
    if placeholder:raise ValueError('Nonempty metadata postings placeholder')
    doc_count,at=read_uvar(payload,at);tokens,at=read_uvar(payload,at);pairs,at=read_uvar(payload,at)
    if doc_count!=len(ids) or tokens>MAX_TOKENS or pairs>MAX_PAIRS:raise ValueError('Typed document/token/pair count differs')
    doc_json_sizes=[len(canonical(key)) for key in ids];restored_json_size=meta_len-2+2;posts={};previous_token=None;seen_pairs=0
    for n in range(tokens):
        size,at=read_uvar(payload,at)
        if not 1<=size<=65535 or size>len(payload)-at:raise ValueError('Invalid typed token size')
        token=payload[at:at+size].decode('utf-8');at+=size
        if previous_token is not None and token<=previous_token:raise ValueError('Noncanonical typed token order')
        previous_token=token;count,at=read_uvar(payload,at)
        if not 1<=count<=len(ids) or seen_pairs+count>pairs:raise ValueError('Invalid typed posting count')
        restored_json_size+=(1 if n else 0)+len(canonical(token))+1+2
        if restored_json_size>expected_size:raise ValueError('Restored JSON would exceed declared source size')
        posting={};previous=-1;values,at=reader.pairs(at,count)
        for j in range(count):
            gap=values[2*j];tf=values[2*j+1];number=previous+gap
            if gap<1 or not 0<=number<len(ids) or not 1<=tf<=MAX_TF:raise ValueError('Invalid typed document delta/frequency')
            restored_json_size+=(1 if j else 0)+doc_json_sizes[number]+1+len(str(tf))
            if restored_json_size>expected_size:raise ValueError('Restored JSON would exceed declared source size')
            posting[ids[number]]=tf;previous=number;seen_pairs+=1
        posts[token]=posting
    if seen_pairs!=pairs or at!=len(payload) or restored_json_size!=expected_size:raise ValueError('Typed payload EOF/count/source-size mismatch')
    model['shared']['postings']=posts;raw=canonical(model)
    if len(raw)!=expected_size:raise ValueError('Restored original JSON length differs')
    return raw

def decode_native(frame,library,expected_sha256):
    if type(frame) is not bytes or not HEADER.size<=len(frame)<=MAX_FRAME:raise ValueError('Invalid index frame size/type')
    magic,method,codec,source_size,payload_size,stored_size,source_sha,payload_sha,stored_sha=HEADER.unpack_from(frame)
    if magic!=MAGIC or method!=1 or codec not in CODECS.values() or source_size>MAX_RAW or payload_size>MAX_PAYLOAD or stored_size!=len(frame)-HEADER.size or (method==0 and payload_size!=source_size):raise ValueError('Invalid index frame header')
    stored=frame[HEADER.size:]
    if hashlib.sha256(stored).digest()!=stored_sha:raise ValueError('Index stored payload SHA differs')
    name=next(k for k,v in CODECS.items() if v==codec);payload=_inflate(stored,name,payload_size)
    if hashlib.sha256(payload).digest()!=payload_sha:raise ValueError('Index typed payload SHA differs')
    raw=payload
    raw=inverse_native(payload,source_size,PairReader(payload,library,expected_sha256))
    if len(raw)!=source_size or hashlib.sha256(raw).digest()!=source_sha:raise ValueError('Original index SHA/size differs')
    return raw

def main():
    import argparse,json,os
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('output');p.add_argument('--library',required=True);p.add_argument('--library-sha256',required=True);args=p.parse_args()
    with Path(args.source).open('rb') as stream:frame=stream.read(MAX_FRAME+1)
    raw=decode_native(frame,args.library,args.library_sha256)
    with Path(args.output).open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'restored_bytes':len(raw),'restored_sha256':hashlib.sha256(raw).hexdigest()}))

if __name__=='__main__':main()
