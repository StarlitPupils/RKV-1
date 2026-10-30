"""Independent source-only audit index built once, never candidate postings."""
from collections import Counter
import hashlib,json,math,re
from rkv1.memory import STOP
from scripts.audit_evidence_view_packet import check,encode


class ReferenceIndex:
    def __init__(self,source,*,expected_source_sha256):
        if type(source) is not bytes or hashlib.sha256(source).hexdigest()!=expected_source_sha256:
            raise ValueError('Original source identity differs')
        self.source=source;self.sha=expected_source_sha256
        self.raws={};self.by_offset={};self.postings={};self.lengths={}
        def pairs(items):
            out={}
            for k,v in items:
                if k in out:raise ValueError('Duplicate original JSON member')
                out[k]=v
            return out
        offset=0
        # One physical JSONL boundary pass; record slices stay tied to full source SHA.
        for line in source.split(b'\n'):
            length=len(line)+(1 if offset+len(line)<len(source) else 0)
            raw=source[offset:offset+length]
            if not raw:continue
            obj=json.loads(raw,object_pairs_hook=pairs)
            if type(obj) is not dict or type(obj.get('title')) is not str or type(obj.get('abstract')) is not list or any(type(v) is not str for v in obj['abstract']):
                raise ValueError('Invalid original paper source')
            key='doc:'+str(obj.get('doc_id'))
            if re.fullmatch('doc:[0-9]+',key) is None or key in self.raws:
                raise ValueError('Invalid or duplicate original paper ID')
            terms=Counter(self.tokenize('\n'.join([obj['title'],*obj['abstract']])))
            self.lengths[key]=sum(terms.values());self.raws[key]=(offset,length,hashlib.sha256(raw).hexdigest(),raw)
            self.by_offset[(offset,length)]=raw
            for term,n in terms.items():self.postings.setdefault(term,{})[key]=n
            offset+=length
        if not self.raws or offset!=len(source) or sum(self.lengths.values())==0:
            raise ValueError('Empty or malformed source index')
        self.n=len(self.raws);self.average=sum(self.lengths.values())/self.n

    @staticmethod
    def tokenize(text):return [w for w in re.findall('[a-z0-9]+',text.casefold()) if len(w)>1 and w not in STOP]

    def rank(self,question):
        query=Counter(self.tokenize(question));scores={}
        for term in sorted(query):
            posting=self.postings.get(term,{})
            if not posting:continue
            idf=math.log(1+(self.n-len(posting)+.5)/(len(posting)+.5))
            for key in sorted(posting):
                tf=posting[key]
                increment=query[term]*idf*tf*2.2/(tf+1.2*(.25+.75*self.lengths[key]/self.average))
                scores[key]=scores.get(key,0)+increment
        return sorted(scores,key=lambda key:(-scores[key],key))[:12]

    def records(self,keys,sid):
        return [{'id':k,'binding':{'snapshot_id':sid,'path':'corpus.jsonl','source_sha256':self.sha,
                  'record_offset':self.raws[k][0],'record_length':self.raws[k][1],'record_sha256':self.raws[k][2],'field':'abstract'}} for k in keys]

    def resolve(self,binding):
        if binding['source_sha256']!=self.sha or binding['path']!='corpus.jsonl' or binding['field']!='abstract':
            raise ValueError('Original source context differs')
        if type(binding['record_offset']) is not int or type(binding['record_length']) is not int:
            raise ValueError('Invalid record boundary type')
        key=(binding['record_offset'],binding['record_length'])
        if key not in self.by_offset:raise ValueError('Not an original complete JSONL record')
        raw=self.by_offset[key]
        if hashlib.sha256(raw).hexdigest()!=binding['record_sha256']:raise ValueError('Record identity differs')
        return raw

    def verify_prediction(self,row,method,*,expected_sid):
        result=row['result'];ordered=self.rank(row['question'])
        if ordered!=result['ordered_candidate_ids']:raise ValueError('Independent source lexical ranking differs')
        records=self.records(ordered,expected_sid)
        if encode(records)!=encode(result['trusted_records']):raise ValueError('Original source record bindings differ')
        encoded=bytes.fromhex(result['view']['encoded_hex'])
        if not records:
            packet={'header':{'snapshot_id':expected_sid,'path':'corpus.jsonl','source_sha256':self.sha,'view_schema':'original-evidence-draft-1','question':row['question']},'items':[]}
            if encoded!=encode(packet):raise ValueError('Empty query lost original source anchor')
            return {}
        return check(self.source,row['question'],records,method,encoded,20000,record_resolver=self.resolve)
