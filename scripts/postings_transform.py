"""Reversible canonical-index postings transform, opaque metadata retained."""
import json

MAX_RAW=64<<20
MAX_PAYLOAD=MAX_RAW+(1<<20)
MAX_DOCS=1_000_000
MAX_TOKENS=1_000_000
MAX_PAIRS=4_000_000
MAX_TF=(1<<31)-1

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate original JSON key')
        result[key]=value
    return result

def _constant(value):raise ValueError('Nonfinite original JSON constant')

def parse(raw):return json.loads(raw,object_pairs_hook=_unique,parse_constant=_constant)

def uvar(value):
    if type(value) is not int or not 0<=value<(1<<64):raise ValueError('Invalid unsigned varint')
    result=bytearray()
    while value>=128:result.append((value&127)|128);value>>=7
    result.append(value);return bytes(result)

def read_uvar(raw,at):
    value=0
    for n in range(10):
        if at>=len(raw):raise ValueError('Truncated unsigned varint')
        byte=raw[at];at+=1
        if n==9 and byte>1:raise ValueError('Unsigned varint overflow')
        value|=(byte&127)<<(7*n)
        if not byte&128:
            if n and byte==0:raise ValueError('Noncanonical unsigned varint')
            return value,at
    raise ValueError('Unsigned varint overflow')

def _schema(model):
    if type(model) is not dict or type(model.get('shared')) is not dict:raise ValueError('Original shared index required')
    shared=model['shared'];posts=shared.get('postings');lengths=shared.get('doc_lengths')
    if type(posts) is not dict or type(lengths) is not dict or len(lengths)>MAX_DOCS or len(posts)>MAX_TOKENS:raise ValueError('Unsupported original postings shape/count')
    ids=sorted(lengths)
    if any(type(key) is not str or not 1<=len(key.encode('utf-8'))<=4096 for key in ids):raise ValueError('Invalid original document ID')
    return posts,ids

def forward(raw):
    if type(raw) is not bytes or len(raw)>MAX_RAW:raise ValueError('Invalid original model bytes')
    model=parse(raw)
    if canonical(model)!=raw:raise ValueError('Typed transform requires exact canonical original JSON')
    postings,ids=_schema(model);numbers={key:i for i,key in enumerate(ids)};meta=dict(model);meta['shared']=dict(model['shared']);meta['shared']['postings']={};meta_raw=canonical(meta)
    rows=0;blocks=[]
    for token,posting in sorted(postings.items()):
        if type(token) is not str or type(posting) is not dict or not 1<=len(posting)<=len(ids):raise ValueError('Invalid original token/posting')
        word=token.encode('utf-8')
        if not 1<=len(word)<=65535:raise ValueError('Invalid original token length')
        block=bytearray(uvar(len(word))+word+uvar(len(posting)));previous=-1
        for key,tf in sorted(posting.items()):
            if key not in numbers or type(tf) is not int or not 1<=tf<=MAX_TF:raise ValueError('Invalid original posting identity or frequency')
            number=numbers[key];block.extend(uvar(number-previous));block.extend(uvar(tf));previous=number;rows+=1
            if rows>MAX_PAIRS:raise ValueError('Too many original postings')
        blocks.append(block)
    payload=uvar(len(meta_raw))+meta_raw+uvar(len(ids))+uvar(len(postings))+uvar(rows)+b''.join(blocks)
    if len(payload)>MAX_PAYLOAD:raise ValueError('Typed payload exceeds bound')
    return payload,{'metadata_json_bytes':len(meta_raw),'documents':len(ids),'vocabulary_tokens':len(postings),'posting_pairs':rows,'typed_payload_bytes':len(payload)}

def inverse(payload,expected_size):
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
        posting={};previous=-1
        for j in range(count):
            gap,at=read_uvar(payload,at);tf,at=read_uvar(payload,at);number=previous+gap
            if gap<1 or not 0<=number<len(ids) or not 1<=tf<=MAX_TF:raise ValueError('Invalid typed document delta/frequency')
            restored_json_size+=(1 if j else 0)+doc_json_sizes[number]+1+len(str(tf))
            if restored_json_size>expected_size:raise ValueError('Restored JSON would exceed declared source size')
            posting[ids[number]]=tf;previous=number;seen_pairs+=1
        posts[token]=posting
    if seen_pairs!=pairs or at!=len(payload) or restored_json_size!=expected_size:raise ValueError('Typed payload EOF/count/source-size mismatch')
    model['shared']['postings']=posts;raw=canonical(model)
    if len(raw)!=expected_size:raise ValueError('Restored original JSON length differs')
    return raw
