"""Explicit source/target byte identities; no association retraining or relabelling."""
import json
from rkv1.core import digest
from scripts.audit_supervised_expansion import validate
from scripts.supervised_expansion import ranking

class TransferRetriever:
    def __init__(self,source_base_raw,sidecar_raw,target_base_raw,*,source_base_sha256,sidecar_sha256,target_base_sha256):
        for raw,sha in ((source_base_raw,source_base_sha256),(sidecar_raw,sidecar_sha256),(target_base_raw,target_base_sha256)):
            if type(raw) is not bytes or type(sha) is not str or digest(raw)!=sha:raise ValueError('Explicit source/learned/target byte SHA differs')
        if source_base_sha256==target_base_sha256:raise ValueError('Transfer requires distinct explicitly named base models')
        source=json.loads(source_base_raw);sidecar=json.loads(sidecar_raw);target=json.loads(target_base_raw);audit=validate(source,sidecar)
        shared=target.get('shared')
        if type(shared) is not dict or type(shared.get('postings')) is not dict or type(shared.get('locators')) is not dict or type(shared.get('doc_lengths')) is not dict or shared.get('N')!=len(shared['doc_lengths']) or shared['N']<1 or shared.get('avgdl',0)<=0:raise ValueError('Target lexical index required')
        self._target=target;self._sidecar=sidecar;self._binding={'schema':'no-retraining-lexical-association-transfer-v1','source_base_sha256':source_base_sha256,'sidecar_sha256':sidecar_sha256,'target_base_sha256':target_base_sha256,'source_association_audit':audit,'source_associations_not_relabelled':True,'loaded_input_bytes':len(source_base_raw)+len(sidecar_raw)+len(target_base_raw)}
    def metadata(self):return json.loads(json.dumps(self._binding))
    def query(self,question,method):return ranking(self._target,self._sidecar,question,method)
