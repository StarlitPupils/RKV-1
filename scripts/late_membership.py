"""Experimental same-scope API; all initial scans and later recomputation are deliberate work."""
import sys
from scripts.catalog_commitment import from_store
from scripts.postings_transform import canonical
from rkv1.core import digest
from rkv1.snapshot_scope import tracked_size
from scripts.ephemeral_membership import anchor_only,requested_members

class LateMembership:
 def __init__(self,scope,sid,method):
  if method not in ('retained','ephemeral'):raise ValueError('Fixed candidate methods required')
  scope.check()
  if scope.snapshot_id!=sid:raise ValueError('Pinned scope SID differs')
  self.scope=scope;self.sid=sid;self.method=method;self.closed=False;self.tree=None
  if method=='retained':self.tree=from_store(scope,sid);self.anchor=self.tree.anchor
  else:self.anchor=anchor_only(scope,sid)
  self.anchor_sha256=digest(canonical(self.anchor))
 def check(self):
  if self.closed:raise ValueError('Prover is closed')
  self.scope.check()
 def issue(self,paths):
  self.check()
  if type(paths) is not list or not 1<=len(paths)<=8 or any(type(p) is not str for p in paths) or len(set(paths))!=len(paths):raise ValueError('Bounded unique explicit paths required')
  if self.tree is not None:packet={'anchor':self.anchor,'members':[self.tree.proof(p) for p in sorted(paths)]}
  else:packet=requested_members(self.scope,self.sid,paths)
  if packet['anchor']!=self.anchor:raise ValueError('Initial anchor differs after late request')
  return packet
 def retained_state_B(self):
  self.check();seen=set();tracked_size((self.scope.files,self.sid),seen)
  result=sys.getsizeof(self)+sys.getsizeof(vars(self))
  for key,value in vars(self).items():
   if key!='scope':result+=tracked_size(key,seen)+tracked_size(value,seen)
  if self.tree is not None:result+=tracked_size(vars(self.tree),seen)
  return result

 def close(self):self.closed=True;self.tree=None;self.anchor=None;self.anchor_sha256=None
