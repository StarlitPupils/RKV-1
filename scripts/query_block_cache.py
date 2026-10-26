"""Assessment-only verified block reuse, never retained across trace scopes."""
from collections import OrderedDict
import sys
from unittest.mock import patch
from rkv1.core import digest,valid_hash


class QueryBlockCache:
    def __init__(self,store,capacity=65536):
        if type(capacity) is not int or capacity<1:raise ValueError('Invalid cache capacity')
        self.store=store;self.capacity=capacity;self.blocks=OrderedDict();self.payload=0;self.active=False
        self.data={'requests':0,'hits':0,'misses':0,'evictions':0,'oversize':0,'peak_payload_bytes':0,
                   'peak_retained_graph_bytes':0,'capacity_payload_bytes':capacity}

    def __enter__(self):
        if self.active:raise RuntimeError('Cache scope already active')
        self.active=True
        self.original=self.store.block;self.patcher=patch.object(self.store,'block',self.block)
        self.patcher.__enter__();return self

    def block(self,key,expected_size):
        if not isinstance(key,str) or not valid_hash(key) or type(expected_size) is not int or expected_size<1:
            raise ValueError('Invalid cached block request')
        self.data['requests']+=1;entry=(key,expected_size)
        if entry in self.blocks:
            raw=self.blocks[entry]
            if len(raw)!=expected_size or digest(raw)!=key:raise ValueError('Cached raw identity mismatch')
            self.blocks.move_to_end(entry);self.data['hits']+=1;return raw
        self.data['misses']+=1
        if expected_size<=self.capacity:
            while self.blocks and self.payload+expected_size>self.capacity:
                _,old=self.blocks.popitem(last=False);self.payload-=len(old);self.data['evictions']+=1
        raw=self.original(key,expected_size)
        if expected_size>self.capacity:self.data['oversize']+=1;return raw
        self.blocks[entry]=raw;self.payload+=len(raw)
        self.data['peak_payload_bytes']=max(self.data['peak_payload_bytes'],self.payload)
        footprint=sys.getsizeof(self)+sys.getsizeof(self.blocks)+sum(sys.getsizeof(k)+sum(map(sys.getsizeof,k))+sys.getsizeof(v) for k,v in self.blocks.items())
        self.data['peak_retained_graph_bytes']=max(self.data['peak_retained_graph_bytes'],footprint)
        return raw

    def __exit__(self,*args):
        try:return self.patcher.__exit__(*args)
        finally:self.blocks.clear();self.payload=0;self.active=False

    def result(self):
        return {**self.data,'retained_payload_bytes_after_scope':self.payload,
                'scope':'Single target-SID trace; payload cap excludes metadata/transient decode; retained graph size includes referenced keys/bytes, not incremental allocator RAM'}
