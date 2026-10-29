"""Experimental cached candidate: rebuild requested paths, retain no complete tree-node index.

Existing full Snapshot metadata and O(N) sorted key list are still required.
The caller must independently authenticate the returned anchor before acceptance.
"""
import hashlib,re
from scripts.postings_transform import canonical
from scripts.source_universe import VALID
HEX=re.compile('[0-9a-f]{64}\\Z')

def _derive(reader,sid,paths,cache,*,anchor_phase=False):
 if type(sid) is not str or not HEX.fullmatch(sid) or type(paths) is not list or not (0 if anchor_phase else 1)<=len(paths)<=8 or any(type(p) is not str or not VALID.fullmatch(p) or len(p)>240 for p in paths) or len(set(paths))!=len(paths):raise ValueError('Explicit SID and bounded selected paths required')
 with reader.snapshot(sid) as snap:
  names=sorted(p for p in snap.files if p.endswith('.logic.jsonl'))
  if not 1<=len(names)<=4096 or any(not VALID.fullmatch(p) or len(p)>240 for p in names) or any(p not in names for p in paths):raise ValueError('Actual bounded eligible catalogue required')
  if cache.sid!=sid or cache.count!=len(names) or cache.closed:raise ValueError('Cache owner/SID/count differs')
  wanted=set(paths);indices={i for i,n in enumerate(names) if n in wanted};entries={};total=sum(snap.files[n]['size'] for n in names)
  def walk(lo,n):
   key=(lo,n)
   if not any(lo<=i<lo+n for i in indices):
    cached=cache.get(key,sid=sid)
    if cached is not None:return cached,{}
   if n==1:
    name=names[lo];item=snap.files[name];e={'path':name,'bytes':item['size'],'sha256':item['sha256']}
    if type(e['bytes']) is not int or not 0<=e['bytes']<1<<63 or type(e['sha256']) is not str or not HEX.fullmatch(e['sha256']):raise ValueError('Original validated metadata shape differs')
    root=hashlib.sha256(bytes([0])+canonical(e)).digest();cache.hash_nodes=min(cache.hash_nodes+1,(1<<30)-1);cache.put(key,root,sid=sid)
    if name in wanted:entries[lo]=e;return root,{lo:[]}
    return root,{}
   cut=1<<((n-1).bit_length()-1);left,lp=walk(lo,cut);right,rp=walk(lo+cut,n-cut)
   for path in lp.values():path.append(right.hex())
   for path in rp.values():path.append(left.hex())
   lp.update(rp);root=hashlib.sha256(bytes([1])+left+right).digest();cache.hash_nodes=min(cache.hash_nodes+1,(1<<30)-1);cache.put(key,root,sid=sid);return root,lp
  root,branches=walk(0,len(names));anchor={'format':'RKVCATALOGANCHOR1','snapshot_id':sid,'eligible_count':len(names),'eligible_payload_B':total,'root_sha256':root.hex()};anchor_sha=hashlib.sha256(canonical(anchor)).hexdigest()
  proofs=[{'format':'RKVCATALOGMEMBER1','snapshot_id':sid,'anchor_sha256':anchor_sha,'leaf_index':i,'entry':entries[i],'siblings':branches[i]} for i in sorted(branches)]
  return {'anchor':anchor,'members':proofs}


def anchor_only(reader,sid,cache):
 return _derive(reader,sid,[],cache,anchor_phase=True)['anchor']

def requested_members(reader,sid,paths,cache):
 return _derive(reader,sid,paths,cache)
