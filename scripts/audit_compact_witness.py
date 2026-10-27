"""Independent header/catalogue mapping audit; never calls compact/expand."""
import json,struct,hashlib
from scripts.postings_transform import canonical,parse
from scripts.proof_frame import decompress
from scripts.audit_selected_witness import audit
HEADER=struct.Struct('<8sBBQQ32s32s')
def verify(frame,original,store,sid):
 if type(frame) is not bytes or len(frame)<=HEADER.size or type(original) is not bytes:raise ValueError('Complete frame/original required')
 magic,method,codec,size,length,sha,payloadsha=HEADER.unpack_from(frame);payload=frame[HEADER.size:]
 if (magic,method) not in ((b'RKVSWC1\n',0),(b'RKVSWC1\n',1),(b'RKVPRF1\n',0)) or codec not in (0,1) or size!=len(original) or sha!=hashlib.sha256(original).digest() or length!=len(payload) or payloadsha!=hashlib.sha256(payload).digest():raise ValueError('Independent actual header/source identity differs')
 body=decompress(payload,codec);c=parse(original)
 if canonical(c)!=original or c['snapshot_id']!=sid:raise ValueError('Explicit original canonical SID differs')
 if method==0:
  if body!=original:raise ValueError('Plain payload differs')
 else:
  actual=parse(body)
  if canonical(actual)!=body:raise ValueError('Noncanonical compact source')
  expected=json.loads(original);paths=expected['selection'].pop('eligible_paths');expected['format']='RKVSELECTCOMPACT1';expected['selection']['eligible_path_count']=len(paths);expected['selection']['eligible_paths_sha256']=hashlib.sha256(json.dumps(paths,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
  if actual!=expected:raise ValueError('Independent compact mapping differs')
  with store.snapshot(sid) as snap:
   real=sorted(p for p in snap.files if p.endswith('.logic.jsonl'))
  if real!=paths:raise ValueError('Independent actual catalogue differs')
 verified=audit(store,sid,c)
 if not verified['original_selected_DAG_verified']:raise ValueError('Original source derivation not checked')
 return {'independent_header_and_catalog_mapping_verified':True,'original_selected_DAG_verified':True,'scientific_entailment_verified':False,'global_verdict':None,'shared_codec_and_old_original_DAG_dependencies':True}
