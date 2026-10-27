"""Experimental: partial selection witnesses, global verdict always null."""
import copy
from contextlib import contextmanager
from rkv1.core import digest
from scripts.source_set_logic import SourceSetVerifier
from scripts.source_universe import VALID

SCOPE='Selected explicit axioms only; found witnesses do not assert full-source coverage or scientific truth'
FIELDS={'format','snapshot_id','selection','query','selected_closure_complete','work_used','work_budget','nodes','support_proof','refute_proof','support_evidence_found','opposite_evidence_found','global_verdict','scientific_entailment_verified','generated_answer','scope'}

def catalog(store,sid,paths,budget):
 if type(sid) is not str or not sid or type(paths) is not list or not 1<=len(paths)<=8 or any(type(p) is not str or not VALID.fullmatch(p) for p in paths) or len(set(paths))!=len(paths):raise ValueError('Pinned SID and one to eight unique selected paths required')
 if type(budget) is not int or not 0<=budget<=1048576:raise ValueError('Selected payload budget required')
 with store.snapshot(sid) as snap:
  universe=sorted(p for p in snap.files if p.endswith('.logic.jsonl'))
  if any(not VALID.fullmatch(p) for p in universe) or any(p not in universe for p in paths):raise ValueError('Malformed or missing eligible path')
  selected=sorted(paths);size=sum(snap.files[p]['size'] for p in selected)
  if size>budget:raise ValueError('Selected payload exceeds budget before any source read')
  return {'snapshot_id':sid,'eligible_paths':universe,'eligible_payload_bytes':sum(snap.files[p]['size'] for p in universe),'selected_paths':selected,'selected_payload_bytes':size,'source_byte_budget':budget,'full_eligible_selection':selected==universe}

class Projection:
 """Explicit internal selection domain; never handed to a caller as the real universe."""
 def __init__(self,store,paths):self.store=store;self.paths=paths
 @contextmanager
 def snapshot(self,sid):
  with self.store.snapshot(sid) as snap:
   paths=self.paths
   class Selected:
    files={p:snap.files[p] for p in paths}
    def read_range(self,path,*args,**kwargs):
     if path not in self.files:raise ValueError('Unselected source read forbidden')
     return snap.read_range(path,*args,**kwargs)
   yield Selected()

class Witness:
 def __init__(self,store,sid,paths,*,source_byte_budget=1048576):
  self.selection=catalog(store,sid,paths,source_byte_budget);self.sid=sid
  self.engine=SourceSetVerifier(Projection(store,self.selection['selected_paths']),sid,self.selection['selected_paths'],source_byte_budget=source_byte_budget)
 def infer(self,query,*,work_budget=10000):
  inner=self.engine.infer(query,work_budget=work_budget)
  c={k:copy.deepcopy(inner[k]) for k in ('query','work_used','work_budget','nodes','support_proof','refute_proof')}
  c.update(format='RKVSELECTWITNESS1',snapshot_id=self.sid,selection=copy.deepcopy(self.selection),selected_closure_complete=inner['complete'],support_evidence_found=inner['support_proof'] is not None,opposite_evidence_found=inner['refute_proof'] is not None,global_verdict=None,scientific_entailment_verified=False,generated_answer=None,scope=SCOPE)
  return c

