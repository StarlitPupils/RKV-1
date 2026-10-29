"""Experimental conservative full-owned-graph node cache; not source-payload caching."""
import hashlib,re,sys
from collections import OrderedDict
HEX=re.compile('[0-9a-f]{64}\\Z')
class NodeLRU:
 __slots__=('sid','sid_bytes','count','capacity','entries','entry_charge','hits','misses','evictions','rewrites','hash_nodes','closed','max_retained_bound_B','max_provisional_bound_B','_base_B')
 def __init__(self,sid,count,*,capacity=65536):
  if type(sid) is not str or not HEX.fullmatch(sid) or type(count) is not int or not 1<=count<=4096 or type(capacity) is not int or not 2048<=capacity<=65536:raise ValueError('Explicit SID/count and full cache budget required')
  self.sid=sid;self.sid_bytes=bytes.fromhex(sid);self.count=count;self.capacity=capacity;self.entries=OrderedDict();self.entry_charge=0;self.hits=0;self.misses=0;self.evictions=0;self.rewrites=0;self.hash_nodes=0;self.closed=False;self.max_retained_bound_B=0;self.max_provisional_bound_B=0
  self._base_B=0;self._base_B=sys.getsizeof(self)+sum(sys.getsizeof(getattr(self,k)) for k in self.__slots__ if k!='entries')
  if self.bound_B()>capacity:raise ValueError('Cache fixed overhead exceeds capacity')
 def bound_B(self):
  return self._base_B+sys.getsizeof(self.entries)+self.entry_charge
 def check(self,key,sid):
  if self.closed or sid!=self.sid or type(key) is not tuple or len(key)!=2 or any(type(v) is not int for v in key) or key[0]<0 or key[1]<1 or key[0]+key[1]>self.count:raise ValueError('Active matching SID and valid tree range required')
 def stamp(self,key,value):return hashlib.sha256(b'RKVNODELRU1\0'+self.sid_bytes+key[0].to_bytes(8,'big')+key[1].to_bytes(8,'big')+value).digest()
 @staticmethod
 def charge(key,record):return sys.getsizeof(key)+sum(sys.getsizeof(v) for v in key)+sys.getsizeof(record)+sum(sys.getsizeof(v) for v in record)
 def get(self,key,*,sid):
  self.check(key,sid)
  if key not in self.entries:self.misses=min(self.misses+1,(1<<30)-1);return None
  record=self.entries[key]
  if type(record) is not tuple or len(record)!=2 or any(type(v) is not bytes or len(v)!=32 for v in record) or record[1]!=self.stamp(key,record[0]):raise ValueError('Cached node identity/checksum differs')
  self.entries.move_to_end(key);self.hits=min(self.hits+1,(1<<30)-1);return record[0]
 def put(self,key,value,*,sid):
  self.check(key,sid)
  if type(value) is not bytes or len(value)!=32:raise ValueError('Only exact node hash allowed')
  if key in self.entries:
   record=self.entries[key]
   if type(record) is not tuple or len(record)!=2 or any(type(v) is not bytes or len(v)!=32 for v in record) or record[1]!=self.stamp(key,record[0]) or record[0]!=value:raise ValueError('Existing node cannot change identity')
   self.entries.move_to_end(key);self.rewrites=min(self.rewrites+1,(1<<30)-1);return
  record=(value,self.stamp(key,value));self.entries[key]=record;self.entry_charge+=self.charge(key,record)
  self.max_provisional_bound_B=max(self.max_provisional_bound_B,self.bound_B())
  while self.entries and self.bound_B()>self.capacity:
   old,removed=self.entries.popitem(last=False);self.entry_charge-=self.charge(old,removed);self.evictions=min(self.evictions+1,(1<<30)-1)
  if self.bound_B()>self.capacity:raise ValueError('Full cache overhead exceeds bound')
  self.max_retained_bound_B=max(self.max_retained_bound_B,self.bound_B())
 def close(self):self.entries.clear();self.entry_charge=0;self.closed=True
