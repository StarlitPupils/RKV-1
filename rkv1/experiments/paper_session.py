"""Bounded reader reuse with explicit immutable snapshot/model identities.

Every request hashes the current model file and performs normal selected CAS
verification. No implicit HEAD, decoded evidence cache, transport or answer.
"""
from collections import OrderedDict
from pathlib import Path
from rkv1.core import digest,valid_hash
from rkv1.experiments.paper_retriever import PaperRetriever,MAX_MODEL_BYTES


class PaperSession:
    def __init__(self,store_root,*,reader_capacity=2):
        if type(reader_capacity) is not int or not 0<=reader_capacity<=4:
            raise ValueError('Reader capacity must be an integer from0 to4')
        self.root=Path(store_root).resolve();self.capacity=reader_capacity
        self._readers=OrderedDict();self.closed=False
        self._counts={'requests':0,'hits':0,'misses':0,'evictions':0,'model_validation_return_B':0,'model_load_return_B':0,'model_loads':0,'failures':0}

    def query(self,question,*,snapshot_id,model_path,model_sha256,method='lexical',max_papers=12,source_byte_budget=4096):
        if self.closed:raise ValueError('Session is closed')
        if not isinstance(question,str) or not question.strip() or len(question)>4096 or '\x00' in question:
            raise ValueError('Explicit bounded question required')
        if not valid_hash(snapshot_id) or not valid_hash(model_sha256):raise ValueError('Explicit snapshot/model SHA required')
        if method not in ('lexical','graph','permuted_graph') or type(max_papers) is not int or not 1<=max_papers<=12 or type(source_byte_budget) is not int or not 0<=source_byte_budget<=4096:
            raise ValueError('Frozen retrieval method and bounded original record budgets required')
        self._counts['requests']+=1
        try:
            path=Path(model_path).resolve()
            with path.open('rb') as stream:raw=stream.read(MAX_MODEL_BYTES+1)
            self._counts['model_validation_return_B']+=len(raw)
            if len(raw)>MAX_MODEL_BYTES or digest(raw)!=model_sha256:raise ValueError('Current model file size or SHA differs')
            key=(snapshot_id,str(path),model_sha256)
            reader=self._readers.get(key)
            if reader is None:
                self._counts['misses']+=1
                reader=PaperRetriever(self.root,snapshot_id,path,model_sha256=model_sha256)
                self._counts['model_load_return_B']+=reader.model_info()['model_bytes']
                self._counts['model_loads']+=1
            else:self._counts['hits']+=1
            # Always reopen the explicit immutable snapshot and verify selected bytes.
            result=reader.query(question,method=method,max_papers=max_papers,source_byte_budget=source_byte_budget)
            if self.capacity:
                self._readers[key]=reader;self._readers.move_to_end(key)
                while len(self._readers)>self.capacity:
                    self._readers.popitem(last=False);self._counts['evictions']+=1
            return result
        except Exception:
            self._counts['failures']+=1
            raise

    def info(self):
        sizes=[r.model_info()['model_bytes'] for r in self._readers.values()]
        return {**self._counts,'reader_capacity':self.capacity,'retained_readers':len(sizes),
                'retained_model_payload_B':sum(sizes),'retained_python_objects_not_measured_by_payload':True,
                'max_retained_model_payload_B':self.capacity*MAX_MODEL_BYTES,'closed':self.closed,
                'model_file_validated_each_request':True,'selected_CAS_verified_each_request':True,
                'decoded_source_cache':False,'implicit_HEAD':False,'answer_or_entailment_verified':False}

    def close(self):
        self._readers.clear();self.closed=True

    def __enter__(self):
        if self.closed:raise ValueError('Session is closed')
        return self

    def __exit__(self,*args):self.close()
