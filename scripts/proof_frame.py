"""Reversible shared-node proof layout; SHA identity is not semantic verification."""
import hashlib,struct,zlib
from scripts.postings_transform import canonical,parse
MAGIC=b'RKVPRF1\n';HEADER=struct.Struct('<8sBBQQ32s32s');MAX_JSON=32<<20;MAX_FRAME=MAX_JSON+MAX_JSON//100+128;MAX_QUERIES=256
VARYING=('query','verdict','support_proof','refute_proof')
ROOT_KEYS={'format','snapshot_id','source_scope','query','complete','verdict','work_used','work_budget','nodes','support_proof','refute_proof','source_grammar_verified','scientific_entailment_verified','generated_answer','scope'}
METHODS={'plain':0,'shared':1};CODECS={'zlib':0,'zstd':1}
def hash_bytes(raw):return hashlib.sha256(raw).digest()
def expected_digest(value):
 if type(value) is not str or len(value)!=64:
  raise ValueError('Explicit trusted expected canonical-root SHA256 required')
 try:
  result=bytes.fromhex(value)
  if len(result)!=32:raise ValueError('Expected root digest length')
  return result
 except ValueError:raise ValueError('Invalid expected root SHA256') from None
def to_shared(raw):
 if type(raw) is not bytes or not 0<len(raw)<=MAX_JSON:raise ValueError('Bounded canonical proof JSON required')
 values=parse(raw)
 if type(values) is not list or not 1<=len(values)<=MAX_QUERIES or canonical(values)!=raw:raise ValueError('Bounded canonical nonempty proof array required')
 for value in values:
  if type(value) is not dict or set(value)!=ROOT_KEYS or value['format']!='RKVSETLOGIC1' or type(value['nodes']) is not list:raise ValueError('Exact supported proof envelope required')
 template={k:v for k,v in values[0].items() if k not in VARYING};queries=[]
 for value in values:
  if {k:v for k,v in value.items() if k not in VARYING}!=template:raise ValueError('Proof closure/source/work metadata differ across batch')
  queries.append({k:value[k] for k in VARYING})
 return canonical({'layout':'shared-explicit-source-closure-v1','template':template,'queries':queries})
def from_shared(raw,root_length):
 if type(raw) is not bytes or not 0<len(raw)<=MAX_JSON or type(root_length) is not int or not 0<root_length<=MAX_JSON:raise ValueError('Bounded shared JSON/root length required')
 value=parse(raw)
 if type(value) is not dict or set(value)!={'layout','template','queries'} or value['layout']!='shared-explicit-source-closure-v1' or canonical(value)!=raw:raise ValueError('Canonical shared layout required')
 template=value['template'];queries=value['queries']
 if type(template) is not dict or set(template)!=ROOT_KEYS-set(VARYING) or template.get('format')!='RKVSETLOGIC1' or type(template.get('nodes')) is not list or type(queries) is not list or not 1<=len(queries)<=MAX_QUERIES:raise ValueError('Shared template/query schema differs')
 result=bytearray(b'[')
 for i,query in enumerate(queries):
  if type(query) is not dict or set(query)!=set(VARYING):raise ValueError('Shared query schema differs')
  part=canonical({**template,**query});additional=len(part)+(1 if i else 0)+1
  if len(result)+additional>root_length or len(result)+additional>MAX_JSON:raise ValueError('Expanded root exceeds declared bound')
  if i:result.extend(b',')
  result.extend(part)
 result.extend(b']')
 if len(result)!=root_length:raise ValueError('Expanded root length differs')
 return bytes(result)
def compress(raw,codec):
 if codec=='zlib':return zlib.compress(raw,9)
 if codec=='zstd':
  import zstandard as zstd
  return zstd.ZstdCompressor(level=3).compress(raw)
 raise ValueError('Unsupported proof codec')
def decompress(raw,codec):
 if codec==0:
  decoder=zlib.decompressobj()
  try:result=decoder.decompress(raw,MAX_JSON+1)
  except zlib.error as exc:raise ValueError('Invalid zlib payload') from exc
  if len(result)>MAX_JSON or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:raise ValueError('Invalid/trailing/oversize zlib payload')
  return result
 if codec==1:
  import zstandard as zstd
  try:size=zstd.frame_content_size(raw)
  except zstd.ZstdError as exc:raise ValueError('Invalid zstd frame') from exc
  if not 0<=size<=MAX_JSON:raise ValueError('Bounded known-size zstd frame required')
  try:result=zstd.ZstdDecompressor().decompress(raw,max_output_size=MAX_JSON,allow_extra_data=False)
  except zstd.ZstdError as exc:raise ValueError('Invalid/trailing zstd frame') from exc
  if len(result)!=size:raise ValueError('Zstd declared length differs')
  return result
 raise ValueError('Unsupported proof codec tag')
def encode_frame(raw,*,method,codec):
 if type(raw) is not bytes or not 0<len(raw)<=MAX_JSON or method not in METHODS or codec not in CODECS:raise ValueError('Bounded proof root and frozen method/codec required')
 payload=raw if method=='plain' else to_shared(raw)
 if len(payload)>MAX_JSON:raise ValueError('Transformed payload bound')
 encoded=compress(payload,codec)
 if len(encoded)>MAX_FRAME-HEADER.size:raise ValueError('Encoded payload bound')
 return HEADER.pack(MAGIC,METHODS[method],CODECS[codec],len(raw),len(encoded),hash_bytes(raw),hash_bytes(encoded))+encoded

def decode_frame(frame,*,expected_root_sha256):
 trusted=expected_digest(expected_root_sha256)
 if type(frame) is not bytes or not HEADER.size<len(frame)<=MAX_FRAME:raise ValueError('Bounded complete proof frame required')
 magic,method,codec,root_length,payload_length,root_sha,payload_sha=HEADER.unpack_from(frame)
 if magic!=MAGIC or method not in (0,1) or codec not in (0,1) or not 0<root_length<=MAX_JSON or payload_length!=len(frame)-HEADER.size or root_sha!=trusted:raise ValueError('Proof header or trusted root identity differs')
 payload=frame[HEADER.size:]
 if hash_bytes(payload)!=payload_sha:raise ValueError('Encoded payload SHA differs')
 decoded=decompress(payload,codec)
 root=decoded if method==0 else from_shared(decoded,root_length)
 if len(root)!=root_length or hash_bytes(root)!=trusted:raise ValueError('Restored trusted root bytes differ')
 return root

def main(argv=None):
 import argparse
 from pathlib import Path
 p=argparse.ArgumentParser(description='Experimental reversible proof bytes only; no semantic verification')
 p.add_argument('operation',choices=('encode','decode'));p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--method',choices=METHODS,default='shared');p.add_argument('--codec',choices=CODECS,default='zlib');p.add_argument('--expected-root-sha256');a=p.parse_args(argv)
 limit=MAX_JSON if a.operation=='encode' else MAX_FRAME
 if not 0<a.source.stat().st_size<=limit:raise ValueError('Input file outside bound')
 raw=a.source.read_bytes()
 if a.operation=='encode':result=encode_frame(raw,method=a.method,codec=a.codec)
 else:
  if a.expected_root_sha256 is None:p.error('decode requires --expected-root-sha256 from a trusted external source')
  result=decode_frame(raw,expected_root_sha256=a.expected_root_sha256)
 with a.output.open('xb') as f:f.write(result)
if __name__=='__main__':main()
