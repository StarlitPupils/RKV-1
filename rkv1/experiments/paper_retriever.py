"""Experimental fixed-model paper evidence API; no answers or default integration."""
from collections import Counter,defaultdict
import copy
import json
import math
from pathlib import Path
import re
from rkv1.core import digest,valid_hash
from rkv1.memory import STOP,_json
from rkv1.store import Store

MAX_FACTS=12
SOURCE_BUDGET=4096
SEEDS=6
NEIGHBORS=6
K1=1.2
B=.75
MAX_MODEL_BYTES=32<<20
__all__=['PaperRetriever']

def tokens(text):return [t for t in re.findall('[a-z0-9]+',text.casefold()) if len(t)>1 and t not in STOP]

def lexical(shared,question):
    if not isinstance(question,str):raise ValueError('Only question text is a retrieval query')
    scores=defaultdict(float);N=shared['N'];avg=shared['avgdl']
    for token,qf in sorted(Counter(tokens(question)).items()):
        posting=shared['postings'].get(token,{})
        if not posting:continue
        idf=math.log(1+(N-len(posting)+.5)/(len(posting)+.5))
        for key,tf in sorted(posting.items()):
            scores[key]+=qf*idf*tf*(K1+1)/(tf+K1*(1-B+B*shared['doc_lengths'][key]/avg))
    return sorted(scores,key=lambda key:(-scores[key],key)),dict(scores)

def ranking(model,question,method):
    ordered,scores=lexical(model['shared'],question)
    if method=='lexical':return ordered
    if method not in ('graph','permuted_graph'):raise ValueError('Unknown method')
    graph=model[method];seeds=ordered[:SEEDS];neighbors=defaultdict(float)
    for seed in seeds:
        edges=graph.get(seed,{ });total=sum(edges.values())
        if total:
            for node,weight in sorted(edges.items()):
                if node not in seeds:neighbors[node]+=scores[seed]*weight/total
    expansion=sorted(neighbors,key=lambda node:(-neighbors[node],node))[:NEIGHBORS]
    return list(dict.fromkeys(seeds+expansion+ordered))

def admit(model,ranked,*,max_facts=MAX_FACTS,max_source_bytes=SOURCE_BUDGET):
    if type(max_facts) is not int or not 1<=max_facts<=MAX_FACTS:raise ValueError('Invalid fact-count admission budget')
    if type(max_source_bytes) is not int or not 0<=max_source_bytes<=SOURCE_BUDGET:raise ValueError('Invalid source-byte admission budget')
    selected=[];seen=set();used=0
    for key in ranked:
        if key in seen:continue
        seen.add(key);length=model['shared']['locators'][key]['length']
        if used+length>max_source_bytes:continue
        selected.append(key);used+=length
        if len(selected)==max_facts:break
    return selected,used


