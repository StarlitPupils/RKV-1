"""Explicit v3 fixed-snapshot batch lookups; no method patching or block cache."""
import time
from .core import valid_hash

MAX_BATCH_KEYS=32
MAX_SOURCE_BUDGET=32<<20


def lookup_many(memory,keys,*,snapshot,max_source_bytes=1<<20):
    """Verify one request view, then every admitted original record occurrence.

    The byte budget covers admitted record lengths, including repeated keys.
    It does not bound CAS traffic, view construction or process RAM. Inputs are
    finite lists/tuples; no implicit HEAD fallback or streaming iterator.
    """
    started=time.perf_counter()
    if type(keys) not in (list,tuple) or not 1<=len(keys)<=MAX_BATCH_KEYS:
        raise ValueError('Batch requires 1 through 32 explicit keys')
    keys=tuple(keys)
    if any(not isinstance(k,str) or not 1<=len(k)<=512 or '\x00' in k for k in keys):
        raise ValueError('Invalid known-source key')
    if not isinstance(snapshot,str) or not valid_hash(snapshot):raise ValueError('Invalid fixed snapshot')
    if type(max_source_bytes) is not int or not 0<=max_source_bytes<=MAX_SOURCE_BUDGET:
        raise ValueError('Invalid batch source-byte budget')
    from .memory_index import QueryResources,view,LOCATORS
    admitted=0;groups=[]
    with QueryResources(memory) as resources:
        manifest=memory._manifest(snapshot,resources)
        if manifest['version']!=3:raise ValueError('Batch lookup requires a v3 manifest')
        with view(memory,manifest,query=resources) as db:
            db.execute('PRAGMA query_only=ON')
            for key in keys:
                rows=[(*r,None,None,None) for r in db.execute('SELECT '+LOCATORS+' FROM locators WHERE key=? LIMIT 2',
                    (key,))]
                if len(rows)>1:raise ValueError('Batch index key is not unique')
                admitted+=sum(int(r[3]) for r in rows)
                if admitted>max_source_bytes:raise ValueError('Batch source-byte budget exceeded')
                groups.append(rows)
            results=[{'source_key':key,'hits':memory._verified_hits(rows,snapshot,manifest,resources)}
                     for key,rows in zip(keys,groups)]
    return {'snapshot_id':snapshot,'scope':'explicit-known-source-batch','results':results,
            'admitted_source_bytes':admitted,'max_source_bytes':max_source_bytes,
            'max_keys':MAX_BATCH_KEYS,
            'consistency':'View verified at request entry; each selected original record reverified per occurrence',
            'wall_s':time.perf_counter()-started}
