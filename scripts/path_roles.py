"""Assessment-only exclusive CAS block-call attribution, no validation bypass."""
from contextlib import ExitStack,contextmanager
from unittest.mock import patch
import rkv1.memory_index as index_module
from scripts.cas_traffic import CASTraffic

ROLES=('manifest_validation','index_view','source_hit','other_trace')


class PathRoles:
    def __init__(self,memory):
        self.memory=memory;self.meter=CASTraffic(memory.store);self.events=[]
        self.role='other_trace';self.active=False

    @contextmanager
    def phase(self,name):
        before=self.role;self.role=name
        try:yield
        finally:self.role=before

    def __enter__(self):
        if self.active:raise RuntimeError('Role scope already active')
        self.active=True;self.stack=ExitStack()
        manifest=self.memory._manifest;hits=self.memory._verified_hits
        view=index_module.view;block=self.memory.store.block
        self.originals=(manifest,hits,view,block)
        def manifested(*args,**kwargs):
            with self.phase('manifest_validation'):return manifest(*args,**kwargs)
        def verified(*args,**kwargs):
            with self.phase('source_hit'):return hits(*args,**kwargs)
        @contextmanager
        def viewed(*args,**kwargs):
            with self.phase('index_view'):
                with view(*args,**kwargs) as db:yield db
        def blocked(key,expected_size):
            before=dict(self.meter.data);role=self.role;error=None;returned=None
            try:
                raw=block(key,expected_size);returned=len(raw);return raw
            except BaseException as exc:error=type(exc).__name__;raise
            finally:
                self.events.append({'index':len(self.events),'role':role,'block_id':key,
                    'expected_size':expected_size,'returned_bytes':returned,'error':error,
                    'traffic':{k:self.meter.data[k]-v for k,v in before.items()}})
        try:
            self.stack.enter_context(self.meter)
            self.stack.enter_context(patch.object(self.memory,'_manifest',manifested))
            self.stack.enter_context(patch.object(self.memory,'_verified_hits',verified))
            self.stack.enter_context(patch.object(index_module,'view',viewed))
            self.stack.enter_context(patch.object(self.memory.store,'block',blocked))
        except BaseException:
            self.stack.close();self.active=False;raise
        return self

    def __exit__(self,*args):
        try:return self.stack.__exit__(*args)
        finally:self.active=False;self.role='other_trace'

    def result(self):
        now=(self.memory._manifest,self.memory._verified_hits,index_module.view,self.memory.store.block)
        return {'events':self.events,'traffic':self.meter.result(),'final_role':self.role,
            'active':self.active,'methods_restored':not self.active and now==self.originals,
            'scope':'Exclusive role at original Store.block entry; heavy trace-only diagnostic, no cache or performance benefit claim'}
