"""Independent proof-layout audit using frozen original bytes, not semantic proof."""
import hashlib,json,struct,zlib
FIELDS=('query','verdict','support_proof','refute_proof')
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def verify_frame(frame,original):
 if type(frame) is not bytes or len(frame)<=90 or type(original) is not bytes or not 0<len(original)<=33554432:raise ValueError('Bounded actual frame and frozen original required')
 magic,method,codec,root_length,payload_length,root_sha,payload_sha=struct.unpack('<8sBBQQ32s32s',frame[:90]);payload=frame[90:]
 if magic!=b'RKVPRF1\n' or method not in (0,1) or codec not in (0,1) or root_length!=len(original) or payload_length!=len(payload) or root_sha!=hashlib.sha256(original).digest() or payload_sha!=hashlib.sha256(payload).digest():raise ValueError('Independent actual header identity differs')
 if codec==0:
  d=zlib.decompressobj();raw=d.decompress(payload,33554433)
  if not d.eof or d.unused_data or d.unconsumed_tail or len(raw)>33554432:raise ValueError('Independent zlib bound/trailing check')
 else:
  import zstandard
  size=zstandard.frame_content_size(payload)
  if not 0<=size<=33554432:raise ValueError('Independent zstd bound')
  raw=zstandard.ZstdDecompressor().decompress(payload,max_output_size=33554432,allow_extra_data=False)
 if method==0:expected=original
 else:
  values=json.loads(original);template={k:v for k,v in values[0].items() if k not in FIELDS};queries=[{k:value[k] for k in FIELDS} for value in values]
  if any({k:v for k,v in value.items() if k not in FIELDS}!=template for value in values):raise ValueError('Original closures not identical')
  expected=canonical({'layout':'shared-explicit-source-closure-v1','template':template,'queries':queries})
 if raw!=expected:raise ValueError('Independent expected layout payload differs')
 return {'actual_frame_sha256':hashlib.sha256(frame).hexdigest(),'frozen_original_sha256':hashlib.sha256(original).hexdigest(),'payload_bytes':len(raw),'method':method,'codec':codec,'independent_header_and_layout_bytes_verified':True,'scientific_entailment_verified':False,'new_source_semantic_audit':False}
