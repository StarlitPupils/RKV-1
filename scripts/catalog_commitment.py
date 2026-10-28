"""Experimental candidate. Trusted-initial-catalog anchor, not a self-authenticating SID proof.

RFC9162 tree hashing idea; application envelope is RKV-specific, not CT wire format.
"""
import copy,hashlib,re
from scripts.postings_transform import canonical
from scripts.source_universe import VALID
HEX=re.compile('[0-9a-f]{64}\\Z');MAX_LEAVES=4096
def h(raw):return hashlib.sha256(raw).digest()
def split(n):return 1<<((n-1).bit_length()-1)

class Catalogue:
 def __init__(self,sid,records):
  if type(sid) is not str or not HEX.fullmatch(sid) or type(records) is not list or not 1<=len(records)<=MAX_LEAVES:raise ValueError('Bounded explicit catalogue required')
  rows=copy.deepcopy(records)
  for e in rows:
   if type(e) is not dict or set(e)!={'path','bytes','sha256'} or type(e['path']) is not str or not VALID.fullmatch(e['path']) or len(e['path'])>240 or type(e['bytes']) is not int or not 0<=e['bytes']<1<<63 or type(e['sha256']) is not str or not HEX.fullmatch(e['sha256']):raise ValueError('Strict original file entry required')
  if [e['path'] for e in rows]!=sorted({e['path'] for e in rows}):raise ValueError('Unique sorted eligible paths required')
  self.records=rows;self.sid=sid;self._nodes={};self._positions={e['path']:i for i,e in enumerate(rows)}
  def tree(lo,n):
   if n==1:value=h(b'\x00'+canonical(rows[lo]))
   else:
    k=split(n);value=h(b'\x01'+tree(lo,k)+tree(lo+k,n-k))
   self._nodes[(lo,n)]=value;return value
  self.anchor={'format':'RKVCATALOGANCHOR1','snapshot_id':sid,'eligible_count':len(rows),'eligible_payload_B':sum(e['bytes'] for e in rows),'root_sha256':tree(0,len(rows)).hex()}
  self.anchor_sha256=hashlib.sha256(canonical(self.anchor)).hexdigest()
 def proof(self,path):
  if path not in self._positions:raise ValueError('Not an eligible original path')
  index=self._positions[path];siblings=[]
  def walk(lo,n):
   if n==1:return
   k=split(n)
   if index<lo+k:walk(lo,k);siblings.append(self._nodes[(lo+k,n-k)].hex())
   else:walk(lo+k,n-k);siblings.append(self._nodes[(lo,k)].hex())
  walk(0,len(self.records))
  return {'format':'RKVCATALOGMEMBER1','snapshot_id':self.sid,'anchor_sha256':self.anchor_sha256,'leaf_index':index,'entry':copy.deepcopy(self.records[index]),'siblings':siblings}

def from_store(store,sid):
 with store.snapshot(sid) as snap:
  rows=[{'path':p,'bytes':snap.files[p]['size'],'sha256':snap.files[p]['sha256']} for p in sorted(snap.files) if p.endswith('.logic.jsonl')]
 return Catalogue(sid,rows)
