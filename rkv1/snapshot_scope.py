"""Finite-batch reuse of a fully validated pinned Snapshot's metadata."""
from contextlib import contextmanager
from types import MappingProxyType
from collections.abc import Mapping
import sys
MAX_TRACKED_METADATA=16<<20

def freeze(value,backings):
 if isinstance(value,dict):
  copied={k:freeze(v,backings) for k,v in value.items()};backings.append(copied);return MappingProxyType(copied)
 if isinstance(value,list):return tuple(freeze(v,backings) for v in value)
 return value

def tracked_size(value,seen=None):
 seen=set() if seen is None else seen
 if id(value) in seen:return 0
 seen.add(id(value));size=sys.getsizeof(value)
 if isinstance(value,Mapping):return size+sum(tracked_size(k,seen)+tracked_size(v,seen) for k,v in value.items())
 if isinstance(value,(tuple,list)):return size+sum(tracked_size(v,seen) for v in value)
 return size

class SnapshotView:
 def __init__(self,owner):self._owner=owner
 @property
 def files(self):self._owner.check();return self._owner._files
 def read_range(self,path,*a,**kw):self._owner.check();return self._owner._snap.read_range(path,*a,**kw)
 def verify(self):self._owner.check();return self._owner._snap.process()
 @property
 def snapshot_id(self):self._owner.check();return self._owner._sid

class SnapshotReadScope:
 """One SID/one synchronous read scope; original payload validation remains active."""
 def __init__(self,store,sid,*,metadata_budget=MAX_TRACKED_METADATA):
  if type(sid) is not str or not sid or type(metadata_budget) is not int or not 0<=metadata_budget<=MAX_TRACKED_METADATA:raise ValueError('Explicit pinned SID and bounded tracked metadata cap required')
  self._store=store;self._sid=sid;self._budget=metadata_budget;self._entered=False;self._active=False;self._snap=None;self._files=None;self._backings=None;self.tracked_metadata_bytes=None
 def check(self):
  if not self._active:raise ValueError('Pinned read scope is not active')
 def __enter__(self):
  if self._entered:raise ValueError('Pinned metadata scope cannot be reentered')
  self._entered=True
  try:
   self._snap=self._store.snapshot(self._sid);self._backings=[];self._files=freeze(self._snap.files,self._backings);self.tracked_metadata_bytes=tracked_size((self._snap.header,self._snap.files,self._snap.offsets,self._files,self._backings))
   if self.tracked_metadata_bytes>self._budget:raise ValueError('Tracked metadata cap exceeded after initial full validation')
   self._active=True;return self
  except BaseException:self.close();raise
 def close(self):
  self._active=False
  if self._snap is not None:self._snap.close()
  self._snap=None;self._files=None;self._backings=None
 def __exit__(self,*args):self.close()
 @contextmanager
 def snapshot(self,sid):
  self.check()
  if type(sid) is not str or sid!=self._sid:raise ValueError('Read scope cannot switch pinned SID or follow HEAD')
  yield SnapshotView(self)

 @property
 def files(self):self.check();return self._files
 @property
 def snapshot_id(self):self.check();return self._sid
 @property
 def closed(self):return not self._active
 def read_range(self,path,*a,**kw):self.check();return self._snap.read_range(path,*a,**kw)
 def verify(self):self.check();return self._snap.process()
