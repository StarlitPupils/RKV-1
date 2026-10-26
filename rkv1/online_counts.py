"""Bounded online byte counts, reset for each independent arithmetic stream.

cdf(context) is sequential and stateful: it incorporates the previous symbol
once per call. It must not be probed repeatedly while encoding a single stream.
"""
from array import array
import hashlib
import json
import sys

RULE = {'alphabet':256,'bos':256,'initial_count':1,'update':2,
        'row_rescale_above':32768,'rescale':'max(1,(n+1)//2)',
        'cdf_total':32768,'cdf_min':1,'remainder':'ascending-symbol',
        'update_timing':'previous-symbol-before-next-prediction','version':1}
RULE_BYTES = json.dumps(RULE,sort_keys=True,separators=(',',':')).encode('ascii')
RULE_SHA = hashlib.sha256(RULE_BYTES).digest()


class Predictor:
    __slots__ = ('order','counts','totals','rescales')

    def __init__(self,order):
        if type(order) is not int or order not in (0,1):raise ValueError('Invalid online order')
        self.order=order
        self.counts=[array('H',[1])*256 for _ in range(257 if order else 1)]
        self.totals=array('I',[256])*len(self.counts)
        if self.counts[0].itemsize!=2 or self.totals.itemsize!=4:
            raise RuntimeError('Online state needs 16/32-bit array storage')
        self.rescales=0

    def accounting(self):
        return {'logical_state_bytes':len(self.counts)*256*2+len(self.totals)*4,
                'owned_state_containers_bytes':sys.getsizeof(self)+sys.getsizeof(self.counts)
                    +sum(map(sys.getsizeof,self.counts))+sys.getsizeof(self.totals),
                'rescale_count':self.rescales,
                'scope':'Owned persistent containers only; temporary CDF/Python/shared runtime also charged by whole-process RSS'}

    def cdf(self,context):
        if (len(context)!=4 or any(type(x) is not int or not 0<=x<=256 for x in context)):
            raise ValueError('Invalid online context')
        previous=context[-1]
        if previous!=256:
            row=context[-2] if self.order else 0
            counts=self.counts[row]
            counts[previous]+=2;self.totals[row]+=2
            if self.totals[row]>32768:
                for i,value in enumerate(counts):counts[i]=max(1,(value+1)//2)
                self.totals[row]=sum(counts);self.rescales+=1
        row=previous if self.order else 0
        counts=self.counts[row];total=self.totals[row]
        frequencies=[1+n*32512//total for n in counts]
        for i in range(32768-sum(frequencies)):frequencies[i]+=1
        cdf=[0]
        for n in frequencies:cdf.append(cdf[-1]+n)
        return cdf
