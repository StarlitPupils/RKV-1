"""Fixed 4-byte context, 4-dimensional embedding and 8-unit integer MLP."""
import struct

MAGIC=b'RKVMLP01'
PARAMETERS=3468
MODEL_BYTES=8+2*PARAMETERS
Q=256
SCORES=[65536]
for _ in range(256):SCORES.append(SCORES[-1]*106449//100000)


class Predictor:
    def __init__(self,model):
        if not isinstance(model,bytes) or len(model)!=MODEL_BYTES or model[:8]!=MAGIC:raise ValueError('Invalid fixed neural model')
        values=struct.unpack('<'+str(PARAMETERS)+'h',model[8:])
        self.embedding=values[:1028];self.w1=values[1028:1156];self.b1=values[1156:1164]
        self.w2=values[1164:3212];self.b2=values[3212:]

    def cdf(self,context):
        if len(context)!=4 or any(type(x) is not int or not 0<=x<=256 for x in context):raise ValueError('Invalid neural context')
        features=[self.embedding[x*4+k] for x in context for k in range(4)]
        hidden=[min(1<<24,max(0,sum(features[i]*self.w1[i*8+j] for i in range(16))//Q+self.b1[j])) for j in range(8)]
        scores=[]
        for j in range(256):
            logit=sum(hidden[i]*self.w2[i*256+j] for i in range(8))//Q+self.b2[j]
            bucket=(max(-8*Q,min(8*Q,logit))+8*Q)//16;scores.append(SCORES[bucket])
        total=sum(scores);frequencies=[1+x*(32768-256)//total for x in scores]
        remaining=32768-sum(frequencies)
        for i in range(remaining):frequencies[i]+=1
        c=[0]
        for value in frequencies:c.append(c[-1]+value)
        return c


def model_bytes(values):
    values=list(values)
    if len(values)!=PARAMETERS or any(type(v) is not int or not -32768<=v<=32767 for v in values):raise ValueError('Invalid neural parameters')
    return MAGIC+struct.pack('<'+str(PARAMETERS)+'h',*values)