def _pairs(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate model JSON key')
        value[key]=item
    return value

def _invalid_constant(value):raise ValueError('Nonfinite model JSON value')

def _validate(model):
    if type(model) is not dict or set(model)!={'shared','graph','permuted_graph'}:raise ValueError('Unsupported paper model schema')
    shared=model['shared']
    if type(shared) is not dict or shared.get('source_kind')!='scifact-whole-original-record-v1':raise ValueError('Unsupported source kind')
    if shared.get('parameters')!={'k1':1.2,'b':.75,'max_facts':12,'source_budget':4096,'seeds':6,'neighbors':6}:raise ValueError('Unsupported frozen parameters')
    if not valid_hash(shared.get('source_sha256')):raise ValueError('Invalid model source identity')
    locators=shared.get('locators');lengths=shared.get('doc_lengths');postings=shared.get('postings');n=shared.get('N');avg=shared.get('avgdl')
    if type(n) is not int or not 1<=n<=100000 or type(locators) is not dict or len(locators)!=n or type(lengths) is not dict or set(lengths)!=set(locators) or type(postings) is not dict:raise ValueError('Invalid model index shape')
    if any(not isinstance(key,str) or re.fullmatch(r'doc:[0-9]+',key) is None for key in locators):raise ValueError('Invalid paper identity')
    for loc in locators.values():
        if type(loc) is not dict or set(loc)!={'offset','length','sha256'} or type(loc['offset']) is not int or type(loc['length']) is not int or loc['offset']<0 or not 1<=loc['length']<=1<<20 or not valid_hash(loc['sha256']):raise ValueError('Invalid original paper locator')
    known_ids=set(locators);previous=0
    for loc in sorted(locators.values(),key=lambda item:item['offset']):
        if loc['offset']<previous:raise ValueError('Overlapping original paper locators')
        previous=loc['offset']+loc['length']
    if any(type(length) is not int or length<0 for length in lengths.values()) or type(avg) not in (int,float) or not math.isfinite(avg) or avg<=0 or avg!=sum(lengths.values())/n:raise ValueError('Invalid index token lengths')
    totals=Counter()
    for token,posting in postings.items():
        if not isinstance(token,str) or tokens(token)!=[token] or type(posting) is not dict or not posting or not set(posting)<=known_ids or any(type(tf) is not int or tf<1 for tf in posting.values()):raise ValueError('Invalid model token posting')
        totals.update(posting)
    if any(totals[key]!=length for key,length in lengths.items()):raise ValueError('Posting/token length mismatch')
    degrees=[]
    for name in ('graph','permuted_graph'):
        graph=model[name]
        if type(graph) is not dict or not set(graph)<=known_ids:raise ValueError('Invalid model graph')
        for key,edges in graph.items():
            if type(edges) is not dict or not edges or key in edges or not set(edges)<=set(graph) or any(type(weight) is not int or weight<1 for weight in edges.values()):raise ValueError('Invalid graph edge')
        if any(graph[other].get(key)!=weight for key,edges in graph.items() for other,weight in edges.items()):raise ValueError('Invalid symmetric graph edge')
        degrees.append(sorted((len(edges),sum(edges.values())) for edges in graph.values()))
    if degrees[0]!=degrees[1]:raise ValueError('Control graph degree mismatch')


class PaperRetriever:
    """Load one explicitly trusted model and pin an immutable scientific snapshot.

    Model path/SHA and SID are caller choices, never inferred from HEAD.
    Returned text is original local evidence; source identity is not entailment.
    """
    def __init__(self,store_root,snapshot_id,model_path,*,model_sha256):
        if not valid_hash(snapshot_id) or not valid_hash(model_sha256):raise ValueError('Explicit snapshot and model SHA required')
        with Path(model_path).open('rb') as stream:raw=stream.read(MAX_MODEL_BYTES+1)
        if len(raw)>MAX_MODEL_BYTES or digest(raw)!=model_sha256:raise ValueError('Model size or SHA differs')
        model=json.loads(raw,object_pairs_hook=_pairs,parse_constant=_invalid_constant);_validate(model)
        self._model=model;self._store=Store(store_root,io_backend='bounded');self._sid=snapshot_id;self._model_sha=model_sha256;self._model_bytes=len(raw)
        with self._store.snapshot(self._sid) as snapshot:self._source(snapshot)

    def _source(self,snapshot):
        entry=snapshot.files.get('corpus.jsonl')
        if entry is None or entry['sha256']!=self._model['shared']['source_sha256'] or any(loc['offset']+loc['length']>entry['size'] for loc in self._model['shared']['locators'].values()):raise ValueError('Pinned source and model differ')
        return entry

    def model_info(self):
        return {'snapshot_id':self._sid,'model_sha256':self._model_sha,'model_bytes':self._model_bytes,'source_sha256':self._model['shared']['source_sha256'],
            'paper_count':self._model['shared']['N'],'parameters':copy.deepcopy(self._model['shared']['parameters']),
            'scope':'Experimental original-paper evidence retrieval; no answer or entailment verification'}

    def query(self,claim,*,method='lexical',max_papers=12,source_byte_budget=4096):
        if not isinstance(claim,str) or not 1<=len(claim)<=4096 or not claim.strip() or '\x00' in claim:raise ValueError('Invalid claim text')
        if method not in ('lexical','graph','permuted_graph'):raise ValueError('Unknown retrieval method')
        # Validate budgets before ranking/Store I/O, including bool-vs-int.
        admit(self._model,[],max_facts=max_papers,max_source_bytes=source_byte_budget)
        ordered=ranking(self._model,claim,method);selected,used=admit(self._model,ordered,max_facts=max_papers,max_source_bytes=source_byte_budget)
        hits=[]
        with self._store.snapshot(self._sid) as snapshot:
            self._source(snapshot)
            for key in selected:
                loc=self._model['shared']['locators'][key];raw=snapshot.read_range('corpus.jsonl',loc['offset'],loc['length'])
                if digest(raw)!=loc['sha256']:raise ValueError('Original paper SHA differs')
                obj=json.loads(raw)
                if 'doc:'+str(obj.get('doc_id'))!=key or not isinstance(obj.get('title'),str) or type(obj.get('abstract')) is not list or any(not isinstance(s,str) for s in obj['abstract']):raise ValueError('Original paper identity or schema differs')
                hits.append({'paper_id':key,'title':obj['title'],'abstract':list(obj['abstract']),
                    'locator':{'snapshot_id':self._sid,'path':'corpus.jsonl',**loc},
                    'title_sha256':digest(obj['title'].encode('utf-8')),'abstract_sha256':digest(_json(obj['abstract']))})
        return {'method':method,'snapshot_id':self._sid,'model_sha256':self._model_sha,'source_sha256':self._model['shared']['source_sha256'],
            'selected_ids':selected,'admitted_record_bytes':used,'max_papers':max_papers,'source_byte_budget':source_byte_budget,
            'hits':hits,'selected_source_identity_verified':True,'scientific_entailment_verified':False,'generated_answer':None}
