"""Independent 32-bit integer arithmetic coding with positive integer CDFs."""
from bisect import bisect_right

TOP=(1<<32)-1
HALF=1<<31
QUARTER=1<<30
TOTAL=32768


def _cdf(value):
    if len(value)!=257 or any(type(x) is not int for x in value) or value[0]!=0 or value[-1]!=TOTAL or any(a>=b for a,b in zip(value,value[1:])):
        raise ValueError('Invalid arithmetic CDF')


def encode(raw,predict):
    low=0;high=TOP;pending=0;output=bytearray();bits=0;byte=0;used=0;context=[256]*4
    def emit(bit):
        nonlocal bits,byte,used
        byte=(byte<<1)|bit;used+=1;bits+=1
        if used==8:output.append(byte);byte=0;used=0
    def resolved(bit):
        nonlocal pending
        emit(bit)
        for _ in range(pending):emit(1-bit)
        pending=0
    for symbol in raw:
        c=predict(context);_cdf(c);width=high-low+1
        high=low+width*c[symbol+1]//TOTAL-1;low=low+width*c[symbol]//TOTAL
        while True:
            if high<HALF:resolved(0)
            elif low>=HALF:resolved(1);low-=HALF;high-=HALF
            elif low>=QUARTER and high<3*QUARTER:pending+=1;low-=QUARTER;high-=QUARTER
            else:break
            low=low*2;high=high*2+1
        context=context[1:]+[symbol]
    pending+=1;resolved(0 if low<QUARTER else 1)
    if used:output.append(byte<<(8-used))
    return bytes(output),bits


def decode(payload,bit_length,length,predict):
    if (type(bit_length) is not int or type(length) is not int or not 0<=length<=1<<20
            or not 2<=bit_length<=16*length+64 or len(payload)!=(bit_length+7)//8):raise ValueError('Invalid arithmetic lengths')
    if bit_length%8 and payload[-1]&((1<<(8-bit_length%8))-1):raise ValueError('Nonzero arithmetic padding')
    position=0
    def bit():
        nonlocal position
        pos=position;position+=1
        if pos>=bit_length:
            if position-bit_length>32:raise ValueError('Arithmetic stream exhausted')
            return 0
        return (payload[pos//8]>>(7-pos%8))&1
    low=0;high=TOP;code=0;context=[256]*4;result=bytearray()
    for _ in range(32):code=(code<<1)|bit()
    for _ in range(length):
        c=predict(context);_cdf(c);width=high-low+1;value=((code-low+1)*TOTAL-1)//width
        symbol=bisect_right(c,value)-1
        if not 0<=symbol<256:raise ValueError('Arithmetic symbol outside alphabet')
        high=low+width*c[symbol+1]//TOTAL-1;low=low+width*c[symbol]//TOTAL
        while True:
            if high<HALF:pass
            elif low>=HALF:low-=HALF;high-=HALF;code-=HALF
            elif low>=QUARTER and high<3*QUARTER:low-=QUARTER;high-=QUARTER;code-=QUARTER
            else:break
            low*=2;high=high*2+1;code=(code*2)+bit()
        result.append(symbol);context=context[1:]+[symbol]
    return bytes(result)
