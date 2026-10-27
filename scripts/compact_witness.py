"""Experimental candidate, context-dependent selected-catalog binding; not general compression."""
import copy
from rkv1.core import digest
from scripts.postings_transform import canonical,parse
from scripts.selected_witness import FIELDS,SCOPE
from scripts.source_universe import VALID
from scripts.proof_frame import HEADER,MAX_JSON,MAX_FRAME,compress,decompress,hash_bytes,expected_digest
MAGIC=b'RKVSWC1\n';METHODS={'plain':0,'compact':1};CODECS={'zlib':0,'zstd':1};MAX_CATALOGUE=4096
SELECTION={'snapshot_id','eligible_paths','eligible_payload_bytes','selected_paths','selected_payload_bytes','source_byte_budget','full_eligible_selection'}
COMPACT_SELECTION=SELECTION-{'eligible_paths'}|{'eligible_path_count','eligible_paths_sha256'}

def original(raw):
 if type(raw) is not bytes or not 0<len(raw)<=MAX_JSON:raise ValueError('Bounded canonical original certificate required')
 c=parse(raw)
 if type(c) is not dict or set(c)!=FIELDS or c.get('format')!='RKVSELECTWITNESS1' or c.get('scope')!=SCOPE or c.get('global_verdict') is not None or c.get('scientific_entailment_verified') is not False or c.get('generated_answer') is not None or canonical(c)!=raw:raise ValueError('Exact canonical selected-witness envelope required')
 selection=c['selection']
 if type(selection) is not dict or set(selection)!=SELECTION or selection.get('snapshot_id')!=c['snapshot_id']:raise ValueError('Original selection schema differs')
 paths=selection['eligible_paths']
 if type(paths) is not list or not 1<=len(paths)<=MAX_CATALOGUE or any(type(p) is not str or not VALID.fullmatch(p) for p in paths) or sorted(set(paths))!=paths:raise ValueError('Bounded canonical eligible path list required')
 return c

def compact(raw):
 c=original(raw);c=copy.deepcopy(c);paths=c['selection'].pop('eligible_paths');c['format']='RKVSELECTCOMPACT1';c['selection'].update(eligible_path_count=len(paths),eligible_paths_sha256=digest(canonical(paths)));return canonical(c)

def expand(raw,store,snapshot_id):
 if type(raw) is not bytes or not 0<len(raw)<=MAX_JSON or type(snapshot_id) is not str:raise ValueError('Bounded compact certificate and explicit pinned SID required')
 c=parse(raw)
 if type(c) is not dict or set(c)!=FIELDS or c.get('format')!='RKVSELECTCOMPACT1' or c.get('snapshot_id')!=snapshot_id or c.get('scope')!=SCOPE or c.get('global_verdict') is not None or c.get('scientific_entailment_verified') is not False or c.get('generated_answer') is not None or canonical(c)!=raw:raise ValueError('Compact envelope or trusted SID differs')
 selection=c['selection']
 if type(selection) is not dict or set(selection)!=COMPACT_SELECTION or selection['snapshot_id']!=snapshot_id or type(selection['eligible_path_count']) is not int or not 1<=selection['eligible_path_count']<=MAX_CATALOGUE:raise ValueError('Bounded catalogue count/schema required')
 expected_digest(selection['eligible_paths_sha256'])
 # The whole real snapshot is validated, not a guessed subset or caller-provided index.
 with store.snapshot(snapshot_id) as snap:
  paths=sorted(p for p in snap.files if p.endswith('.logic.jsonl'))
  if any(not VALID.fullmatch(p) for p in paths) or len(paths)!=selection['eligible_path_count'] or digest(canonical(paths))!=selection['eligible_paths_sha256']:raise ValueError('Actual pinned catalogue differs from compact binding')
 c=copy.deepcopy(c);del c['selection']['eligible_path_count'];del c['selection']['eligible_paths_sha256'];c['selection']['eligible_paths']=paths;c['format']='RKVSELECTWITNESS1';result=canonical(c)
 if len(result)>MAX_JSON:raise ValueError('Expanded certificate bound')
 original(result);return result

def encode_frame(raw,*,method,codec):
 if type(raw) is not bytes or not 0<len(raw)<=MAX_JSON or method not in METHODS or codec not in CODECS:raise ValueError('Bounded source and fixed method/codec required')
 body=raw if method=='plain' else compact(raw);payload=compress(body,codec)
 if len(payload)>MAX_FRAME-HEADER.size:raise ValueError('Encoded payload bound')
 return HEADER.pack(MAGIC,METHODS[method],CODECS[codec],len(raw),len(payload),hash_bytes(raw),hash_bytes(payload))+payload

def decode_frame(frame,*,store,snapshot_id,expected_root_sha256):
 trusted=expected_digest(expected_root_sha256)
 if type(frame) is not bytes or not HEADER.size<len(frame)<=MAX_FRAME:raise ValueError('Bounded complete compact frame required')
 magic,method,codec,size,length,root_sha,payload_sha=HEADER.unpack_from(frame)
 if magic!=MAGIC or method not in (0,1) or codec not in (0,1) or not 0<size<=MAX_JSON or length!=len(frame)-HEADER.size or root_sha!=trusted:raise ValueError('Header or trusted root identity differs')
 payload=frame[HEADER.size:]
 if hash_bytes(payload)!=payload_sha:raise ValueError('Encoded payload SHA differs')
 decoded=decompress(payload,codec);root=decoded if method==0 else expand(decoded,store,snapshot_id)
 if len(root)!=size or hash_bytes(root)!=trusted:raise ValueError('Expanded trusted canonical original differs')
 return root

if __name__=='__main__':
 import argparse
 from pathlib import Path
 from rkv1.store import Store
 p=argparse.ArgumentParser(description='Context-bound compact proof bytes; not semantic or scientific verification')
 sub=p.add_subparsers(dest='command',required=True);enc=sub.add_parser('encode');enc.add_argument('source',type=Path);enc.add_argument('output',type=Path);enc.add_argument('--method',choices=tuple(METHODS),default='compact');enc.add_argument('--codec',choices=tuple(CODECS),default='zstd');dec=sub.add_parser('decode');dec.add_argument('source',type=Path);dec.add_argument('output',type=Path);dec.add_argument('--store',type=Path,required=True);dec.add_argument('--snapshot',required=True);dec.add_argument('--expected-root-sha256',required=True);a=p.parse_args()
 result=encode_frame(a.source.read_bytes(),method=a.method,codec=a.codec) if a.command=='encode' else decode_frame(a.source.read_bytes(),store=Store(a.store,io_backend='bounded'),snapshot_id=a.snapshot,expected_root_sha256=a.expected_root_sha256)
 with a.output.open('xb') as f:f.write(result)
