"""Assessment-only fixed-SID v3 view, verified once per single trace scope."""
from contextlib import ExitStack
import sqlite3
import sys
import time
from unittest.mock import patch
from rkv1.core import valid_hash
from rkv1.memory_index import QueryResources,view,LOCATORS


def graph_bytes(roots):
    seen=set();pending=list(roots);total=0
    while pending:
        obj=pending.pop()
        if id(obj) in seen:continue
        seen.add(id(obj));total+=sys.getsizeof(obj)
        if isinstance(obj,dict):pending.extend(obj.keys());pending.extend(obj.values())
        elif isinstance(obj,(list,tuple,set)):pending.extend(obj)
    return total


class QueryView:
    def __init__(self,memory,snapshot):
        if not isinstance(snapshot,str) or not valid_hash(snapshot):raise ValueError('Invalid fixed snapshot')
        self.memory=memory;self.snapshot=snapshot;self.used=False;self.active=False
        self.data={'lookup_calls':0,'view_builds':0,'peak_sqlite_logical_page_bytes':0,
            'peak_metadata_graph_bytes':0,'peak_snapshots':0,'peak_deltas':0,
            'lookup_restored':None,'resources_cleared':None,'view_closed':None}

    def observe(self):
        r=self.resources;db=self.db
        pages=db.execute('PRAGMA page_count').fetchone()[0];size=db.execute('PRAGMA page_size').fetchone()[0]
        self.data['peak_sqlite_logical_page_bytes']=max(self.data['peak_sqlite_logical_page_bytes'],pages*size)
        roots=[self.manifest,r.deltas,r.snapshots]+[s.files for s in r.snapshots.values()]
        self.data['peak_metadata_graph_bytes']=max(self.data['peak_metadata_graph_bytes'],graph_bytes(roots))
        self.data['peak_snapshots']=max(self.data['peak_snapshots'],len(r.snapshots))
        self.data['peak_deltas']=max(self.data['peak_deltas'],len(r.deltas))

    def __enter__(self):
        if self.used:raise RuntimeError('Single-use view scope')
        self.used=True;self.stack=ExitStack();self.original=self.memory.lookup
        self.resources=None;self.db=None;self.manifest=None
        try:
            self.resources=self.stack.enter_context(QueryResources(self.memory))
            self.manifest=self.memory._manifest(self.snapshot,self.resources)
            if self.manifest['version']!=3:raise ValueError('Assessment view requires a v3 manifest')
            self.db=self.stack.enter_context(view(self.memory,self.manifest,query=self.resources));self.data['view_builds']=1
            self.db.execute('PRAGMA query_only=ON')
            self.data['view_storage']='in-memory-replay-copy' if self.manifest['deltas'] else 'read-only-base-connection'
            self.stack.enter_context(patch.object(self.memory,'lookup',self.lookup))
            self.active=True;self.observe();return self
        except BaseException:
            self.__exit__(*sys.exc_info());raise

    def lookup(self,key,*,snapshot=None):
        if not self.active:raise RuntimeError('View scope is not active')
        if snapshot!=self.snapshot:raise ValueError('View scope requires its explicit fixed SID')
        if not isinstance(key,str) or not 1<=len(key)<=512 or '\x00' in key:raise ValueError('Invalid known-source key')
        began=time.perf_counter();self.data['lookup_calls']+=1
        rows=[(*row,None,None,None) for row in self.db.execute('SELECT '+LOCATORS+' FROM locators WHERE key=?',(key,))]
        try:
            hits=self.memory._verified_hits(rows,self.snapshot,self.manifest,self.resources)
            return {'snapshot_id':self.snapshot,'source_key':key,'scope':'explicit-known-source','hits':hits,'wall_s':time.perf_counter()-began}
        finally:self.observe()

    def __exit__(self,*args):
        resources=self.resources;db=self.db
        try:return self.stack.__exit__(*args)
        finally:
            self.active=False;self.data['lookup_restored']=self.memory.lookup==self.original
            self.data['resources_cleared']=resources is None or (not resources.snapshots and not resources.deltas)
            if db is not None:
                try:db.execute('SELECT 1')
                except sqlite3.ProgrammingError:self.data['view_closed']=True
                else:self.data['view_closed']=False
            self.resources=None;self.db=None;self.manifest=None

    def result(self):
        return {**self.data,'active':self.active,
            'scope':'Single fixed-SID trace; full view validated on entry, selected original records reverified each lookup; no decoded block cache. Logical SQLite pages and Python metadata graph exclude allocator/native buffers/patch bookkeeping; not total RAM.'}
