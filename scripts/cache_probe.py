"""Experimental scoped causal observer; no alternate cache policy or production timing."""
from collections import Counter
from scripts.node_lru import NodeLRU
_ACTIVE=False
class CacheProbe:
 def __enter__(self):
  global _ACTIVE
  if _ACTIVE:raise ValueError('Nested/global concurrent observation unsupported')
  _ACTIVE=True;self.original=NodeLRU.get;self.target=None;self.running=False
  def observed(cache,key,*,sid):
   result=self.original(cache,key,sid=sid)
   if self.running and cache is self.target:
    self.lookups+=1
    if result is None:self.misses+=1
    else:self.hits+=1
    if key in self.initial:
     self.asked_initial.add(key)
     if result is None:self.lost_initial.add(key);self.lost_events+=1
   return result
  self.wrapper=observed;NodeLRU.get=observed;return self
 def begin(self,cache,indices):
  if self.running:raise ValueError('Query already active')
  self.target=cache;self.initial=frozenset(cache.entries);self.relevant={k for k in self.initial if not any(k[0]<=i<k[0]+k[1] for i in indices)};self.asked_initial=set();self.lost_initial=set();self.lookups=self.hits=self.misses=self.lost_events=0;self.initial_hits=cache.hits;self.initial_misses=cache.misses;self.hist=dict(Counter(k[1] for k in self.initial));self.running=True
 def end(self):
  if not self.running:raise ValueError('No query active')
  self.running=False;assert self.lookups==self.hits+self.misses and self.target.hits-self.initial_hits==self.hits and self.target.misses-self.initial_misses==self.misses and self.lost_initial<=self.asked_initial<=self.relevant
  return {'lookups':self.lookups,'hits':self.hits,'misses':self.misses,'initial_entries':len(self.initial),'initial_relevant_entries':len(self.relevant),'initial_relevant_asked_unique':len(self.asked_initial),'initial_entries_lost_before_lookup_unique':len(self.lost_initial),'initial_entries_lost_before_lookup_events':self.lost_events,'initial_relevant_not_asked':len(self.relevant-self.asked_initial),'initial_span_histogram':{str(k):v for k,v in sorted(self.hist.items())}}
 def __exit__(self,*args):
  global _ACTIVE
  NodeLRU.get=self.original;_ACTIVE=False;self.target=None;self.running=False;self.initial=frozenset();self.relevant=set()
