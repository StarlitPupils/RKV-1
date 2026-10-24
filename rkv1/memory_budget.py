"""Deterministic writer budgets for v3 replay, not a wall-clock latency limit."""
from bisect import bisect_right

DEFAULT_BUDGET={'version':1,'max_changes':32,'max_record_bytes':256<<10,'max_cas_bytes':2<<20}
MAXIMUMS={'max_changes':100000,'max_record_bytes':64<<20,'max_cas_bytes':1<<30}


def budget(value=None):
    value=DEFAULT_BUDGET.copy() if value is None else value
    if (type(value) is not dict or set(value)!=set(DEFAULT_BUDGET) or type(value['version']) is not int or value['version']!=1
            or any(type(value[name]) is not int or not 1<=value[name]<=limit for name,limit in MAXIMUMS.items())):
        raise ValueError('Invalid memory replay budget')
    return dict(value)


def range_work(snap,meta):
    """Charge each touched raw chunk per read, including repeated references."""
    _,path,offset,length,_,_=meta;entry=snap.files[path]
    if type(offset) is not int or type(length) is not int or offset<0 or length<0 or offset+length>entry['size']:
        raise ValueError('Invalid replay budget byte range')
    total=0
    if length:
        starts=snap.offsets[path];index=bisect_right(starts,offset)-1
        while index<len(entry['chunks']) and starts[index]<offset+length:
            total+=entry['chunks'][index]['size'];index+=1
    return total


def evaluate(memory,base,sid,prior,removed,upserted,limits):
    changes=len(removed)+len(upserted)
    result={'changes':changes,'record_reads':None,'record_bytes':None,'cas_bytes':None,'reason':None,'limits':limits}
    if changes>limits['max_changes']:result['reason']='changes';return result
    reads=[(base,prior[key]) for key in removed]
    for meta in upserted:
        old=prior.get(meta[0])
        if old and old[4]==meta[4]:continue
        if old:reads.append((base,old))
        reads.append((sid,meta))
    result['record_reads']=len(reads);result['record_bytes']=sum(meta[3] for _,meta in reads)
    if result['record_bytes']>limits['max_record_bytes']:result['reason']='record-bytes';return result
    if not reads:result['cas_bytes']=0;return result
    with memory.store.snapshot(base) as old, memory.store.snapshot(sid) as current:
        snapshots={base:old,sid:current}
        result['cas_bytes']=sum(range_work(snapshots[which],meta) for which,meta in reads)
    if result['cas_bytes']>limits['max_cas_bytes']:result['reason']='cas-bytes'
    return result
