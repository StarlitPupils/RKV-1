"""Experimental full-entry metadata cache experiment, same owner/anchor checks as v080."""
import sys
from rkv1.core import digest
from rkv1.snapshot_scope import tracked_size
from scripts.postings_transform import canonical
from scripts.span_node_lru import SpanNodeLRU
from scripts.cached_membership import anchor_only,requested_members
class SpanMembership:
 def __init__(self,scope,sid):
  scope.check()
  if scope.snapshot_id!=sid:raise ValueError('Pinned SID differs')
  self.scope=scope;self.sid=sid;self.closed=False;self.cache=SpanNodeLRU(sid,sum(p.endswith('.logic.jsonl') for p in scope.files),capacity=65536);self.anchor=anchor_only(scope,sid,self.cache);self.anchor_sha256=digest(canonical(self.anchor))
 def issue(self,paths):
  if self.closed:raise ValueError('Prover closed')
  self.scope.check();packet=requested_members(self.scope,self.sid,paths,self.cache)
  if packet['anchor']!=self.anchor:raise ValueError('Cached root differs from initial trusted anchor')
  return packet
 def retained_state_B(self):
  if self.closed:raise ValueError('Prover closed')
  self.scope.check();seen=set();tracked_size((self.scope.files,self.sid),seen);size=sys.getsizeof(self)+sys.getsizeof(vars(self))
  for k,v in vars(self).items():
   if k!='scope':size+=tracked_size(k,seen)+tracked_size(v,seen)
  for k in self.cache.__slots__:size+=tracked_size(getattr(self.cache,k),seen)
  return size
 def close(self):self.cache.close();self.closed=True;self.anchor=None;self.anchor_sha256=None
